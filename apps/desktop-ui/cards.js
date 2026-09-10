// Adapted from Nikke-Local-Lab c05fc1c392a523b9e17ebe0cbd4811bed9c19adb editor.js.
// Card DOM, icon rails, growth strip and filters retained; account adapter lives in app.js.
import { bindCardGesture } from './card-gesture.js';
const byId=id=>document.getElementById(id);
const value=id=>byId(id).value.trim();
let state,effectiveProfileValue,configuredCharacterLevel,openNikkeDetail,isSelecting,isChosen,selectCharacter;
export function connectRenderer(context){({state,effectiveProfileValue,configuredCharacterLevel,openNikkeDetail,isSelecting=()=>false,isChosen=()=>false,selectCharacter}=context);}
const uiAssetRoot='/editor/assets/ui';
const manufacturerLabels = Object.freeze({
  elysion: "엘리시온", missilis: "미실리스", tetra: "테트라",
  pilgrim: "필그림", abnormal: "어브노멀"
});
const classLabels = Object.freeze({ attacker: "화력형", defender: "방어형", supporter: "지원형" });
const weaponLabels = Object.freeze({
  assault_rifle: "소총", machine_gun: "머신건", rocket_launcher: "런처",
  shotgun: "샷건", sniper_rifle: "저격소총", submachine_gun: "기관단총"
});
const weaponShortLabels = Object.freeze({
  assault_rifle: "AR", machine_gun: "MG", rocket_launcher: "RL",
  shotgun: "SG", sniper_rifle: "SR", submachine_gun: "SMG"
});
const elementLabels = Object.freeze({
  fire: "작열", water: "수냉", wind: "풍압", electric: "전격", iron: "철갑"
});
const elementGlyphs = Object.freeze({
  fire: "◆", water: "⬟", wind: "⬢", electric: "✦", iron: "◇"
});

const elementAssetNames = Object.freeze({
  fire: "fire", water: "water", wind: "wind", electric: "electric", iron: "iron"
});
const weaponAssetNames = Object.freeze({
  assault_rifle: "assault_rifle", machine_gun: "machine_gun",
  rocket_launcher: "rocket_launcher", shotgun: "shotgun",
  sniper_rifle: "sniper_rifle", submachine_gun: "submachine_gun"
});
const burstAssetCodes = Object.freeze({ 1: "1", 2: "2", 3: "3", 5: "p" });
const burstDisplayLabels = Object.freeze({ 1: "Ⅰ", 2: "Ⅱ", 3: "Ⅲ", 5: "P" });
export function appendPortrait(container, portraitPath, displayName, lazy = false) {
  let image = null;
  const fallback = () => {
    image?.remove();
    if (container.querySelector(":scope > .portrait-fallback")) return;
    const initial = document.createElement("span");
    initial.className = "portrait-fallback";
    initial.textContent = (displayName || "N").slice(0, 1);
    container.prepend(initial);
  };
  if (!portraitPath) {
    fallback();
    return;
  }
  image = document.createElement("img");
  image.src = portraitPath;
  image.alt = "";
  if (lazy) image.loading = "lazy";
  image.addEventListener("error", fallback, { once: true });
  container.appendChild(image);
}
function appendPresentationImage(container, path, className, alt, fallbackText = "?") {
  const image = document.createElement("img");
  image.className = className;
  image.src = path;
  image.alt = alt || "";
  image.loading = "lazy";
  image.addEventListener("error", () => {
    image.remove();
    if (!fallbackText) return;
    const fallback = document.createElement("span");
    fallback.className = `${className} presentation-image-fallback`;
    fallback.textContent = fallbackText;
    container.appendChild(fallback);
  }, { once: true });
  container.appendChild(image);
  return image;
}
function burstLabel(step) { return burstDisplayLabels[step] || "-"; }
function burstAssetPath(step) {
  const code = burstAssetCodes[step];
  return code ? `${uiAssetRoot}/burst-${code}.png` : null;
}
export function renderNikkeCards(subjects = null, ownedSubjects = null) {
  const target = byId("nikke-card-list");
  const profileOwnedSubjects = ownedSubjects || new Set((state.currentProfile?.values || [])
    .filter((item) => item.fieldCode === "character_level" && item.subjectUid)
    .map((item) => item.subjectUid));
  const allSubjects = subjects || (state.presentation.characters || [])
    .map((item) => item.characterUid);
  const query = value("nikke-search").toLocaleLowerCase("ko-KR");
  const burst = value("nikke-filter-burst");
  const manufacturer = value("nikke-filter-manufacturer");
  const combatClass = value("nikke-filter-class");
  const element = value("nikke-filter-element");
  const visible = allSubjects.filter((subjectUid) => {
    const item = state.presentationByCharacter.get(subjectUid);
    const name = item?.displayName || "이름 미확인 니케";
    return (!query || name.toLocaleLowerCase("ko-KR").includes(query)) &&
      (burst === "all" || String(item?.burstStep) === burst || item?.burstStep === 5) &&
      (manufacturer === "all" || item?.manufacturerCode === manufacturer) &&
      (combatClass === "all" || item?.combatClassCode === combatClass) &&
      (element === "all" || item?.elementCode === element);
  }).sort((left, right) => {
    const leftOwned = profileOwnedSubjects.has(left);
    const rightOwned = profileOwnedSubjects.has(right);
    if (leftOwned !== rightOwned) return rightOwned ? 1 : -1;
    const leftPowerKnown = state.combatPowerByCharacter.has(left);
    const rightPowerKnown = state.combatPowerByCharacter.has(right);
    if (leftPowerKnown !== rightPowerKnown) return rightPowerKnown ? 1 : -1;
    const powerOrder = (state.combatPowerByCharacter.get(right) ?? 0) -
      (state.combatPowerByCharacter.get(left) ?? 0);
    if (powerOrder !== 0) return powerOrder;
    const leftName = state.presentationByCharacter.get(left)?.displayName || "";
    const rightName = state.presentationByCharacter.get(right)?.displayName || "";
    return leftName.localeCompare(rightName, "ko");
  });
  target.replaceChildren();
  const visibleOwnedCount = visible.filter((subjectUid) =>
    profileOwnedSubjects.has(subjectUid)).length;
  byId("nikke-count").textContent =
    `보유 ${visibleOwnedCount} / 전체 ${visible.length}`;
  for (const subjectUid of visible) {
    const item = state.presentationByCharacter.get(subjectUid) || {};
    const isOwned = profileOwnedSubjects.has(subjectUid);
    const card = document.createElement("button");
    card.type = "button";
    card.className = "nikke-card";
    card.classList.toggle("nikke-card-unowned", !isOwned);
    card.dataset.characterUid = subjectUid;
    card.dataset.owned = String(isOwned);
    card.dataset.rarity = item.rarityCode || "unknown";
    card.setAttribute("aria-current", String(state.selectedNikkeUid === subjectUid));
    if (isSelecting()) {
      card.setAttribute('aria-pressed', String(isChosen(subjectUid)));
      card.classList.add('formation-choice');
      card.title = '클릭: 편성 · 1초 누르기 / Alt+Enter: 상세';
    }
    const portrait = document.createElement("span");
    portrait.className = "nikke-portrait";
    appendPortrait(portrait, item.portraitPath, item.displayName, true);
    const iconRail = document.createElement("span");
    iconRail.className = "nikke-icon-rail";
    const iconDefinitions = [
      {
        kind: "element",
        label: elementLabels[item.elementCode] || "속성 미확인",
        path: elementAssetNames[item.elementCode]
          ? `${uiAssetRoot}/code-${elementAssetNames[item.elementCode]}.png`
          : null,
        fallback: elementGlyphs[item.elementCode] || "?"
      },
      {
        kind: "weapon",
        label: weaponLabels[item.weaponCode] || "무기군 미확인",
        path: weaponAssetNames[item.weaponCode]
          ? `${uiAssetRoot}/weapon-${weaponAssetNames[item.weaponCode]}.png`
          : null,
        fallback: weaponShortLabels[item.weaponCode] || "?"
      },
      {
        kind: "burst",
        label: item.burstStep ? `버스트 ${burstLabel(item.burstStep)}` : "버스트 미확인",
        path: burstAssetPath(item.burstStep),
        fallback: burstLabel(item.burstStep)
      }
    ];
    for (const icon of iconDefinitions) {
      const badge = document.createElement("span");
      badge.className = icon.kind;
      badge.title = icon.label;
      badge.setAttribute("aria-label", icon.label);
      if (icon.path) appendPresentationImage(badge, icon.path, "card-system-icon", "", icon.fallback);
      else badge.textContent = icon.fallback;
      iconRail.appendChild(badge);
    }
    portrait.appendChild(iconRail);
    if (!isOwned) {
      const unowned = document.createElement("span");
      unowned.className = "nikke-unowned-badge";
      unowned.textContent = "미보유";
      portrait.appendChild(unowned);
    }
    const body = document.createElement("span");
    body.className = "nikke-card-body";
    const identity = document.createElement("span");
    identity.className = "nikke-card-identity";
    const name = document.createElement("strong");
    name.textContent = item.displayName || "이름 미확인 니케";
    const level = isOwned ? configuredCharacterLevel(subjectUid) : null;
    const levelBadge = document.createElement("span");
    levelBadge.className = "nikke-level";
    const levelCaption = document.createElement("small");
    levelCaption.textContent = "LV.";
    const levelValue = document.createElement("b");
    levelValue.textContent = level == null ? "미보유" : String(level);
    levelBadge.append(levelCaption, levelValue);
    const storedLimit = effectiveProfileValue("limit_break", subjectUid)?.integerValue;
    const core = effectiveProfileValue("core_level", subjectUid)?.integerValue;
    const limit = core > 0 ? 3 : Math.max(0, Math.min(3, storedLimit));
    const limitStrip = document.createElement("span");
    limitStrip.className = "limit-strip";
    for (let index = 0; index < 3; index++) {
      appendPresentationImage(
        limitStrip,
        `${uiAssetRoot}/star-${index < limit ? "filled" : "empty"}.png`,
        "limit-star",
        "",
        index < limit ? "★" : "☆");
    }
    if (core >= 1) {
      const evolve = document.createElement("span");
      evolve.className = "core-evolve";
      evolve.style.backgroundImage = `url('${uiAssetRoot}/evolve.png')`;
      evolve.textContent = core >= 7 ? "MAX" : String(core);
      limitStrip.appendChild(evolve);
    }
    const job = document.createElement("img");
    job.className = "nikke-job-mark";
    job.src = `${uiAssetRoot}/job-${item.combatClassCode || "attacker"}.png`;
    job.alt = "";
    job.addEventListener("error", () => job.remove(), { once: true });
    if (storedLimit == null || core == null || !isOwned) { limitStrip.replaceChildren(); limitStrip.textContent = isOwned ? "성장 미확인" : ""; }
    body.appendChild(job);
    identity.append(limitStrip, name);
    body.append(levelBadge, identity);
    card.append(portrait, body);
    bindCardGesture(card, { isSelecting, select: () => selectCharacter(subjectUid), detail: () => {
      state.selectedNikkeUid = subjectUid;
      byId("nikke-subject").value = subjectUid;
      openNikkeDetail(subjectUid);
    }});
    target.appendChild(card);
  }
  if (visible.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "조건에 맞는 니케가 없습니다.";
    target.appendChild(empty);
  }
}

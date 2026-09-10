// Renderer functions copied verbatim from Nikke-Local-Lab c05fc1c editor.js.
// Snapshot projection and edit operations live in local-lab-adapter.js.
import { state, effectiveProfileValue, configuredSynchroLevel, queueIntegerValue,
  queueControlledValue, queueReferenceValue, queueExactValue, upsertProfileOperations,
  renderNikkeDetail, renderEditOperations } from "./local-lab-adapter.js";
const byId=id=>document.getElementById(id);
const uiAssetRoot="/editor/assets/ui";
const manufacturerLabels = Object.freeze({
  elysion: "엘리시온", missilis: "미실리스", tetra: "테트라",
  pilgrim: "필그림", abnormal: "어브노멀"
});
const classLabels = Object.freeze({ attacker: "화력형", defender: "방어형", supporter: "지원형" });
const weaponLabels = Object.freeze({
  assault_rifle: "소총", machine_gun: "머신건", rocket_launcher: "런처",
  shotgun: "샷건", sniper_rifle: "저격소총", submachine_gun: "기관단총"
});
const elementLabels = Object.freeze({
  fire: "작열", water: "수냉", wind: "풍압", electric: "전격", iron: "철갑"
});
const burstDisplayLabels = Object.freeze({ 1: "Ⅰ", 2: "Ⅱ", 3: "Ⅲ", 5: "P" });
const equipmentSlotLabels = Object.freeze({
  head: "머리", torso: "몸통", arms: "팔", legs: "다리"
});

function appendPortrait(container, portraitPath, displayName, lazy = false) {
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

function exactValueText(projection, unitLabel = null) {
  if (!projection || projection.unscaledValue == null) return "-";
  const scale = projection.decimalScale || 0;
  const ratioMultiplier = unitLabel === "%" ? 100 : 1;
  const fractionDigits = unitLabel === "%" ? Math.max(0, scale - 2) : scale;
  return (projection.unscaledValue / (10 ** scale) * ratioMultiplier).toLocaleString("ko-KR", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits
  });
}

function enhancedEquipmentStatText(stat, enhancementLevel, basisPointsPerLevel) {
  const fallback = String(stat?.value ?? "미확인");
  const parsedFallback = Number(fallback.replaceAll(",", ""));
  const baseValue = Number(stat?.baseValue ?? parsedFallback);
  const level = Number(enhancementLevel);
  const rate = Number(basisPointsPerLevel);
  if (!Number.isSafeInteger(baseValue) || baseValue < 0 ||
      !Number.isSafeInteger(level) || level < 0 ||
      !Number.isSafeInteger(rate) || rate < 0) {
    return fallback;
  }
  const numerator = baseValue * (10_000 + level * rate);
  if (!Number.isSafeInteger(numerator)) return fallback;
  // All equipment stats are non-negative. Adding half the denominator before
  // integer division reproduces the client's nearest-integer rounding.
  return Math.floor((numerator + 5_000) / 10_000).toLocaleString("ko-KR");
}

function numericEditor(labelText, fieldCode, subjectUid, minimum = 0, maximum = null) {
  const label = document.createElement("label");
  label.textContent = labelText;
  const input = document.createElement("input");
  input.type = "number";
  input.required = true;
  input.min = String(minimum);
  if (maximum != null) input.max = String(maximum);
  input.value = String(effectiveProfileValue(fieldCode, subjectUid)?.integerValue ?? minimum);
  input.addEventListener("change", () => {
    if (!input.reportValidity()) return;
    queueIntegerValue(fieldCode, subjectUid, input.value, minimum);
    renderNikkeDetail(subjectUid);
  });
  label.appendChild(input);
  return label;
}

function synchronizedLevelEditor(subjectUid) {
  const label = document.createElement("label");
  label.textContent = "레벨 (싱크로 적용)";
  const input = document.createElement("input");
  input.type = "number";
  input.value = String(configuredSynchroLevel());
  input.disabled = true;
  label.appendChild(input);
  return label;
}

function limitBreakEditor(subjectUid) {
  const group = document.createElement("div");
  group.className = "growth-visual-field limit-break-editor";
  const label = document.createElement("span");
  label.textContent = "돌파";
  const stars = document.createElement("div");
  stars.className = "growth-stars";
  const current = effectiveProfileValue("limit_break", subjectUid)?.integerValue ?? 0;
  const currentCore = effectiveProfileValue("core_level", subjectUid)?.integerValue ?? 0;
  for (let index = 1; index <= 3; index++) {
    const button = document.createElement("button");
    button.type = "button";
    button.title = `${index}돌파`;
    button.setAttribute("aria-pressed", String(index <= current));
    appendPresentationImage(
      button,
      `${uiAssetRoot}/star-${index <= current ? "filled" : "empty"}.png`,
      "growth-star-image",
      `${index}번째 돌파`,
      index <= current ? "★" : "☆");
    button.addEventListener("click", () => {
      const nextLimit = index === current && currentCore === 0 ? 0 : index;
      upsertProfileOperations([
        {
          fieldCode: "limit_break", subjectUid, valueKind: "integer",
          integerValue: nextLimit, booleanValue: null, referenceUid: null,
          unscaledValue: null, decimalScale: null, controlledValue: null
        },
        {
          fieldCode: "core_level", subjectUid, valueKind: "integer",
          integerValue: 0, booleanValue: null, referenceUid: null,
          unscaledValue: null, decimalScale: null, controlledValue: null
        }
      ]);
      renderNikkeDetail(subjectUid);
    });
    stars.appendChild(button);
  }
  group.append(label, stars);
  return group;
}

function coreBreakEditor(subjectUid) {
  const group = document.createElement("div");
  group.className = "growth-visual-field core-break-editor";
  const label = document.createElement("span");
  label.textContent = "코어 강화";
  const control = document.createElement("div");
  control.className = "core-stepper";
  const currentLimit = Math.max(0, Math.min(3,
    effectiveProfileValue("limit_break", subjectUid)?.integerValue ?? 0));
  const currentCore = Math.max(0, Math.min(7,
    effectiveProfileValue("core_level", subjectUid)?.integerValue ?? 0));
  const currentProgress = Math.min(10,
    currentCore > 0 ? 3 + currentCore : currentLimit);
  const badge = document.createElement("span");
  badge.className = "core-evolve detail-core-evolve";
  badge.style.backgroundImage = `url('${uiAssetRoot}/evolve.png')`;
  badge.textContent = currentCore >= 7 ? "MAX" : String(currentCore);
  for (const [caption, delta] of [["−", -1], ["+", 1]]) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = caption;
    button.disabled = delta < 0 ? currentProgress <= 0 : currentProgress >= 10;
    button.addEventListener("click", () => {
      const nextProgress = Math.max(0, Math.min(10, currentProgress + delta));
      const nextLimit = Math.min(3, nextProgress);
      const nextCore = Math.max(0, nextProgress - 3);
      upsertProfileOperations([
        {
          fieldCode: "limit_break", subjectUid, valueKind: "integer",
          integerValue: nextLimit, booleanValue: null, referenceUid: null,
          unscaledValue: null, decimalScale: null, controlledValue: null
        },
        {
          fieldCode: "core_level", subjectUid, valueKind: "integer",
          integerValue: nextCore, booleanValue: null, referenceUid: null,
          unscaledValue: null, decimalScale: null, controlledValue: null
        }
      ]);
      renderNikkeDetail(subjectUid);
    });
    control.appendChild(button);
    if (delta < 0) control.appendChild(badge);
  }
  group.append(label, control);
  return group;
}

function renderEquipmentDetail(subjectUid) {
  const summary = byId("equipment-summary");
  summary.replaceChildren();
  const title = document.createElement("strong");
  title.className = "equipment-summary-title";
  title.textContent = "장비 효과 보기";
  const totalGrid = document.createElement("div");
  totalGrid.className = "equipment-total-grid";
  const totals = collectEquipmentOverloadTotals(subjectUid);
  for (const total of totals) {
    const row = document.createElement("div");
    row.className = "equipment-total-row";
    const label = document.createElement("span");
    label.textContent = `[${total.displayName}]`;
    const amount = document.createElement("strong");
    amount.textContent = total.value.toLocaleString("ko-KR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }) + total.unitLabel;
    row.append(label, amount);
    totalGrid.appendChild(row);
  }
  if (totals.length === 0) {
    const empty = document.createElement("p");
    empty.className = "equipment-total-empty";
    empty.textContent = "설정된 오버로드 옵션이 없습니다.";
    totalGrid.appendChild(empty);
  }
  summary.append(title, totalGrid);
  const list = byId("equipment-list");
  list.replaceChildren();
  for (const slot of ["head", "torso", "arms", "legs"]) {
    const prefix = `equipment.${slot}`;
    const definition = effectiveProfileValue(`${prefix}.definition`, subjectUid);
    const support = state.presentationBySupport.get(definition?.referenceUid) || {};
    const enhancementLevel = Number(
      effectiveProfileValue(`${prefix}.enhancement_level`, subjectUid)?.integerValue ?? 0);
    const card = document.createElement("article");
    card.className = "equipment-card surface";
    const header = document.createElement("div");
    header.className = "equipment-card-header";
    const icon = document.createElement("button");
    icon.type = "button";
    icon.className = "equipment-icon";
    icon.title = `${equipmentSlotLabels[slot]} 장비 변경`;
    icon.setAttribute("aria-label", `${equipmentSlotLabels[slot]} 장비 변경`);
    if (support.imagePath) {
      appendPresentationImage(
        icon, support.imagePath, "equipment-image", support.displayName || "",
        equipmentSlotLabels[slot].slice(0, 1));
    } else {
      icon.textContent = equipmentSlotLabels[slot].slice(0, 1);
    }
    if (support.tier) {
      const tierBadge = document.createElement("span");
      tierBadge.className = "equipment-tier-badge";
      tierBadge.textContent = `T${support.tier}`;
      icon.appendChild(tierBadge);
    }
    const heading = document.createElement("div");
    heading.className = "equipment-stat-panel";
    const name = document.createElement("strong");
    name.textContent = support.displayName || `${equipmentSlotLabels[slot]} 장비`;
    const statTitle = document.createElement("span");
    statTitle.className = "equipment-column-title";
    statTitle.textContent = "장비 능력치";
    const statRows = document.createElement("div");
    statRows.className = "equipment-stat-rows";
    const supportStats = (support.stats || [])
      .filter((item) => item.label !== "능력치" || item.value !== "0");
    for (const item of supportStats) {
      const statRow = document.createElement("div");
      const statLabel = document.createElement("span");
      statLabel.textContent = item.label;
      const statValue = document.createElement("strong");
      statValue.textContent = enhancedEquipmentStatText(
        item,
        enhancementLevel,
        support.enhancementStatIncreaseBasisPointsPerLevel ?? 1_000);
      statRow.append(statLabel, statValue);
      statRows.appendChild(statRow);
    }
    if (supportStats.length === 0) {
      const missing = document.createElement("span");
      missing.textContent = "능력치 미확인";
      statRows.appendChild(missing);
    }
    heading.append(name, statTitle, statRows);
    const enhancement = numericEditor(
      "강화",
      `${prefix}.enhancement_level`,
      subjectUid,
      0,
      support.maximumEnhancementLevel ?? 5);
    enhancement.className = "equipment-enhancement";
    enhancement.querySelector("input").disabled = !definition;
    header.append(icon, heading, enhancement);
    const optionList = document.createElement("div");
    optionList.className = "overload-list";
    const effectTitle = document.createElement("strong");
    effectTitle.className = "equipment-column-title overload-column-title";
    effectTitle.textContent = "장비 효과";
    const effectNotice = document.createElement("small");
    effectNotice.className = "equipment-effect-notice";
    effectNotice.textContent = "효과의 수치는 전투 진입 시 적용됩니다.";
    optionList.append(effectTitle, effectNotice);
    for (let line = 1; line <= 3; line++) {
      const linePrefix = `${prefix}.overload.${line}`;
      const optionState = effectiveProfileValue(`${linePrefix}.state`, subjectUid)?.controlledValue;
      const optionDefinition = optionState === "absent"
        ? null
        : effectiveProfileValue(`${linePrefix}.definition`, subjectUid);
      const optionValue = optionState === "absent"
        ? null
        : effectiveProfileValue(`${linePrefix}.value`, subjectUid);
      const option = state.presentationByOverload.get(optionDefinition?.referenceUid) || {};
      const row = document.createElement("div");
      row.className = `overload-row ${overloadTierClass(optionValue, option)}`;
      const optionName = document.createElement("select");
      optionName.setAttribute("aria-label", `오버로드 옵션 ${line}`);
      const empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "옵션 없음";
      optionName.appendChild(empty);
      for (const candidate of state.presentation.overloadOptions || []) {
        const choice = document.createElement("option");
        choice.value = candidate.definitionUid;
        choice.textContent = candidate.displayName;
        optionName.appendChild(choice);
      }
      optionName.value = optionDefinition?.referenceUid || "";
      optionName.addEventListener("change", () => {
        if (!optionName.value) {
          for (const suffix of ["definition", "unit", "value"]) {
            const index = state.editOperations.findIndex((item) =>
              item.fieldCode === `${linePrefix}.${suffix}` && item.subjectUid === subjectUid);
            if (index >= 0) state.editOperations.splice(index, 1);
          }
          queueControlledValue(`${linePrefix}.state`, subjectUid, "absent");
          renderEditOperations();
          renderNikkeDetail(subjectUid);
          return;
        }
        const selected = state.presentationByOverload.get(optionName.value);
        const initialValue = selected?.legalValues?.[0];
        if (!initialValue) throw new Error("overload_legal_value_missing");
        queueControlledValue(`${linePrefix}.state`, subjectUid, "present");
        queueReferenceValue(`${linePrefix}.definition`, subjectUid, optionName.value);
        // Overload values are stored as normalized ratios. The percent sign is
        // presentation-only and exactValueText applies the display conversion.
        queueControlledValue(`${linePrefix}.unit`, subjectUid, "ratio");
        queueExactValue(`${linePrefix}.value`, subjectUid,
          String(initialValue.unscaledValue), initialValue.decimalScale);
        renderNikkeDetail(subjectUid);
      });
      const shown = document.createElement("label");
      shown.textContent = option.unitLabel || "%";
      const input = document.createElement("select");
      input.setAttribute("aria-label", `오버로드 옵션 ${line} 수치`);
      for (const legalValue of option.legalValues || []) {
        const choice = document.createElement("option");
        choice.value = `${legalValue.unscaledValue}:${legalValue.decimalScale}`;
        choice.textContent = exactValueText(legalValue, option.unitLabel || "%");
        input.appendChild(choice);
      }
      input.value = optionValue
        ? `${optionValue.unscaledValue}:${optionValue.decimalScale || 0}`
        : "";
      input.disabled = !optionDefinition;
      input.addEventListener("change", () => {
        const [unscaledValue, decimalScale] = input.value.split(":");
        queueExactValue(`${linePrefix}.value`, subjectUid, unscaledValue, Number(decimalScale));
        renderNikkeDetail(subjectUid);
      });
      shown.prepend(input);
      row.append(optionName, shown);
      optionList.appendChild(row);
    }
    const picker = document.createElement("div");
    picker.className = "equipment-picker";
    picker.hidden = true;
    const pickerTitle = document.createElement("strong");
    pickerTitle.textContent = `${equipmentSlotLabels[slot]} 장비 선택`;
    const pickerChoices = document.createElement("div");
    pickerChoices.className = "equipment-picker-choices";
    const character = state.presentationByCharacter.get(subjectUid) || {};
    const candidates = (state.presentation.supportDefinitions || [])
      .filter((item) => item.kindCode === "equipment" &&
        item.slotCode === slot &&
        item.combatClassCode === character.combatClassCode &&
        [9, 10].includes(item.tier))
      .sort((left, right) => left.tier - right.tier);
    for (const candidate of candidates) {
      const choice = document.createElement("button");
      choice.type = "button";
      choice.className = "equipment-picker-choice";
      choice.classList.toggle("selected", candidate.definitionUid === definition?.referenceUid);
      choice.setAttribute("aria-pressed",
        String(candidate.definitionUid === definition?.referenceUid));
      const choiceIcon = document.createElement("span");
      choiceIcon.className = "equipment-picker-icon";
      appendPresentationImage(
        choiceIcon, candidate.imagePath, "equipment-picker-image",
        candidate.displayName || "", `T${candidate.tier}`);
      const choiceCopy = document.createElement("span");
      const choiceTier = document.createElement("b");
      choiceTier.textContent = `${candidate.tier}티어`;
      const choiceName = document.createElement("small");
      choiceName.textContent = candidate.displayName;
      choiceCopy.append(choiceTier, choiceName);
      choice.append(choiceIcon, choiceCopy);
      choice.addEventListener("click", () => {
        const currentEnhancement = Number(
          effectiveProfileValue(`${prefix}.enhancement_level`, subjectUid)?.integerValue ?? 0);
        const equipmentSelectionOperations = [
          {
            fieldCode: `${prefix}.state`, subjectUid, valueKind: "controlled",
            integerValue: null, booleanValue: null, referenceUid: null,
            unscaledValue: null, decimalScale: null, controlledValue: "equipped"
          },
          {
            fieldCode: `${prefix}.definition`, subjectUid, valueKind: "reference",
            integerValue: null, booleanValue: null, referenceUid: candidate.definitionUid,
            unscaledValue: null, decimalScale: null, controlledValue: null
          },
          {
            fieldCode: `${prefix}.enhancement_level`, subjectUid, valueKind: "integer",
            integerValue: currentEnhancement, booleanValue: null, referenceUid: null,
            unscaledValue: null, decimalScale: null, controlledValue: null
          },
          candidate.tier === 10
            ? {
              fieldCode: `${prefix}.manufacturer_matched`, subjectUid,
              valueKind: "controlled", integerValue: null, booleanValue: null,
              referenceUid: null, unscaledValue: null, decimalScale: null,
              controlledValue: "not_applicable"
            }
            : {
              fieldCode: `${prefix}.manufacturer_matched`, subjectUid,
              valueKind: "boolean", integerValue: null, booleanValue: false,
              referenceUid: null, unscaledValue: null, decimalScale: null,
              controlledValue: null
            }
        ];
        if (candidate.tier === 9) {
          for (let line = 1; line <= 3; line++) {
            equipmentSelectionOperations.push({
              fieldCode: `${prefix}.overload.${line}.state`, subjectUid,
              valueKind: "controlled", integerValue: null, booleanValue: null,
              referenceUid: null, unscaledValue: null, decimalScale: null,
              controlledValue: "absent"
            });
          }
        }
        // A definition without state/enhancement is not a legal equipment shape
        // when the source slot was empty. Queue the complete selection atomically.
        upsertProfileOperations(equipmentSelectionOperations);
        renderNikkeDetail(subjectUid);
      });
      pickerChoices.appendChild(choice);
    }
    if (candidates.length === 0) {
      const missing = document.createElement("span");
      missing.className = "equipment-picker-missing";
      missing.textContent = "선택 가능한 9·10티어 장비 정보가 없습니다.";
      pickerChoices.appendChild(missing);
    }
    picker.append(pickerTitle, pickerChoices);
    icon.addEventListener("click", () => {
      picker.hidden = !picker.hidden;
      icon.setAttribute("aria-expanded", String(!picker.hidden));
    });
    icon.setAttribute("aria-expanded", "false");
    card.append(header, optionList, picker);
    list.appendChild(card);
  }
}

function overloadTierClass(valueProjection, option) {
  const level = overloadLevel(valueProjection, option);
  return level === 0 ? "overload-tier-normal" : `overload-level-${level}`;
}

function overloadLevel(valueProjection, option) {
  if (!valueProjection || !Array.isArray(option.legalValues) || option.legalValues.length === 0) {
    return 0;
  }
  const legal = [...option.legalValues].sort((left, right) =>
    (left.unscaledValue / (10 ** (left.decimalScale || 0))) -
    (right.unscaledValue / (10 ** (right.decimalScale || 0))));
  const ordinal = legal.findIndex((item) =>
    item.unscaledValue === valueProjection.unscaledValue &&
    (item.decimalScale || 0) === (valueProjection.decimalScale || 0));
  return ordinal < 0 ? 0 : ordinal + 1;
}

function collectEquipmentOverloadTotals(subjectUid) {
  const totals = new Map();
  for (const slot of ["head", "torso", "arms", "legs"]) {
    for (let line = 1; line <= 3; line++) {
      const prefix = `equipment.${slot}.overload.${line}`;
      if (effectiveProfileValue(`${prefix}.state`, subjectUid)?.controlledValue === "absent") continue;
      const definition = effectiveProfileValue(`${prefix}.definition`, subjectUid);
      const projection = effectiveProfileValue(`${prefix}.value`, subjectUid);
      const option = state.presentationByOverload.get(definition?.referenceUid);
      if (!option || projection?.unscaledValue == null) continue;
      const scale = projection.decimalScale || 0;
      const multiplier = option.unitLabel === "%" ? 100 : 1;
      const value = projection.unscaledValue / (10 ** scale) * multiplier;
      const key = option.definitionUid || option.displayName;
      const current = totals.get(key) || {
        displayName: option.displayName || "오버로드 옵션",
        unitLabel: option.unitLabel || "%",
        value: 0
      };
      current.value += value;
      totals.set(key, current);
    }
  }
  return [...totals.values()];
}

function renderSkillDetail(subjectUid) {
  const target = byId("skill-editor");
  target.replaceChildren();
  for (const [fieldCode, label] of [
    ["skill_1_level", "스킬 1"], ["skill_2_level", "스킬 2"], ["burst_level", "버스트 스킬"]
  ]) {
    const card = numericEditor(label, fieldCode, subjectUid, 1);
    card.className = "skill-card surface";
    target.appendChild(card);
  }
}

function srCollectionLevel15Stats(weaponCode) {
  const srCollections = (state.presentation.supportDefinitions || []).filter((item) =>
    item.kindCode === "collection" && item.rarityCode === "sr" &&
    item.weaponCode === weaponCode);
  if (srCollections.length !== 1) return [];
  return (srCollections[0].levels || [])
    .find((item) => item.level === 15)?.stats || [];
}

function renderCollectionDetail(subjectUid, presentation) {
  const target = byId("collection-editor");
  target.replaceChildren();
  const kind = effectiveProfileValue("collection.kind", subjectUid)?.controlledValue || "none";
  const definition = effectiveProfileValue("collection.definition", subjectUid);
  const support = state.presentationBySupport.get(definition?.referenceUid) || {};
  const header = document.createElement("div");
  header.className = "collection-header";
  const icon = document.createElement("span");
  icon.className = "collection-icon";
  if (support.imagePath) {
    appendPresentationImage(
      icon, support.imagePath, "collection-image", support.displayName || "",
      weaponLabels[presentation.weaponCode]?.slice(0, 1) || "소");
  } else {
    icon.textContent = weaponLabels[presentation.weaponCode]?.slice(0, 1) || "소";
  }
  const copy = document.createElement("div");
  const title = document.createElement("h3");
  title.textContent = support.displayName || (kind === "favorite" ? "애장품" : "SR 소장품");
  const description = document.createElement("p");
  description.textContent = kind === "favorite"
    ? `${presentation.displayName || "선택 니케"} 전용 애장품`
    : `${weaponLabels[presentation.weaponCode] || "무기군"} 전용 소장품`;
  copy.append(title, description);
  const phase = document.createElement("div");
  phase.className = "collection-phase";
  const currentCollectionLevel = effectiveProfileValue("collection.level", subjectUid)?.integerValue ?? 0;
  const phaseGrade = document.createElement("strong");
  phaseGrade.textContent = kind === "favorite" ? "애장품" : "SR";
  const phaseLevel = document.createElement("span");
  phaseLevel.textContent = `Phase ${currentCollectionLevel}`;
  phase.append(phaseGrade, phaseLevel);
  const phaseStars = document.createElement("span");
  phaseStars.className = "collection-phase-stars";
  for (let index = 0; index < 3; index++) {
    appendPresentationImage(
      phaseStars, `${uiAssetRoot}/star-filled.png`, "collection-star", "", "★");
  }
  phase.appendChild(phaseStars);
  copy.appendChild(phase);
  header.append(icon, copy);
  const selector = document.createElement("label");
  selector.textContent = "소장품 종류";
  const collectionSelect = document.createElement("select");
  for (const candidate of (state.presentation.supportDefinitions || []).filter((item) =>
    (item.kindCode === "collection" &&
      (!item.weaponCode || item.weaponCode === presentation.weaponCode)) ||
    (item.kindCode === "favorite" && item.favoriteCharacterUid === subjectUid))) {
    const option = document.createElement("option");
    option.value = candidate.definitionUid;
    option.textContent = candidate.displayName;
    collectionSelect.appendChild(option);
  }
  collectionSelect.value = definition?.referenceUid || "";
  collectionSelect.addEventListener("change", () => {
    const selected = state.presentationBySupport.get(collectionSelect.value);
    const selectedKind = selected?.kindCode === "favorite"
      ? "favorite"
      : "generic_collection";
    const selectedMaximumLevel = selectedKind === "favorite"
      ? Math.max(0, ...(selected?.levels || []).map((item) => item.level))
      : 15;
    const selectedLevel = Math.min(
      effectiveProfileValue("collection.level", subjectUid)?.integerValue ?? 0,
      selectedMaximumLevel || 0);
    // Detached collections have no stored level. Definition, kind and level must
    // therefore be submitted together to form one legal selected collection.
    upsertProfileOperations([
      {
        fieldCode: "collection.definition", subjectUid, valueKind: "reference",
        integerValue: null, booleanValue: null, referenceUid: collectionSelect.value,
        unscaledValue: null, decimalScale: null, controlledValue: null
      },
      {
        fieldCode: "collection.kind", subjectUid, valueKind: "controlled",
        integerValue: null, booleanValue: null, referenceUid: null,
        unscaledValue: null, decimalScale: null, controlledValue: selectedKind
      },
      {
        fieldCode: "collection.level", subjectUid, valueKind: "integer",
        integerValue: selectedLevel, booleanValue: null, referenceUid: null,
        unscaledValue: null, decimalScale: null, controlledValue: null
      }
    ]);
    renderNikkeDetail(subjectUid);
  });
  selector.appendChild(collectionSelect);
  const maximumLevel = kind === "favorite"
    ? Math.max(0, ...(support.levels || []).map((item) => item.level))
    : 15;
  const level = numericEditor("소장품 레벨", "collection.level", subjectUid, 0,
    maximumLevel || null);
  level.className = "collection-level";
  level.querySelector("input").disabled = !definition;
  const currentLevel = currentCollectionLevel;
  const favoriteBaseStats = kind === "favorite"
    ? srCollectionLevel15Stats(presentation.weaponCode)
    : [];
  const currentStats = favoriteBaseStats.length ? favoriteBaseStats : (support.levels || [])
    .filter((item) => item.level <= currentLevel)
    .sort((left, right) => right.level - left.level)[0]?.stats || [];
  const stats = document.createElement("div");
  stats.className = "collection-stats";
  stats.textContent = currentStats.length
    ? currentStats.map((item) => `${item.label} ${item.value}`).join(" · ")
    : "능력치 정보 없음";
  target.append(header, selector, level, stats);
}

export { renderEquipmentDetail, renderSkillDetail, renderCollectionDetail, synchronizedLevelEditor, numericEditor, limitBreakEditor, coreBreakEditor };

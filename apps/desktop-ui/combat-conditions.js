/**
 * Boss distance and boss weak element conditions (F-COND-1, UI part F-COND-U).
 *
 * Replaces the deck-wide "적정 거리" / "우월 코드" checkboxes with two per-member conditions:
 * - bossDistance: integer 0-100 or null. A member gets the proper-distance bonus when its own weapon range
 *   [min, max] contains the distance (both ends inclusive, provisional). RL 0-0 in the source data means
 *   "no proper-distance bonus" and is flagged for confirmation.
 * - bossWeakElement: Fire/Water/Wind/Iron/Electronic or null. A member gets the element-advantage bonus when its
 *   element is the boss's weak element. No element matchup chart is used; the user states the weakness.
 * Rules are the Director's provisional defaults; the engine decides, the UI only previews.
 *
 * Wire: Backend 796eec3, docs/single-deck-compute-contract.ko.md "F-COND-B".
 * - GET /api/runtime/combat-conditions: weapon-group table, elements with icon URLs, source.
 * - GET /api/snapshots/{id}/combat-conditions?characterIds=...: member profiles in request order.
 * - conditions.combat.bossDistance / bossWeakElement; in the new mode properDistance/elementAdvantage are omitted
 *   (mixing is HTTP 400) and "all unset" sends both new fields as explicit null.
 * - Saved replay (top level) and compute BatchStatus.input carry conditionCompatibility {mode, label, ...};
 *   old records are read through .../condition-compatibility. Old values are displayed, never reinterpreted.
 * `confirmed: false` reproduces the pre-wire form (old checkboxes) for comparison tests only.
 */

import { errorText as friendlyError } from './display-labels.js';
export const COND_WIRE = Object.freeze({
  confirmed: true,
  catalogRoute: '/runtime/combat-conditions',
  membersRoute: (snapshotId, ids) => `/snapshots/${encodeURIComponent(snapshotId)}/combat-conditions?characterIds=${ids.map(encodeURIComponent).join(',')}`,
  replayCompatibilityRoute: id => `/runtime/skill-replays/${encodeURIComponent(id)}/condition-compatibility`,
  experimentCompatibilityRoute: id => `/compute/experiments/${encodeURIComponent(id)}/condition-compatibility`
});

export const DISTANCE_MIN = 0;
export const DISTANCE_MAX = 100;

// code = presentation elementCode / icon name; wire = contract value (Electronic keeps its wire spelling).
export const WEAK_ELEMENTS = Object.freeze([
  { code: 'fire', wire: 'Fire', label: '작열', en: 'Fire' },
  { code: 'water', wire: 'Water', label: '수냉', en: 'Water' },
  { code: 'wind', wire: 'Wind', label: '풍압', en: 'Wind' },
  { code: 'iron', wire: 'Iron', label: '철갑', en: 'Iron' },
  { code: 'electric', wire: 'Electronic', label: '전격', en: 'Electronic' }
]);
// Contract weaponType -> label; presentation weaponCode maps onto the same types.
export const WEAPON_LABELS = Object.freeze({ SG: '샷건', SMG: '기관단총', AR: '소총', MG: '머신건', SR: '저격소총', RL: '런처' });
const WEAPON_ORDER = ['SG', 'SMG', 'AR', 'MG', 'SR', 'RL'];
const PRESENTATION_WEAPONS = { shotgun: 'SG', submachine_gun: 'SMG', assault_rifle: 'AR', machine_gun: 'MG', sniper_rifle: 'SR', rocket_launcher: 'RL' };
const WEAPON_ICONS = Object.fromEntries(Object.entries(PRESENTATION_WEAPONS).map(([code, type]) => [type, code]));

const isInt = v => Number.isInteger(v);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const elementByCode = code => WEAK_ELEMENTS.find(e => e.code === code || e.wire === code) ?? null;
const text = v => typeof v === 'string' && v.trim() ? v.trim() : null;

export function createConditionState(initial = {}) {
  return { bossDistance: isInt(initial.bossDistance) ? initial.bossDistance : null,
    bossWeakElement: elementByCode(initial.bossWeakElement)?.code ?? null };
}

/** Strict: '' means unset; anything else must be an integer 0-100 (never clamped or rounded). */
export function parseDistance(value) {
  const trimmed = String(value ?? '').trim();
  if (trimmed === '') return null;
  if (!/^\d{1,3}$/.test(trimmed)) throw new Error('보스 거리는 0~100 사이 정수로 입력하세요.');
  const number = Number(trimmed);
  if (number < DISTANCE_MIN || number > DISTANCE_MAX) throw new Error('보스 거리는 0~100 사이 정수로 입력하세요.');
  return number;
}

export const distanceSummary = state => state.bossDistance === null ? '미설정' : String(state.bossDistance);
export function elementSummary(state) {
  const element = elementByCode(state.bossWeakElement);
  return element ? element.label : '없음';
}

/** Range status of one member profile at a distance. rangeBonusAvailable=false (RL 0-0) is data, not an error. */
export function rangeStatus(profile, distance) {
  if (!profile || !isInt(profile.min) || !isInt(profile.max)) return { kind: 'unknown', text: '사거리 정보 없음' };
  if (profile.rangeBonusAvailable === false || (profile.min === 0 && profile.max === 0))
    return { kind: 'no_bonus', text: '보너스 없음 (0–0)' };
  if (distance === null) return { kind: 'unset', text: `적정 ${profile.min}–${profile.max} · 거리 미설정` };
  return distance >= profile.min && distance <= profile.max
    ? { kind: 'in', text: `적정 거리 (${profile.min}–${profile.max})` }
    : { kind: 'out', text: `범위 밖 (${profile.min}–${profile.max})` };
}

function normalizeProfile(p) {
  if (!p || p.characterId == null) return null;
  return { characterId: String(p.characterId), name: text(p.name), weaponType: text(p.weaponType),
    min: isInt(p.bonusRangeMin) ? p.bonusRangeMin : null, max: isInt(p.bonusRangeMax) ? p.bonusRangeMax : null,
    element: elementByCode(p.element)?.code ?? null,
    rangeBonusAvailable: typeof p.rangeBonusAvailable === 'boolean' ? p.rangeBonusAvailable : null,
    diagnostic: text(p.diagnostic) };
}

/** GET /api/runtime/combat-conditions -> view model. Nothing is filled in when a field is missing. */
export function normalizeCatalog(payload) {
  const rows = Array.isArray(payload?.weaponRanges) ? payload.weaponRanges : [];
  const weaponRanges = rows.filter(r => r && typeof r.weaponType === 'string').map(r => {
    const ranges = (Array.isArray(r.ranges) ? r.ranges : []).filter(x => x && isInt(x.min) && isInt(x.max))
      .map(x => ({ min: x.min, max: x.max, count: isInt(x.count) ? x.count : null, isTypical: x.isTypical === true }));
    return { weaponType: r.weaponType, label: WEAPON_LABELS[r.weaponType] ?? r.weaponType,
      characterCount: isInt(r.characterCount) ? r.characterCount : null,
      typical: ranges.find(x => x.isTypical) ?? null, ranges,
      exceptions: (Array.isArray(r.exceptions) ? r.exceptions : []).map(normalizeProfile).filter(Boolean),
      rangeBonusAvailable: typeof r.rangeBonusAvailable === 'boolean' ? r.rangeBonusAvailable : null,
      diagnostics: (Array.isArray(r.diagnostics) ? r.diagnostics : []).map(String) };
  }).sort((a, b) => (WEAPON_ORDER.indexOf(a.weaponType) + 1 || 99) - (WEAPON_ORDER.indexOf(b.weaponType) + 1 || 99));
  const icons = {};
  for (const e of Array.isArray(payload?.elements) ? payload.elements : []) {
    const element = elementByCode(e?.value);
    if (element && text(e.iconUrl)) icons[element.code] = e.iconUrl;
  }
  const source = payload?.source && typeof payload.source === 'object'
    ? [text(payload.source.path), text(payload.source.version)].filter(Boolean).join(' · ') : null;
  return { weaponRanges, icons, source, runtimeDataId: text(payload?.runtimeDataId), gameVerified: payload?.gameVerified === true };
}

/** GET /api/snapshots/{id}/combat-conditions -> { [characterId]: profile }. */
export function normalizeMembers(payload) {
  const members = {};
  for (const profile of (Array.isArray(payload?.members) ? payload.members : []).map(normalizeProfile).filter(Boolean))
    members[profile.characterId] = profile;
  return members;
}

/** Per-member preview from API profiles; presentation elementCode is only a fallback when profiles are absent. */
export function memberPreview(members, profiles, state) {
  return (members ?? []).map(m => {
    const profile = profiles?.[m.id] ?? null;
    const element = profile?.element ?? elementByCode(m.elementCode)?.code ?? null;
    return {
      id: m.id, name: m.displayName ?? '이름 미확인',
      weaponType: profile?.weaponType ?? PRESENTATION_WEAPONS[m.weaponCode] ?? null,
      distance: rangeStatus(profile, state.bossDistance),
      element,
      elementMatch: element === null ? null : state.bossWeakElement !== null && element === state.bossWeakElement
    };
  });
}

/** New-mode combat fields. Both are always sent (explicit null = unset/none); the old bools are never added. */
export function conditionWire(state, confirmed = COND_WIRE.confirmed) {
  if (!confirmed) return null;
  return { bossDistance: state.bossDistance, bossWeakElement: elementByCode(state.bossWeakElement)?.wire ?? null };
}

/**
 * conditionCompatibility (saved replay top level / BatchStatus.input / condition-compatibility endpoint) ->
 * display. The Backend label is shown as given; values are described, never converted between modes.
 */
export function describeCompatibility(compat) {
  if (!compat || typeof compat !== 'object' || !text(compat.mode)) return { mode: 'unknown', text: '전투 조건 모드 기록 없음' };
  const label = text(compat.label);
  if (compat.mode === 'per_member') {
    const state = createConditionState(compat);
    return { mode: 'per_member', label, text: `${label ?? '보스 거리·약점(멤버별)'} · 보스 거리 ${distanceSummary(state)} · 약점 ${elementSummary(state)}` };
  }
  if (compat.mode === 'legacy_global') {
    const on = v => v === true ? '적용' : v === false ? '미적용' : '기록 없음';
    return { mode: 'legacy', label, text: `${label ?? '이전 방식(전원 적용)'} · 적정 거리 ${on(compat.legacyProperDistance)} · 우월 코드 ${on(compat.legacyElementAdvantage)}` };
  }
  return { mode: 'unknown', label, text: `${label ?? '알 수 없는 조건 모드'} (${compat.mode})` };
}

/** Summary of the conditions the form will send (statistics screen, before a batch exists). */
export function describePlannedConditions(state) {
  return `보스 거리 ${distanceSummary(state)} · 약점 ${elementSummary(state)} (멤버별 판정)`;
}

const defaultIcon = code => `/editor/assets/ui/code-${code}.png`;
const iconFor = (catalog, code) => catalog?.icons?.[code] ?? defaultIcon(code);

export function renderConditionControls(state, { legacy = null, catalog = null } = {}) {
  const element = elementByCode(state.bossWeakElement);
  return `<div class="cond-controls" role="group" aria-label="보스 거리·약점 속성">
    <div class="cond-control"><button type="button" class="cond-icon-btn" data-cond-open="distance" aria-haspopup="dialog" aria-label="보스 거리 설정"><span aria-hidden="true">↔</span></button>
      <span class="cond-value" data-cond-value="distance">적정 거리 · ${esc(distanceSummary(state))}</span></div>
    <div class="cond-control"><button type="button" class="cond-icon-btn" data-cond-open="element" aria-haspopup="dialog" aria-label="보스 약점 속성 설정">${element
      ? `<img src="${esc(iconFor(catalog, element.code))}" alt="">` : '<span aria-hidden="true">◇</span>'}</button>
      <span class="cond-value" data-cond-value="element">약점 · ${esc(elementSummary(state))}</span></div>
    ${legacy ? `<span class="status-pill warning cond-legacy">${esc(legacy)}</span>` : ''}
  </div>`;
}

export function renderDistanceDialog(state, catalog, preview, { error = null, membersError = null, nameOf = x => x.name ?? '이름 미확인' } = {}) {
  const rangeText = r => r.rangeBonusAvailable === false || (r.typical && r.typical.min === 0 && r.typical.max === 0)
    ? '0–0 · 보너스 없음' : r.typical ? `${r.typical.min}–${r.typical.max}` : '미확인';
  // Character codes are not shown; the Korean display name comes from the app's character data.
  const exceptionText = x => `${esc(nameOf(x))}: ${x.min ?? '?'}–${x.max ?? '?'}`;
  const weaponCell = r => `<span class="cond-weapon">${WEAPON_ICONS[r.weaponType] ? `<img src="/editor/assets/ui/weapon-${WEAPON_ICONS[r.weaponType]}.png" alt="">` : ''}<span>${esc(r.label)}</span></span>`;
  const table = catalog?.weaponRanges?.length ? `<div class="table-scroll"><table class="cond-range-table">
      <thead><tr><th>무기군</th><th>적정 사거리</th><th>인원</th><th>예외</th></tr></thead><tbody>${catalog.weaponRanges.map(r => `<tr data-weapon="${esc(r.weaponType)}"><td>${weaponCell(r)}</td><td>${esc(rangeText(r))}</td><td>${r.characterCount ?? '—'}</td><td>${r.exceptions.length ? r.exceptions.map(exceptionText).join(', ') : '—'}</td></tr>`).join('')}</tbody></table></div>`
    : `<p class="cond-load-error" data-cond-error="catalog" role="alert">무기군별 적정 사거리를 불러오지 못했습니다.${error ? ` ${esc(error)}` : ''}</p>`;
  const members = preview.length ? `<ul class="cond-member-list">${preview.map(m =>
    `<li data-member="${esc(m.id)}" data-distance-kind="${m.distance.kind}"><strong>${esc(m.name)}</strong> <span>${esc(WEAPON_LABELS[m.weaponType] ?? '무기 미확인')}</span> <em>${esc(m.distance.text)}</em></li>`).join('')}</ul>` : '';
  const value = state.bossDistance ?? '';
  return `<form method="dialog" class="cond-dialog-body" data-cond-form="distance">
    <h3 id="cond-distance-title">보스 거리</h3>
    <p class="microcopy">0~100 정수. 각 니케는 자기 무기의 적정 사거리 안에 거리가 들어가면 적정 거리 보너스를 받습니다. 미설정이면 전원 보너스 없음.</p>
    <div class="cond-distance-inputs">
      <input type="range" name="distanceRange" min="${DISTANCE_MIN}" max="${DISTANCE_MAX}" step="1" value="${value === '' ? 50 : value}" aria-label="보스 거리 슬라이더">
      <input type="number" name="distance" min="${DISTANCE_MIN}" max="${DISTANCE_MAX}" step="1" inputmode="numeric" value="${value}" placeholder="미설정" aria-label="보스 거리">
      <button type="button" data-cond-unset>미설정</button>
    </div>
    <p class="cond-error" role="alert" hidden></p>
    <h4>현재 덱</h4>${membersError ? `<p class="cond-load-error" data-cond-error="members" role="alert">멤버 사거리·속성을 불러오지 못했습니다. ${esc(membersError)}</p>` : ''}${members}
    <h4>무기군별 적정 사거리</h4>${table}
    <div class="cond-actions"><button type="button" data-cond-cancel>취소</button><button type="submit" class="primary" value="apply">적용</button></div>
  </form>`;
}

export function renderElementDialog(state, preview, catalog = null, { error = null } = {}) {
  const buttons = WEAK_ELEMENTS.map(e => {
    const members = preview.filter(m => m.element === e.code).map(m => m.name);
    return `<button type="button" class="cond-element ${state.bossWeakElement === e.code ? 'selected' : ''}" data-cond-element="${e.code}" aria-pressed="${state.bossWeakElement === e.code}">
      <img src="${esc(iconFor(catalog, e.code))}" alt=""><span>${esc(e.label)}</span><small class="cond-element-members">${members.length ? `덱: ${esc(members.join(', '))}` : '덱에 없음'}</small></button>`;
  }).join('');
  return `<div class="cond-dialog-body" data-cond-form="element">
    <h3 id="cond-element-title">보스의 약점 속성</h3>
    <p class="cond-emphasis">보스의 약점 속성 — 이 속성 니케가 우월 코드 보너스를 받습니다.</p>
    ${error ? `<p class="cond-load-error" data-cond-error="members" role="alert">덱 멤버 속성을 확인하지 못했습니다. ${esc(error)}</p>` : ''}
    <div class="cond-element-grid">${buttons}
      <button type="button" class="cond-element ${state.bossWeakElement === null ? 'selected' : ''}" data-cond-element="" aria-pressed="${state.bossWeakElement === null}"><span>없음</span><small class="cond-element-members">전원 보너스 없음</small></button></div>
    <div class="cond-actions"><button type="button" data-cond-cancel>닫기</button></div>
  </div>`;
}

/**
 * Mounts the controls inside `container` and owns the dialogs. No hidden form inputs: the request builder reads
 * getState(). ESC and the close buttons dismiss without applying. loadCatalog()/loadMembers(ids) call the API.
 */
export function mountConditionControls(container, { getMembers = () => [], loadCatalog = async () => null,
  loadMembers = async () => null, onChange = () => {}, legacy = null, getCharacterName = () => null } = {}) {
  let state = createConditionState();
  let catalog = null, catalogError = null, catalogPromise = null;
  let profiles = null, profilesKey = null, profilesError = null, lastTrigger = null;
  const doc = container.ownerDocument;
  const dialog = doc.createElement('dialog');
  dialog.className = 'cond-dialog';
  doc.body.append(dialog);
  const preview = (s = state) => memberPreview(getMembers(), profiles, s);
  const paint = () => { container.innerHTML = renderConditionControls(state, { legacy, catalog }); };
  const names = () => new Map(getMembers().map(m => [String(m.id), m.displayName ?? null]));
  const errorText = error => describeCombatProfileError(error, names())?.text ?? friendlyError(error);
  const ensureCatalog = () => catalogPromise ??= Promise.resolve(loadCatalog())
    .then(payload => { catalog = payload ? normalizeCatalog(payload) : null; catalogError = null; return catalog; })
    .catch(error => { catalog = null; catalogError = errorText(error); catalogPromise = null; return null; });
  const ensureProfiles = () => {
    const ids = getMembers().map(m => m.id);
    const key = ids.join(',');
    if (!ids.length) { profiles = null; profilesKey = key; return Promise.resolve(null); }
    if (key === profilesKey && profiles) return Promise.resolve(profiles);
    return Promise.resolve(loadMembers(ids)).then(payload => { profiles = payload ? normalizeMembers(payload) : null; profilesKey = key; profilesError = null; return profiles; })
      .catch(error => { profiles = null; profilesKey = null; profilesError = errorText(error); return null; });
  };
  const focusOpener = () => {
    const kind = lastTrigger?.dataset?.condOpen;
    (kind ? container.querySelector(`[data-cond-open="${kind}"]`) : null)?.focus();
  };
  // Apply closes and repaints synchronously, then returns focus at once (the close event itself is queued).
  const set = next => { state = { ...state, ...next }; legacy = null; paint(); onChange(state); focusOpener(); };

  function openDistance(trigger) {
    lastTrigger = trigger;
    let draft = state.bossDistance;
    const render = () => {
      dialog.setAttribute('aria-labelledby', 'cond-distance-title');
      dialog.innerHTML = renderDistanceDialog({ ...state, bossDistance: draft }, catalog, preview({ ...state, bossDistance: draft }), { error: catalogError, membersError: profilesError,
        nameOf: x => getCharacterName(x.characterId) ?? x.name ?? '이름 미확인' });
      const form = dialog.querySelector('form');
      const number = form.elements.distance, slider = form.elements.distanceRange, error = form.querySelector('.cond-error');
      const refresh = () => {
        const list = dialog.querySelector('.cond-member-list');
        if (!list) return;
        for (const m of preview({ ...state, bossDistance: draft })) {
          const li = list.querySelector(`[data-member="${CSS.escape(m.id)}"]`);
          if (li) { li.dataset.distanceKind = m.distance.kind; li.querySelector('em').textContent = m.distance.text; }
        }
      };
      number.oninput = () => {
        try { draft = parseDistance(number.value); error.hidden = true; if (draft !== null) slider.value = String(draft); }
        catch (e) { error.textContent = e.message; error.hidden = false; }
        refresh();
      };
      slider.oninput = () => { draft = Number(slider.value); number.value = slider.value; error.hidden = true; refresh(); };
      form.querySelector('[data-cond-unset]').onclick = () => { draft = null; number.value = ''; error.hidden = true; refresh(); };
      form.querySelector('[data-cond-cancel]').onclick = () => dialog.close();
      form.onsubmit = event => {
        event.preventDefault();
        try { draft = parseDistance(number.value); } catch (e) { error.textContent = e.message; error.hidden = false; return; }
        dialog.close(); set({ bossDistance: draft });
      };
      number.focus();
    };
    // Re-render once data arrives, but never replace the inputs while the user types when data was already there.
    const stale = !catalog || !profiles || profilesKey !== getMembers().map(m => m.id).join(',');
    render();
    dialog.showModal();
    if (stale) Promise.all([ensureCatalog(), ensureProfiles()]).then(() => {
      if (dialog.open && dialog.querySelector('[data-cond-form="distance"]')) {
        const typed = dialog.querySelector('[name="distance"]')?.value;
        try { draft = parseDistance(typed); } catch { /* keep draft */ }
        render();
      }
    });
  }

  function openElement(trigger) {
    lastTrigger = trigger;
    const render = () => {
      dialog.setAttribute('aria-labelledby', 'cond-element-title');
      dialog.innerHTML = renderElementDialog(state, preview(), catalog, { error: profilesError ?? catalogError });
      dialog.querySelectorAll('[data-cond-element]').forEach(button => button.onclick = () => {
        dialog.close(); set({ bossWeakElement: button.dataset.condElement || null });
      });
      dialog.querySelector('[data-cond-cancel]').onclick = () => dialog.close();
      (dialog.querySelector('.cond-element.selected') ?? dialog.querySelector('.cond-element'))?.focus();
    };
    const stale = !catalog || !profiles || profilesKey !== getMembers().map(m => m.id).join(',');
    render();
    dialog.showModal();
    if (stale) Promise.all([ensureCatalog(), ensureProfiles()]).then(() => {
      if (dialog.open && dialog.querySelector('[data-cond-form="element"]')) render();
    });
  }

  container.addEventListener('click', event => {
    const button = event.target.closest('[data-cond-open]');
    if (!button) return;
    if (button.dataset.condOpen === 'distance') openDistance(button); else openElement(button);
  });
  // Closing by apply, cancel or ESC returns focus to the (re-rendered) opener.
  // The close event is queued; if the dialog was reopened meanwhile (fast keyboard use), keep the new content.
  dialog.addEventListener('close', () => {
    if (dialog.open) return;
    dialog.innerHTML = '';
    if (!container.contains(doc.activeElement)) focusOpener();
  });
  paint();
  return {
    getState: () => ({ ...state }),
    setState: next => { state = createConditionState(next); paint(); },
    isLegacy: () => legacy !== null,
    loadCatalog: ensureCatalog,
    dispose: () => dialog.remove()
  };
}

// B-FIX-2 wire: HTTP 409 {code:"combat_profile_invalid", message, characterId, field, reason} on both
// combat-conditions GETs, replay POST and compute POST; plus the older 409 combat_profile_catalog_missing and
// 400 combat_member_profile_missing:<id>. These are server data problems, not connection failures.
const PROFILE_REASONS = {
  missing: '값 없음(키 누락)', null: '값이 null', wrong_type: '자료형 오류', out_of_range: '범위 오류(0–100, 최소 ≤ 최대)',
  unsupported_value: '지원하지 않는 값', id_mismatch: 'ID 불일치', weapon_mismatch: '무기군 불일치', hash_mismatch: '출처 해시 불일치'
};
const PROFILE_FIELDS = { bonusRangeMin: '최소 사거리', bonusRangeMax: '최대 사거리', element: '속성', weaponType: '무기군',
  name: '이름', characterId: '캐릭터 ID' };
const PREPARE_HINT = '사거리·속성 데이터를 확인하고 준비 스크립트(prepare_combat_conditions.py)로 다시 준비해야 합니다.';

/**
 * Korean diagnostic for a combat profile error, or null when the error is something else. `error` is the Error
 * thrown by the app's api() (status, code, details = response body). `names` maps characterId -> display name.
 */
export function describeCombatProfileError(error, names = null) {
  const body = error?.details && typeof error.details === 'object' ? error.details : {};
  const message = String(body.message ?? error?.message ?? '');
  const code = text(error?.code) ?? text(body.code) ?? (message.match(/^(combat_profile_invalid|combat_profile_catalog_missing|combat_member_profile_missing)/)?.[1] ?? null);
  // Character codes are not shown; an unnamed character stays unnamed.
  const who = id => { const name = names?.get?.(String(id)) ?? null; return name && name !== String(id) ? name : '이름 미확인 캐릭터'; };
  if (code === 'combat_profile_invalid') {
    const field = text(body.field);
    const key = field?.split('.').pop() ?? null;
    const reason = text(body.reason);
    const subject = body.characterId != null ? who(body.characterId) : '카탈로그·출처';
    // U-FIX-6: field meaning in Korean only; the raw path stays in the structured error.
    const fieldText = key && PROFILE_FIELDS[key] ? PROFILE_FIELDS[key] : /\.source\./.test(field ?? '') ? '출처 정보' : field ? '데이터 항목' : '항목 미기록';
    return { code, characterId: body.characterId ?? null, field, reason,
      text: `사거리·속성 데이터 오류 · ${subject} · ${fieldText} · ${PROFILE_REASONS[reason] ?? '사유 미확인'}. ${PREPARE_HINT}`,
      raw: field ? `${code}: ${field}: ${reason ?? '?'}` : message };
  }
  if (code === 'combat_profile_catalog_missing') {
    return { code, characterId: null, field: null, reason: null, raw: message,
      text: '현재 데이터에는 사거리·속성 정보가 준비되지 않았습니다. 보스 거리·약점 조건을 쓰려면 준비 스크립트(prepare_combat_conditions.py)로 데이터를 준비해야 합니다.' };
  }
  if (code === 'combat_member_profile_missing') {
    const id = message.split(':')[1]?.trim() ?? null;
    return { code, characterId: id, field: null, reason: 'missing', raw: message,
      text: `${id ? who(id) : '편성 멤버'}의 사거리·속성 데이터가 없습니다. ${PREPARE_HINT}` };
  }
  return null;
}

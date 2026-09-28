/**
 * Boss distance and boss weak element conditions (F-COND-1, UI part F-COND-U).
 *
 * Replaces the deck-wide "적정 거리" / "우월 코드" checkboxes with two per-member conditions:
 * - bossDistance: integer 0-100 or unset. A member gets the proper-distance bonus when its own weapon range
 *   [min, max] contains the distance (both ends inclusive, provisional). Range 0-0 (RL in the source data) means
 *   "no proper-distance bonus" and is flagged for confirmation.
 * - bossWeakElement: one of five elements or none. A member gets the element-advantage bonus when its element is
 *   the boss's weak element. No element matchup chart is used; the user states the weakness.
 * Decisions are the Director's provisional defaults (boss-distance-element-assignments-2026-09-28.ko.md).
 *
 * The Backend wire is not published yet. COND_WIRE.confirmed stays false: the live form keeps the old checkboxes
 * and requests. The new controls run against mock data until the Director announces the confirmed wire.
 * Every provisional wire detail (route, field names, element spelling) lives in this file only.
 */

export const COND_WIRE = Object.freeze({
  confirmed: false,
  // Provisional until Backend F-COND-B publishes the contract.
  rangesRoute: snapshotId => `/runtime/combat-ranges?snapshotId=${encodeURIComponent(snapshotId)}`
});

export const DISTANCE_MIN = 0;
export const DISTANCE_MAX = 100;

// code = presentation elementCode / icon name; wire = provisional contract spelling (Director: Electronic).
export const WEAK_ELEMENTS = Object.freeze([
  { code: 'fire', wire: 'Fire', label: '작열', en: 'Fire' },
  { code: 'water', wire: 'Water', label: '수냉', en: 'Water' },
  { code: 'wind', wire: 'Wind', label: '풍압', en: 'Wind' },
  { code: 'iron', wire: 'Iron', label: '철갑', en: 'Iron' },
  { code: 'electric', wire: 'Electronic', label: '전격', en: 'Electric' }
]);
export const WEAPON_LABELS = Object.freeze({ shotgun: '샷건', submachine_gun: '기관단총', assault_rifle: '소총',
  machine_gun: '머신건', sniper_rifle: '저격소총', rocket_launcher: '런처' });
const WEAPON_ORDER = ['shotgun', 'submachine_gun', 'assault_rifle', 'machine_gun', 'sniper_rifle', 'rocket_launcher'];

const isInt = v => Number.isInteger(v);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const elementByCode = code => WEAK_ELEMENTS.find(e => e.code === code || e.wire === code) ?? null;

export function createConditionState(initial = {}) {
  return { bossDistance: isInt(initial.bossDistance) ? initial.bossDistance : null,
    bossWeakElement: elementByCode(initial.bossWeakElement)?.code ?? null };
}

/** Strict: '' means unset; anything else must be an integer 0-100 (never clamped or rounded). */
export function parseDistance(text) {
  const trimmed = String(text ?? '').trim();
  if (trimmed === '') return null;
  if (!/^\d{1,3}$/.test(trimmed)) throw new Error('보스 거리는 0~100 사이 정수로 입력하세요.');
  const value = Number(trimmed);
  if (value < DISTANCE_MIN || value > DISTANCE_MAX) throw new Error('보스 거리는 0~100 사이 정수로 입력하세요.');
  return value;
}

export const distanceSummary = state => state.bossDistance === null ? '미설정' : String(state.bossDistance);
export function elementSummary(state) {
  const element = elementByCode(state.bossWeakElement);
  return element ? `${element.label}(${element.en})` : '없음';
}

/** Range status of one member at a distance. RL-style 0-0 is data, not an error, and needs confirmation. */
export function rangeStatus(range, distance) {
  if (!range || !isInt(range.min) || !isInt(range.max)) return { kind: 'unknown', text: '사거리 정보 없음' };
  if (range.min === 0 && range.max === 0) return { kind: 'no_bonus', text: '보너스 없음(데이터 0–0, 확인 필요)' };
  if (distance === null) return { kind: 'unset', text: `적정 ${range.min}–${range.max} · 거리 미설정` };
  return distance >= range.min && distance <= range.max
    ? { kind: 'in', text: `적정 거리 (${range.min}–${range.max})` }
    : { kind: 'out', text: `범위 밖 (${range.min}–${range.max})` };
}

/**
 * Normalises the range payload. Provisional shape (mock until the Backend contract):
 * { weaponRanges: [{ weaponCode, min, max, count, exceptions: [{ characterId, min, max }] }],
 *   members: { [characterId]: { min, max, element, weaponCode } }, source }
 */
export function normalizeRanges(payload) {
  const rows = Array.isArray(payload?.weaponRanges) ? payload.weaponRanges : [];
  const weaponRanges = rows.filter(r => r && typeof r.weaponCode === 'string')
    .map(r => ({ weaponCode: r.weaponCode, label: WEAPON_LABELS[r.weaponCode] ?? r.weaponCode,
      min: isInt(r.min) ? r.min : null, max: isInt(r.max) ? r.max : null, count: isInt(r.count) ? r.count : null,
      exceptions: (Array.isArray(r.exceptions) ? r.exceptions : []).filter(x => x && x.characterId != null)
        .map(x => ({ characterId: String(x.characterId), min: isInt(x.min) ? x.min : null, max: isInt(x.max) ? x.max : null })) }))
    .sort((a, b) => (WEAPON_ORDER.indexOf(a.weaponCode) + 1 || 99) - (WEAPON_ORDER.indexOf(b.weaponCode) + 1 || 99));
  const members = {};
  for (const [id, m] of Object.entries(payload?.members ?? {})) {
    members[String(id)] = { min: isInt(m?.min) ? m.min : null, max: isInt(m?.max) ? m.max : null,
      element: elementByCode(m?.element)?.code ?? null, weaponCode: typeof m?.weaponCode === 'string' ? m.weaponCode : null };
  }
  return { weaponRanges, members, source: typeof payload?.source === 'string' ? payload.source : null };
}

/** Per-member preview. Element comes from the range payload, else from presentation (elementCode). */
export function memberPreview(members, ranges, state) {
  return (members ?? []).map(m => {
    const data = ranges?.members?.[m.id] ?? null;
    const element = data?.element ?? elementByCode(m.elementCode)?.code ?? null;
    return {
      id: m.id, name: m.displayName ?? m.id,
      weaponCode: data?.weaponCode ?? m.weaponCode ?? null,
      distance: rangeStatus(data && { min: data.min, max: data.max }, state.bossDistance),
      element,
      elementMatch: element === null ? null : state.bossWeakElement !== null && element === state.bossWeakElement
    };
  });
}

/** Condition fields for a request. Confirmed wire only; otherwise null and the caller keeps the legacy bools. */
export function conditionWire(state, confirmed = COND_WIRE.confirmed) {
  if (!confirmed) return null;
  return { bossDistance: state.bossDistance, bossWeakElement: elementByCode(state.bossWeakElement)?.wire ?? null };
}

/**
 * Describes saved conditions. New fields -> per-member mode; old bools only -> "이전 방식(전원 적용)", shown as
 * stored and never reinterpreted as a distance or an element.
 */
export function describeConditionMode(combat) {
  if (!combat || typeof combat !== 'object') return { mode: 'unknown', text: '전투 조건 기록 없음' };
  const hasNew = 'bossDistance' in combat || 'bossWeakElement' in combat;
  const hasOld = typeof combat.properDistance === 'boolean' || typeof combat.elementAdvantage === 'boolean';
  if (hasNew) {
    const state = createConditionState(combat);
    return { mode: 'per_member', text: `보스 거리 ${distanceSummary(state)} · 약점 ${elementSummary(state)} (멤버별 판정)` };
  }
  if (hasOld) {
    const on = v => v === true ? '적용' : v === false ? '미적용' : '기록 없음';
    return { mode: 'legacy', text: `이전 방식(전원 적용) · 적정 거리 ${on(combat.properDistance)} · 우월 코드 ${on(combat.elementAdvantage)}` };
  }
  return { mode: 'unknown', text: '거리·속성 조건 기록 없음' };
}

const icon = code => `/editor/assets/ui/${code}.png`;

export function renderConditionControls(state, { legacy = null } = {}) {
  const element = elementByCode(state.bossWeakElement);
  return `<div class="cond-controls" role="group" aria-label="보스 거리·약점 속성">
    <div class="cond-control"><button type="button" class="cond-icon-btn" data-cond-open="distance" aria-haspopup="dialog" aria-label="보스 거리 설정"><span aria-hidden="true">↔</span></button>
      <span class="cond-value" data-cond-value="distance">적정 거리 · ${esc(distanceSummary(state))}</span></div>
    <div class="cond-control"><button type="button" class="cond-icon-btn" data-cond-open="element" aria-haspopup="dialog" aria-label="보스 약점 속성 설정">${element
      ? `<img src="${icon(`code-${element.code}`)}" alt="">` : '<span aria-hidden="true">◇</span>'}</button>
      <span class="cond-value" data-cond-value="element">약점 · ${esc(elementSummary(state))}</span></div>
    ${legacy ? `<span class="status-pill warning cond-legacy">${esc(legacy)}</span>` : ''}
  </div>`;
}

export function renderDistanceDialog(state, ranges, preview) {
  const table = ranges?.weaponRanges?.length ? `<div class="table-scroll"><table class="cond-range-table">
      <thead><tr><th>무기군</th><th>적정 사거리</th><th>인원</th><th>예외</th></tr></thead><tbody>${ranges.weaponRanges.map(r => {
        const range = r.min === 0 && r.max === 0 ? '0–0 · 보너스 없음(확인 필요)' : r.min === null ? '미확인' : `${r.min}–${r.max}`;
        const exceptions = r.exceptions.length ? r.exceptions.map(x => `${esc(x.characterId)}: ${x.min}–${x.max}`).join(', ') : '—';
        return `<tr data-weapon="${esc(r.weaponCode)}"><td>${esc(r.label)}</td><td>${esc(range)}</td><td>${r.count ?? '—'}</td><td>${exceptions}</td></tr>`;
      }).join('')}</tbody></table></div>` : '<p class="microcopy">무기군별 적정 사거리를 불러오지 못했습니다.</p>';
  const members = preview.length ? `<ul class="cond-member-list">${preview.map(m =>
    `<li data-member="${esc(m.id)}" data-distance-kind="${m.distance.kind}"><strong>${esc(m.name)}</strong> <span>${esc(WEAPON_LABELS[m.weaponCode] ?? '무기 미확인')}</span> <em>${esc(m.distance.text)}</em></li>`).join('')}</ul>` : '';
  const value = state.bossDistance ?? '';
  return `<form method="dialog" class="cond-dialog-body" data-cond-form="distance">
    <h3 id="cond-distance-title">보스 거리</h3>
    <p class="microcopy">0~100 정수. 각 니케는 자기 무기의 적정 사거리 안에 거리가 들어가면 적정 거리 보너스를 받습니다(평타만, 양끝 포함 · 잠정). 미설정이면 전원 보너스 없음.</p>
    <div class="cond-distance-inputs">
      <input type="range" name="distanceRange" min="${DISTANCE_MIN}" max="${DISTANCE_MAX}" step="1" value="${value === '' ? 50 : value}" aria-label="보스 거리 슬라이더" ${value === '' ? 'data-unset="true"' : ''}>
      <input type="number" name="distance" min="${DISTANCE_MIN}" max="${DISTANCE_MAX}" step="1" inputmode="numeric" value="${value}" placeholder="미설정" aria-label="보스 거리">
      <button type="button" data-cond-unset>미설정</button>
    </div>
    <p class="cond-error" role="alert" hidden></p>
    <h4>현재 덱</h4>${members}
    <h4>무기군별 적정 사거리</h4>${table}
    <p class="microcopy">무기군 표는 참고용이며 판정은 캐릭터별 값을 씁니다(예외 캐릭터 반영).${ranges?.source ? ` 원천 ${esc(ranges.source)}` : ''}</p>
    <div class="cond-actions"><button type="button" data-cond-cancel>취소</button><button type="submit" class="primary" value="apply">적용</button></div>
  </form>`;
}

export function renderElementDialog(state, preview) {
  const buttons = WEAK_ELEMENTS.map(e => {
    const members = preview.filter(m => m.element === e.code).map(m => m.name);
    return `<button type="button" class="cond-element ${state.bossWeakElement === e.code ? 'selected' : ''}" data-cond-element="${e.code}" aria-pressed="${state.bossWeakElement === e.code}">
      <img src="${icon(`code-${e.code}`)}" alt=""><span>${esc(e.label)} <small>${esc(e.en)}</small></span><small class="cond-element-members">${members.length ? `덱: ${esc(members.join(', '))}` : '덱에 없음'}</small></button>`;
  }).join('');
  return `<div class="cond-dialog-body" data-cond-form="element">
    <h3 id="cond-element-title">보스의 약점 속성</h3>
    <p class="cond-emphasis">보스의 약점 속성 — 이 속성 니케가 우월 코드 보너스를 받습니다.</p>
    <p class="microcopy">니케 자신의 속성이나 보스 자신의 속성이 아닙니다. 속성 상성표는 쓰지 않고, 고른 약점과 같은 속성의 니케만 보너스를 받습니다.</p>
    <div class="cond-element-grid">${buttons}
      <button type="button" class="cond-element ${state.bossWeakElement === null ? 'selected' : ''}" data-cond-element="" aria-pressed="${state.bossWeakElement === null}"><span>없음</span><small class="cond-element-members">전원 보너스 없음</small></button></div>
    <div class="cond-actions"><button type="button" data-cond-cancel>닫기</button></div>
  </div>`;
}

/**
 * Mounts the controls inside `container` and owns the two dialogs. No hidden form inputs: the request builder
 * reads getState(). ESC and the close buttons dismiss a dialog without applying.
 */
export function mountConditionControls(container, { getMembers = () => [], loadRanges = async () => null, onChange = () => {}, legacy = null } = {}) {
  let state = createConditionState();
  let ranges = null;
  let rangesPromise = null;
  let lastTrigger = null;
  const doc = container.ownerDocument;
  const dialog = doc.createElement('dialog');
  dialog.className = 'cond-dialog';
  doc.body.append(dialog);
  const preview = () => memberPreview(getMembers(), ranges, state);
  const paint = () => { container.innerHTML = renderConditionControls(state, { legacy }); };
  const ensureRanges = () => rangesPromise ??= Promise.resolve(loadRanges()).then(r => { ranges = r ? normalizeRanges(r) : null; return ranges; })
    .catch(() => { ranges = null; rangesPromise = null; return null; });
  const set = next => { state = { ...state, ...next }; legacy = null; paint(); onChange(state); };

  function openDistance(trigger) {
    lastTrigger = trigger;
    const render = () => {
      dialog.setAttribute('aria-labelledby', 'cond-distance-title');
      dialog.innerHTML = renderDistanceDialog(state, ranges, preview());
      const form = dialog.querySelector('form');
      const number = form.elements.distance, slider = form.elements.distanceRange, error = form.querySelector('.cond-error');
      let draft = state.bossDistance;
      const refresh = () => {
        const list = dialog.querySelector('.cond-member-list');
        if (!list) return;
        for (const m of memberPreview(getMembers(), ranges, { ...state, bossDistance: draft })) {
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
    render();
    dialog.showModal();
    if (!ranges) ensureRanges().then(() => { if (dialog.open && dialog.querySelector('[data-cond-form="distance"]')) render(); });
  }

  function openElement(trigger) {
    lastTrigger = trigger;
    dialog.setAttribute('aria-labelledby', 'cond-element-title');
    dialog.innerHTML = renderElementDialog(state, preview());
    dialog.querySelectorAll('[data-cond-element]').forEach(button => button.onclick = () => {
      dialog.close(); set({ bossWeakElement: button.dataset.condElement || null });
    });
    dialog.querySelector('[data-cond-cancel]').onclick = () => dialog.close();
    dialog.showModal();
    (dialog.querySelector('.cond-element.selected') ?? dialog.querySelector('.cond-element'))?.focus();
  }

  container.addEventListener('click', event => {
    const button = event.target.closest('[data-cond-open]');
    if (!button) return;
    if (button.dataset.condOpen === 'distance') openDistance(button); else openElement(button);
  });
  // Closing by apply, cancel or ESC returns focus to the (re-rendered) opener.
  dialog.addEventListener('close', () => {
    dialog.innerHTML = '';
    const kind = lastTrigger?.dataset?.condOpen;
    (kind ? container.querySelector(`[data-cond-open="${kind}"]`) : null)?.focus();
  });
  paint();
  return {
    getState: () => ({ ...state }),
    setState: next => { state = createConditionState(next); paint(); },
    isLegacy: () => legacy !== null,
    loadRanges: ensureRanges,
    dispose: () => dialog.remove()
  };
}

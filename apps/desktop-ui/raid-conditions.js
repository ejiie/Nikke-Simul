/**
 * Solo raid "전투 조건" cleanup and boss selection (F-COND-2, UI part F2-U; requests R3-R8).
 *
 * - R3 battle time fixed at 180 s, R7 shotgun coefficient fixed at "발사 1회" (per_trigger): no inputs, constant values.
 * - R5 critical stays selectable; the default is "확률 적용" (sample).
 * - R4 enemy DEF switches automatically: 30,925 from the start, 31,784 after the deck's cumulative damage passes
 *   2,000,000,000.
 * - R8 boss selection is display-and-save only (no battle effect yet).
 * Wire: Backend aa1b71e, docs/single-deck-compute-contract.ko.md "F2-B". New requests omit conditionProfile
 * (solo_raid) and rely on its defaults (defenseMode team_damage_threshold, DEF 30925); only an explicit replay of an
 * old result would send conditionProfile "legacy". Saved results carry battleConditions (top level / input), the
 * actual switch in result.defense (runs[].defense), and boss {id,name,imageUrl,season}; older records are read
 * through .../battle-conditions. The boss list is GET /api/presentation/solo-raid-bosses; the POST top-level bossId
 * stores the selection. `confirmed: false` reproduces the pre-wire form for comparison tests only.
 */

export const DURATION_SECONDS = 180;
export const DURATION_FRAMES = DURATION_SECONDS * 60;
export const PELLET_POLICY = 'per_trigger';
export const DEFAULT_CRIT_MODE = 'sample';
export const DEF_BEFORE = 30925;
export const DEF_AFTER = 31784;
export const DEF_SWITCH_DAMAGE = 2_000_000_000;

export const DEF_WIRE = Object.freeze({
  confirmed: true,
  // solo_raid defaults: defenseMode team_damage_threshold with the server-fixed start DEF; nothing to send.
  combatFields: () => ({}),
  replayRoute: id => `/runtime/skill-replays/${encodeURIComponent(id)}/battle-conditions`,
  experimentRoute: id => `/compute/experiments/${encodeURIComponent(id)}/battle-conditions`
});

export const BOSS_WIRE = Object.freeze({
  confirmed: true,
  listRoute: '/presentation/solo-raid-bosses',
  // Top-level request field on both POSTs; omitted/null = the default (dummy) boss.
  requestFields: bossId => (bossId ? { bossId } : {}),
  dummyId: 'dummy'
});

export const CRIT_OPTIONS = Object.freeze([
  { value: 'sample', label: '확률 적용' }, { value: 'off', label: '끔' }, { value: 'on', label: '항상 크리' }
]);

const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const num = v => Number(v).toLocaleString('ko-KR');
const text = v => typeof v === 'string' && v.trim() ? v.trim() : null;
const ELEMENT_LABELS = { fire: '작열', water: '수냉', wind: '풍압', iron: '철갑', electric: '전격',
  Fire: '작열', Water: '수냉', Wind: '풍압', Iron: '철갑', Electronic: '전격' };
const ELEMENT_ICONS = { Fire: 'fire', Water: 'water', Wind: 'wind', Iron: 'iron', Electronic: 'electric',
  fire: 'fire', water: 'water', wind: 'wind', iron: 'iron', electric: 'electric' };

/** Crit select options with the R5 default. */
export function critOptionsHtml(selected = DEFAULT_CRIT_MODE) {
  return CRIT_OPTIONS.map(o => `<option value="${o.value}"${o.value === selected ? ' selected' : ''}>${esc(o.label)}</option>`).join('');
}

/** Guidance under the conditions, matching the DEF mode actually sent. */
export function conditionsNote(confirmed = DEF_WIRE.confirmed) {
  const fixed = `전투 시간 ${DURATION_SECONDS}초 · 샷건 계수 발사 1회 고정.`;
  const def = confirmed
    ? `적 방어력은 ${num(DEF_BEFORE)}로 시작해 이 덱의 누적 대미지가 20억을 넘은 뒤부터 ${num(DEF_AFTER)}로 자동 전환됩니다.`
    : '방어력은 이번 검산 전체에 고정됩니다. 누적 대미지에 따른 자동 전환은 아직 적용하지 않습니다.';
  return `${fixed} ${def} 검산 스탯은 싱크로 레벨 400 고정입니다.`;
}

/** Combat fields for DEF: automatic mode once confirmed, otherwise the selected fixed value (old behaviour). */
export function defenseFields(selectedDefense, confirmed = DEF_WIRE.confirmed) {
  if (confirmed) return DEF_WIRE.combatFields();  // the fixed-DEF select is gone; the server applies the switch rule
  const value = Number(selectedDefense);
  return Number.isFinite(value) ? { enemyDefense: value } : {};
}

/**
 * Describes the conditions a saved result used, exactly as stored (R3/R4/R7 records made earlier keep their own
 * time, fixed DEF and shotgun setting). `defenseMode` is an optional Backend display object for the DEF mode.
 */
export function describeSavedCombat(combat, { battleConditions = null, boss = null } = {}) {
  const bc = battleConditions && typeof battleConditions === 'object' ? battleConditions : null;
  if ((!combat || typeof combat !== 'object') && !bc) return null;
  combat = combat && typeof combat === 'object' ? combat : {};
  const parts = [];
  const frames = Number.isFinite(bc?.durationFrames) ? bc.durationFrames : combat.durationFrames;
  if (Number.isFinite(frames)) parts.push(`${num(frames / 60)}초`);
  if (bc && text(bc.label)) {
    parts.push(bc.defenseMode === 'fixed' && Number.isFinite(bc.initialDefense)
      ? `${bc.label} · 방어력 ${num(bc.initialDefense)}`
      : Number.isFinite(bc.initialDefense) && Number.isFinite(bc.switchedDefense)
        ? `${bc.label} (${num(bc.initialDefense)} → ${num(bc.switchedDefense)})` : bc.label);
  } else if (Number.isFinite(combat.enemyDefense)) parts.push(`방어력 ${num(combat.enemyDefense)} 고정`);
  const crit = CRIT_OPTIONS.find(o => o.value === combat.critMode);
  if (crit) parts.push(`크리티컬 ${crit.label}`);
  const pellet = text(bc?.pelletCoefficientPolicy) ?? combat.pelletCoefficientPolicy;
  if (pellet === 'per_trigger') parts.push('샷건 계수 발사 1회');
  else if (pellet === 'per_pellet') parts.push('샷건 계수 펠릿마다');
  if (boss && text(boss.name)) parts.push(`보스 ${boss.name}`);
  return parts.length ? parts.join(' · ') : null;
}

/** The actual DEF over the battle (result.defense / runs[].defense). null = not recorded (older results). */
export function describeDefenseResult(defense, { names = null } = {}) {
  if (!defense || typeof defense !== 'object') return null;
  const initial = Number.isFinite(defense.initialDefense) ? defense.initialDefense : null;
  const final = Number.isFinite(defense.finalDefense) ? defense.finalDefense : initial;
  if (defense.mode === 'fixed') return initial === null ? null : `방어력 ${num(initial)} 고정`;
  const hit = defense.switchAfterHit && typeof defense.switchAfterHit === 'object' ? defense.switchAfterHit : null;
  if (!hit) return `방어력 전환 없음 · 끝까지 ${num(final ?? DEF_BEFORE)} (누적 피해 20억 이하)`;
  const who = hit.characterId != null ? (names?.get?.(String(hit.characterId)) ?? '니케') : '니케';
  const when = Number.isFinite(hit.frame) ? `${num(Math.round(hit.frame / 60 * 100) / 100)}초(${num(hit.frame)}프레임)` : '시점 미기록';
  const cumulative = Number.isFinite(hit.cumulativeDamage) ? ` · 누적 ${num(hit.cumulativeDamage)}` : '';
  return `방어력 ${num(hit.previousDefense ?? initial)} → ${num(hit.newDefense ?? final)} · ${when} ${who} 타격 후 전환${cumulative}`;
}

/**
 * GET /api/presentation/solo-raid-bosses -> { defaultBossId, bosses, notice }. Only `bosses` are selectable (Korean
 * names only). Diagnostics are never listed or shown by name; they become a short readiness notice.
 */
export function normalizeBosses(payload) {
  const defaultId = text(payload?.defaultBossId) ?? BOSS_WIRE.dummyId;
  const rows = Array.isArray(payload?.bosses) ? payload.bosses : Array.isArray(payload) ? payload : [];
  const bosses = rows.filter(b => b && text(String(b.id ?? '')) && text(b.name)).map(b => ({
    id: String(b.id), name: b.name.trim(), season: Number.isInteger(b.season) ? b.season : null,
    imageUrl: text(b.imageUrl), weakElement: text(b.weakElement), dummy: String(b.id) === defaultId || b.dummy === true }));
  bosses.sort((a, b) => Number(b.dummy) - Number(a.dummy) || (b.season ?? -1) - (a.season ?? -1));
  const diagnostics = Array.isArray(payload?.diagnostics) ? payload.diagnostics : [];
  const codes = new Set(diagnostics.map(d => d?.code));
  const notice = codes.has('boss_catalog_not_prepared') ? '보스 목록 준비 중 · 지금은 더미 보스만 선택할 수 있습니다.'
    : diagnostics.length ? '일부 보스 이름 준비 중'   // only when bosses were actually excluded
    : null;
  return { defaultId, bosses, notice };
}

function bossCard(boss, selected, { compact = false } = {}) {
  const element = boss.weakElement && ELEMENT_LABELS[boss.weakElement];
  const art = boss.imageUrl
    ? `<img class="boss-pick-image" src="${esc(boss.imageUrl)}" alt="" loading="lazy">`
    : `<span class="boss-pick-placeholder" aria-hidden="true">${boss.dummy ? '' : '보스'}</span>`;
  return `<button type="button" class="boss-pick-card${compact ? ' compact' : ''}${boss.dummy ? ' dummy' : ''}" data-boss-id="${esc(boss.id)}" aria-pressed="${selected}">
    <span class="boss-pick-art">${boss.season !== null ? `<span class="boss-pick-season">SEASON ${boss.season}</span>` : ''}${art}</span>
    <span class="boss-pick-content"><strong>${esc(boss.name)}</strong>
      <small>${boss.dummy ? '현재 동작 · 보스별 조건 없음' : element ? `기본 약점 ${esc(element)}` : '솔로 레이드'}</small></span>
    ${element ? `<img class="boss-pick-element" src="/editor/assets/ui/code-${ELEMENT_ICONS[boss.weakElement]}.png" alt="">` : ''}
  </button>`;
}

export function renderBossSelector(bosses, selectedId, { error = null, notice = null } = {}) {
  const selected = bosses.find(b => b.id === selectedId) ?? bosses[0] ?? null;
  return `<div class="boss-select" role="group" aria-label="보스 선택">
    <span class="boss-select-label">보스</span>
    ${selected ? bossCard(selected, true, { compact: true }).replace('class="boss-pick-card', 'data-boss-open="1" aria-haspopup="dialog" class="boss-pick-card') : '<span class="microcopy">보스 목록 없음</span>'}
    ${error ? `<p class="cond-load-error" data-boss-error role="alert">보스 목록을 불러오지 못했습니다. ${esc(error)}</p>` : ''}
    ${notice ? `<p class="microcopy boss-select-notice" data-boss-notice>${esc(notice)}</p>` : ''}
    <p class="microcopy boss-select-note">보스 선택은 표시·저장만 합니다. 보스별 약점·거리 반영은 다음 단계입니다.</p>
  </div>`;
}

export function renderBossDialog(bosses, selectedId, { notice = null } = {}) {
  return `<div class="cond-dialog-body boss-dialog-body">
    <h3 id="boss-dialog-title">보스 선택</h3>
    ${notice ? `<p class="microcopy" data-boss-notice>${esc(notice)}</p>` : ''}
    <div class="boss-pick-grid">${bosses.map(b => bossCard(b, b.id === selectedId)).join('')}</div>
    <div class="cond-actions"><button type="button" data-boss-cancel>닫기</button></div>
  </div>`;
}

/** Mounts the boss selector. Default = dummy boss. Selection is kept in memory and read by the request builder. */
export function mountBossSelector(container, { loadBosses = async () => null, onChange = () => {} } = {}) {
  let bosses = [{ id: BOSS_WIRE.dummyId, name: '더미 보스', season: null, imageUrl: null, weakElement: null, dummy: true }];
  let selectedId = BOSS_WIRE.dummyId, error = null, notice = null;
  const doc = container.ownerDocument;
  const dialog = doc.createElement('dialog');
  dialog.className = 'boss-dialog';
  dialog.setAttribute('aria-labelledby', 'boss-dialog-title');
  doc.body.append(dialog);
  const paint = () => { container.innerHTML = renderBossSelector(bosses, selectedId, { error, notice }); };
  const focusOpener = () => container.querySelector('[data-boss-open]')?.focus();
  const ready = Promise.resolve(loadBosses()).then(payload => {
    const list = normalizeBosses(payload);
    if (list.bosses.length) bosses = list.bosses;
    notice = list.notice;
    if (!bosses.some(b => b.id === selectedId)) selectedId = bosses.some(b => b.id === list.defaultId) ? list.defaultId : bosses[0].id;
    error = null; paint();
  }).catch(e => { error = e?.message ?? String(e); paint(); });
  function open() {
    dialog.innerHTML = renderBossDialog(bosses, selectedId, { notice });
    dialog.querySelectorAll('[data-boss-id]').forEach(button => button.onclick = () => {
      selectedId = button.dataset.bossId; dialog.close(); paint(); focusOpener(); onChange(selectedId);
    });
    dialog.querySelector('[data-boss-cancel]').onclick = () => dialog.close();
    dialog.showModal();
    (dialog.querySelector('[aria-pressed="true"]') ?? dialog.querySelector('[data-boss-id]'))?.focus();
  }
  container.addEventListener('click', event => { if (event.target.closest('[data-boss-open]')) open(); });
  dialog.addEventListener('close', () => { if (dialog.open) return; dialog.innerHTML = ''; if (!container.contains(doc.activeElement)) focusOpener(); });
  paint();
  return {
    ready,
    getSelected: () => bosses.find(b => b.id === selectedId) ?? null,
    getSelectedId: () => selectedId,
    dispose: () => dialog.remove()
  };
}

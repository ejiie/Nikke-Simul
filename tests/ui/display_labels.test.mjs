// U-FIX-4 (F2-Q-2): internal keys are shown as Korean labels; API/stored keys are untouched.
// No browser, no network. Usage: node tests/ui/display_labels.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = path.resolve(import.meta.dirname, '../..');
const labels = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/display-labels.js')));
const adapter = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/damage-log-adapter.js')));
const viewer = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/damage-log.js')));
const compute = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/compute-adapter.js')));
const cond = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/combat-conditions.js')));
const raid = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/raid-conditions.js')));
const { own } = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/own-lookup.js')));

const checks = [];
async function check(name, fn) {
  try { await fn(); checks.push({ name, passed: true }); }
  catch (error) { checks.push({ name, passed: false, error: String(error.message).split('\n').slice(0, 6).join(' | ') }); }
}
const names = new Map([['5004', '앨리스'], ['5009', '누아르']]);
const nameOf = id => names.get(id) ?? null;
const leak = /overload:|cube:|collection:|equipment:|manual:|function:|skill:|StatAtk|native_|basis |\b50\d\d\b|#/;

await check('source_keys_to_korean', () => {
  const cases = [
    ['overload:5004:head:1:StatAtk', '앨리스 · 머리 1번 줄 · 공격력'],
    ['overload:5009:leg:3:StatChargeDamage', '누아르 · 다리 3번 줄 · 차지 대미지'],
    ['overload:9999:arm:2:NewOption', '이름 미확인 · 팔 2번 줄 · 오버로드 옵션'],
    ['cube:7000001:StatAtk', '큐브 · 공격력'], ['cube:7000001:Mystery', '큐브 효과'],
    ['collection:123:StatCriticalDamage', '소장품 · 크리티컬 대미지'], ['collection:123:x', '소장품 효과'],
    ['equipment:torso', '장비 · 몸통'], ['manual:attack:2', '직접 입력한 버프 2'],
    ['function:227110701', '스킬 효과'],  // U-FIX-5: no function numbers ['skill:5004:1', '앨리스 · 스킬 효과'],
    ['synthetic_f2u_threshold', '기타 효과'], ['weird:5004:raw', '기타 효과'], ['', '기타 효과']
  ];
  for (const [key, want] of cases) assert.equal(labels.describeSourceKey(key, { nameOf }), want, key);
  // A function key the caller can resolve is shown as character · slot.
  assert.equal(labels.describeSourceKey('function:227110701', { resolveFunction: id => id === '227110701' ? '누아르 · 스킬 1' : null }), '누아르 · 스킬 1');
  for (const [key] of cases) assert.ok(!/\b50\d\d\b|9999|7000001|:/.test(labels.describeSourceKey(key, { nameOf })), key);
  assert.equal(labels.basisLabel('native_recipient'), '수혜자 기초 스탯 기준');
  assert.equal(labels.basisLabel('unexpected_basis'), '적용 기준 미확인');
  assert.equal(labels.basisLabel(null), '적용 기준 미기록');
});

await check('audit_attack_sources_show_names_not_keys', () => {
  const entry = { hitId: 1, frame: 60, damage: 10, calculation: { policy: 'client_f32', terms: [] }, buffs: [],
    hit: { statAttack: 100, attackBuffs: [{ source: 'overload:5004:head:1:StatAtk', rate: 0.0477, stacks: 1, rawRate10000: '477' },
      { source: 'cube:7000001:StatAtk', rate: 0.05, stacks: 1 }],
    runtimeAttackBuffs: [{ source: 'skill:5009:227110701', rate: 0.1, stacks: 1 }, { source: 'synthetic_f2u_threshold', rate: 100, stacks: 1 }],
    attackFlatBuffs: [{ source: 'function:127131004', amount: 50, exactAmount: '50' }] } };
  const ctx = adapter.createAuditContext({ inputs: [{ weapon: { characterId: '5009' }, skills: { slots: { skill1: { functionIds: [227110701], functionPhases: {} } } } }] },
    [{ id: '5004', displayName: '앨리스' }, { id: '5009', displayName: '누아르' }]);
  const audit = adapter.buildHitAudit(entry, ctx);
  assert.deepEqual(audit.attackSources.map(s => s.source), ['앨리스 · 머리 1번 줄 · 공격력', '큐브 · 공격력', '누아르 · 스킬 1', '기타 효과', '스킬 효과']);
  assert.equal(audit.attackSources[0].valueText, '+4.77%');
  const text = viewer.renderDamageAuditPanel({ hitId: 1, shotId: 1, seconds: 1 }, audit).replace(/<[^>]+>/g, ' ');
  assert.ok(text.includes('상시 비율 · 앨리스 · 머리 1번 줄 · 공격력'));
  assert.ok(!/overload:|cube:|skill:|synthetic_f2u|StatAtk/.test(text), 'raw key in the panel text');
  assert.ok(!/함수|227110701|127131004/.test(text), 'function number in the panel text'); // U-FIX-5
  // The stored entry is untouched (display-only).
  assert.equal(entry.hit.attackBuffs[0].source, 'overload:5004:head:1:StatAtk');
});

await check('effect_basis_and_unknown_type_labels', () => {
  const d = adapter.describeBuffSnapshot({ effect: { source: '5004', target: '5004', type: 0, value: 1, stacks: 1, basis: 'native_recipient', expiresAt: null } }, 0);
  assert.equal(d.basisText, '수혜자 기초 스탯 기준');
  const u = adapter.describeBuffSnapshot({ effect: { source: '5004', target: '5004', type: 999, value: 1, stacks: 1, basis: 'odd_basis', expiresAt: null } }, 0);
  assert.equal(u.label, '미해석 효과'); assert.equal(u.basisText, '적용 기준 미확인');
  assert.ok(!leak.test(`${d.basisText} ${u.label} ${u.basisText}`));
});

// U-FIX-6: server texts are shown in Korean only; log-target notices use names.
await check('server_messages_korean_only', () => {
  const f = labels.friendlyServerMessage;
  assert.equal(f('boss_id_unknown', 400), '선택한 보스를 찾을 수 없습니다. 보스를 다시 선택하세요.');
  assert.equal(f('combat_profile_invalid: combatProfiles.characters.5004.bonusRangeMin: missing', 409), '사거리·속성 데이터에 오류가 있습니다.');
  assert.equal(f('combat_profile_catalog_missing: prepare pinned public roster catalog', 409), '사거리·속성 데이터가 준비되지 않았습니다.');
  assert.equal(f('statAttack_must_be_integer_never_truncated', 400), '요청을 처리하지 못했습니다 (HTTP 400).');
  assert.equal(f('Unexpected server failure', 500), '요청을 처리하지 못했습니다 (HTTP 500).');
  assert.equal(f('평타 계수가 없습니다.', 400), '평타 계수가 없습니다.');                       // registered server text is kept
  assert.equal(f('편성을 먼저 저장하세요.', 400), '요청을 처리하지 못했습니다 (HTTP 400).');   // unregistered Korean text is not shown either
  assert.equal(f('캐릭터 5004 데이터 없음', 400), '요청을 처리하지 못했습니다 (HTTP 400).');
  assert.equal(f(null), '요청을 처리하지 못했습니다.');
});

await check('log_target_notice_uses_names', async () => {
  const members = [{ id: '5004', displayName: '앨리스' }, { id: '5011', displayName: '리타' }];
  const replay = { id: 'r1', conditions: {}, result: { damageLog: { schemaVersion: 1, characterId: '5004', status: 'complete', entries: [], totalDamage: 1 } } };
  const embedded = await adapter.fetchDamageLog(async () => { throw new Error('no server'); }, 'r1', '5011', replay, members);
  assert.equal(embedded.message, '현재 리플레이는 앨리스의 대미지 로그만 수집되었습니다. 리타의 로그를 수집하려면 대상을 선택하고 다시 검산하세요.');
  const server = await adapter.fetchDamageLog(async () => ({ exportSchemaVersion: 1, collectionStatus: 'complete',
    replay: { result: { damageLog: { schemaVersion: 1, characterId: '5004', status: 'complete', entries: [], totalDamage: 1 } } } }), 'r1', '5011', { id: 'r1' }, members);
  assert.ok(server.message.startsWith('현재 리플레이는 앨리스의') && server.message.includes('리타의 로그'));
  const unknown = await adapter.fetchDamageLog(async () => { throw new Error('x'); }, 'r1', '5044', replay, members);
  assert.ok(unknown.message.includes('이름 미확인 니케의 로그') && !/50\d\d/.test(unknown.message + embedded.message + server.message));
});

await check('compute_reason_codes_korean', () => {
  const r = labels.reasonLabel;
  assert.equal(r('bounded_workload_benchmark'), '제한된 후보 실측으로 선택');
  assert.equal(r('full_battle_provider_not_implemented'), '전체 전투 GPU 계산 미구현');
  assert.equal(r('some_new_reason_code'), '기타 사유');
  assert.equal(r('사용자 지정'), '기타 사유'); // U-FIX-7: allow-list only
  assert.equal(r(null), null);
});

// U-FIX-7 (QA 2nd block): server text is shown only when registered (allow-list); no deny-list of "code-like" shapes.
await check('unregistered_server_text_is_never_shown_whatever_it_contains', () => {
  const registered = '평타 계수가 없습니다.';
  const mixed = ['검사 필요: effectiveAttack', '검사 필요: calculation.terms', '검사 필요: terms[].name', '검사 필요: terms[0].operation',
    '검사 필요: attackBuffs[0].source', '검사 필요: cache/replays', String.raw`검사 필요: runtime\catalog`, '검사 필요: skill1Rate', '검사 필요: multiply 1.25; qa_unknown_transform',
    '검사 필요: 0x10', '정상처럼 보이는 한국어 문장입니다.', 'plain english', `${registered} terms[0].operation`, `${registered}
`, ` ${registered}`];
  for (const raw of mixed) {
    assert.equal(labels.koreanText(raw, '대체'), '대체', raw);
    assert.equal(labels.friendlyServerMessage(raw, 400), '요청을 처리하지 못했습니다 (HTTP 400).', raw);
    assert.equal(labels.errorText(Object.assign(new Error(raw), { status: 500 })), '요청을 처리하지 못했습니다 (HTTP 500).', raw);
    assert.equal(labels.reasonLabel(raw), '기타 사유', raw);
  }
  assert.equal(labels.koreanText(registered, '대체'), registered);
  assert.equal(labels.errorText(new Error(registered)), registered);
  assert.ok(labels.isRegisteredMessage('수집기를 완료하지 못했습니다.'));
  // UI-authored Korean (display errors, labels) keeps its numbers and abbreviations.
  for (const ok of ['배율 3.5배 적용', 'GPU를 사용할 수 없습니다.', 'LV.5 달성', '서버 로그 내보내기 실패 (HTTP 500)'])
    assert.equal(labels.errorText(labels.displayError(ok)), ok, ok);
  assert.equal(labels.friendlyServerMessage('gpu_unavailable'), 'GPU를 사용할 수 없습니다.');
});

await check('snapshot_change_lines_use_registered_templates', () => {
  const known = new Set(['앨리스']);
  const d = labels.describeChange;
  assert.equal(d('앨리스: 스펙 변경', known), '앨리스: 스펙 변경');
  assert.equal(d('앨리스: head 장비/잠금 변경', known), '앨리스: 머리 장비/잠금 변경');
  assert.equal(d('최초 수집: 12명', known), '최초 수집: 12명');
  assert.equal(d('계정 스탯 변경', known), '계정 스탯 변경');
  assert.equal(d('5004: 신규 수집', known), '이름 미확인 니케: 신규 수집');
  assert.equal(d('앨리스: terms[0].operation 변경', known), '변경 내역 (상세 미확인)');
});

// U-FIX-7 QA: a log lookup without a log shows a Korean notice and never builds the graph (U7-Q-3).
await check('missing_damage_log_shows_korean_notice_without_exception', async () => {
  const container = { innerHTML: '', querySelectorAll: () => [] };
  const select = { onchange: null };
  globalThis.document = { getElementById: id => id === 'damage-log-container' ? container : id === 'log-character-select' ? select : null };
  try {
    const members = [{ id: '5004', displayName: '앨리스', burstStep: 3 }];
    for (const failure of [new TypeError('Failed to fetch'), Object.assign(new Error('boom'), { status: 500 })]) {
      const api = async () => { throw failure; };
      const v = viewer.createDamageLogViewer({ api, getSnapshot: () => ({ id: 's' }), getMembersWithMeta: () => members, getToken: () => '', status: () => {} });
      v.setReplay({ id: 'r1', result: { totalDamage: 1145772 }, conditions: {} });
      await new Promise(resolve => setTimeout(resolve, 50));
      const text = container.innerHTML;
      assert.ok(text.includes('피해 로그를 불러오지 못했습니다'), text.slice(0, 200));
      assert.ok(!text.includes('Failed to fetch') && !text.includes('boom') && !text.includes('damage-graph-svg'));
    }
  } finally { delete globalThis.document; }
});

await check('registered_messages_match_server_sources', async () => {
  const { spawnSync } = await import('node:child_process');
  const r = spawnSync(process.execPath, [path.join(root, 'tests/ui/tools/gen_registered_messages.mjs'), '--check'], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr + r.stdout);
});

// U-FIX-7 QA 3rd block (U7-Q-4/5): label tables answer own keys only; inherited members never reach the screen.
const INHERITED = ['constructor', 'toString', '__proto__', 'hasOwnProperty', 'valueOf', 'isPrototypeOf', 'toLocaleString'];
await check('own_lookup_ignores_inherited_members', () => {
  for (const key of INHERITED) {
    assert.equal(own({ a: 1 }, key), undefined, key);
    assert.equal(own(Object.create(null), key), undefined, key);
  }
  assert.equal(own({ a: 1 }, 'a'), 1);
  assert.equal(own({ 1: 'x' }, 1), 'x');
  assert.equal(own(null, 'a'), undefined);
  assert.equal(own({ a: 1 }, { toString() { return 'a'; } }), undefined);
});

await check('label_tables_never_show_inherited_members', () => {
  const bad = /function|\[object|native code|undefined|null|constructor|toString|__proto__|hasOwnProperty|valueOf|isPrototypeOf/;
  for (const key of INHERITED) {
    const shown = [
      labels.slotLabel(key), labels.optionLabel(key) ?? '없음', labels.basisLabel(key), labels.reasonLabel(key),
      labels.friendlyServerMessage(key, 400), labels.errorText(new Error(key)),
      labels.describeSourceKey(`overload:5004:${key}:1:${key}`, { nameOf: () => '앨리스' }),
      labels.describeSourceKey(`cube:1:${key}`), labels.describeSourceKey(`${key}:1:2`),
      compute.describeComputeError(key), compute.describeUnsupportedReason(key) ?? '없음',
      compute.describeBatch({ id: 'b', state: key }).stateLabel,
      compute.describeHardwareProfile({ gpus: [{ id: 'g', name: 'GPU', stages: { runtime: key }, reason: key }] }).devices.map(d => d.stageLabel).join(' '),
      adapter.termLabel(key, 'client_f32'), adapter.termLabel(key, 'legacy_term_floor'),
      adapter.describeStepOperation(key, key, 'client_f32'), adapter.describeStepOperation('final', key, 'final_round_even'),
      cond.normalizeCatalog({ weaponRanges: [{ weaponType: key, ranges: [] }] }).weaponRanges.map(r => r.label).join(' '),
      cond.describeCombatProfileError({ code: 'combat_profile_invalid', details: { field: `a.${key}`, reason: key, characterId: key } })?.text ?? '',
      cond.describeCompatibility({ mode: key }).text
    ];
    for (const text of shown) assert.ok(!bad.test(String(text).replace(/미확인|미구현|미기록|미해석/g, '')), `${key}: ${text}`);
  }
});

await check('unregistered_mode_and_values_are_not_echoed', () => {
  for (const mode of ['qa_unknown_mode', 'terms[0].operation', 'skill1Rate', '0x10']) {
    const d = cond.describeCompatibility({ mode, label: '검사 필요: effectiveAttack' });
    assert.equal(d.mode, 'unknown');
    assert.equal(d.text, '알 수 없는 조건 모드', mode);
    assert.ok(!d.text.includes(mode));
  }
  assert.equal(cond.describeCompatibility({ mode: 'legacy_global', label: '이전 방식(전원 적용)', legacyProperDistance: true }).text.startsWith('이전 방식(전원 적용)'), true);
  const saved = raid.describeSavedCombat({ durationFrames: 10800 }, { battleConditions: { label: '검사 필요: terms[0].operation', defenseMode: 'fixed', initialDefense: 30925 } });
  assert.ok(!saved.includes('terms[0]') && saved.includes('전투 조건'), saved);
  const registeredLabel = raid.describeSavedCombat({}, { battleConditions: { label: '이전 방식(고정 방어력)', defenseMode: 'fixed', initialDefense: 30925 } });
  assert.ok(registeredLabel.includes('이전 방식(고정 방어력)'));
});

const failed = checks.filter(c => !c.passed);
console.log(JSON.stringify({ total: checks.length, failed: failed.length, checks }, null, 2));
if (failed.length) process.exit(1);

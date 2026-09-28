// F-COND-U: boss distance / weak element condition model checks against the confirmed F-COND-B wire shape.
// Evidence type: MOCK ONLY (fixtures/combat-conditions-mock.json). No browser, no network.
// Usage: node tests/ui/combat_conditions.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = path.resolve(import.meta.dirname, '../..');
const cond = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/combat-conditions.js')));
const mock = JSON.parse(fs.readFileSync(path.join(import.meta.dirname, 'fixtures/combat-conditions-mock.json'), 'utf8'));
const catalog = cond.normalizeCatalog(mock.catalog);
const profiles = cond.normalizeMembers(mock.members);
const members = [
  { id: '5011', displayName: '리타' }, { id: '5008', displayName: '블랑' }, { id: '5009', displayName: '누아르' },
  { id: '5004', displayName: '앨리스' }, { id: '5044', displayName: '모더니아' }
];

const checks = [];
async function check(name, fn) {
  try { await fn(); checks.push({ name, passed: true }); }
  catch (error) { checks.push({ name, passed: false, error: String(error.message).split('\n').slice(0, 6).join(' | ') }); }
}

await check('confirmed_wire_routes_and_fields', () => {
  assert.equal(cond.COND_WIRE.confirmed, true);
  assert.equal(cond.COND_WIRE.catalogRoute, '/runtime/combat-conditions');
  assert.equal(cond.COND_WIRE.membersRoute('snap 1', ['5011', '5008']), '/snapshots/snap%201/combat-conditions?characterIds=5011,5008');
  assert.equal(cond.COND_WIRE.replayCompatibilityRoute('r1'), '/runtime/skill-replays/r1/condition-compatibility');
  assert.equal(cond.COND_WIRE.experimentCompatibilityRoute('e1'), '/compute/experiments/e1/condition-compatibility');
  assert.deepEqual(cond.conditionWire({ bossDistance: 35, bossWeakElement: 'fire' }), { bossDistance: 35, bossWeakElement: 'Fire' });
  // "All unset" is the new mode with both fields explicitly null; the old bools never appear.
  const unset = cond.conditionWire(cond.createConditionState());
  assert.deepEqual(unset, { bossDistance: null, bossWeakElement: null });
  assert.ok(!('properDistance' in unset) && !('elementAdvantage' in unset));
  assert.equal(cond.conditionWire({ bossDistance: 0, bossWeakElement: 'electric' }).bossWeakElement, 'Electronic');
  assert.equal(cond.conditionWire({ bossDistance: 0, bossWeakElement: null }, false), null);
});

await check('distance_parse_is_strict_integer_0_100', () => {
  assert.equal(cond.parseDistance(''), null);
  assert.equal(cond.parseDistance(' 0 '), 0);
  assert.equal(cond.parseDistance('100'), 100);
  for (const bad of ['-1', '101', '35.5', '1e2', 'abc', '3 5']) assert.throws(() => cond.parseDistance(bad), /0~100/, bad);
});

await check('range_status_boundaries_inclusive_and_rl', () => {
  const r = { min: 15, max: 35, rangeBonusAvailable: true };
  assert.equal(cond.rangeStatus(r, 14).kind, 'out');
  assert.equal(cond.rangeStatus(r, 15).kind, 'in');
  assert.equal(cond.rangeStatus(r, 35).kind, 'in');
  assert.equal(cond.rangeStatus(r, 36).kind, 'out');
  assert.equal(cond.rangeStatus(r, null).kind, 'unset');
  assert.equal(cond.rangeStatus(profiles['5009'], 0).kind, 'no_bonus');
  assert.match(cond.rangeStatus(profiles['5009'], 0).text, /보너스 없음\(데이터 0–0, 확인 필요\)/);
  assert.equal(cond.rangeStatus(null, 30).kind, 'unknown');
});

await check('catalog_and_member_profiles', () => {
  assert.deepEqual(catalog.weaponRanges.map(r => r.weaponType), ['SG', 'SMG', 'AR', 'MG', 'SR', 'RL']);
  const sr = catalog.weaponRanges.find(r => r.weaponType === 'SR');
  assert.deepEqual([sr.typical.min, sr.typical.max, sr.characterCount], [45, 100, 36]);
  assert.deepEqual(sr.exceptions.map(x => [x.characterId, x.name, x.min, x.max, x.element]), [['5042', 'Harran', 25, 45, 'electric']]);
  assert.equal(catalog.weaponRanges.find(r => r.weaponType === 'RL').rangeBonusAvailable, false);
  assert.equal(catalog.icons.electric, '/editor/assets/ui/code-electric.png');
  assert.equal(catalog.gameVerified, false);
  assert.deepEqual(Object.keys(profiles).sort(), ['5004', '5008', '5009', '5011', '5044']); // display order comes from the deck
  assert.equal(profiles['5004'].element, 'electric');
});

await check('member_preview_mixed_deck', () => {
  const preview = cond.memberPreview(members, profiles, { bossDistance: 35, bossWeakElement: 'fire' });
  assert.deepEqual(preview.map(m => m.distance.kind), ['in', 'in', 'no_bonus', 'out', 'in']);
  assert.deepEqual(preview.map(m => m.elementMatch), [true, false, true, false, false]);
  assert.deepEqual(preview.map(m => m.weaponType), ['SMG', 'MG', 'RL', 'SR', 'SR']);
  const none = cond.memberPreview(members, profiles, cond.createConditionState());
  assert.ok(none.every(m => m.elementMatch === false));
  // Without profiles nothing is guessed; presentation element/weapon only fill the display.
  const unknown = cond.memberPreview([{ id: 'x', elementCode: 'iron', weaponCode: 'shotgun' }], null, { bossDistance: 30, bossWeakElement: 'iron' });
  assert.equal(unknown[0].distance.kind, 'unknown'); assert.equal(unknown[0].elementMatch, true); assert.equal(unknown[0].weaponType, 'SG');
});

await check('distance_dialog_table', () => {
  const html = cond.renderDistanceDialog({ bossDistance: 35, bossWeakElement: null }, catalog, cond.memberPreview(members, profiles, { bossDistance: 35, bossWeakElement: null }));
  assert.ok(html.includes('0–0 · 보너스 없음(확인 필요)'));
  assert.ok(html.includes('Harran (#5042): 25–45'));
  assert.equal((html.match(/data-weapon=/g) ?? []).length, 6);
  assert.ok(html.includes('실게임 검증 전'));
  const failed = cond.renderDistanceDialog(cond.createConditionState(), null, [], { error: 'combat_profile_catalog_missing' });
  assert.ok(failed.includes('불러오지 못했습니다. combat_profile_catalog_missing'));
});

await check('element_dialog_states_boss_weakness_explicitly', () => {
  const preview = cond.memberPreview(members, profiles, { bossDistance: null, bossWeakElement: 'fire' });
  const html = cond.renderElementDialog({ bossDistance: null, bossWeakElement: 'fire' }, preview, catalog);
  assert.ok(html.includes('보스의 약점 속성 — 이 속성 니케가 우월 코드 보너스를 받습니다'));
  assert.ok(html.includes('니케 자신의 속성이나 보스 자신의 속성이 아닙니다'));
  assert.equal((html.match(/data-cond-element="/g) ?? []).length, 6);
  for (const e of ['fire', 'water', 'wind', 'iron', 'electric']) assert.ok(html.includes(`/editor/assets/ui/code-${e}.png`), e);
  assert.ok(html.includes('덱: 리타, 누아르'));
  assert.match(html, /data-cond-element="fire" aria-pressed="true"/);
});

await check('compatibility_display_uses_backend_mode', () => {
  const fresh = cond.describeCompatibility({ mode: 'per_member', label: '보스 거리·약점(멤버별)', legacyProperDistance: false,
    legacyElementAdvantage: false, bossDistance: 35, bossWeakElement: 'Fire' });
  assert.equal(fresh.mode, 'per_member');
  assert.equal(fresh.text, '보스 거리·약점(멤버별) · 보스 거리 35 · 약점 작열(Fire)');
  const unset = cond.describeCompatibility({ mode: 'per_member', label: '보스 거리·약점(멤버별)', bossDistance: null, bossWeakElement: null });
  assert.equal(unset.text, '보스 거리·약점(멤버별) · 보스 거리 미설정 · 약점 없음');
  const legacy = cond.describeCompatibility({ mode: 'legacy_global', label: '이전 방식(전원 적용)', legacyProperDistance: true,
    legacyElementAdvantage: false, bossDistance: null, bossWeakElement: null });
  assert.equal(legacy.mode, 'legacy');
  assert.equal(legacy.text, '이전 방식(전원 적용) · 적정 거리 적용 · 우월 코드 미적용');
  assert.equal(cond.describeCompatibility(null).mode, 'unknown');
  assert.equal(cond.describePlannedConditions({ bossDistance: 35, bossWeakElement: 'fire' }), '보스 거리 35 · 약점 작열(Fire) (멤버별 판정)');
  const controls = cond.renderConditionControls({ bossDistance: 35, bossWeakElement: 'fire' }, { legacy: legacy.text, catalog });
  assert.ok(controls.includes('적정 거리 · 35') && controls.includes('약점 · 작열(Fire)') && controls.includes('이전 방식(전원 적용)'));
  assert.ok(!controls.includes('type="hidden"'));
});

await check('escaping', () => {
  const evil = cond.normalizeCatalog({ weaponRanges: [{ weaponType: '<b>x</b>', ranges: [{ min: 1, max: 2, isTypical: true }],
    exceptions: [{ characterId: '<img>', name: '<i>n</i>', bonusRangeMin: 1, bonusRangeMax: 2 }] }] });
  const html = cond.renderDistanceDialog(cond.createConditionState(), evil,
    [{ id: '"q', name: '<i>n</i>', weaponType: null, distance: { kind: 'unset', text: '<s>' } }]);
  assert.ok(!html.includes('<b>x</b>') && !html.includes('<img>') && !html.includes('<i>n</i>') && !html.includes('<s>'));
});

// U-FIX-2 (B-FIX-2 wire): combat profile data errors get a Korean diagnostic, never a connection failure.
const apiError = (status, body) => Object.assign(new Error(body.message ?? `요청 실패 (${status})`), { status, code: body.code ?? null, details: body });
await check('combat_profile_invalid_diagnostics', () => {
  const names = new Map([['5004', '앨리스']]);
  const body = { code: 'combat_profile_invalid', message: 'combat_profile_invalid: combatProfiles.characters.5004.bonusRangeMin: missing',
    characterId: '5004', field: 'combatProfiles.characters.5004.bonusRangeMin', reason: 'missing' };
  const d = cond.describeCombatProfileError(apiError(409, body), names);
  assert.equal(d.code, 'combat_profile_invalid');
  assert.equal(d.text, '사거리·속성 데이터 오류 · 앨리스(#5004) · 최소 사거리(bonusRangeMin) · 값 없음(키 누락). 서버 runtime의 사거리·속성 데이터 확인 후 prepare_combat_conditions.py로 다시 준비해야 합니다.');
  assert.equal(d.raw, 'combat_profile_invalid: combatProfiles.characters.5004.bonusRangeMin: missing');
  const reasons = { null: '값이 null', wrong_type: '자료형 오류', out_of_range: '범위 오류(0–100, 최소 ≤ 최대)', unsupported_value: '지원하지 않는 값',
    id_mismatch: 'ID 불일치', weapon_mismatch: '무기군 불일치', hash_mismatch: '출처 해시 불일치' };
  for (const [reason, label] of Object.entries(reasons))
    assert.ok(cond.describeCombatProfileError(apiError(409, { ...body, reason }), names).text.includes(label), reason);
  const element = cond.describeCombatProfileError(apiError(409, { ...body, characterId: '9999', field: 'combatProfiles.characters.9999.element', reason: 'unsupported_value' }), names);
  assert.match(element.text, /#9999 · 속성\(element\) · 지원하지 않는 값/);
  const source = cond.describeCombatProfileError(apiError(409, { ...body, characterId: null, field: 'combatProfiles.source.sha256', reason: 'hash_mismatch' }));
  assert.match(source.text, /카탈로그·출처 · combatProfiles\.source\.sha256 · 출처 해시 불일치/);
  // Code only in the message still maps (older error shape).
  assert.equal(cond.describeCombatProfileError(apiError(409, { message: body.message })).code, 'combat_profile_invalid');
});

await check('catalog_missing_member_missing_and_unrelated', () => {
  const missing = cond.describeCombatProfileError(apiError(409, { message: 'combat_profile_catalog_missing' }));
  assert.match(missing.text, /combatProfiles\)가 준비되지 않았습니다.*prepare_combat_conditions\.py/);
  const member = cond.describeCombatProfileError(apiError(400, { message: 'combat_member_profile_missing:5011' }), new Map([['5011', '리타']]));
  assert.match(member.text, /^리타\(#5011\)의 사거리·속성 데이터가 없습니다/);
  assert.equal(cond.describeCombatProfileError(apiError(400, { message: 'boss_conditions_mixed_with_legacy' })), null);
  assert.equal(cond.describeCombatProfileError(new TypeError('Failed to fetch')), null);
});

await check('dialogs_show_catalog_and_member_errors', () => {
  const html = cond.renderDistanceDialog(cond.createConditionState(), null, [], { error: 'E-CAT', membersError: 'E-MEM' });
  assert.ok(html.includes('data-cond-error="catalog"') && html.includes('E-CAT'));
  assert.ok(html.includes('data-cond-error="members"') && html.includes('멤버 사거리·속성을 불러오지 못했습니다. E-MEM'));
  const el = cond.renderElementDialog(cond.createConditionState(), [], null, { error: 'E-MEM' });
  assert.ok(el.includes('data-cond-error="members"') && el.includes('E-MEM'));
});

const failed = checks.filter(c => !c.passed);
console.log(JSON.stringify({ evidence: 'mock_only_not_api', total: checks.length, failed: failed.length, checks }, null, 2));
if (failed.length) process.exit(1);

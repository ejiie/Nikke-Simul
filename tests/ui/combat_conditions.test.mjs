// F-COND-U: boss distance / weak element condition model checks. Evidence type: MOCK ONLY
// (fixtures/combat-ranges-mock.json, provisional wire). No browser, no network.
// Usage: node tests/ui/combat_conditions.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = path.resolve(import.meta.dirname, '../..');
const cond = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/combat-conditions.js')));
const mock = JSON.parse(fs.readFileSync(path.join(import.meta.dirname, 'fixtures/combat-ranges-mock.json'), 'utf8'));
const ranges = cond.normalizeRanges(mock);
const members = [
  { id: '5011', displayName: '리타' }, { id: '5008', displayName: '블랑' }, { id: '5009', displayName: '누아르' },
  { id: '5004', displayName: '앨리스' }, { id: '5044', displayName: '모더니아' }
];

const checks = [];
async function check(name, fn) {
  try { await fn(); checks.push({ name, passed: true }); }
  catch (error) { checks.push({ name, passed: false, error: String(error.message).split('\n').slice(0, 6).join(' | ') }); }
}

await check('wire_unconfirmed_keeps_live_requests', () => {
  assert.equal(cond.COND_WIRE.confirmed, false);
  assert.equal(cond.conditionWire({ bossDistance: 35, bossWeakElement: 'fire' }), null);
  assert.deepEqual(cond.conditionWire({ bossDistance: 35, bossWeakElement: 'fire' }, true), { bossDistance: 35, bossWeakElement: 'Fire' });
  assert.deepEqual(cond.conditionWire(cond.createConditionState(), true), { bossDistance: null, bossWeakElement: null });
  assert.equal(cond.conditionWire({ bossDistance: 0, bossWeakElement: 'electric' }, true).bossWeakElement, 'Electronic');
});

await check('distance_parse_is_strict_integer_0_100', () => {
  assert.equal(cond.parseDistance(''), null);
  assert.equal(cond.parseDistance(' 0 '), 0);
  assert.equal(cond.parseDistance('100'), 100);
  for (const bad of ['-1', '101', '35.5', '1e2', 'abc', '3 5']) assert.throws(() => cond.parseDistance(bad), /0~100/, bad);
});

await check('range_status_boundaries_inclusive_and_rl_zero', () => {
  const r = { min: 15, max: 35 };
  assert.equal(cond.rangeStatus(r, 14).kind, 'out');
  assert.equal(cond.rangeStatus(r, 15).kind, 'in');
  assert.equal(cond.rangeStatus(r, 35).kind, 'in');
  assert.equal(cond.rangeStatus(r, 36).kind, 'out');
  assert.equal(cond.rangeStatus(r, null).kind, 'unset');
  const rl = cond.rangeStatus({ min: 0, max: 0 }, 0);
  assert.equal(rl.kind, 'no_bonus'); assert.match(rl.text, /보너스 없음\(데이터 0–0, 확인 필요\)/);
  assert.equal(cond.rangeStatus(null, 30).kind, 'unknown');
  assert.equal(cond.rangeStatus({ min: 1.5, max: 3 }, 2).kind, 'unknown');
});

await check('member_preview_mixed_deck', () => {
  const preview = cond.memberPreview(members, ranges, { bossDistance: 35, bossWeakElement: 'fire' });
  assert.deepEqual(preview.map(m => m.distance.kind), ['in', 'in', 'no_bonus', 'out', 'in']);
  assert.deepEqual(preview.map(m => m.elementMatch), [true, false, true, false, false]);
  assert.equal(preview[3].element, 'electric');
  const none = cond.memberPreview(members, ranges, cond.createConditionState());
  assert.ok(none.every(m => m.elementMatch === false));
  assert.ok(none.filter(m => m.distance.kind !== 'no_bonus').every(m => m.distance.kind === 'unset'));
  // Unknown range data is never guessed; presentation element is a fallback only.
  const unknown = cond.memberPreview([{ id: 'x', elementCode: 'iron' }], ranges, { bossDistance: 30, bossWeakElement: 'iron' });
  assert.equal(unknown[0].distance.kind, 'unknown'); assert.equal(unknown[0].elementMatch, true);
});

await check('weapon_table_order_exceptions_and_sources', () => {
  assert.deepEqual(ranges.weaponRanges.map(r => r.weaponCode), ['shotgun', 'submachine_gun', 'assault_rifle', 'machine_gun', 'sniper_rifle', 'rocket_launcher']);
  assert.deepEqual(ranges.weaponRanges[4].exceptions, [{ characterId: 'synthetic-sr-exception', min: 25, max: 45 }]);
  const html = cond.renderDistanceDialog({ bossDistance: 35, bossWeakElement: null }, ranges, cond.memberPreview(members, ranges, { bossDistance: 35, bossWeakElement: null }));
  assert.ok(html.includes('0–0 · 보너스 없음(확인 필요)'));
  assert.ok(html.includes('synthetic-sr-exception: 25–45'));
  assert.equal((html.match(/data-weapon=/g) ?? []).length, 6);
  assert.ok(cond.renderDistanceDialog(cond.createConditionState(), null, []).includes('불러오지 못했습니다'));
});

await check('element_dialog_states_boss_weakness_explicitly', () => {
  const preview = cond.memberPreview(members, ranges, { bossDistance: null, bossWeakElement: 'fire' });
  const html = cond.renderElementDialog({ bossDistance: null, bossWeakElement: 'fire' }, preview);
  assert.ok(html.includes('보스의 약점 속성 — 이 속성 니케가 우월 코드 보너스를 받습니다'));
  assert.ok(html.includes('니케 자신의 속성이나 보스 자신의 속성이 아닙니다'));
  assert.equal((html.match(/data-cond-element="/g) ?? []).length, 6);
  for (const e of ['fire', 'water', 'wind', 'iron', 'electric']) assert.ok(html.includes(`/editor/assets/ui/code-${e}.png`), e);
  assert.ok(html.includes('덱: 리타, 누아르'));
  assert.match(html, /data-cond-element="fire" aria-pressed="true"/);
});

await check('summaries_and_legacy_mode', () => {
  assert.equal(cond.distanceSummary({ bossDistance: null }), '미설정');
  assert.equal(cond.distanceSummary({ bossDistance: 0 }), '0');
  assert.equal(cond.elementSummary({ bossWeakElement: 'fire' }), '작열(Fire)');
  assert.equal(cond.elementSummary({ bossWeakElement: null }), '없음');
  const legacy = cond.describeConditionMode({ properDistance: true, elementAdvantage: false });
  assert.equal(legacy.mode, 'legacy');
  assert.equal(legacy.text, '이전 방식(전원 적용) · 적정 거리 적용 · 우월 코드 미적용');
  const fresh = cond.describeConditionMode({ bossDistance: 35, bossWeakElement: 'Fire' });
  assert.equal(fresh.mode, 'per_member'); assert.match(fresh.text, /보스 거리 35 · 약점 작열\(Fire\)/);
  assert.equal(cond.describeConditionMode({ bossDistance: null, bossWeakElement: null }).mode, 'per_member');
  assert.equal(cond.describeConditionMode({}).mode, 'unknown');
  const controls = cond.renderConditionControls({ bossDistance: 35, bossWeakElement: 'fire' }, { legacy: legacy.text });
  assert.ok(controls.includes('적정 거리 · 35') && controls.includes('약점 · 작열(Fire)') && controls.includes('이전 방식(전원 적용)'));
  assert.ok(!controls.includes('type="hidden"'));
});

await check('escaping', () => {
  const html = cond.renderDistanceDialog(cond.createConditionState(), cond.normalizeRanges({
    weaponRanges: [{ weaponCode: '<b>x</b>', min: 1, max: 2, exceptions: [{ characterId: '<img>', min: 1, max: 2 }] }] }),
    [{ id: '"q', name: '<i>n</i>', weaponCode: null, distance: { kind: 'unset', text: '<s>' } }]);
  assert.ok(!html.includes('<b>x</b>') && !html.includes('<img>') && !html.includes('<i>n</i>') && !html.includes('<s>'));
});

const failed = checks.filter(c => !c.passed);
console.log(JSON.stringify({ evidence: 'mock_only_not_api', total: checks.length, failed: failed.length, checks }, null, 2));
if (failed.length) process.exit(1);

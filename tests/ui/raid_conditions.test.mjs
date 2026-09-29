// F2-U (F-COND-2 R3-R8) model checks against the confirmed F2-B wire shape. Evidence type: MOCK ONLY
// (fixtures/solo-raid-bosses-mock.json). No browser, no network. Usage: node tests/ui/raid_conditions.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = path.resolve(import.meta.dirname, '../..');
const raid = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/raid-conditions.js')));
const bosses = JSON.parse(fs.readFileSync(path.join(import.meta.dirname, 'fixtures/solo-raid-bosses-mock.json'), 'utf8'));

const checks = [];
async function check(name, fn) {
  try { await fn(); checks.push({ name, passed: true }); }
  catch (error) { checks.push({ name, passed: false, error: String(error.message).split('\n').slice(0, 6).join(' | ') }); }
}

await check('fixed_values_and_crit_default', () => {
  assert.equal(raid.DURATION_FRAMES, 10800);                  // R3: 180 s fixed
  assert.equal(raid.PELLET_POLICY, 'per_trigger');            // R7: 발사 1회 fixed
  assert.equal(raid.DEFAULT_CRIT_MODE, 'sample');             // R5
  const html = raid.critOptionsHtml();
  assert.match(html, /^<option value="sample" selected>확률 적용<\/option>/);
  assert.ok(html.includes('>끔<') && html.includes('>항상 크리<'));
});

await check('def_mode_confirmed_wire', () => {
  assert.equal(raid.DEF_WIRE.confirmed, true);
  // solo_raid defaults: nothing DEF-related is sent (no conditionProfile, no enemyDefense, no defenseMode).
  assert.deepEqual(raid.defenseFields('31784'), {});
  assert.deepEqual(raid.defenseFields('31784', false), { enemyDefense: 31784 });   // pre-wire comparison only
  assert.equal(raid.DEF_WIRE.replayRoute('r 1'), '/runtime/skill-replays/r%201/battle-conditions');
  assert.equal(raid.DEF_WIRE.experimentRoute('e1'), '/compute/experiments/e1/battle-conditions');
  const note = raid.conditionsNote();
  assert.match(note, /전투 시간 180초 · 샷건 계수 발사 1회 고정/);
  assert.match(note, /30,925로 시작해 이 덱의 누적 대미지가 20억을 넘은 뒤부터 31,784로 자동 전환/);
});

await check('saved_conditions_from_battle_conditions', () => {
  const solo = { profile: 'solo_raid', label: '덱 누적 피해에 따라 방어력 자동 전환', defenseMode: 'team_damage_threshold', initialDefense: 30925,
    switchedDefense: 31784, damageThreshold: 2000000000, durationFrames: 10800, pelletCoefficientPolicy: 'per_trigger' };
  assert.equal(raid.describeSavedCombat({ critMode: 'sample' }, { battleConditions: solo, boss: { id: 'solo-raid-41', name: '모의 보스 A' } }),
    '180초 · 덱 누적 피해에 따라 방어력 자동 전환 (30,925 → 31,784) · 크리티컬 확률 적용 · 샷건 계수 발사 1회 · 보스 모의 보스 A');
  // Older records: the endpoint's legacy label and the values stored at the time; nothing reinterpreted.
  const legacy = { profile: 'legacy', label: '이전 방식(고정 방어력)', defenseMode: 'fixed', initialDefense: 31784, switchedDefense: null,
    damageThreshold: null, durationFrames: 7200, pelletCoefficientPolicy: 'per_pellet' };
  assert.equal(raid.describeSavedCombat({ critMode: 'off', durationFrames: 7200, enemyDefense: 31784, pelletCoefficientPolicy: 'per_pellet' }, { battleConditions: legacy }),
    '120초 · 이전 방식(고정 방어력) · 방어력 31,784 · 크리티컬 끔 · 샷건 계수 펠릿마다');
  assert.equal(raid.describeSavedCombat({ durationFrames: 7200, enemyDefense: 30925 }), '120초 · 방어력 30,925 고정');
  assert.equal(raid.describeSavedCombat(null), null);
});

await check('defense_result_switch_and_none', () => {
  const names = new Map([['5009', '누아르']]);
  const switched = { mode: 'team_damage_threshold', initialDefense: 30925, finalDefense: 31784, damageThreshold: 2000000000,
    switchAfterHit: { frame: 1133, hitTraceId: 3804, hitOrdinal: 2011, characterId: '5009', effect: 'normal_attack',
      cumulativeDamage: 2001052869, previousDefense: 30925, newDefense: 31784 } };
  assert.equal(raid.describeDefenseResult(switched, { names }), '방어력 30,925 → 31,784 · 18.88초(1,133프레임) 누아르 타격 후 전환 · 누적 2,001,052,869');
  assert.equal(raid.describeDefenseResult({ ...switched, finalDefense: 30925, switchAfterHit: null }), '방어력 전환 없음 · 끝까지 30,925 (누적 피해 20억 이하)');
  assert.equal(raid.describeDefenseResult({ mode: 'fixed', initialDefense: 31784, finalDefense: 31784, damageThreshold: null, switchAfterHit: null }), '방어력 31,784 고정');
  assert.equal(raid.describeDefenseResult(null), null);  // older results: not recorded
  assert.ok(!raid.describeDefenseResult(switched).includes('3804'), 'internal trace ids stay hidden');
});

await check('boss_list_confirmed_shape_and_notice', () => {
  assert.equal(raid.BOSS_WIRE.confirmed, true);
  assert.equal(raid.BOSS_WIRE.listRoute, '/presentation/solo-raid-bosses');
  assert.deepEqual(raid.BOSS_WIRE.requestFields('solo-raid-41'), { bossId: 'solo-raid-41' });
  assert.deepEqual(raid.BOSS_WIRE.requestFields(null), {});
  const list = raid.normalizeBosses(bosses);
  assert.deepEqual(list.bosses.map(b => b.id), ['dummy', 'solo-raid-41', 'solo-raid-40', 'solo-raid-39']);  // default first, then newest season
  assert.equal(list.defaultId, 'dummy');
  assert.equal(list.notice, '일부 보스 이름 준비 중');
  assert.equal(raid.normalizeBosses({ defaultBossId: 'dummy', bosses: [{ id: 'dummy', name: '더미 보스' }], diagnostics: [{ code: 'boss_catalog_not_prepared' }] }).notice,
    '보스 목록 준비 중 · 지금은 더미 보스만 선택할 수 있습니다.');
  assert.equal(raid.normalizeBosses({ defaultBossId: 'dummy', bosses: [{ id: 'dummy', name: '더미 보스' }], diagnostics: [], complete: true }).notice, null);
  assert.equal(raid.normalizeBosses({ defaultBossId: 'dummy', bosses: [{ id: 'dummy', name: '더미 보스' }], diagnostics: [], complete: false }).notice, null);
  // Excluded bosses are never listed, and a row without a Korean name is not selectable.
  assert.ok(!list.bosses.some(b => b.id === 'solo-raid-42'));
  assert.equal(raid.normalizeBosses({ bosses: [{ id: 'x', name: null }] }).bosses.length, 0);
  const selector = raid.renderBossSelector(list.bosses, 'dummy', { notice: list.notice });
  assert.ok(selector.includes('더미 보스') && selector.includes('data-boss-open') && selector.includes('일부 보스 이름 준비 중'));
  const dialog = raid.renderBossDialog(list.bosses, 'solo-raid-41', { notice: list.notice });
  assert.equal((dialog.match(/data-boss-id=/g) ?? []).length, 4);
  assert.match(dialog, /data-boss-id="solo-raid-41" aria-pressed="true"/);
  assert.ok(dialog.includes('SEASON 41') && dialog.includes('일부 보스 이름 준비 중') && !dialog.includes('42'));
  assert.ok(!/enikk|https?:\/\/|한국어 이름 원천 미확인/i.test(dialog), 'no source or raw diagnostic text in the UI');
  const evil = raid.renderBossDialog(raid.normalizeBosses({ bosses: [{ id: '<x>', name: '<img src=x>', imageUrl: '"><script>' }] }).bosses, null);
  assert.ok(!evil.includes('<img src=x>') && !evil.includes('"><script>'));
});

// U-FIX-3 / F2-Q-1: the statistics DEF card follows the stored policy and runs.
await check('defense_policy_card_auto_switch_none_legacy', () => {
  const names = new Map([['5004', '앨리스']]);
  const bc = { profile: 'solo_raid', label: '덱 누적 피해에 따라 방어력 자동 전환', defenseMode: 'team_damage_threshold', initialDefense: 30925, switchedDefense: 31784 };
  const sw = { mode: 'team_damage_threshold', initialDefense: 30925, finalDefense: 31784, damageThreshold: 2000000000,
    switchAfterHit: { frame: 750, hitTraceId: 3076, characterId: '5004', cumulativeDamage: 2013492851, previousDefense: 30925, newDefense: 31784 } };
  const none = { mode: 'team_damage_threshold', initialDefense: 30925, finalDefense: 30925, damageThreshold: 2000000000, switchAfterHit: null };
  const planned = raid.describeDefensePolicy({}, null, { planned: true });
  assert.deepEqual(planned, { value: '자동 전환 (30,925 → 31,784)', sub: '누적 대미지 20억 초과 후 다음 타격부터 전환' });
  const one = raid.describeDefensePolicy({ defPolicy: 'team_damage_threshold:30925:2000000000:31784', battleConditions: bc }, [sw], { names });
  assert.equal(one.value, '자동 전환 (30,925 → 31,784)');
  assert.equal(one.sub, '방어력 30,925 → 31,784 · 12.5초(750프레임) 앨리스 타격 후 전환 · 누적 2,013,492,851');
  const two = raid.describeDefensePolicy({ defPolicy: 'team_damage_threshold:30925:2000000000:31784' }, [none, sw], { names, partial: true });
  assert.match(two.sub, /^2회 중 1회 전환 \(불러온 결과 기준\) · 첫 결과: 방어력 30,925 → 31,784/);
  const noSwitch = raid.describeDefensePolicy({ battleConditions: bc }, [none, none]);
  assert.equal(noSwitch.sub, '전환 없음 · 2회 모두 누적 20억 이하');
  assert.match(raid.describeDefensePolicy({ battleConditions: bc }, []).sub, /실행 결과의 전환 기록 없음/);
  // The old fixed message never appears for the automatic mode.
  for (const card of [planned, one, two, noSwitch]) assert.ok(!(card.value + card.sub).includes('자동 20억 전환 없음'));
  const legacy = raid.describeDefensePolicy({ defPolicy: 'fixed:31784', battleConditions: { profile: 'legacy', label: '이전 방식(고정 방어력)', defenseMode: 'fixed', initialDefense: 31784 } }, [null]);
  assert.deepEqual(legacy, { value: '이전 방식 · 방어력 31,784 고정', sub: '이전 방식(고정 방어력) · 누적 대미지에 따른 전환 없음(당시 조건)' });
  assert.equal(raid.describeDefensePolicy({ defPolicy: 'fixed:30925' }).value, '이전 방식 · 방어력 30,925 고정');  // record without battleConditions
  assert.ok(!one.sub.includes('5004') && !one.sub.includes('3076'));
});

const failed = checks.filter(c => !c.passed);
console.log(JSON.stringify({ evidence: 'mock_only_not_api', total: checks.length, failed: failed.length, checks }, null, 2));
if (failed.length) process.exit(1);

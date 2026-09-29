// F2-U (F-COND-2 R3-R8) model checks. Evidence type: MOCK ONLY (fixtures/solo-raid-bosses-mock.json, provisional
// DEF/boss wire). No browser, no network. Usage: node tests/ui/raid_conditions.test.mjs
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

await check('def_mode_until_and_after_wire', () => {
  assert.equal(raid.DEF_WIRE.confirmed, false);
  assert.deepEqual(raid.defenseFields('31784'), { enemyDefense: 31784 });       // live before the wire: old select
  assert.deepEqual(raid.defenseFields('31784', true), { enemyDefenseMode: 'cumulative_switch' });
  assert.ok(!('enemyDefense' in raid.defenseFields(null, true)));
  assert.match(raid.conditionsNote(false), /자동 전환은 아직 적용하지 않습니다/);
  const note = raid.conditionsNote(true);
  assert.match(note, /전투 시간 180초 · 샷건 계수 발사 1회 고정/);
  assert.match(note, /30,925로 시작해 이 덱의 누적 대미지가 20억을 넘은 뒤부터 31,784로 자동 전환/);
  assert.equal(raid.DEF_SWITCH_DAMAGE, 2000000000);
});

await check('saved_combat_shows_stored_values', () => {
  assert.equal(raid.describeSavedCombat({ durationFrames: 10800, enemyDefenseMode: 'cumulative_switch', critMode: 'sample', pelletCoefficientPolicy: 'per_trigger' }),
    '180초 · 방어력 자동 전환 (30,925 → 31,784) · 크리티컬 확률 적용 · 샷건 계수 발사 1회');
  // Older records keep their own time, fixed DEF and shotgun setting; nothing is reinterpreted.
  assert.equal(raid.describeSavedCombat({ durationFrames: 7200, enemyDefense: 31784, critMode: 'off', pelletCoefficientPolicy: 'per_pellet' }),
    '120초 · 방어력 31,784 고정 · 크리티컬 끔 · 샷건 계수 펠릿마다');
  assert.equal(raid.describeSavedCombat({ durationFrames: 10800, enemyDefense: 30925 }, { defenseMode: { label: '방어력 자동 전환(서버 표시)' }, boss: { name: '더미 보스' } }),
    '180초 · 방어력 자동 전환(서버 표시) · 보스 더미 보스');
  assert.equal(raid.describeSavedCombat(null), null);
});

await check('boss_list_dummy_first_and_display_only', () => {
  assert.equal(raid.BOSS_WIRE.confirmed, false);
  assert.deepEqual(raid.BOSS_WIRE.conditionFields('mock-a'), { boss: { id: 'mock-a' } });
  const list = raid.normalizeBosses({ bosses: [...bosses.bosses].reverse() });
  assert.equal(list[0].id, 'dummy'); assert.equal(list[0].dummy, true);
  assert.equal(list.length, 4);
  const selector = raid.renderBossSelector(list, 'dummy');
  assert.ok(selector.includes('더미 보스') && selector.includes('data-boss-open') && selector.includes('표시·저장만'));
  const dialog = raid.renderBossDialog(list, 'mock-a');
  assert.equal((dialog.match(/data-boss-id=/g) ?? []).length, 4);
  assert.match(dialog, /data-boss-id="mock-a" aria-pressed="true"/);
  assert.ok(dialog.includes('SEASON 41') && dialog.includes('기본 약점 작열') && dialog.includes('/editor/assets/ui/code-fire.png'));
  assert.ok(dialog.includes('기본 약점 전격'));
  assert.ok(!/enikk|https?:\/\//i.test(dialog), 'no source shown in the UI');
  const evil = raid.renderBossDialog(raid.normalizeBosses({ bosses: [{ id: '<x>', name: '<img src=x>', imageUrl: '"><script>' }] }), null);
  assert.ok(!evil.includes('<img src=x>') && !evil.includes('"><script>'));
});

const failed = checks.filter(c => !c.passed);
console.log(JSON.stringify({ evidence: 'mock_only_not_api', total: checks.length, failed: failed.length, checks }, null, 2));
if (failed.length) process.exit(1);

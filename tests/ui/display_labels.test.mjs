// U-FIX-4 (F2-Q-2): internal keys are shown as Korean labels; API/stored keys are untouched.
// No browser, no network. Usage: node tests/ui/display_labels.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = path.resolve(import.meta.dirname, '../..');
const labels = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/display-labels.js')));
const adapter = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/damage-log-adapter.js')));
const viewer = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/damage-log.js')));

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

const failed = checks.filter(c => !c.passed);
console.log(JSON.stringify({ total: checks.length, failed: failed.length, checks }, null, 2));
if (failed.length) process.exit(1);

// Per-hit damage audit checks for the desktop UI (no browser, no network, no product mutation).
// Units follow SkillReplay.AddEffect; terms come from HitCalculator.Compare (fixtures/hit-calculator-cases.json
// holds synthetic inputs run through the real calculator). Optional real saved replay is read only.
// Usage: node tests/ui/damage_audit.test.mjs [saved-replay.json] [output-dir]
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = path.resolve(import.meta.dirname, '../..');
const adapter = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/damage-log-adapter.js')));
const viewer = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/damage-log.js')));
const fixture = JSON.parse(fs.readFileSync(path.join(import.meta.dirname, 'fixtures/hit-calculator-cases.json'), 'utf8'));
const [realPath, outputDir] = process.argv.slice(2);

const checks = [];
async function check(name, fn) {
  try { await fn(); checks.push({ name, passed: true }); }
  catch (error) { checks.push({ name, passed: false, error: String(error.message).split('\n').slice(0, 6).join(' | ') }); }
}

const replayWithInputs = {
  inputs: [{ weapon: { characterId: '5009' }, skills: { slots: {
    skill1: { skillId: 2271107, functionIds: [227110701], functionPhases: {} },
    burst: { skillId: 1271307, functionIds: [], functionPhases: { after_hurt: [127031004] } } } } }],
  result: { conditions: { interruptionTarget: false } }
};
const members = [{ id: '5009', displayName: '누아르' }, { id: '5008', displayName: '5008' }, { id: '5004', displayName: '앨리스' }];
const ctx = adapter.createAuditContext(replayWithInputs, members);
const snapshot = (effect, extra = {}) => ({
  effect: { source: '5009', target: '5004', functionId: 227110701, groupId: 2271101, stacks: 1, expiresAt: null, ...effect },
  appliedAtFrame: 0, eventId: 1, burstCastId: null, ...extra
});
const describe = (effect, frame = 100, extra, context = ctx) => adapter.describeBuffSnapshot(snapshot(effect, extra), frame, context);
const caseEntry = (name, policy) => {
  const c = fixture.cases[name];
  const calculation = c.candidates.find(x => x.policy === policy);
  return { hitId: 1, frame: 600, damage: calculation.damage, hit: c.hit, calculation, buffs: [] };
};
const html = (entry, context = ctx) => viewer.renderDamageAuditPanel({ hitId: 1, shotId: 2, seconds: 10 }, adapter.buildHitAudit(entry, context));

await check('attack_flat_vs_rate_by_basis', () => {
  const flat = describe({ type: 1, value: 17191, basis: 'native_caster_flat_at_application' });
  assert.equal(flat.unit, 'flat'); assert.equal(flat.label, '공격력(고정)'); assert.equal(flat.valueText, '+17,191');
  assert.ok(!flat.valueText.includes('%'));
  assert.equal(describe({ type: 1, value: 0.1442, basis: 'native_recipient' }).valueText, '+14.42%');
  const self = describe({ type: 1, value: 0.5512, basis: 'native_caster' });
  assert.equal(self.valueText, '+55.12%'); assert.match(self.basisText, /시전자/);
  const odd = describe({ type: 1, value: 0.3, basis: 'unexpected_basis' });
  assert.equal(odd.unit, 'raw'); assert.equal(odd.valueText, '원값 0.3'); assert.match(odd.note, /예상하지 않은 basis/);
});

await check('heal_is_hp_amount_not_percent', () => {
  const heal = describe({ type: 2, value: 131666.853, basis: 'caster_final_max_hp_at_application' });
  assert.equal(heal.valueText, '초당 HP +131,666.853'); assert.ok(!heal.valueText.includes('%'));
  assert.equal(describe({ type: 2, value: 165770.72639999999, basis: 'caster_final_max_hp_at_application' }).valueText, '초당 HP +165,770.7264');
});

await check('charge_speed_rate_vs_caster_centiseconds', () => {
  assert.equal(describe({ type: 61, value: 0.8015, basis: 'native_caster' }).valueText, '+80.15%');
  const cs = describe({ type: 61, value: 12, basis: 'caster_charge_centiseconds' });
  assert.equal(cs.label, '차지 시간'); assert.equal(cs.valueText, '-0.12초'); assert.equal(cs.unit, 'chargeCs');
});

await check('ammo_unit_only_when_proven', () => {
  // Integer 1 can be 1발 (Integer) or 100% (Percent 10000/10000); never pick one without metadata.
  for (const value of [1, 4, 0, -2]) {
    const d = describe({ type: 14, value, basis: 'native_recipient' });
    assert.equal(d.unit, 'unknownUnit'); assert.equal(d.valueText, `단위 미확인 · 원값 ${value}`); assert.equal(d.known, false);
    assert.ok(!d.valueText.includes('발') && !d.valueText.includes('%'));
  }
  assert.equal(describe({ type: 14, value: 4, basis: 'native_recipient', stacks: 2 }).valueText, '단위 미확인 · 원값 4 · 2스택');
  const rate = describe({ type: 14, value: 0.4517, basis: 'native_recipient' });
  assert.equal(rate.valueText, '+45.17%'); assert.match(rate.note, /Percent/);
  assert.equal(describe({ type: 14, value: -0.25, basis: 'native_recipient' }).valueText, '-25%');
  assert.equal(describe({ type: 14, value: 4, basis: 'odd_basis' }).valueText, '원값 4');
  assert.equal(adapter.classifyBuffForHit(describe({ type: 14, value: 1, basis: 'native_recipient' }), {}, ctx).group, 'indirect');
});

const critHit = () => ({ ...fixture.cases.crit_core_fullburst_distance.hit });
const withHit = hit => ({ ...caseEntry('crit_core_fullburst_distance', 'legacy_term_floor'), hit });

await check('breakdown_flags_tri_state', () => {
  const empty = adapter.buildDamageBreakdown({ hit: {}, damage: 10 });
  assert.ok(empty.bonuses.every(x => x.active === null)); assert.equal(empty.bonusSum, null); assert.equal(empty.charge.applied, null);
  const emptyHtml = html(withHit({}));
  assert.ok(emptyHtml.includes('미확인') && emptyHtml.includes('풀차지 여부 미기록') && emptyHtml.includes('크리티컬 미기록'));
  assert.ok(!emptyHtml.includes('풀차지 아님') && !emptyHtml.includes('미적용'));
  const noHit = adapter.buildDamageBreakdown({ damage: 10, calculation: caseEntry('crit_core_fullburst_distance', 'legacy_term_floor').calculation });
  assert.ok(noHit.bonuses.every(x => x.active === null)); assert.equal(noHit.bonusSum, null); assert.equal(noHit.charge.applied, null);
  const nullCrit = adapter.buildDamageBreakdown(withHit({ ...critHit(), crit: null }));
  assert.equal(nullCrit.bonuses.find(x => x.name === 'critical').active, null);
  assert.equal(nullCrit.bonuses.find(x => x.name === 'core').active, true); assert.equal(nullCrit.bonusSum, null);
  const missing = critHit(); delete missing.properDistance; delete missing.fullCharge;
  const missingB = adapter.buildDamageBreakdown(withHit(missing));
  assert.equal(missingB.bonuses.find(x => x.name === 'distance').active, null); assert.equal(missingB.charge.applied, null); assert.equal(missingB.bonusSum, null);
  const noBonusValue = critHit(); delete noBonusValue.critBonus;
  assert.equal(adapter.buildDamageBreakdown(withHit(noBonusValue)).bonusSum, null);
  assert.equal(adapter.buildDamageBreakdown(withHit({ ...critHit(), crit: 'true' })).bonusSum, null);
  const allFalse = { ...critHit(), crit: false, core: false, fullBurst: false, properDistance: false, fullCharge: false };
  const falseB = adapter.buildDamageBreakdown(withHit(allFalse));
  assert.ok(falseB.bonuses.every(x => x.active === false)); assert.equal(falseB.bonusSum, 0); assert.equal(falseB.charge.applied, false);
  const falseHtml = html(withHit(allFalse));
  assert.ok(falseHtml.includes('풀차지 아님 → 1') && falseHtml.includes('크리티컬 미적용'));
  assert.equal(adapter.buildDamageBreakdown({ hit: { fullCharge: false } }).charge.applied, false);
  assert.equal(adapter.buildDamageBreakdown({ hit: { fullCharge: true } }).charge.applied, null);
  assert.equal(adapter.buildDamageBreakdown({ hit: { fullCharge: true, chargeApplicable: true } }).charge.applied, true);
  const normal = adapter.buildDamageBreakdown(caseEntry('crit_core_fullburst_distance', 'legacy_term_floor'));
  assert.ok(normal.bonuses.every(x => x.active === true)); assert.equal(normal.charge.applied, true);
});

await check('classification_never_infers_from_missing', () => {
  const cls = (effect, hit, context = ctx) => adapter.classifyBuffForHit(describe(effect), hit, context);
  const crit = { type: 51, value: 0.1246, basis: 'native_recipient' };
  assert.deepEqual([{}, { crit: null }, { crit: false }, { crit: true }].map(h => cls(crit, h).group), ['unverified', 'unverified', 'excluded', 'applied']);
  assert.equal(cls(crit, {}).reason, '크리티컬 여부 미기록');
  assert.equal(adapter.classifyBuffForHit({ typeId: 51, value: null, unit: 'raw' }, {}, null).group, 'unverified');
  assert.equal(cls({ ...crit, value: null }, { crit: true }).group, 'unverified');
  const charge = { type: 11, value: 0.07, basis: 'native_caster' };
  assert.deepEqual([{}, { fullCharge: false }, { fullCharge: true }, { fullCharge: true, chargeApplicable: true }].map(h => cls(charge, h).group),
    ['unverified', 'excluded', 'unverified', 'applied']);
  const pierce = { type: 54, value: 10, basis: 'native_caster' };
  assert.deepEqual([{}, { pierce: true }, { pierce: false }, { pierce: true, pierceDamage: 0 }, { pierce: true, pierceDamage: 0.2 }].map(h => cls(pierce, h).group),
    ['unverified', 'unverified', 'indirect', 'indirect', 'applied']);
  const taken = { type: 42, target: 'boss', value: 0.39, basis: 'native_recipient' };
  assert.equal(cls(taken, {}).group, 'unverified'); assert.equal(cls(taken, { damageTaken: 0.39 }).group, 'applied');
  assert.equal(cls({ ...taken, value: null }, { damageTaken: 0.39 }).group, 'unverified');
  assert.equal(cls({ ...taken, target: null }, { damageTaken: 0.39 }).group, 'unverified');
  assert.equal(cls({ ...taken, basis: 'odd_basis' }, { damageTaken: 0.39 }).group, 'unverified');
  assert.equal(cls({ type: 1, value: 0.1, basis: 'native_recipient' }, {}).reason, '타격 공격력 입력 목록 미기록');
  const interrupted = { ...ctx, interruptionTarget: true };
  assert.equal(cls({ type: 96, value: null, basis: 'native_recipient' }, {}, interrupted).group, 'unverified');
  assert.equal(cls({ type: 96, value: 0.1, basis: 'native_recipient' }, {}, interrupted).group, 'applied');
  assert.equal(cls({ type: 61, value: 0.8, basis: 'native_caster' }, {}).group, 'indirect');
  // Without any hit record: type-only facts stay, hit-dependent claims become unverified.
  assert.equal(cls({ type: 61, value: 0.8, basis: 'native_caster' }, null).group, 'indirect');
  assert.equal(cls({ type: 14, value: 1, basis: 'native_recipient' }, undefined).group, 'indirect');
  assert.equal(cls({ ...taken, target: '5004' }, null).group, 'indirect');
  for (const effect of [crit, charge, pierce, taken, { type: 1, value: 0.1, basis: 'native_recipient' }, { type: 777, value: 1 }]) {
    assert.equal(cls(effect, null).group, 'unverified', `type ${effect.type}`);
  }
});

await check('hit_model_flags_tri_state', () => {
  const base = caseEntry('crit_core_fullburst_distance', 'legacy_term_floor');
  const keys = ['isCritical', 'isCore', 'isTeamFullBurst', 'isSelfBurstActive', 'isFullCharge'];
  const empty = adapter.mapServerEntryToHit({ ...base, hit: {} });
  for (const key of keys) assert.equal(empty[key], null, key);
  const explicit = adapter.mapServerEntryToHit({ ...base, fullCharge: false, ownBurstEffectActive: false, hit: { crit: false, core: false, fullBurst: false } });
  for (const key of keys) assert.equal(explicit[key], false, key);
  const yes = adapter.mapServerEntryToHit({ ...base, fullCharge: true, ownBurstEffectActive: true });
  for (const key of keys) assert.equal(yes[key], true, key);
});

await check('raw_state_types_never_percent', () => {
  for (const type of [0, 5, 40, 54]) {
    const d = describe({ type, value: 10, basis: 'native_caster' });
    assert.equal(d.valueText, '원값 10', `type ${type}`); assert.ok(!d.valueText.includes('%'));
  }
  assert.equal(describe({ type: 54, value: 10, basis: 'native_caster' }).typeKey, 'StatPenetration');
});

await check('sign_zero_decimal_null', () => {
  const minus = describe({ type: 8, value: -0.0749, basis: 'native_recipient' });
  assert.equal(minus.valueText, '-7.49%'); assert.ok(!minus.valueText.includes('+-'));
  assert.equal(describe({ type: 51, value: 0, basis: 'native_recipient' }).valueText, '0%');
  assert.equal(describe({ type: 51, value: 0.1246, basis: 'native_recipient' }).valueText, '+12.46%');
  const taken = describe({ type: 42, target: 'boss', value: 0.3926, basis: 'native_recipient' });
  assert.equal(taken.label, '적 받는 대미지'); assert.equal(taken.valueText, '+39.26%');
  assert.equal(describe({ type: 11, value: null, basis: 'native_caster' }).valueText, '값 미기록');
  assert.equal(adapter.formatAuditNumber(-0), '0'); assert.equal(adapter.formatAuditNumber(null), '미제공');
  assert.equal(adapter.formatSignedAudit(-3.5, '%'), '-3.5%'); assert.equal(adapter.formatAuditNumber(503670.89506356005), '503,670.89506356');
});

await check('unknown_type_is_explicit', () => {
  const unknown = describe({ type: 999, value: 5, basis: 'native_caster' });
  assert.equal(unknown.label, '미해석 효과 (type 999)'); assert.equal(unknown.valueText, '원값 5'); assert.equal(unknown.known, false);
  assert.match(unknown.basisText, /basis native_caster/);
  assert.equal(describe({ type: undefined, value: 5 }).label, '미해석 효과 (type 미기록)');
});

await check('source_name_and_id_fallback', () => {
  const noir = describe({ type: 1, value: 1, basis: 'native_caster_flat_at_application' });
  assert.equal(noir.sourceText, '누아르 (#5009)'); assert.equal(noir.originText, '스킬 1 · 함수 227110701');
  assert.equal(describe({ source: '5008', type: 2, value: 1, basis: 'caster_final_max_hp_at_application' }).sourceText, '니케 #5008');
  assert.equal(describe({ source: '5044', type: 8, value: 0.1, basis: 'native_recipient' }).sourceText, '니케 #5044');
  assert.equal(describe({ source: '5009', functionId: 127031004, type: 42, value: 0.1, basis: 'native_recipient' }).originText, '버스트 · 함수 127031004');
  assert.equal(describe({ functionId: 119111002, type: 61, value: 0.1, basis: 'native_caster' }).originText, '함수 119111002 · 슬롯 미확인(하위 스킬·연결 함수)');
  assert.match(describe({ type: 1, value: 1, basis: 'native_caster' }, 100, { burstCastId: 7 }).originText, /버스트 시전 이벤트 #7/);
  const bare = describe({ functionId: 42, type: 1, value: 1, basis: 'native_caster' }, 100, undefined, adapter.createAuditContext(null, []));
  assert.equal(bare.originText, '함수 42'); assert.equal(bare.sourceText, '니케 #5009');
  assert.equal(describe({ functionId: null, type: 1, value: 1, basis: 'native_caster' }).originText, '함수 ID 미기록');
});

await check('duration_states', () => {
  const none = describe({ type: 1, value: 0.1, basis: 'native_recipient', expiresAt: null });
  assert.equal(none.durationKind, 'none'); assert.equal(none.remainingFrames, null);
  const live = describe({ type: 1, value: 0.1, basis: 'native_recipient', expiresAt: 150 }, 90);
  assert.equal(live.durationText, '잔여 60F(약 1초)'); assert.equal(live.remainingFrames, 60);
  assert.equal(describe({ type: 1, value: 0.1, basis: 'native_recipient', expiresAt: 360 }, 100).durationText, '잔여 260F(약 4.33초)');
  assert.equal(describe({ type: 1, value: 0.1, basis: 'native_recipient', expiresAt: 100 }, 100).durationKind, 'expired');
  const unrecorded = snapshot({ type: 1, value: 0.1, basis: 'native_recipient' }); delete unrecorded.effect.expiresAt;
  assert.equal(adapter.describeBuffSnapshot(unrecorded, 100, ctx).durationText, '지속시간 미제공');
  const noFrame = adapter.describeBuffSnapshot(snapshot({ type: 1, value: 0.1, basis: 'native_recipient', expiresAt: 150 }), undefined, ctx);
  assert.equal(noFrame.durationKind, 'absolute'); assert.equal(noFrame.durationText, '150F 만료(타격 프레임 미확인)');
});

await check('stacks_multiplied_once', () => {
  assert.equal(describe({ type: 1, value: 0.1, basis: 'native_recipient', stacks: 3 }).valueText, '스택당 +10% × 3 = +30%');
  assert.equal(describe({ type: 1, value: 100, basis: 'native_caster_flat_at_application', stacks: 2 }).valueText, '스택당 +100 × 2 = +200');
  assert.equal(describe({ type: 54, value: 10, basis: 'native_caster', stacks: 2 }).valueText, '원값 10 · 2스택');
  assert.equal(describe({ type: 1, value: 0.1, basis: 'native_recipient', stacks: 0 }).stacks, null);
});

await check('classification_uses_hit_fields', () => {
  const hit = fixture.cases.crit_core_fullburst_distance.hit;
  const classify = (effect, h = hit, context = ctx) => adapter.classifyBuffForHit(describe(effect), h, context);
  assert.equal(classify({ source: '5011', functionId: 108231001, type: 1, value: 0.66, basis: 'native_recipient' }).axis, '최종 공격력 · 비율 합산');
  assert.equal(classify({ type: 1, value: 17191, basis: 'native_caster_flat_at_application' }).axis, '최종 공격력 · 고정 가산');
  assert.equal(classify({ source: '5044', functionId: 1, type: 1, value: 0.1, basis: 'native_recipient' }).group, 'unverified');
  assert.equal(classify({ type: 51, value: 0.1246, basis: 'native_recipient' }).group, 'applied');
  assert.equal(classify({ type: 51, value: 0.1246, basis: 'native_recipient' }, { ...hit, crit: false }).group, 'excluded');
  assert.equal(classify({ type: 11, value: 0.07, basis: 'native_caster' }).group, 'applied');
  assert.equal(classify({ type: 11, value: 0.07, basis: 'native_caster' }, fixture.cases.non_full_charge_core.hit).group, 'excluded');
  assert.equal(classify({ type: 42, target: 'boss', value: 0.39, basis: 'native_recipient' }).axis, 'B4 · 받는 대미지');
  assert.equal(classify({ type: 42, target: '5004', value: 0.39, basis: 'native_recipient' }).group, 'indirect');
  for (const type of [61, 14, 8, 2, 62, 94, 0]) assert.equal(classify({ type, value: 1, basis: 'native_recipient' }).group, 'indirect', `type ${type}`);
  assert.equal(classify({ type: 96, value: 0.1, basis: 'native_recipient' }).group, 'excluded');
  assert.equal(classify({ type: 96, value: 0.1, basis: 'native_recipient' }, hit, null).group, 'unverified');
  assert.equal(classify({ type: 54, value: 10, basis: 'native_caster' }).group, 'indirect');
  assert.equal(classify({ type: 54, value: 10, basis: 'native_caster' }, { ...hit, pierceDamage: 0.2 }).group, 'applied');
  assert.equal(classify({ type: 777, value: 1 }).group, 'unverified');
  assert.equal(classify({ type: 1, value: 1, basis: 'native_recipient' }, null).group, 'unverified');
});

await check('additive_bonus_group_and_three_rounding_policies', () => {
  const hit = fixture.cases.crit_core_fullburst_distance.hit;
  for (const policy of ['legacy_term_floor', 'nested_floor', 'final_round_even']) {
    const entry = caseEntry('crit_core_fullburst_distance', policy);
    const b = adapter.buildDamageBreakdown(entry);
    assert.equal(b.policy, policy); assert.equal(b.finalMatchesStored, true); assert.equal(b.finalValue, entry.damage);
    assert.ok(b.bonuses.every(x => x.active === true));
    assert.ok(Math.abs(b.bonusSum - (hit.distanceBonus + hit.burstBonus + hit.critBonus + hit.coreBonus)) < 1e-12);
    assert.deepEqual(b.factors.map(x => x.factor), [1.1, 1.3926, 1.3]);
    assert.ok(Math.abs(b.p - b.attackDefenseDifference * b.coefficient * b.charge.value) < 1e-6);
    const steps = Object.fromEntries(b.steps.map(s => [s.name, s]));
    if (policy === 'final_round_even') {
      assert.ok(!steps.base); assert.ok(Math.abs(steps.B2.after - b.p * (1 + b.bonusSum)) < 1e-6);
      assert.match(adapter.describeRoundingFormula(policy).join('\n'), /동률은 짝수/);
    } else {
      const floored = ['base', 'distance', 'fullBurst', 'critical', 'core'].reduce((s, n) => s + steps[n].after, 0);
      assert.equal(b.b2, floored);
      // The removed UI hint multiplied crit/core/full-burst factors; the engine adds them.
      const multiplied = Math.floor(b.p * (1 + hit.distanceBonus) * (1 + hit.burstBonus) * (1 + hit.critBonus) * (1 + hit.coreBonus) * 1.1 * 1.3926 * 1.3);
      assert.notEqual(multiplied, entry.damage);
      assert.equal(b.factors.every(f => f.floored), policy === 'nested_floor');
    }
    const text = html(entry);
    assert.ok(!text.includes('크리배율 × 코어배율 × 풀버스트배율'));
    assert.ok(text.includes('저장된 발당 피해와 일치'));
    assert.ok(!/NaN|undefined|Infinity/.test(text));
  }
});

await check('non_full_charge_minimum_and_missing_terms', () => {
  const nonFull = adapter.buildDamageBreakdown(caseEntry('non_full_charge_core', 'legacy_term_floor'));
  assert.equal(nonFull.charge.applied, false); assert.equal(nonFull.charge.value, 1);
  assert.ok(html(caseEntry('non_full_charge_core', 'legacy_term_floor')).includes('풀차지 아님 → 1'));
  for (const policy of ['legacy_term_floor', 'nested_floor', 'final_round_even']) {
    const entry = caseEntry('minimum_damage', policy);
    const b = adapter.buildDamageBreakdown(entry);
    assert.deepEqual(b.minimum && b.minimum.after, 1); assert.equal(b.finalValue, 1); assert.equal(b.finalMatchesStored, true);
    const text = html(entry);
    assert.ok(text.includes('최소 피해 1')); assert.ok(text.includes('미적용 (최소 피해)'));
  }
  const bare = { hitId: 9, frame: 10, damage: 500, calculation: { policy: 'legacy_term_floor' }, buffs: [] };
  const b = adapter.buildDamageBreakdown(bare);
  assert.equal(b.hasSteps, false); assert.deepEqual(b.missing, ['terms']);
  for (const key of ['baseAttack', 'effectiveAttack', 'defense', 'attackDefenseDifference', 'coefficient', 'p', 'finalValue']) assert.equal(b[key], null, key);
  assert.equal(b.charge.value, null); assert.equal(b.bonusSum, null); assert.equal(b.finalMatchesStored, null);
  const text = html(bare);
  assert.ok(text.includes('검산할 수 없습니다')); assert.ok(text.includes('미제공')); assert.ok(!/NaN|undefined/.test(text));
  const partial = caseEntry('crit_core_fullburst_distance', 'legacy_term_floor');
  partial.calculation = { ...partial.calculation, terms: partial.calculation.terms.filter(t => t.name !== 'charge') };
  const pb = adapter.buildDamageBreakdown(partial);
  assert.deepEqual(pb.missing, ['charge']); assert.equal(pb.charge.value, null);
  assert.ok(html(partial).includes('누락된 계산 항목: charge'));
  const mapped = adapter.mapServerEntryToHit(bare);
  assert.equal(mapped.audit.baseAtk, null); assert.equal(mapped.audit.chargeMultiplier, null); assert.equal(mapped.audit.statDiff, null);
  const wrong = { ...caseEntry('non_full_charge_core', 'legacy_term_floor'), damage: 1 };
  assert.equal(adapter.buildDamageBreakdown(wrong).finalMatchesStored, false);
  assert.ok(html(wrong).includes('불일치'));
});

await check('html_escape', () => {
  const evil = adapter.createAuditContext(replayWithInputs, [{ id: '5009', displayName: '<img src=x onerror=alert(1)>' }]);
  const entry = caseEntry('crit_core_fullburst_distance', 'legacy_term_floor');
  entry.calculation = { ...entry.calculation, policy: '<b>p</b>', terms: [...entry.calculation.terms, { name: '<script>x</script>', before: 1, after: 1, operation: '"><svg onload=1>' }] };
  entry.buffs = [snapshot({ type: 999, value: 1, basis: '<i>b</i>' })];
  const text = viewer.renderDamageAuditPanel({ hitId: '<x>', shotId: null, seconds: 1 }, adapter.buildHitAudit(entry, evil));
  for (const raw of ['<img src=x', '<script>', '<svg', '<b>p</b>', '<i>b</i>', '#<x>']) assert.ok(!text.includes(raw), raw);
  assert.ok(text.includes('&lt;img src=x onerror=alert(1)&gt;')); assert.ok(text.includes('&lt;script&gt;'));
});

await check('synthetic_preview_uses_engine_shape', () => {
  const log = adapter.createSyntheticDamageLog('5004', null, members);
  const audit = adapter.buildHitAudit(log.hits[0].rawEntry, adapter.createAuditContext(null, members));
  assert.equal(audit.breakdown.hasSteps, false); assert.ok(audit.breakdown.baseAttack > 0);
  const all = Object.values(audit.effects).flat();
  assert.ok(all.length >= 2); assert.ok(all.every(e => e.typeId === 1 && e.valueText.endsWith('%')));
  assert.ok(!/NaN|undefined/.test(viewer.renderDamageAuditPanel(log.hits[0], audit)));
});

let real = null;
if (realPath) {
  await check('real_saved_replay_all_entries', () => {
    const saved = JSON.parse(fs.readFileSync(realPath, 'utf8'));
    const replay = saved.replay ?? saved;
    const log = replay.result.damageLog;
    const context = adapter.createAuditContext(replay, []);
    const samples = {}; const groups = { applied: 0, excluded: 0, indirect: 0, unverified: 0 };
    let checked = 0;
    for (const entry of log.entries) {
      const audit = adapter.buildHitAudit(entry, context);
      const b = audit.breakdown;
      assert.equal(b.finalMatchesStored, true, `hit ${entry.hitId}`);
      assert.equal(b.effectiveAttack, entry.calculation.terms.find(t => t.name === 'effectiveAttack').after);
      if (b.policy !== 'final_round_even' && !b.minimum) {
        const s = Object.fromEntries(b.steps.map(x => [x.name, x.after]));
        assert.equal(b.b2, s.base + s.distance + s.fullBurst + s.critical + s.core, `B2 hit ${entry.hitId}`);
      }
      for (const [name, list] of Object.entries(audit.effects)) {
        groups[name] += list.length;
        for (const e of list) {
          assert.ok(!e.valueText.includes('+-') && !/NaN|undefined/.test(e.valueText), e.valueText);
          if (e.typeId === 2) assert.ok(e.valueText.startsWith('초당 HP') && !e.valueText.includes('%'));
          if (e.basis === 'native_caster_flat_at_application') assert.ok(!e.valueText.includes('%'));
          if (e.typeId === 14 && Number.isInteger(e.value)) assert.ok(e.valueText.startsWith('단위 미확인') && !e.valueText.includes('발'), e.valueText);
          const key = `${e.typeId}:${e.basis}:${e.sourceId}:${e.functionId}`;
          samples[key] ??= { label: e.label, valueText: e.valueText, group: e.group, axis: e.axis, reason: e.reason,
            origin: e.originText, raw: { type: e.typeId, value: e.value, stacks: e.stacks, basis: e.basis, expiresAt: e.raw.effect.expiresAt } };
        }
      }
      const text = viewer.renderDamageAuditPanel({ hitId: entry.hitId, shotId: entry.shotId, seconds: entry.seconds }, audit);
      assert.ok(!/NaN|undefined|Infinity/.test(text), `render hit ${entry.hitId}`);
      checked++;
    }
    real = { path: realPath, entries: checked, policy: log.entries[0]?.calculation?.policy, groups, samples };
  });
}

const failed = checks.filter(c => !c.passed);
const summary = { kind: 'ui_damage_audit_unit', passed: failed.length === 0, total: checks.length, failed: failed.length, checks, real };
if (outputDir) {
  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(path.join(outputDir, 'unit-summary.json'), JSON.stringify(summary, null, 2));
}
console.log(JSON.stringify({ ...summary, real: real && { ...real, samples: Object.keys(real.samples).length } }, null, 2));
if (failed.length) process.exit(1);

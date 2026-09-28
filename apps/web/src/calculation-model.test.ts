import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { auditTableHtml, buildHitRequest, changedHitFields, comparisonTableHtml, conversionText, EXPERIMENTAL_INPUTS, exactInteger, HIT_WIRE, hitErrorText, orderCandidates, parseAttackBuffs, parseExperimentalInput, percentToRaw10000, type Hit } from './calculation-model';

// MOCK ONLY: tests/ui/fixtures/client-f32-mock.json is a UI fixture (Python binary32), not an API response.
const mock = JSON.parse(readFileSync(new URL('../../../tests/ui/fixtures/client-f32-mock.json', import.meta.url), 'utf8'));
const four = mock.cases.crit_core_fullburst_distance.comparison.candidates;
const stageA = { ...HIT_WIRE, confirmed: false };

describe('attack buff inputs', () => {
  it('preserves equal effects for joint OL and skill rounding', () => {
    const buffs = parseAttackBuffs('1.4, 1.4, 50');
    expect(buffs.map(buff => buff.rate)).toEqual([.014, .014, .5]);
    expect(buffs.map(buff => buff.stacks)).toEqual([1,1,1]);
    expect(parseAttackBuffs('')).toEqual([]);
  });
  it('rejects missing values and text rather than silently using zero', () => {
    for (const text of ['50,', 'abc', '30,,20', 'Infinity']) expect(() => parseAttackBuffs(text)).toThrow();
  });
  it('compares serialized buff terms, not array identity, for recorded edits', () => {
    const original = { statAttack: 100, attackBuffs: [], runtimeAttackBuffs: [] } as Hit;
    expect(changedHitFields({ ...original, runtimeAttackBuffs: [] }, original)).toEqual([]);
    expect(changedHitFields({ ...original, runtimeAttackBuffs: parseAttackBuffs('50') }, original)).toEqual(['runtimeAttackBuffs']);
  });
});

describe('client_f32 schema 3 wire (mock data)', () => {
  it('shows client_f32 first as default and keeps the earlier three as comparison candidates', () => {
    const { candidates, missing } = orderCandidates(four);
    expect(candidates.map(c => c.policy)).toEqual(['client_f32', 'legacy_term_floor', 'final_round_even', 'nested_floor']);
    expect(candidates.map(c => c.role)).toEqual(['default', 'comparison', 'comparison', 'comparison']);
    expect(missing).toEqual([]);
    const html = comparisonTableHtml(four, HIT_WIRE, 'client_f32');
    expect(html.indexOf('data-policy="client_f32"')).toBeLessThan(html.indexOf('data-policy="legacy_term_floor"'));
    expect(html.match(/비교 후보/g)).toHaveLength(3);
    expect(html.match(/policy-tag selected/g)).toHaveLength(1);
    expect(html).toContain('4,460,740');
    expect(comparisonTableHtml(four.slice(0, 3))).toContain('응답에 없는 정책: client_f32');
    expect(comparisonTableHtml([...four, { policy: '<x>', damage: 1, residual: null, relativeError: null }])).toContain('&lt;x&gt;');
  });
  it('shows unavailable candidates with their reason, never as 0, and prefers exact integer strings', () => {
    const rows = [{ policy: 'client_f32', damage: 9007199254740992, residual: null, relativeError: null, status: 'available', exactDamage: '9007199254740993' },
      { policy: 'legacy_term_floor', damage: null, residual: null, relativeError: null, status: 'unavailable', errorCode: 'Damage exceeds precision limit.', terms: [] }];
    const html = comparisonTableHtml(rows);
    expect(html).toContain('9,007,199,254,740,993');
    expect(html).toContain('계산 불가 · Damage exceeds precision limit.');
    expect(html).toContain('data-status="unavailable"');
    expect(exactInteger(null, 12)).toBe('12');
    expect(exactInteger(null, null)).toBe('—');
  });
  it('builds the schema 3 request with policy and the two rates; stage-A shape stays schema 2', () => {
    const hit = { statAttack: 100, attackBuffs: [], runtimeAttackBuffs: [] } as Hit;
    expect(HIT_WIRE.confirmed).toBe(true);
    expect(buildHitRequest(hit, 5, { statDamageRatio: 2, defenceRatioRate: .25 }))
      .toEqual({ inputSchemaVersion: 3, roundingPolicy: 'client_f32', input: { ...hit, statDamageRatio: 2, defenceRatioRate: .25 }, observedDamage: 5 });
    expect(buildHitRequest(hit, null, { statDamageRatio: 1, defenceRatioRate: 0 }, 'nested_floor').roundingPolicy).toBe('nested_floor');
    expect(buildHitRequest(hit, null, { statDamageRatio: 2, defenceRatioRate: .25 }, 'client_f32', stageA))
      .toEqual({ inputSchemaVersion: 2, input: hit, observedDamage: null });
  });
  it('renders conversion, audit terms and server error codes', () => {
    expect(conversionText({ originalSchemaVersion: 2, targetSchemaVersion: 3, converted: true, method: 'v2_to_v3_neutral_rates', appliedDefaults: { statDamageRatio: 1, defenceRatioRate: 0 } }))
      .toBe('schema 2 → 3 변환 (v2_to_v3_neutral_rates) · 적용한 중립값 statDamageRatio=1, defenceRatioRate=0');
    expect(conversionText({ originalSchemaVersion: 3, targetSchemaVersion: 3, converted: false, method: 'none', appliedDefaults: {} })).toBeNull();
    const audit = auditTableHtml(four.at(-1));
    expect(audit.match(/data-term=/g)).toHaveLength(10);
    expect(auditTableHtml(null)).toContain('기록 없음');
    expect(hitErrorText('statAttack_must_be_integer_never_truncated')).toBe('정수만 허용합니다 (소수를 절삭하지 않음) · statAttack_must_be_integer_never_truncated');
    expect(hitErrorText('selected_policy_unavailable: x')).toContain('선택한 정책');
    expect(hitErrorText('other')).toBe('other');
  });
  it('sends exact 1/10000 numerators for manual attack buffs and rejects finer percentages', () => {
    expect(parseAttackBuffs('14.5, 1.4, -3').map(b => b.rawRate10000)).toEqual(['1450', '140', '-300']);
    expect(percentToRaw10000('0.01')).toBe('1');
    expect(percentToRaw10000('12.300')).toBe('1230');
    expect(() => parseAttackBuffs('1.234')).toThrow(/1\/10000/);
  });
  it('uses neutral defaults and rejects instead of truncating experimental inputs', () => {
    expect(EXPERIMENTAL_INPUTS.map(s => [s.key, s.neutral])).toEqual([['statDamageRatio', 1], ['defenceRatioRate', 0]]);
    expect(EXPERIMENTAL_INPUTS.every(s => s.note.includes('실험·미확정'))).toBe(true);
    expect(parseExperimentalInput('defenceRatioRate', '0.25')).toBe(.25);
    for (const bad of ['', 'x', '1.5']) expect(() => parseExperimentalInput('defenceRatioRate', bad)).toThrow();
    expect(() => parseExperimentalInput('statDamageRatio', '-1')).toThrow();
  });
});

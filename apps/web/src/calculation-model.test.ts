import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { buildHitRequest, changedHitFields, comparisonTableHtml, EXPERIMENTAL_INPUTS, HIT_WIRE, orderCandidates, parseAttackBuffs, parseExperimentalInput, type Hit } from './calculation-model';

// MOCK ONLY: tests/ui/fixtures/client-f32-mock.json is a UI fixture (Python binary32), not an API response.
const mock = JSON.parse(readFileSync(new URL('../../../tests/ui/fixtures/client-f32-mock.json', import.meta.url), 'utf8'));
const four = mock.cases.crit_core_fullburst_distance.comparison.candidates;
const confirmed = { ...HIT_WIRE, confirmed: true };

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

describe('client_f32 stage A (mock)', () => {
  it('shows client_f32 first as default and keeps the earlier three as comparison candidates', () => {
    const { candidates, missing } = orderCandidates(four);
    expect(candidates.map(c => c.policy)).toEqual(['client_f32', 'legacy_term_floor', 'final_round_even', 'nested_floor']);
    expect(candidates.map(c => c.role)).toEqual(['default', 'comparison', 'comparison', 'comparison']);
    expect(missing).toEqual([]);
    const html = comparisonTableHtml(four, confirmed);
    expect(html.indexOf('data-policy="client_f32"')).toBeLessThan(html.indexOf('data-policy="legacy_term_floor"'));
    expect(html.match(/비교 후보/g)).toHaveLength(3);
    expect(html).toContain('4,460,740');
    expect(comparisonTableHtml(four.slice(0, 3), confirmed)).toContain('응답에 없는 정책: client_f32');
    expect(comparisonTableHtml([...four, { policy: '<x>', damage: 1, residual: null, relativeError: null }], confirmed)).toContain('&lt;x&gt;');
  });
  it('keeps the live request at schema 2 without the new fields until the wire is confirmed', () => {
    const hit = { statAttack: 100, attackBuffs: [], runtimeAttackBuffs: [] } as Hit;
    expect(HIT_WIRE.confirmed).toBe(false);
    const live = buildHitRequest(hit, null, { statDamageRatio: 2, defenceRatioRate: .25 });
    expect(live).toEqual({ inputSchemaVersion: 2, input: hit, observedDamage: null });
    const draft = buildHitRequest(hit, 5, { statDamageRatio: 2, defenceRatioRate: .25 }, confirmed);
    expect(draft).toEqual({ inputSchemaVersion: 3, input: { ...hit, statDamageRatio: 2, defenceRatioRate: .25 }, observedDamage: 5 });
    expect(comparisonTableHtml(four.slice(0, 3))).not.toContain('비교 후보');
  });
  it('uses neutral defaults and rejects instead of truncating experimental inputs', () => {
    expect(EXPERIMENTAL_INPUTS.map(s => [s.key, s.neutral])).toEqual([['statDamageRatio', 1], ['defenceRatioRate', 0]]);
    expect(EXPERIMENTAL_INPUTS.every(s => s.note.includes('실험·미확정'))).toBe(true);
    expect(parseExperimentalInput('defenceRatioRate', '0.25')).toBe(.25);
    for (const bad of ['', 'x', '1.5']) expect(() => parseExperimentalInput('defenceRatioRate', bad)).toThrow();
    expect(() => parseExperimentalInput('statDamageRatio', '-1')).toThrow();
  });
});

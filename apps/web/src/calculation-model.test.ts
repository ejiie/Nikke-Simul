import { describe, expect, it } from 'vitest';
import { changedHitFields, parseAttackBuffs, type Hit } from './calculation-model';

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

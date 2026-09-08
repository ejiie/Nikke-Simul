export type StatBuff = { source: string; rate: number; stacks: number };
export type Hit = Record<string, unknown> & { attackBuffs: StatBuff[]; runtimeAttackBuffs: StatBuff[] };

// Preserve separate effects, including equal values: the backend groups OL + skill terms together.
export function parseAttackBuffs(text: string): StatBuff[] {
  if (!text.trim()) return [];
  const tokens = text.split(',').map(value => value.trim());
  if (tokens.length > 100 || tokens.some(value => !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(value)))
    throw new Error('공격력 버프는 50, 30처럼 쉼표로 구분한 숫자로 입력하세요.');
  // Shift the decimal before binary64 parsing so 1.4% matches a stored ratio of .014.
  return tokens.map((value, i) => ({ source: `manual:attack:${i + 1}`, rate: Number(`${value}e-2`), stacks: 1 }));
}

export function changedHitFields(hit: Hit, original: Hit): string[] {
  return Object.keys(hit).filter(key => JSON.stringify(hit[key]) !== JSON.stringify(original[key]));
}

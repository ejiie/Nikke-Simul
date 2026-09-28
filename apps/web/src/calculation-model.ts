import { escape } from './model';
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

// client_f32 transition (I-UI stage A). The engine (H-F32) defaults to client_f32 and keeps the three
// earlier policies as comparison candidates. Until the Backend publishes the schema 3 wire contract the
// live request stays schema 2; the client presentation is exercised with mock fixtures only.
export const HIT_WIRE = { confirmed: false, liveInputSchemaVersion: 2, clientInputSchemaVersion: 3 } as const;
export type Wire = { confirmed: boolean; liveInputSchemaVersion: number; clientInputSchemaVersion: number };

export const HIT_POLICIES = [
  { id: 'client_f32', label: '클라이언트 float32', role: 'default', note: '공격력 long 조립 → float32 대미지 경로 → 사사오입 · 실측 대조 전' },
  { id: 'legacy_term_floor', label: 'C# 항별 내림', role: 'comparison', note: '과거 기본' },
  { id: 'final_round_even', label: '최종 반올림 (절반은 짝수)', role: 'comparison', note: '' },
  { id: 'nested_floor', label: '항별 + 단계별 내림', role: 'comparison', note: '' }
] as const;

export type Candidate = { policy: string; damage: number; residual: number | null; relativeError: number | null;
  terms?: { name: string; before: number; after: number; operation: string }[] };

// client_f32 first (the engine appends it fourth), earlier policies in registry order, unknown last; nothing dropped.
export function orderCandidates(candidates: Candidate[]) {
  const rank = (c: Candidate) => { const i = HIT_POLICIES.findIndex(p => p.id === c.policy); return i < 0 ? HIT_POLICIES.length : i; };
  const ordered = candidates.map((c, i) => ({ c, i })).sort((a, b) => rank(a.c) - rank(b.c) || a.i - b.i).map(({ c }) => {
    const info = HIT_POLICIES.find(p => p.id === c.policy);
    return { ...c, label: info?.label ?? `미해석 정책 ${c.policy}`, role: info?.role ?? 'unknown' };
  });
  const present = new Set(candidates.map(c => c.policy));
  return { candidates: ordered, missing: HIT_POLICIES.filter(p => !present.has(p.id)).map(p => p.id) };
}

// Experimental inputs: neutral defaults only (H-SRC found no confirmed source or boss value).
export const EXPERIMENTAL_INPUTS = [
  { key: 'statDamageRatio', neutral: 1, min: 0, max: undefined, note: '실험·미확정 · 원천 불명(스킬 계수는 가설) · 중립 1' },
  { key: 'defenceRatioRate', neutral: 0, min: 0, max: 1, note: '실험·미확정 · 최근 기믹 · 적용 보스·값 불명 · 중립 0' }
] as const;
export type ExperimentalKey = typeof EXPERIMENTAL_INPUTS[number]['key'];

export function parseExperimentalInput(key: ExperimentalKey, text: string): number {
  const spec = EXPERIMENTAL_INPUTS.find(s => s.key === key)!;
  const trimmed = text.trim();
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(trimmed)) throw new Error(`${key}: 숫자를 입력하세요.`);
  const value = Number(trimmed);
  if (!Number.isFinite(value) || value < spec.min || (spec.max !== undefined && value > spec.max))
    throw new Error(`${key}: ${spec.min}${spec.max !== undefined ? `~${spec.max}` : ' 이상'} 범위만 허용합니다.`);
  return value;
}

// Unconfirmed wire: schema 2 without the new fields (the live API rejects unknown schema). Confirmed: schema 3.
// Provisional shape; stage B replaces it with the Backend's published HitRequest.
export function buildHitRequest(hit: Hit, observed: number | null, experimental: Record<ExperimentalKey, number>, wire: Wire = HIT_WIRE) {
  if (!wire.confirmed) return { inputSchemaVersion: wire.liveInputSchemaVersion, input: hit, observedDamage: observed };
  return { inputSchemaVersion: wire.clientInputSchemaVersion, input: { ...hit, ...experimental }, observedDamage: observed };
}

const fmt = (v: number) => v.toLocaleString('ko-KR', { maximumFractionDigits: 8 });
export function comparisonTableHtml(candidates: Candidate[], wire: Wire = HIT_WIRE): string {
  const { candidates: rows, missing } = orderCandidates(candidates);
  const tag = (role: string) => role === 'default' ? '<span class="policy-tag default">기본</span>'
    : role === 'comparison' ? (wire.confirmed ? '<span class="policy-tag">비교 후보</span>' : '') : '<span class="policy-tag unknown">미해석</span>';
  const body = rows.map(c => `<tr data-policy="${escape(c.policy)}"><td>${escape(c.label)} ${tag(c.role)}</td><td>${fmt(c.damage)}</td><td>${c.residual === null ? '—' : fmt(c.residual)}</td><td>${c.relativeError === null ? '—' : fmt(c.relativeError * 100) + '%'}</td></tr>`).join('');
  const gap = wire.confirmed && missing.length ? `<p class="notice">응답에 없는 정책: ${missing.map(escape).join(', ')}</p>` : '';
  return `<div class="calc-table"><table><thead><tr><th>${wire.confirmed ? '대미지 정책' : '정수화 후보'}</th><th>대미지</th><th>실측 차이</th><th>상대오차</th></tr></thead><tbody>${body}</tbody></table></div>${gap}`;
}

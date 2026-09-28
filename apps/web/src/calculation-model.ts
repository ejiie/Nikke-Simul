import { escape } from './model';
export type StatBuff = { source: string; rate: number; stacks: number; rawRate10000?: string | null };
export type Hit = Record<string, unknown> & { attackBuffs: StatBuff[]; runtimeAttackBuffs: StatBuff[] };

// Preserve separate effects, including equal values: the backend groups OL + skill terms together.
export function parseAttackBuffs(text: string): StatBuff[] {
  if (!text.trim()) return [];
  const tokens = text.split(',').map(value => value.trim());
  if (tokens.length > 100 || tokens.some(value => !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(value)))
    throw new Error('공격력 버프는 50, 30처럼 쉼표로 구분한 숫자로 입력하세요.');
  // Shift the decimal before binary64 parsing so 1.4% matches a stored ratio of .014. The exact 1/10000
  // numerator travels as a decimal string (schema 3); finer percentages are rejected, never truncated.
  return tokens.map((value, i) => ({ source: `manual:attack:${i + 1}`, rate: Number(`${value}e-2`), stacks: 1,
    rawRate10000: percentToRaw10000(value) }));
}

export function changedHitFields(hit: Hit, original: Hit): string[] {
  return Object.keys(hit).filter(key => JSON.stringify(hit[key]) !== JSON.stringify(original[key]));
}

// client_f32 wire (Backend 74ca24f, contract "I-BE schema 3"). client_f32 is the default policy; the
// earlier three are comparison candidates that keep their historical arithmetic and ignore the new rates.
// `confirmed: false` keeps only the stage-A schema 2 request shape for comparison tests.
export const HIT_WIRE = { confirmed: true, liveInputSchemaVersion: 2, clientInputSchemaVersion: 3 } as const;
export type Wire = { confirmed: boolean; liveInputSchemaVersion: number; clientInputSchemaVersion: number };

export const HIT_POLICIES = [
  { id: 'client_f32', label: '클라이언트 float32', role: 'default', note: '공격력 long 조립 → float32 대미지 경로 → 사사오입 · 실측 대조 전' },
  { id: 'legacy_term_floor', label: 'C# 항별 내림', role: 'comparison', note: '과거 기본' },
  { id: 'final_round_even', label: '최종 반올림 (절반은 짝수)', role: 'comparison', note: '' },
  { id: 'nested_floor', label: '항별 + 단계별 내림', role: 'comparison', note: '' }
] as const;
export const DEFAULT_POLICY = 'client_f32';

export type Term = { name: string; before: number; after: number; operation: string };
export type Candidate = { policy: string; damage: number | null; residual: number | null; relativeError: number | null;
  terms?: Term[]; status?: string; errorCode?: string | null; exactDamage?: string | null };
export type HitConversion = { originalSchemaVersion: number; targetSchemaVersion: number; converted: boolean; method: string;
  appliedDefaults: Record<string, unknown> };
export type HitResponse = { id: string; createdAt: string; inputSchemaVersion: number; rulesVersion: string; status: string;
  input: Hit; originalInput: Record<string, unknown>; conversion: HitConversion; effectiveAttack: number; exactEffectiveAttack: string;
  observedDamage: number | null; selectedPolicy: string; selectedCandidate: Candidate; candidates: Candidate[]; limitations: string[];
  sourceArtifact: unknown };

// client_f32 first, earlier policies in registry order, unknown last; nothing dropped.
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

export function buildHitRequest(hit: Hit, observed: number | null, experimental: Record<ExperimentalKey, number>,
  roundingPolicy: string = DEFAULT_POLICY, wire: Wire = HIT_WIRE) {
  if (!wire.confirmed) return { inputSchemaVersion: wire.liveInputSchemaVersion, input: hit, observedDamage: observed };
  return { inputSchemaVersion: wire.clientInputSchemaVersion, roundingPolicy, input: { ...hit, ...experimental }, observedDamage: observed };
}

const fmt = (v: number) => v.toLocaleString('ko-KR', { maximumFractionDigits: 8 });

// Exact decimal strings win over binary64 display numbers for integers (contract: exactDamage/exactEffectiveAttack).
export function exactInteger(exact: string | null | undefined, display: number | null | undefined): string {
  if (typeof exact === 'string' && /^-?\d+$/.test(exact)) return BigInt(exact).toLocaleString('ko-KR');
  return typeof display === 'number' && Number.isFinite(display) ? fmt(display) : '—';
}

const LIMITATION_TEXT: Record<string, string> = {
  experimental_source_mapping: 'statDamageRatio·defenceRatioRate·break/parts 원천 대응은 실험·미확정',
  historical_policies_ignore_statDamageRatio_and_defenceRatioRate: '비교 후보(과거 3정책)는 새 두 비율을 적용하지 않음',
  audit_terms_are_binary64_display_values_use_exact_fields_for_integers: '단계 값은 binary64 표시값 · 정수 결과는 exact 필드 기준'
};
export const limitationText = (code: string) => LIMITATION_TEXT[code] ?? code;

export function conversionText(conversion: HitConversion | null | undefined): string | null {
  if (!conversion?.converted) return null;
  const defaults = Object.entries(conversion.appliedDefaults ?? {}).map(([k, v]) => `${k}=${v}`).join(', ');
  return `schema ${conversion.originalSchemaVersion} → ${conversion.targetSchemaVersion} 변환 (${conversion.method}) · 적용한 중립값 ${defaults}`;
}

export function comparisonTableHtml(candidates: Candidate[], wire: Wire = HIT_WIRE, selectedPolicy: string | null = null): string {
  const { candidates: rows, missing } = orderCandidates(candidates);
  const tag = (role: string) => role === 'default' ? '<span class="policy-tag default">기본</span>'
    : role === 'comparison' ? (wire.confirmed ? '<span class="policy-tag">비교 후보</span>' : '') : '<span class="policy-tag unknown">미해석</span>';
  const body = rows.map(c => {
    const unavailable = c.status === 'unavailable';
    const damage = unavailable ? `<span class="policy-unavailable">계산 불가 · ${escape(c.errorCode ?? '이유 미제공')}</span>`
      : exactInteger(c.exactDamage, c.damage);
    const selected = c.policy === selectedPolicy ? ' <span class="policy-tag selected">선택</span>' : '';
    return `<tr data-policy="${escape(c.policy)}" data-status="${escape(c.status ?? 'available')}"><td>${escape(c.label)} ${tag(c.role)}${selected}</td><td>${damage}</td><td>${c.residual == null ? '—' : fmt(c.residual)}</td><td>${c.relativeError == null ? '—' : fmt(c.relativeError * 100) + '%'}</td></tr>`;
  }).join('');
  const gap = wire.confirmed && missing.length ? `<p class="notice">응답에 없는 정책: ${missing.map(escape).join(', ')}</p>` : '';
  return `<div class="calc-table"><table><thead><tr><th>${wire.confirmed ? '대미지 정책' : '정수화 후보'}</th><th>대미지</th><th>실측 차이</th><th>상대오차</th></tr></thead><tbody>${body}</tbody></table></div>${gap}`;
}

export function auditTableHtml(candidate: Candidate | null | undefined): string {
  const terms = candidate?.terms ?? [];
  if (!candidate || !terms.length) return '<p class="muted">선택 정책의 계산 단계 기록 없음</p>';
  const v = (x: number) => typeof x === 'number' && Number.isFinite(x) ? fmt(x) : '—';
  return `<div class="calc-table audit"><table><thead><tr><th>단계 (${escape(candidate.policy)})</th><th>입력</th><th>결과</th><th>연산</th></tr></thead><tbody>${terms.map(t =>
    `<tr data-term="${escape(t.name)}"><td>${escape(t.name)}</td><td>${v(t.before)}</td><td>${v(t.after)}</td><td class="calc-op">${escape(t.operation)}</td></tr>`).join('')}</tbody></table></div>`;
}

// Attack buff text in percent -> exact 1/10000 numerator string; finer input is an error, never truncated.
export function percentToRaw10000(text: string): string {
  const match = /^([+-]?)(\d*)(?:\.(\d*))?$/.exec(text.trim());
  if (!match || !(match[2] || match[3])) throw new Error('공격력 버프는 50, 30처럼 숫자로 입력하세요.');
  const fraction = (match[3] ?? '').replace(/0+$/, '');
  if (fraction.length > 2) throw new Error(`공격력 버프 ${text.trim()}%: 0.01%(1/10000) 단위보다 정밀한 값은 허용하지 않습니다.`);
  const raw = BigInt((match[2] || '0') + fraction.padEnd(2, '0'));
  return (match[1] === '-' && raw !== 0n ? '-' : '') + raw.toString();
}

// HTTP 400 {message} from the hit API: keep the server code, prefix a Korean reason. Never retried with other policies.
const HIT_ERRORS: [RegExp, string][] = [
  [/_must_be_integer_never_truncated/, '정수만 허용합니다 (소수를 절삭하지 않음)'],
  [/rate_requires_exact_1_per_10000_units|_requires_exact_1_per_10000_units/, '공격력 비율은 1/10000 단위만 허용합니다'],
  [/exact_integer_requires_decimal_string_or_safe_integer_number/, '정확한 정수는 십진 문자열 또는 안전 정수만 허용합니다'],
  [/^hit_integer_overflow/, '정수 범위를 넘었습니다'],
  [/^invalid_client_f32_input/, 'client_f32 입력 오류'],
  [/^selected_policy_unavailable/, '선택한 정책으로는 이 입력을 계산할 수 없습니다'],
  [/^schema2_cannot_contain_schema3_rates/, 'schema 2 입력에는 새 두 비율을 넣을 수 없습니다'],
  [/^unknown_hit_field|^unknown_attack_buff_field/, '허용되지 않은 입력 필드'],
  [/^invalid_observed_damage/, '실측 대미지는 양의 안전 정수만 허용합니다']
];
export function hitErrorText(message: string): string {
  const known = HIT_ERRORS.find(([pattern]) => pattern.test(message));
  return known ? `${known[1]} · ${message}` : message;
}

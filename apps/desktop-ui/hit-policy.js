/**
 * Damage policy registry for the desktop UI.
 *
 * The engine (H-F32, 5ced15a) makes client_f32 the default and keeps the three earlier policies as
 * comparison candidates. Backend 74ca24f publishes the wire ("I-BE schema 3" in
 * docs/single-deck-compute-contract.ko.md): replay/compute conditions.roundingPolicy accepts the same four
 * policies and defaults to client_f32. `confirmed: false` reproduces the stage-A (pre-schema 3) choices for tests.
 */

export const CLIENT_F32 = 'client_f32';

export const CLIENT_F32_WIRE = Object.freeze({
  confirmed: true,
  inputSchemaVersion: 3
});

export const HIT_POLICIES = Object.freeze([
  { id: CLIENT_F32, label: '클라이언트 float32', role: 'default',
    note: '공격력 long 조립 → float32 대미지 경로 → 사사오입 · 실측 대조 전' },
  { id: 'legacy_term_floor', label: 'C# 항별 내림', role: 'comparison', note: '과거 기본 · 비교 후보' },
  { id: 'final_round_even', label: '최종 반올림 (절반은 짝수)', role: 'comparison', note: '비교 후보' },
  { id: 'nested_floor', label: '항별 + 단계별 내림', role: 'comparison', note: '비교 후보' }
]);

const byId = new Map(HIT_POLICIES.map(p => [p.id, p]));

export function policyInfo(id) {
  return byId.get(id) ?? { id: id ?? null, label: `미해석 정책 ${id ?? '미제공'}`, role: 'unknown', note: '표시 규칙 없음' };
}

/** Policy the UI sends by default. The unconfirmed (stage A) branch is the earlier legacy default. */
export function defaultPolicy(confirmed = CLIENT_F32_WIRE.confirmed) {
  return confirmed ? CLIENT_F32 : 'legacy_term_floor';
}

/** Options for a policy <select>: client_f32 default first, then the comparison candidates. */
export function policyOptions(confirmed = CLIENT_F32_WIRE.confirmed) {
  return HIT_POLICIES.filter(p => confirmed || p.id !== CLIENT_F32).map(p => ({
    value: p.id,
    label: confirmed && p.role === 'comparison' ? `비교 후보 · ${p.label}` : p.role === 'default' ? `${p.label} (기본)` : p.label,
    selected: p.id === defaultPolicy(confirmed)
  }));
}

/**
 * Orders Compare candidates for display: client_f32 first (engine appends it fourth), then the earlier
 * policies in registry order, then anything unknown. Nothing is dropped; missing expected policies are listed.
 */
export function orderCandidates(candidates) {
  const list = Array.isArray(candidates) ? candidates.filter(c => c && typeof c === 'object') : [];
  const rank = c => { const i = HIT_POLICIES.findIndex(p => p.id === c.policy); return i < 0 ? HIT_POLICIES.length : i; };
  const ordered = list.map((c, i) => ({ c, i })).sort((a, b) => rank(a.c) - rank(b.c) || a.i - b.i)
    .map(({ c }) => ({ ...c, info: policyInfo(c.policy) }));
  const present = new Set(list.map(c => c.policy));
  return { candidates: ordered, missing: HIT_POLICIES.filter(p => !present.has(p.id)).map(p => p.id) };
}

/**
 * Experimental single-hit inputs added by H-F32. Neutral defaults only; no source/boss estimate is filled in.
 * H-SRC: statDamageRatio source unresolved (skill coefficient is a user hypothesis); defenceRatioRate
 * candidate MonsterData.DefenceRatioRatio has no values in the collected tables.
 */
export const EXPERIMENTAL_HIT_INPUTS = Object.freeze([
  { key: 'statDamageRatio', label: 'statDamageRatio', neutral: 1, min: 0,
    note: '실험·미확정 · 원천 불명(스킬 계수는 가설) · 중립 1' },
  { key: 'defenceRatioRate', label: 'defenceRatioRate', neutral: 0, min: 0, max: 1,
    note: '실험·미확정 · 최근 기믹 · 적용 보스·값 불명 · 중립 0' }
]);

/** Strict parse: rejects blanks, text and out-of-range values rather than substituting a neutral value. */
export function parseExperimentalInput(key, text) {
  const spec = EXPERIMENTAL_HIT_INPUTS.find(s => s.key === key);
  if (!spec) throw new Error(`알 수 없는 실험 입력 ${key}`);
  const trimmed = String(text ?? '').trim();
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(trimmed)) throw new Error(`${spec.label}: 숫자를 입력하세요.`);
  const value = Number(trimmed);
  if (!Number.isFinite(value) || value < spec.min || (spec.max !== undefined && value > spec.max))
    throw new Error(`${spec.label}: ${spec.min}${spec.max !== undefined ? `~${spec.max}` : ' 이상'} 범위만 허용합니다.`);
  return value;
}

/**
 * Wire long reader. Exact fields (exactDamage, exactEffectiveAttack, rawRate10000, exactAmount) are decimal
 * strings; audit before/after are binary64 numbers. Numbers beyond 2^53 are flagged as possibly rounded.
 */
export function readWireLong(value) {
  if (typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value))
    return { value, text: String(value), exact: Number.isSafeInteger(value) };
  if (typeof value === 'string' && /^-?\d+$/.test(value)) {
    const exact = BigInt(value);
    const number = Number(value);
    return { value: number, text: exact.toString(), exact: BigInt(number) === exact };
  }
  return null;
}

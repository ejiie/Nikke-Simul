/**
 * Damage policy registry for the desktop UI (client_f32 transition, I-UI stage A).
 *
 * The engine (H-F32, 5ced15a) makes client_f32 the default and keeps the three earlier policies as
 * comparison candidates. The Backend wire contract for schema 3 is not published yet, so
 * CLIENT_F32_WIRE.confirmed stays false: live screens keep sending the current schema/policies, and the
 * client_f32 presentation below is exercised with mock fixtures only. Stage B flips the flag after the
 * Backend commit is merged and the confirmed wire shape is connected.
 */

export const CLIENT_F32 = 'client_f32';

export const CLIENT_F32_WIRE = Object.freeze({
  confirmed: false,
  // Current API compares against the Core constant; the engine raises it to 3 with client_f32.
  liveInputSchemaVersion: 2,
  clientInputSchemaVersion: 3
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

/** Engine default when a stored replay/log omits the policy. Before stage B the live API still defaults to legacy. */
export function defaultPolicy(confirmed = CLIENT_F32_WIRE.confirmed) {
  return confirmed ? CLIENT_F32 : 'legacy_term_floor';
}

/** Options for a policy <select>. Unconfirmed wire keeps the earlier three only, so live requests do not change. */
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
 * Wire long reader. Backend has not fixed number vs string for large longs; accept both, keep the exact text,
 * and flag numbers beyond 2^53 as possibly rounded by JSON parsing.
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

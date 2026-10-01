/**
 * Korean display labels for internal keys (U-FIX-4). API and stored keys stay as they are; only on-screen text uses
 * these labels. Character codes and raw key strings are never returned; unknown shapes get a generic Korean label.
 */

import { REGISTERED_MESSAGES } from './registered-messages.js';
import { own } from './own-lookup.js';

export const SLOT_LABELS = Object.freeze({ head: '머리', torso: '몸통', arm: '팔', arms: '팔', leg: '다리', legs: '다리' });

// Overload/option definition ids -> Korean (same wording as the equipment editor, without "증가").
export const OPTION_LABELS = Object.freeze({
  StatAtk: '공격력', IncHurtDef: '방어력', StatDef: '방어력', StatAmmoLoad: '최대 장탄 수', StatAmmo: '최대 장탄 수',
  StatCritical: '크리티컬 확률', StatCriticalDamage: '크리티컬 대미지', StatChargeDamage: '차지 대미지',
  StatChargeTime: '차지 속도', IncElementDmg: '우월코드 대미지', StatAccuracyCircle: '명중률'
});

export const BASIS_LABELS = Object.freeze({
  native_recipient: '수혜자 기초 스탯 기준', native_caster: '시전자 기초 스탯 기준',
  native_caster_flat_at_application: '시전자 기준 · 부여 시점 고정값',
  caster_final_max_hp_at_application: '시전자 최종 최대 HP 기준 · 부여 시점 고정',
  caster_charge_centiseconds: '시전자 차지 시간 기준'
});

export const slotLabel = key => own(SLOT_LABELS, key) ?? '장비';
export const optionLabel = key => own(OPTION_LABELS, key) ?? null;
export const basisLabel = key => key ? own(BASIS_LABELS, key) ?? '적용 기준 미확인' : '적용 기준 미기록';

/**
 * Display text for a buff source key such as `overload:5004:head:1:StatAtk`, `cube:<id>:<type>`,
 * `collection:<id>:<type>`, `equipment:<slot>`, `manual:attack:<n>`, `function:<id>` (resolved by `resolveFunction`, else
 * "스킬 효과"; function numbers are never shown). `skill:<character>:<function>`
 * is handled by the caller (it knows the skill slots); here it becomes the character name only.
 * `nameOf(characterId)` returns a Korean name or null.
 */
export function describeSourceKey(source, { nameOf = () => null, resolveFunction = () => null } = {}) {
  const parts = String(source ?? '').split(':');
  const name = id => (id && nameOf(String(id))) || '이름 미확인';
  switch (parts[0]) {
    case 'overload': {
      const line = /^\d+$/.test(parts[3] ?? '') ? ` ${parts[3]}번 줄` : '';
      return `${name(parts[1])} · ${slotLabel(parts[2])}${line} · ${optionLabel(parts[4]) ?? '오버로드 옵션'}`;
    }
    case 'cube': return optionLabel(parts[2]) ? `큐브 · ${optionLabel(parts[2])}` : '큐브 효과';
    case 'collection': return optionLabel(parts[2]) ? `소장품 · ${optionLabel(parts[2])}` : '소장품 효과';
    case 'equipment': return `장비 · ${slotLabel(parts[1])}`;
    case 'manual': return /^\d+$/.test(parts[2] ?? '') ? `직접 입력한 버프 ${parts[2]}` : '직접 입력한 버프';
    // U-FIX-5: never the function number; the caller may resolve it to "character · slot".
    case 'function': return (/^\d+$/.test(parts[1] ?? '') && resolveFunction(parts[1])) || '스킬 효과';
    case 'skill': return `${name(parts[1])} · 스킬 효과`;
    default: return '기타 효과';
  }
}

// U-FIX-6/7: server error texts are codes/paths. Allow-list only: a mapped code or a registered Korean text
// (registered-messages.js, generated from the server sources) is shown; anything else becomes a generic Korean text,
// whatever it contains. There is no deny-list of "code-like" shapes. The raw text stays on the Error as
// `serverMessage` (and in `details`) for logic, never for display.
const SERVER_MESSAGES = Object.freeze({
  analysis_not_integrated: '통계 모듈이 연결되지 않아 집계를 제공할 수 없습니다.',
  gpu_unavailable: 'GPU를 사용할 수 없습니다.',
  saved_tactic_stale: '저장된 버스트 전술이 현재 편성과 달라 사용할 수 없습니다.',
  engine_or_rules_version_changed: '엔진·규칙 버전이 바뀐 이전 실험은 재개할 수 없습니다.',
  prepared_input_fingerprint_mismatch: '저장된 준비 입력이 일치하지 않아 재개할 수 없습니다.',
  baseline_input_mismatch: '기준 실험과 조건이 달라 비교할 수 없습니다.',
  baseline_required: '비교 기준 실험이 없습니다.',
  warmup_excluded_from_statistics: '예열 실행은 통계에서 제외됩니다.',
  invalid_experiment_input: '실험 요청 값이 올바르지 않습니다.',
  boss_conditions_mixed_with_legacy: '보스 거리·약점 조건과 이전 방식 조건을 함께 보낼 수 없습니다.',
  boss_id_unknown: '선택한 보스를 찾을 수 없습니다. 보스를 다시 선택하세요.',
  condition_profile_invalid: '전투 조건 프로필이 올바르지 않습니다.',
  legacy_defense_mode_requires_fixed: '이전 방식 조건은 고정 방어력만 사용할 수 있습니다.',
  solo_raid_duration_fixed_10800: '솔로 레이드 전투 시간은 180초로 고정입니다.',
  solo_raid_pellet_policy_fixed_per_trigger: '샷건 계수는 발사 1회로 고정입니다.',
  solo_raid_defense_mode_requires_team_damage_threshold: '방어력은 누적 대미지 자동 전환만 사용할 수 있습니다.',
  invalid_enemy_defense: '적 방어력 값이 올바르지 않습니다.',
  combat_profile_catalog_missing: '사거리·속성 데이터가 준비되지 않았습니다.',
  combat_profile_invalid: '사거리·속성 데이터에 오류가 있습니다.',
  combat_member_profile_missing: '편성 멤버의 사거리·속성 데이터가 없습니다.'
});

/** True only for an exact registered server text. */
export const isRegisteredMessage = text => typeof text === 'string' && REGISTERED_MESSAGES.has(text);

/** Korean text for a server error message: mapped code or registered text, else a generic text. */
export function friendlyServerMessage(raw, status = null) {
  const message = String(raw ?? '');
  const code = Object.keys(SERVER_MESSAGES).find(key => message === key || message.startsWith(`${key}:`) || message.startsWith(`${key} `));
  if (code) return own(SERVER_MESSAGES, code);
  if (isRegisteredMessage(message)) return message;
  return Number.isInteger(status) ? `요청을 처리하지 못했습니다 (HTTP ${status}).` : '요청을 처리하지 못했습니다.';
}

// U-FIX-6: execution/hardware reason codes on the statistics screen, in Korean. Unknown codes are not shown raw.
const REASON_LABELS = Object.freeze({
  bounded_workload_benchmark: '제한된 후보 실측으로 선택', partial_workload_benchmark: '일부 후보 실측으로 선택',
  benchmark_budget_cpu_fallback: '실측 시간 부족으로 CPU 기본값 사용', validated_policy_cache: '검증된 이전 실측 재사용',
  measured_cache: '이전 실측 재사용', cache_reused: '이전 실측 재사용', current_engine_cpu: '현재 엔진 CPU 경로',
  conservative_resource_limit: '자원 여유를 두고 제한', memory_limit: '메모리 한도', memory_unknown_conservative_limit: '메모리 정보가 없어 보수적으로 제한',
  insufficient_memory: '메모리 부족', gpu_unavailable: 'GPU 사용 불가', device_unavailable: '장치 사용 불가', driver_missing: '드라이버 없음',
  full_battle_provider_not_implemented: '전체 전투 GPU 계산 미구현', gpu_not_implemented: 'GPU 계산 미구현', not_implemented: '미구현', not_measured: '실측 안 함', not_run: '실행 안 함',
  run_failed: '실행 실패', candidates_not_completed: '후보 실측 미완료', stage_budget_exhausted: '단계 시간 한도 도달',
  total_budget_exhausted: '전체 시간 한도 도달', external_cancelled: '외부 취소', cpu_topology_invalid: 'CPU 정보 확인 불가',
  gpu_entry_invalid: 'GPU 정보 확인 불가', inventory_access_denied: '장치 목록 접근 거부', inventory_failed: '장치 목록 조회 실패',
  inventory_os_unsupported: '이 OS에서는 장치 목록 조회 미지원', inventory_timeout: '장치 목록 조회 시간 초과',
  invalid_backend: '잘못된 계산 장치 요청', invalid_resource_limit: '잘못된 자원 한도', invalid_tuning_budget: '잘못된 실측 시간 한도'
});

export function reasonLabel(code) {
  const key = String(code ?? '').trim();
  if (!key) return null;
  return own(REASON_LABELS, key) ?? '기타 사유';
}

/**
 * Korean text for a caught Error. Errors the UI itself raised with Korean text carry `display: true`
 * (see `displayError`); anything else (transport/English/unregistered server text) goes through the allow-list.
 */
export const errorText = error => error?.display === true && typeof error.message === 'string' ? error.message
  : friendlyServerMessage(error?.message, Number.isInteger(error?.status) ? error.status : null);
export const displayError = (message, extra = {}) => Object.assign(new Error(message), { display: true }, extra);
/** Server-supplied free text (job/connection/issue messages): shown only when registered, else the Korean fallback. */
export const koreanText = (raw, fallback) => (isRegisteredMessage(String(raw ?? '')) ? String(raw) : fallback);

/**
 * Snapshot change lines are server templates ("<이름>: 스펙 변경" ...). Only the registered templates are shown; the
 * character name is kept only when it is a known display name, and the slot goes through `slotLabel`.
 */
export function describeChange(line, knownNames = new Set()) {
  const text = String(line ?? '');
  const fixed = ['계정 스탯 변경', '계정 큐브 레벨 변경', '스펙 변경 없음'];
  if (fixed.includes(text)) return text;
  const first = /^최초 수집: (\d{1,5})명$/.exec(text);
  if (first) return text;
  const named = /^(.+): (신규 수집|스펙 변경|로스터에서 제외)$/.exec(text);
  if (named) return `${knownNames.has(named[1]) ? named[1] : '이름 미확인 니케'}: ${named[2]}`;
  const slot = /^(.+): (head|torso|arm|arms|leg|legs) 장비\/잠금 변경$/.exec(text);
  if (slot) return `${knownNames.has(slot[1]) ? slot[1] : '이름 미확인 니케'}: ${slotLabel(slot[2])} 장비/잠금 변경`;
  return '변경 내역 (상세 미확인)';
}

/**
 * Damage Log & Burst Tactics Boundary Adapter (U3 Integration Edition)
 *
 * Provides strict isolation and exact schema mapping between Desktop UI and Backend (B2) / Engine (E1).
 *
 * Conforms to:
 * - Backend contract: docs/damage-log-api-contract.ko.md (b63ad12 / bf19679)
 * - Engine contract: docs/damage-log-engine-contract.ko.md (3b92101 / 908047f)
 *
 * Distinctly separates real API integration from explicit mock fixtures.
 * Never silently disguises uncollected/failed logs as mocks.
 */

export const DAMAGE_LOG_SCHEMA_VERSION = 1;
export const DAMAGE_LOG_PROVISIONAL_NOTICE = '잠정 정확도 · 실게임 관측 대조 전 합성 시뮬레이션';

/**
 * Validates burst tactics against current formation members and rules.
 * Returns diagnostic badges, issues, and execution status.
 */
export function auditBurstTactics(membersWithMeta, tactics) {
  const issues = [];
  const memberIds = new Set(membersWithMeta.map(m => m.id));

  // 1. Stale ID check: Nikkes present in tactics but not in current formation
  const tacticNikkeIds = new Set([
    ...(tactics?.allowlist ? Object.keys(tactics.allowlist) : []),
    ...(tactics?.priority?.stage1 ?? []),
    ...(tactics?.priority?.stage2 ?? []),
    ...(tactics?.priority?.stage3 ?? []),
    tactics?.firstCaster
  ].filter(Boolean));

  const staleIds = [];
  for (const tid of tacticNikkeIds) {
    if (!memberIds.has(tid)) {
      staleIds.push(tid);
    }
  }
  if (staleIds.length > 0) {
    issues.push({
      code: 'stale_id',
      level: 'warning',
      message: `편성에서 제외된 니케가 버스트 설정에 남아 있습니다: ${staleIds.join(', ')}`,
      staleIds
    });
  }

  // 2. Stage completeness check: Formation must have at least one Burst I, II, III
  const formationStages = { 1: 0, 2: 0, 3: 0 };
  for (const m of membersWithMeta) {
    if (m.burstStep >= 1 && m.burstStep <= 3) {
      formationStages[m.burstStep]++;
    }
  }

  for (let s = 1; s <= 3; s++) {
    if (formationStages[s] === 0) {
      issues.push({
        code: `missing_stage_${s}`,
        level: 'error',
        message: `현재 편성에 버스트 ${['I', 'II', 'III'][s - 1]}단계 니케가 없습니다. 버스트 사이클이 진행되지 않습니다.`
      });
    }
  }

  // 3. Incomplete tactic check: Allowed Nikkes in stage
  if (tactics?.allowlist) {
    for (let s = 1; s <= 3; s++) {
      const stageMembers = membersWithMeta.filter(m => m.burstStep === s);
      if (stageMembers.length > 0) {
        const allowedCount = stageMembers.filter(m => tactics.allowlist[m.id] !== false).length;
        if (allowedCount === 0) {
          issues.push({
            code: `all_disabled_stage_${s}`,
            level: 'error',
            message: `버스트 ${['I', 'II', 'III'][s - 1]}단계의 모든 니케가 사용 제외로 설정되었습니다. 버스트 발동이 차단됩니다.`
          });
        }
      }
    }
  }

  // 4. Priority only mode vs First Caster mismatch check
  if (tactics?.stage3Mode === 'priority_only') {
    const p1 = tactics.priority?.stage3?.[0];
    if (tactics.firstCaster && p1 && tactics.firstCaster !== p1) {
      const p1Member = membersWithMeta.find(m => m.id === p1);
      const firstMember = membersWithMeta.find(m => m.id === tactics.firstCaster);
      issues.push({
        code: 'priority_only_mismatch',
        level: 'error',
        message: `우선순위 고정 모드에서는 1순위 니케(${p1Member?.displayName || p1})만 버스트를 발동합니다. 첫 시전자(${firstMember?.displayName || tactics.firstCaster})와 불일치합니다.`
      });
    }
  }

  const hasError = issues.some(i => i.level === 'error');
  const executionStatus = staleIds.length > 0 ? 'stale'
    : hasError ? 'draft_incomplete'
    : 'requires_execution_validation';

  return {
    valid: !hasError,
    executionStatus,
    issues,
    staleIds
  };
}

/**
 * Creates default burst tactics based on current formation members.
 */
export function createDefaultTactics(membersWithMeta) {
  const allowlist = {};
  const stage1 = [];
  const stage2 = [];
  const stage3 = [];

  for (const m of membersWithMeta) {
    allowlist[m.id] = true;
    if (m.burstStep === 1) stage1.push(m.id);
    else if (m.burstStep === 2) stage2.push(m.id);
    else if (m.burstStep === 3) stage3.push(m.id);
  }

  const hasAlice = stage3.includes('5004');
  const firstCaster = hasAlice ? '5004' : (stage3[0] ?? null);

  return {
    version: 2,
    allowlist,
    priority: {
      stage1,
      stage2,
      stage3
    },
    burst3Rotation: [...stage3],
    stage3Mode: 'alternate', // 'alternate' (순환 교대) | 'priority_only' (우선순위 고정)
    firstCaster,
    fallbackPolicy: 'next_ready' // 'next_ready' | 'wait_preferred'
  };
}

/**
 * Converts internal UI tactics model to Backend/Engine BurstTacticSettings (schemaVersion: 1)
 */
export function toServerTacticDto(tactics, membersWithMeta) {
  if (!tactics) return null;

  const memberIds = new Set(membersWithMeta.map(m => m.id));
  const allowedCharacterIds = membersWithMeta
    .map(m => m.id)
    .filter(id => tactics.allowlist?.[id] !== false);

  const filterAllowed = list => (list || []).filter(id => memberIds.has(id) && allowedCharacterIds.includes(id));

  const stage1Priority = filterAllowed(tactics.priority?.stage1);
  const stage2Priority = filterAllowed(tactics.priority?.stage2);
  const stage3Priority = filterAllowed(tactics.priority?.stage3);

  let burst3Rotation = [];
  if (tactics.stage3Mode === 'priority_only') {
    if (tactics.firstCaster && stage3Priority.length > 0 && tactics.firstCaster !== stage3Priority[0]) {
      throw new Error(`priority_only_mismatch: first caster ${tactics.firstCaster} conflicts with priority 1 ${stage3Priority[0]}`);
    }
    burst3Rotation = stage3Priority.slice(0, 1);
  } else {
    // If customized burst3Rotation exists and is valid subset, preserve order and subset
    if (tactics.burst3Rotation && Array.isArray(tactics.burst3Rotation) && tactics.burst3Rotation.length > 0) {
      burst3Rotation = tactics.burst3Rotation.filter(id => memberIds.has(id) && allowedCharacterIds.includes(id));
      if (burst3Rotation.length === 0) burst3Rotation = [...stage3Priority];
    } else {
      burst3Rotation = stage3Priority.length > 0 ? [...stage3Priority] : [];
    }
  }

  // Preserve null if user did not specify a first caster (E1/B2 allows null as first element of rotation)
  let firstBurst3CharacterId = null;
  if (tactics.firstCaster && typeof tactics.firstCaster === 'string' && tactics.firstCaster.trim() !== '') {
    firstBurst3CharacterId = tactics.firstCaster;
  }

  return {
    schemaVersion: 1,
    allowedCharacterIds,
    stage1Priority,
    stage2Priority,
    stage3Priority,
    burst3Rotation,
    firstBurst3CharacterId,
    unavailablePolicy: tactics.fallbackPolicy === 'wait_preferred' ? 'wait_preferred' : 'next_ready'
  };
}

/**
 * Converts Backend/Engine BurstTacticSettings (schemaVersion: 1) to internal UI tactics model
 */
export function fromServerTacticDto(dto, membersWithMeta) {
  if (!dto) return createDefaultTactics(membersWithMeta);

  const allowlist = {};
  const allowedSet = new Set(dto.allowedCharacterIds || []);

  if (Array.isArray(membersWithMeta) && membersWithMeta.length > 0) {
    for (const m of membersWithMeta) {
      allowlist[m.id] = allowedSet.has(m.id);
    }
  }

  for (const id of allowedSet) {
    if (allowlist[id] === undefined) {
      allowlist[id] = true;
    }
  }

  const allReferencedIds = new Set([
    ...(dto.stage1Priority || []),
    ...(dto.stage2Priority || []),
    ...(dto.stage3Priority || []),
    ...(dto.burst3Rotation || [])
  ]);
  for (const id of allReferencedIds) {
    if (allowlist[id] === undefined) {
      allowlist[id] = allowedSet.has(id);
    }
  }

  const stage3Priority = dto.stage3Priority || [];
  const rotation = dto.burst3Rotation ? [...dto.burst3Rotation] : [];
  const isPriorityOnly = rotation.length === 1 && rotation[0] === stage3Priority[0];

  return {
    version: 2,
    allowlist,
    priority: {
      stage1: dto.stage1Priority || [],
      stage2: dto.stage2Priority || [],
      stage3: stage3Priority
    },
    burst3Rotation: rotation,
    stage3Mode: isPriorityOnly ? 'priority_only' : 'alternate',
    firstCaster: dto.firstBurst3CharacterId ?? null, // Preserve exact null if server had null!
    fallbackPolicy: dto.unavailablePolicy || 'next_ready'
  };
}

/**
 * Saves burst tactic to server (PUT /api/accounts/{id}/burst-tactic)
 */
export async function saveBurstTacticToServer(api, accountId, snapshotId, formationSlots, tactics, membersWithMeta) {
  if (!api || !accountId) return { ok: false, error: '계정이 선택되지 않았습니다.' };
  const dto = toServerTacticDto(tactics, membersWithMeta);
  const payload = {
    snapshotId,
    formationSlots,
    tactic: dto
  };

  try {
    const res = await api(`/accounts/${accountId}/burst-tactic`, 'PUT', payload);
    return { ok: true, data: res };
  } catch (err) {
    return { ok: false, error: err.message || '서버 전술 저장 실패' };
  }
}

/**
 * Loads burst tactic from server (GET /api/accounts/{id}/burst-tactic)
 */
export async function loadBurstTacticFromServer(api, accountId, membersWithMeta) {
  if (!api || !accountId) return { ok: false, error: '계정이 선택되지 않았습니다.' };

  try {
    const res = await api(`/accounts/${accountId}/burst-tactic`, 'GET');
    if (res && res.saved && res.saved.tactic) {
      const parsed = fromServerTacticDto(res.saved.tactic, membersWithMeta);
      return {
        ok: true,
        tactics: parsed,
        stale: Boolean(res.stale),
        executionStatus: res.executionStatus || 'saved',
        rawDto: res.saved.tactic
      };
    } else {
      return { ok: true, tactics: null, stale: false, executionStatus: res?.executionStatus || 'legacy' };
    }
  } catch (err) {
    return { ok: false, error: err.message || '서버 전술 조회 실패' };
  }
}

// ---------------------------------------------------------------------------
// Per-hit damage audit presentation.
// Meaning follows the engine: SkillReplay.AddEffect stores Effect.Value together with a basis and
// HitCalculator.Compare records the calculation terms. Nothing here recomputes or replaces damage.
// ---------------------------------------------------------------------------

// Official FunctionType wire values (legacy OfficialSkillEnums mirror), limited to the types
// SkillReplay.CheckSupport accepts. unit = how AddEffect stores Value for a native_* basis:
// ratio = FunctionValue/10000 (sign already normalised by the engine), raw = FunctionValue as is.
const AUDIT_FUNCTION_TYPES = {
  0: { key: 'None', label: '상태 표식', unit: 'raw' },
  1: { key: 'StatAtk', label: '공격력', unit: 'ratio' },
  2: { key: 'HealCharacter', label: 'HP 지속 회복', unit: 'heal' },
  3: { key: 'HealCover', label: '엄폐물 회복', unit: 'raw' },
  5: { key: 'AllAmmo', label: '탄약 무제한', unit: 'raw' },
  8: { key: 'StatAccuracyCircle', label: '명중률', unit: 'ratio' },
  11: { key: 'StatChargeDamage', label: '차지 대미지', unit: 'ratio' },
  14: { key: 'StatAmmo', label: '최대 장탄 수', unit: 'ammo' },
  27: { key: 'GainAmmo', label: '탄 회복', unit: 'raw' },
  40: { key: 'Immortal', label: '불사', unit: 'raw' },
  42: { key: 'DamageReduction', label: '받는 대미지', unit: 'ratio' },
  51: { key: 'StatCriticalDamage', label: '크리티컬 대미지', unit: 'ratio' },
  54: { key: 'StatPenetration', label: '관통', unit: 'raw' },
  61: { key: 'StatChargeTime', label: '차지 속도', unit: 'ratio' },
  62: { key: 'DrainHpBuff', label: '흡혈', unit: 'ratio' },
  72: { key: 'UseCharacterSkillId', label: '스킬 호출', unit: 'raw' },
  75: { key: 'Damage', label: '스킬 대미지', unit: 'raw' },
  83: { key: 'ChangeCoolTimeUlti', label: '버스트 쿨타임 변경', unit: 'raw' },
  94: { key: 'StatHpHeal', label: '최대 HP', unit: 'ratio' },
  96: { key: 'BreakDamage', label: '저지 대미지', unit: 'ratio' }
};
const AUDIT_SLOT_LABELS = { skill1: '스킬 1', skill2: '스킬 2', burst: '버스트' };
const AUDIT_TERM_LABELS = {
  effectiveAttack: '최종 공격력', effectiveDefense: '적용 방어력', charge: '차지 배율', P: '기본 피해 P',
  base: '⌊P⌋ 기본항', distance: '적정 거리 항', fullBurst: '풀버스트 항', critical: '크리티컬 항', core: '코어 항',
  B2: 'B2 가산 묶음', B3: 'B3 공격·관통·파츠 대미지', B4: 'B4 받는 대미지', B5: 'B5 우월 코드',
  final: '최종 정수화', minimum: '최소 피해'
};
const NATIVE_BASES = new Set(['native_recipient', 'native_caster']);
const isFiniteNumber = v => typeof v === 'number' && Number.isFinite(v);

/** Formats an engine number without binary float noise; keeps sign and meaningful decimals. */
export function formatAuditNumber(value) {
  if (!isFiniteNumber(value)) return '미제공';
  const clean = Number.isInteger(value) ? value : Number(value.toPrecision(15));
  const text = clean.toLocaleString('ko-KR', { maximumFractionDigits: 12 });
  return text === '-0' ? '0' : text;
}

/** Positive values get '+', negative values keep their own '-' (never '+-'). */
export function formatSignedAudit(value, suffix = '') {
  if (!isFiniteNumber(value)) return '미제공';
  return (value > 0 ? '+' : '') + formatAuditNumber(value) + suffix;
}

const formatRate = rate => isFiniteNumber(rate) ? formatSignedAudit(rate * 100, '%') : '미제공';

/** expiresAt is exclusive; null is the engine's no-expiry/conditional effect; undefined is unrecorded. */
export function describeAuditDuration(expiresAt, frame) {
  if (expiresAt === undefined) return { kind: 'unknown', text: '지속시간 미제공' };
  if (expiresAt === null) return { kind: 'none', text: '만료 없음(전투 지속·조건 해제 시 제거)' };
  if (!isFiniteNumber(expiresAt)) return { kind: 'unknown', text: '지속시간 해석 불가' };
  if (!isFiniteNumber(frame)) return { kind: 'absolute', text: `${expiresAt}F 만료(타격 프레임 미확인)` };
  const remaining = expiresAt - frame;
  if (remaining <= 0) return { kind: 'expired', text: `만료 프레임 경과(${expiresAt}F) · 기록 확인 필요` };
  // Frames are the exact value; seconds are a rounded reading aid only.
  return { kind: 'remaining', text: `잔여 ${remaining}F(약 ${formatAuditNumber(Math.round(remaining / 60 * 100) / 100)}초)` };
}

/**
 * Builds name/slot lookups from a saved replay (inputs[].skills.slots) and formation members.
 * Only direct slot function IDs are mapped; nested/connected functions stay as explicit IDs.
 */
export function createAuditContext(replay, membersWithMeta = []) {
  const names = new Map();
  for (const m of membersWithMeta || []) {
    if (m?.id != null && m.displayName && String(m.displayName) !== String(m.id)) names.set(String(m.id), String(m.displayName));
  }
  const slots = new Map();
  const inputs = Array.isArray(replay?.inputs) ? replay.inputs : null;
  for (const input of inputs ?? []) {
    const characterId = input?.weapon?.characterId;
    if (characterId == null) continue;
    for (const [slot, definition] of Object.entries(input?.skills?.slots ?? {})) {
      const ids = [...(definition?.functionIds ?? []), ...Object.values(definition?.functionPhases ?? {}).flat()];
      for (const id of ids) if (id) slots.set(`${characterId}:${id}`, slot);
    }
  }
  const conditions = replay?.result?.conditions ?? replay?.conditions ?? null;
  const interruptionTarget = typeof conditions?.interruptionTarget === 'boolean' ? conditions.interruptionTarget : null;
  return { names, slots, hasInputs: inputs !== null, interruptionTarget };
}

function auditNikkeText(id, ctx) {
  if (id == null || id === '') return '출처 미기록';
  const name = ctx?.names?.get(String(id));
  return name ? `${name} (#${id})` : `니케 #${id}`;
}

function auditOriginText(sourceId, functionId, burstCastId, ctx) {
  const parts = [];
  if (functionId == null) parts.push('함수 ID 미기록');
  else {
    const slot = ctx?.slots?.get(`${sourceId}:${functionId}`);
    if (slot) parts.push(`${AUDIT_SLOT_LABELS[slot] ?? slot} · 함수 ${functionId}`);
    else parts.push(ctx?.hasInputs ? `함수 ${functionId} · 슬롯 미확인(하위 스킬·연결 함수)` : `함수 ${functionId}`);
  }
  if (burstCastId != null) parts.push(`버스트 시전 이벤트 #${burstCastId}`);
  return parts.join(' · ');
}

/** Describes one DamageBuffSnapshot: official type name, engine unit/basis, stacks and duration. */
export function describeBuffSnapshot(snapshot, frame, ctx = null) {
  const effect = snapshot?.effect ?? {};
  const typeId = Number.isInteger(effect.type) ? effect.type : null;
  const def = typeId === null ? null : AUDIT_FUNCTION_TYPES[typeId] ?? null;
  const value = isFiniteNumber(effect.value) ? effect.value : null;
  const stacks = Number.isInteger(effect.stacks) && effect.stacks > 0 ? effect.stacks : null;
  const basis = typeof effect.basis === 'string' && effect.basis ? effect.basis : null;
  const rawBasisText = basis ? `basis ${basis}` : 'basis 미기록';
  let label = def ? def.label : `미해석 효과 (type ${effect.type ?? '미기록'})`;
  let unit = 'raw';
  let basisText = rawBasisText;
  let note = def ? null : '추정 단위 없이 원값 표시';
  if (def) {
    const standard = basis === 'native_recipient' ? '수혜자 기준' : basis === 'native_caster' ? '시전자 기준' : null;
    if (typeId === 1 && basis === 'native_caster_flat_at_application') {
      unit = 'flat'; label = '공격력(고정)'; basisText = '시전자 기초 공격력 × 비율 · 부여 시점 고정값';
    } else if (typeId === 1 && NATIVE_BASES.has(basis)) {
      unit = 'ratio'; basisText = basis === 'native_recipient' ? '수혜자 기초 공격력 기준' : '시전자(본인) 기초 공격력 기준';
    } else if (typeId === 2 && basis === 'caster_final_max_hp_at_application') {
      unit = 'hpPerSecond'; basisText = '시전자 최종 최대 HP 기준 · 부여 시점 고정';
    } else if (typeId === 61 && basis === 'caster_charge_centiseconds') {
      unit = 'chargeCs'; label = '차지 시간'; basisText = '시전자 차지 시간 기준 · 고정 단축량';
    } else if (typeId === 14 && NATIVE_BASES.has(basis)) {
      // StatAmmo is Integer (raw count kept as an integer) or Percent (raw/10000). The snapshot carries no
      // value type, so only a non-integer value proves Percent; an integer (1 = 1발 or 100%) stays unknown.
      basisText = standard;
      if (value !== null && !Number.isInteger(value)) { unit = 'ratio'; note = '소수 원값 → 비율(Percent) 확정'; }
      else { unit = 'unknownUnit'; note = '탄 수/비율 구분 기록 없음'; }
    } else if (def.unit === 'ratio' && NATIVE_BASES.has(basis)) {
      unit = 'ratio'; basisText = standard;
    } else if (def.unit !== 'raw') {
      note = '예상하지 않은 basis · 원값 그대로 표시';
    }
    if (typeId === 42 && effect.target === 'boss') label = '적 받는 대미지';
  }
  const format = v => unit === 'ratio' ? formatRate(v)
    : unit === 'flat' ? formatSignedAudit(v)
    : unit === 'hpPerSecond' ? `초당 HP ${formatSignedAudit(v)}`
    : unit === 'chargeCs' ? formatSignedAudit(-v / 100, '초')
    : unit === 'unknownUnit' ? `단위 미확인 · 원값 ${formatAuditNumber(v)}`
    : `원값 ${formatAuditNumber(v)}`;
  let valueText;
  if (value === null) valueText = '값 미기록';
  else if (stacks !== null && stacks > 1) {
    valueText = unit === 'raw' || unit === 'unknownUnit'
      ? `${format(value)} · ${stacks}스택` : `스택당 ${format(value)} × ${stacks} = ${format(value * stacks)}`;
  } else valueText = format(value);
  const duration = describeAuditDuration(effect.expiresAt, frame);
  const sourceId = effect.source != null ? String(effect.source) : null;
  const functionId = effect.functionId ?? null;
  return {
    typeId,
    typeKey: def?.key ?? null,
    known: Boolean(def) && unit !== 'unknownUnit' && !note?.startsWith('예상하지'),
    label,
    unit,
    value,
    valueText,
    stacks,
    basis,
    basisText,
    note,
    targetId: effect.target ?? null,
    sourceId,
    sourceText: auditNikkeText(sourceId, ctx),
    functionId,
    originText: auditOriginText(sourceId, functionId, snapshot?.burstCastId ?? null, ctx),
    durationKind: duration.kind,
    durationText: duration.text,
    // Legacy fields kept for existing consumers; `value` stays the raw engine value (no unit applied).
    source: auditNikkeText(sourceId, ctx),
    type: label,
    remainingFrames: duration.kind === 'remaining' ? effect.expiresAt - frame : null,
    raw: snapshot
  };
}

/**
 * Decides whether an active effect is an input of this hit's HitCalculator call.
 * Uses stored hit fields only; contributions that the log cannot prove stay 'unverified'.
 */
// A missing or null flag is "not recorded", never false.
const triState = v => v === true ? true : v === false ? false : null;

const HIT_INDEPENDENT_TYPES = new Set([0, 2, 3, 5, 8, 14, 27, 40, 61, 62, 94]); // never HitCalculator inputs

export function classifyBuffForHit(desc, hit, ctx = null) {
  const hitMissing = !hit || typeof hit !== 'object';
  const ownTarget = desc.typeId === 42 && desc.targetId != null && desc.targetId !== 'boss';
  if (hitMissing && !HIT_INDEPENDENT_TYPES.has(desc.typeId) && !ownTarget) {
    return { group: 'unverified', axis: null, reason: '타격 계산 입력(hit) 미제공' };
  }
  hit = hitMissing ? {} : hit;
  const indirect = reason => ({ group: 'indirect', axis: null, reason });
  const unverified = (axis, reason) => ({ group: 'unverified', axis, reason });
  const applied = axis => ({ group: 'applied', axis, reason: null });
  const excluded = (axis, reason) => ({ group: 'excluded', axis, reason });
  // Additive/multiplier effects need a recorded value with the engine's ratio basis before a claim.
  const measurable = desc.value !== null && desc.unit === 'ratio';
  const unmeasured = axis => unverified(axis, '값 또는 basis 미확인');
  switch (desc.typeId) {
    case 1: {
      const rates = Array.isArray(hit.runtimeAttackBuffs) ? hit.runtimeAttackBuffs : null;
      const flats = Array.isArray(hit.attackFlatBuffs) ? hit.attackFlatBuffs : null;
      const key = `skill:${desc.sourceId}:${desc.functionId}`;
      if (rates?.some(b => b?.source === key)) return applied('최종 공격력 · 비율 합산');
      if (flats?.some(b => b?.source === key)) return applied('최종 공격력 · 고정 가산');
      return unverified('최종 공격력', rates && flats ? '타격 공격력 입력 목록에 같은 출처가 없음' : '타격 공격력 입력 목록 미기록');
    }
    case 11: {
      const fullCharge = triState(hit.fullCharge);
      if (fullCharge === false) return excluded('차지 배율', '풀차지 타격 아님 → 차지 배율 1');
      if (fullCharge === null || triState(hit.chargeApplicable) !== true) return unverified('차지 배율', '풀차지 적용 여부 미기록');
      return measurable ? applied('차지 배율 · 가산항') : unmeasured('차지 배율 · 가산항');
    }
    case 51: {
      const crit = triState(hit.crit);
      if (crit === false) return excluded('크리티컬 보너스', '크리티컬 아님');
      if (crit === null) return unverified('크리티컬 보너스', '크리티컬 여부 미기록');
      return measurable ? applied('가산 묶음 · 크리티컬 보너스') : unmeasured('가산 묶음 · 크리티컬 보너스');
    }
    case 42:
      if (desc.targetId == null) return unverified('B4 · 받는 대미지', '효과 대상 미기록');
      if (desc.targetId !== 'boss') return indirect('아군 대상 효과 · 이 타격 산식 항 아님');
      if (!isFiniteNumber(hit.damageTaken)) return unverified('B4 · 받는 대미지', '타격 받는 대미지 입력 미기록');
      return measurable ? applied('B4 · 받는 대미지') : unmeasured('B4 · 받는 대미지');
    case 96:
      if (ctx?.interruptionTarget === false) return excluded('B3', '저지 대상 조건 꺼짐');
      if (ctx?.interruptionTarget !== true) return unverified('B3', '저지 대상 조건 미확인');
      return measurable ? applied('B3 · 공격 대미지(저지 대상)') : unmeasured('B3 · 공격 대미지(저지 대상)');
    case 54: {
      const pierce = triState(hit.pierce);
      if (pierce === null) return unverified('B3 · 관통 대미지', '관통 판정 미기록');
      if (pierce === false) return indirect('이 타격은 관통 판정 없음');
      if (!isFiniteNumber(hit.pierceDamage)) return unverified('B3 · 관통 대미지', '관통 대미지 입력 미기록');
      return hit.pierceDamage !== 0 ? applied('B3 · 관통 대미지') : indirect('관통 판정만 활성 · 관통 대미지 보너스 0');
    }
    case 5: case 14: case 27: case 61:
      return indirect('발사·탄약 흐름에 영향 · 피해 산식 항 아님');
    case 8:
      return indirect('명중 판정용 · 피해 산식 항 아님');
    case 2: case 3: case 40: case 62: case 94:
      return indirect('회복·생존 효과 · 피해 산식 항 아님');
    case 0:
      return indirect('상태 표식 · 다른 효과의 발동 조건');
    default:
      return { group: 'unverified', axis: null, reason: '미해석 효과 · 피해 반영 여부 판단 불가' };
  }
}

/**
 * Reads the stored HitCalculator breakdown (calculation.terms + hit). Missing values stay null.
 * Object-form terms (legacy/synthetic preview) only fill the headline cards.
 */
export function buildDamageBreakdown(entry) {
  const hit = entry?.hit && typeof entry.hit === 'object' ? entry.hit : null;
  const calc = entry?.calculation && typeof entry.calculation === 'object' ? entry.calculation : null;
  const list = Array.isArray(calc?.terms) ? calc.terms.filter(t => t && typeof t.name === 'string') : null;
  const legacy = !list && calc?.terms && typeof calc.terms === 'object' ? calc.terms : null;
  const term = name => list?.find(t => t.name === name) ?? null;
  const val = v => isFiniteNumber(v) ? v : null;
  const attackTerm = term('effectiveAttack');
  const defenseTerm = term('effectiveDefense');
  const chargeTerm = term('charge');
  const pTerm = term('P');
  const minimumTerm = term('minimum');
  const finalTerm = term('final');
  const bonuses = [
    ['distance', '적정 거리', 'properDistance', 'distanceBonus'],
    ['fullBurst', '풀버스트', 'fullBurst', 'burstBonus'],
    ['critical', '크리티컬', 'crit', 'critBonus'],
    ['core', '코어', 'core', 'coreBonus']
  ].map(([name, label, flag, field]) => {
    const t = term(name);
    return { name, label, active: triState(hit?.[flag]), bonus: val(hit?.[field]),
      term: t ? { before: val(t.before), after: val(t.after) } : null };
  });
  // Known only when every flag is explicit and every active bonus value is recorded.
  const bonusSum = bonuses.every(b => b.active === false || (b.active === true && b.bonus !== null))
    ? bonuses.reduce((sum, b) => sum + (b.active ? b.bonus : 0), 0) : null;
  const factors = ['B3', 'B4', 'B5'].map(name => {
    const t = term(name);
    const match = /^multiply\s+([^;\s]+)/.exec(t?.operation ?? '');
    const factor = match ? Number(match[1]) : NaN;
    return { name, label: AUDIT_TERM_LABELS[name], present: Boolean(t), factor: isFiniteNumber(factor) ? factor : null,
      before: val(t?.before), after: val(t?.after), floored: /floor/.test(t?.operation ?? '') };
  });
  const finalValue = val(finalTerm?.after) ?? val(minimumTerm?.after);
  const storedDamage = val(entry?.damage);
  const required = ['effectiveAttack', 'effectiveDefense', 'charge', 'P'];
  return {
    policy: typeof calc?.policy === 'string' && calc.policy ? calc.policy : null,
    hasSteps: Boolean(list?.length),
    baseAttack: val(attackTerm?.before) ?? val(hit?.statAttack) ?? val(legacy?.baseAttack),
    effectiveAttack: val(attackTerm?.after) ?? val(legacy?.effectiveAttack),
    defense: val(defenseTerm?.after) ?? val(legacy?.effectiveDefense),
    defenseIgnored: defenseTerm?.operation === 'ignore',
    attackDefenseDifference: val(pTerm?.before) ?? val(legacy?.statDifference),
    coefficient: val(hit?.coefficient) ?? val(legacy?.skillMultiplier),
    charge: {
      value: val(chargeTerm?.after) ?? val(legacy?.charge) ?? val(legacy?.chargeMultiplier),
      // HitCalculator: charge = FullCharge ? … : 1 and FullCharge requires ChargeApplicable.
      applied: triState(hit?.fullCharge) === false ? false
        : triState(hit?.fullCharge) === true && triState(hit?.chargeApplicable) === true ? true : null,
      base: val(hit?.chargeBase), multiplierBonus: val(hit?.chargeMultiplierBonus), add: val(hit?.chargeAdd)
    },
    p: val(pTerm?.after),
    minimum: minimumTerm ? { before: val(minimumTerm.before), after: val(minimumTerm.after) } : null,
    bonuses,
    bonusSum,
    b2: val(term('B2')?.after),
    factors,
    finalValue,
    storedDamage,
    calculationDamage: val(calc?.damage),
    finalMatchesStored: finalValue !== null && storedDamage !== null ? finalValue === storedDamage : null,
    steps: (list ?? []).map(t => ({ name: t.name, label: AUDIT_TERM_LABELS[t.name] ?? `기록 항목 ${t.name}`,
      before: val(t.before), after: val(t.after), operation: typeof t.operation === 'string' ? t.operation : '' })),
    missing: list ? required.filter(n => !term(n)).concat(finalTerm || minimumTerm ? [] : ['final']) : ['terms']
  };
}

/** Human-readable formula for the stored rounding policy (HitCalculator.Compare). */
export function describeRoundingFormula(policy, minimum = false) {
  const lines = ['P = (최종 공격력 − 방어력) × 스킬 계수 × 차지 배율',
    '차지 배율 = 풀차지면 기본 × (1 + 배율 증가) + 가산, 아니면 1'];
  if (minimum) return [...lines, '방어력 ≥ 공격력 → 최소 피해 1 (가산 묶음·B3~B5 미적용)'];
  const floorB2 = 'B2 = ⌊P⌋ + ⌊P×거리⌋ + ⌊P×풀버스트⌋ + ⌊P×크리⌋ + ⌊P×코어⌋ (보너스끼리 더하는 가산 묶음, 항마다 내림)';
  switch (policy) {
    case 'legacy_term_floor': return [...lines, floorB2, '최종 = ⌊B2 × B3 × B4 × B5⌋'];
    case 'nested_floor': return [...lines, floorB2, '최종 = ⌊⌊⌊B2 × B3⌋ × B4⌋ × B5⌋ (곱할 때마다 내림)'];
    case 'final_round_even': return [...lines, 'B2 = P × (1 + 거리 + 풀버스트 + 크리 + 코어) (가산 묶음, 중간 정수화 없음)',
      '최종 = 반올림(B2 × B3 × B4 × B5, 동률은 짝수) · 최소 1'];
    default: return [...lines, `정수화 정책 ${policy ?? '미제공'}: 해석 불가 · 아래 저장 단계를 그대로 확인`];
  }
}

/** Complete audit model for one stored DamageLogEntry. */
export function buildHitAudit(entry, ctx = null) {
  const breakdown = buildDamageBreakdown(entry);
  const effects = (Array.isArray(entry?.buffs) ? entry.buffs : []).map(b => {
    const desc = describeBuffSnapshot(b, entry?.frame, ctx);
    return { ...desc, ...classifyBuffForHit(desc, entry?.hit, ctx) };
  });
  const hit = entry?.hit && typeof entry.hit === 'object' ? entry.hit : null;
  const sourceText = source => {
    const match = /^skill:([^:]+):(\d+)$/.exec(source ?? '');
    return match ? `${auditNikkeText(match[1], ctx)} · ${auditOriginText(match[1], Number(match[2]), null, ctx)}` : String(source ?? '출처 미기록');
  };
  const rateText = b => Number.isInteger(b?.stacks) && b.stacks > 1
    ? `스택당 ${formatRate(b.rate)} × ${b.stacks}` : formatRate(b?.rate);
  const attackSources = hit ? [
    ...(hit.attackBuffs ?? []).map(b => ({ kind: '상시 비율', source: sourceText(b?.source), valueText: rateText(b) })),
    ...(hit.runtimeAttackBuffs ?? []).map(b => ({ kind: '전투 중 비율', source: sourceText(b?.source), valueText: rateText(b) })),
    ...(hit.attackFlatBuffs ?? []).map(b => ({ kind: '고정 가산', source: sourceText(b?.source), valueText: formatSignedAudit(b?.amount) }))
  ] : null;
  const group = name => effects.filter(e => e.group === name);
  return {
    breakdown,
    formula: describeRoundingFormula(breakdown.policy, breakdown.minimum !== null),
    effectCount: effects.length,
    effects: { applied: group('applied'), excluded: group('excluded'), indirect: group('indirect'), unverified: group('unverified') },
    attackSources
  };
}

/**
 * Maps a single native server/engine DamageLogEntry to the UI hit model.
 */
export function mapServerEntryToHit(entry, defaultRoundingPolicy = 'final_round_even', auditContext = null) {
  if (!entry) return null;

  const hitContext = entry.hit || {};
  const calc = entry.calculation || {};
  const buffs = entry.buffs || [];

  // Parse terms from array [{ name, before, after, operation }] or object
  const termsMap = {};
  if (Array.isArray(calc.terms)) {
    for (const t of calc.terms) {
      if (t && t.name) {
        termsMap[t.name] = t.after !== undefined ? t.after : t.before;
      }
    }
  } else if (calc.terms && typeof calc.terms === 'object') {
    Object.assign(termsMap, calc.terms);
  }

  // true / false / null(미기록): a missing flag is never reported as false.
  const isCritical = triState(hitContext.crit);
  const isCore = triState(hitContext.core);
  const isTeamFullBurst = triState(hitContext.fullBurst);
  const isSelfBurstActive = triState(entry.ownBurstEffectActive);
  const isFullCharge = triState(entry.fullCharge); // engine null = not a charge weapon or unrecorded

  // chargeRatioRaw / 10000 -> 0~1 ratio
  const chargeRate = (entry.chargeRatioRaw === null || entry.chargeRatioRaw === undefined)
    ? null
    : (entry.chargeRatioRaw / 10000);

  // Numeric kind mapping: NormalHit=2, DirectSkillHit=3, AdditionalHit=4
  const kindNumber = Number(entry.kind);
  const kindLabel = kindNumber === 2 ? '평타' : kindNumber === 3 ? '스킬' : kindNumber === 4 ? '추가타' : '타격';

  // Audit headline values come from the stored breakdown only; missing values stay null, never 0/1.
  const breakdown = buildDamageBreakdown(entry);
  const activeBuffs = buffs.map(b => describeBuffSnapshot(b, entry.frame, auditContext));

  return {
    hitId: entry.hitId,
    parentId: entry.parentId,
    shotId: entry.shotId != null ? entry.shotId : null,
    pelletIndex: entry.pelletIndex != null ? entry.pelletIndex : null,
    frame: entry.frame,
    seconds: typeof entry.seconds === 'number' ? Number(entry.seconds.toFixed(2)) : Number((entry.frame / 60).toFixed(2)),
    characterId: entry.source,
    target: entry.target,
    effect: entry.effect || (isSelfBurstActive ? 'burst_weapon_hit' : 'normal_attack'),
    kind: kindNumber,
    kindLabel,
    damage: entry.damage,
    cumulativeDamage: entry.cumulativeDamage,
    weaponShotId: entry.weaponShotId,
    chargeRatioRaw: entry.chargeRatioRaw,
    chargeRate,
    isFullCharge,
    effectiveChargeFrames: entry.effectiveChargeFrames != null ? entry.effectiveChargeFrames : null,
    actualChargeFrames: entry.actualChargeFrames != null ? entry.actualChargeFrames : null,
    isCritical,
    isCore,
    isTeamFullBurst,
    isSelfBurstActive,
    ownBurstCastId: entry.ownBurstCastId != null ? entry.ownBurstCastId : null,
    audit: {
      baseAtk: breakdown.baseAttack,
      buffedAtk: breakdown.effectiveAttack,
      effectiveDefense: breakdown.defense,
      statDiff: breakdown.attackDefenseDifference,
      skillMultiplier: breakdown.coefficient,
      chargeMultiplier: breakdown.charge.value,
      roundingPolicy: calc.policy || calc.roundingPolicy || defaultRoundingPolicy,
      activeBuffs,
      terms: termsMap,
      hitContext,
      rawCalculation: calc
    },
    rawEntry: entry
  };
}

/**
 * Fetches damage log from server with strict distinction between:
 * - Real server log (collected / no_damage)
 * - Server uncollected / legacy replay
 * - Explicit mock fixture (only when user requested mock preview)
 */
export async function fetchDamageLog(api, replayId, characterId, replayData, membersWithMeta, options = {}) {
  const { allowMock = false } = options;

  // 1. Direct result inspection: check if replayData contains damageLog from native execution
  const embeddedLog = replayData?.result?.damageLog || replayData?.damageLog;
  if (embeddedLog) {
    if (embeddedLog.characterId && embeddedLog.characterId !== characterId) {
      if (!allowMock) {
        return {
          isMock: false,
          status: 'uncollected',
          schemaVersion: null,
          truncated: false,
          log: null,
          message: `현재 리플레이는 ${embeddedLog.characterId}의 대미지 로그만 수집되었습니다. ${characterId}의 로그를 수집하려면 대상을 선택하고 다시 검산하세요.`
        };
      }
    } else {
      if (embeddedLog.schemaVersion && embeddedLog.schemaVersion !== DAMAGE_LOG_SCHEMA_VERSION) {
        return {
          isMock: false,
          status: 'unsupported_schema',
          schemaVersion: embeddedLog.schemaVersion,
          truncated: false,
          log: null,
          message: `지원하지 않는 로그 스키마 버전입니다 (v${embeddedLog.schemaVersion}).`
        };
      }
      if (embeddedLog.totalDamage === 0 && (!embeddedLog.entries || embeddedLog.entries.length === 0)) {
        return {
          isMock: false,
          status: 'no_damage',
          schemaVersion: embeddedLog.schemaVersion || DAMAGE_LOG_SCHEMA_VERSION,
          truncated: false,
          log: {
            characterId,
            totalHits: 0,
            totalDamage: 0,
            hits: [],
            fullBursts: replayData?.result?.teamBurst?.fullBursts || []
          },
          message: '전투 중 해당 니케의 유효 피해 기록이 0입니다.'
        };
      }

      const roundingPolicy = replayData?.conditions?.roundingPolicy || 'final_round_even';
      const auditContext = createAuditContext(replayData, membersWithMeta);
      const hits = (embeddedLog.entries || []).map(e => mapServerEntryToHit(e, roundingPolicy, auditContext));
      const isTruncated = Boolean(embeddedLog.truncated || embeddedLog.status === 'truncated');
      return {
        isMock: false,
        status: embeddedLog.status === 'truncated' ? 'truncated' : 'collected',
        schemaVersion: embeddedLog.schemaVersion || DAMAGE_LOG_SCHEMA_VERSION,
        truncated: isTruncated,
        truncationReason: embeddedLog.truncationReason,
        log: {
          characterId: embeddedLog.characterId || characterId,
          totalHits: hits.length,
          totalDamage: embeddedLog.totalDamage,
          fullBursts: replayData?.result?.teamBurst?.fullBursts || [],
          hits,
          // Saved replay (inputs/conditions) used only to label audit sources; never mutated.
          auditSource: replayData
        }
      };
    }
  }

  // 2. Query dedicated server API endpoint: GET /api/runtime/skill-replays/{id}/damage-log
  if (replayId && api) {
    try {
      const res = await api(`/runtime/skill-replays/${replayId}/damage-log?characterId=${characterId}`);
      // Unpack envelope: { exportSchemaVersion, collectionStatus, replay: { result: { damageLog } } }
      const serverLog = res?.replay?.result?.damageLog || res?.result?.damageLog || res?.damageLog || (res?.entries ? res : null);
      const collectionStatus = res?.collectionStatus;

      if (collectionStatus === 'not_collected' || (!serverLog && res)) {
        if (!allowMock) {
          return {
            isMock: false,
            status: 'uncollected',
            schemaVersion: null,
            truncated: false,
            log: null,
            message: '과거 실행 결과이거나 대미지 로그가 수집되지 않은 리플레이입니다.'
          };
        }
      } else if (serverLog) {
        if (serverLog.characterId && serverLog.characterId !== characterId) {
          if (!allowMock) {
            return {
              isMock: false,
              status: 'uncollected',
              schemaVersion: null,
              truncated: false,
              log: null,
              message: `현재 리플레이는 ${serverLog.characterId}의 대미지 로그만 수집되었습니다. ${characterId}의 로그를 수집하려면 대상을 선택하고 다시 검산하세요.`
            };
          }
        } else if (serverLog.schemaVersion && serverLog.schemaVersion !== DAMAGE_LOG_SCHEMA_VERSION) {
          return {
            isMock: false,
            status: 'unsupported_schema',
            schemaVersion: serverLog.schemaVersion,
            truncated: false,
            log: null,
            message: `지원하지 않는 로그 스키마 버전입니다 (v${serverLog.schemaVersion}).`
          };
        } else if (serverLog.totalDamage === 0 && (!serverLog.entries || serverLog.entries.length === 0)) {
          return {
            isMock: false,
            status: 'no_damage',
            schemaVersion: serverLog.schemaVersion || DAMAGE_LOG_SCHEMA_VERSION,
            truncated: false,
            log: {
              characterId,
              totalHits: 0,
              totalDamage: 0,
              hits: [],
              fullBursts: res?.replay?.result?.teamBurst?.fullBursts || []
            },
            message: '전투 중 해당 니케의 유효 피해 기록이 0입니다.'
          };
        } else {
          const roundingPolicy = res?.replay?.conditions?.roundingPolicy || replayData?.conditions?.roundingPolicy || 'final_round_even';
          const auditSource = res?.replay || replayData || null;
          const auditContext = createAuditContext(auditSource, membersWithMeta);
          const hits = (serverLog.entries || []).map(e => mapServerEntryToHit(e, roundingPolicy, auditContext));
          const isTruncated = Boolean(serverLog.truncated || serverLog.status === 'truncated');
          return {
            isMock: false,
            status: serverLog.status === 'truncated' ? 'truncated' : 'collected',
            schemaVersion: serverLog.schemaVersion || DAMAGE_LOG_SCHEMA_VERSION,
            truncated: isTruncated,
            truncationReason: serverLog.truncationReason,
            log: {
              characterId: serverLog.characterId || characterId,
              totalHits: hits.length,
              totalDamage: serverLog.totalDamage,
              fullBursts: res?.replay?.result?.teamBurst?.fullBursts || replayData?.result?.teamBurst?.fullBursts || [],
              hits,
              auditSource
            }
          };
        }
      }
    } catch (err) {
      if (!allowMock) {
        return {
          isMock: false,
          status: 'api_error',
          error: err.message,
          schemaVersion: null,
          truncated: false,
          log: null,
          message: `서버 통신 실패: ${err.message}`
        };
      }
    }
  }

  // 3. If log was not found or uncollected, do NOT silently disguise as mock
  if (!allowMock) {
    return {
      isMock: false,
      status: 'uncollected',
      schemaVersion: null,
      truncated: false,
      log: null,
      message: '서버 백엔드/엔진에서 시간별 발당 피해 로그를 아직 수집하지 않았습니다.'
    };
  }

  // 4. Explicit Mock Mode requested by user
  const mockLog = createSyntheticDamageLog(characterId, replayData, membersWithMeta);
  return {
    isMock: true,
    status: 'collected',
    schemaVersion: DAMAGE_LOG_SCHEMA_VERSION,
    truncated: false,
    log: mockLog
  };
}

/**
 * Generates synthetic per-shot damage log for a given character and replay context.
 */
export function createSyntheticDamageLog(characterId, replayData, membersWithMeta) {
  const isAlice = characterId === '5004';
  const isModernia = characterId === '5044';
  const durationFrames = replayData?.conditions?.combat?.durationFrames ?? 10800;
  const fullBursts = replayData?.result?.teamBurst?.fullBursts ?? [
    { cycle: 1, caster: '5004', startFrame: 650, endFrame: 1250 },
    { cycle: 2, caster: '5044', startFrame: 1850, endFrame: 2750 },
    { cycle: 3, caster: '5004', startFrame: 3350, endFrame: 3950 },
    { cycle: 4, caster: '5044', startFrame: 4550, endFrame: 5450 },
    { cycle: 5, caster: '5004', startFrame: 6050, endFrame: 6650 }
  ];

  const hits = [];
  let currentFrame = 12;
  let shotId = 1;
  let hitId = 1;
  let cumulativeDamage = 0;

  const baseAtk = isAlice ? 48500 : isModernia ? 44200 : 38000;
  const def = replayData?.conditions?.combat?.enemyDefense ?? 30925;

  while (currentFrame < durationFrames) {
    const activeFb = fullBursts.find(fb => currentFrame >= fb.startFrame && (fb.endFrame === null || currentFrame < fb.endFrame));
    const isTeamFullBurst = Boolean(activeFb);

    let isSelfBurstActive = false;
    if (isAlice) {
      const aliceCasts = fullBursts.filter(fb => fb.caster === '5004');
      isSelfBurstActive = aliceCasts.some(fb => currentFrame >= fb.startFrame && currentFrame < fb.startFrame + 600);
    } else if (isModernia) {
      const moderniaCasts = fullBursts.filter(fb => fb.caster === '5044');
      isSelfBurstActive = moderniaCasts.some(fb => currentFrame >= fb.startFrame && currentFrame < fb.startFrame + 900);
    }

    let intervalFrames = 60;
    let isFullCharge = false;
    let chargeRate = 1.0;
    let chargeFrames = 0;

    if (isAlice) {
      if (isSelfBurstActive) {
        chargeFrames = 12;
        intervalFrames = 15;
        isFullCharge = true;
        chargeRate = 1.0;
      } else {
        chargeFrames = 54;
        intervalFrames = 62;
        isFullCharge = (shotId % 15 !== 0);
        chargeRate = isFullCharge ? 1.0 : 0.65;
      }
    } else if (isModernia) {
      intervalFrames = 6;
      isFullCharge = false;
      chargeRate = 1.0;
    } else {
      intervalFrames = 40;
    }

    const isCritical = (shotId % 4 === 0 || (isSelfBurstActive && shotId % 2 === 0));
    const isCore = (shotId % 3 !== 0);

    const literBuff = isTeamFullBurst ? 0.44 : 0.15;
    const selfBurstBuff = isSelfBurstActive ? (isAlice ? 0.55 : 0.25) : 0.0;
    const noirBuff = 0.14;
    const totalBuffRatio = literBuff + selfBurstBuff + noirBuff;

    const buffedAtk = Math.round(baseAtk * (1 + totalBuffRatio));
    const statDiff = Math.max(1, buffedAtk - def);

    let skillMultiplier = isAlice ? 3.50 : isModernia ? 0.77 : 1.0;
    let chargeMultiplier = isAlice ? (isFullCharge ? 2.50 : 1.0 + 1.5 * chargeRate) : 1.0;
    let critMultiplier = isCritical ? 1.70 : 1.0;
    let coreMultiplier = isCore ? 2.00 : 1.0;
    let fullBurstMultiplier = isTeamFullBurst ? 1.50 : 1.0;

    let hitDamage = Math.round(statDiff * skillMultiplier * chargeMultiplier * critMultiplier * coreMultiplier * fullBurstMultiplier);
    if (hitDamage <= 0) hitDamage = 100;

    cumulativeDamage += hitDamage;

    // Synthetic preview only: engine-shaped StatAtk (type 1) rate effects with an explicit basis.
    const activeBuffs = [
      { source: '5011', type: 1, value: literBuff, basis: 'native_recipient', remainingFrames: isTeamFullBurst ? 300 : 120 },
      { source: '5009', type: 1, value: noirBuff, basis: 'native_recipient', remainingFrames: null }
    ];
    if (isSelfBurstActive) {
      activeBuffs.push({ source: characterId, type: 1, value: selfBurstBuff, basis: 'native_caster', remainingFrames: 450 });
    }

    const syntheticEntry = {
      hitId,
      parentId: 0,
      shotId,
      pelletIndex: null,
      frame: currentFrame,
      seconds: Number((currentFrame / 60).toFixed(2)),
      source: characterId,
      target: 'boss',
      effect: isSelfBurstActive ? 'skill:50043:weapon' : 'normal_attack',
      kind: 2,
      skillId: isSelfBurstActive ? 50043 : null,
      functionId: null,
      damage: hitDamage,
      cumulativeDamage,
      weaponShotId: shotId,
      chargeRatioRaw: Math.round(chargeRate * 10000),
      fullCharge: isFullCharge,
      effectiveChargeFrames: chargeFrames,
      actualChargeFrames: chargeFrames,
      ownBurstEffectActive: isSelfBurstActive,
      ownBurstCastId: isSelfBurstActive ? 1 : null,
      hit: {
        crit: isCritical,
        core: isCore,
        fullBurst: isTeamFullBurst,
        baseAttack: baseAtk,
        attack: buffedAtk,
        defense: def,
        damageRatio: skillMultiplier,
        chargeMultiplier,
        critMultiplier,
        coreMultiplier,
        fullBurstMultiplier
      },
      calculation: {
        policy: replayData?.conditions?.roundingPolicy ?? 'final_round_even',
        terms: {
          baseAttack: baseAtk,
          effectiveAttack: buffedAtk,
          effectiveDefense: def,
          statDifference: statDiff,
          skillMultiplier,
          chargeMultiplier,
          critMultiplier,
          coreMultiplier,
          fullBurstMultiplier
        }
      },
      buffs: activeBuffs.map(b => ({
        effect: { source: b.source, target: characterId, functionId: null, groupId: null, type: b.type, value: b.value,
          stacks: 1, expiresAt: b.remainingFrames === null ? null : currentFrame + b.remainingFrames, basis: b.basis },
        appliedAtFrame: currentFrame,
        burstCastId: isSelfBurstActive ? 1 : null
      }))
    };

    hits.push(mapServerEntryToHit(syntheticEntry, replayData?.conditions?.roundingPolicy));

    shotId++;
    hitId++;
    currentFrame += intervalFrames;

    if (isAlice && shotId % 20 === 0 && !isSelfBurstActive) {
      currentFrame += 90;
    }
  }

  return {
    characterId,
    totalHits: hits.length,
    totalDamage: cumulativeDamage,
    durationFrames,
    fullBursts,
    hits,
    auditSource: replayData ?? null
  };
}

/**
 * Exports damage log to JSON envelope matching Backend DamageLogExport.Read structure.
 */
export function exportDamageLogToJson(arg1, arg2) {
  let meta = {};
  let damageLogData = {};
  if (arg1 && (arg1.hits || arg1.totalDamage !== undefined || arg1.characterId)) {
    damageLogData = arg1;
    meta = arg2 || {};
  } else {
    meta = arg1 || {};
    damageLogData = arg2 || {};
  }

  // If rawReplay is already provided, conform exactly to DamageLogExport.Read
  if (meta.rawReplay) {
    const replayClone = JSON.parse(JSON.stringify(meta.rawReplay));
    const log = replayClone.result?.damageLog;
    return JSON.stringify({
      exportSchemaVersion: 1,
      collectionStatus: log ? (log.status || 'complete') : 'not_collected',
      replay: replayClone
    }, null, 2);
  }

  const entries = (damageLogData.hits || []).map(h => h.rawEntry || {
    hitId: h.hitId,
    parentId: h.parentId ?? 0,
    shotId: h.shotId,
    pelletIndex: h.pelletIndex,
    frame: h.frame,
    seconds: h.seconds,
    source: h.characterId,
    target: h.target || 'target',
    effect: h.effect || 'normal_attack',
    kind: h.kind || 2,
    damage: h.damage,
    cumulativeDamage: h.cumulativeDamage,
    weaponShotId: h.weaponShotId || h.shotId,
    chargeRatioRaw: h.chargeRatioRaw,
    fullCharge: h.isFullCharge,
    effectiveChargeFrames: h.effectiveChargeFrames,
    actualChargeFrames: h.actualChargeFrames,
    ownBurstEffectActive: h.isSelfBurstActive,
    hit: h.audit?.hitContext,
    calculation: h.audit?.rawCalculation,
    buffs: (h.audit?.activeBuffs || []).map(b => b.raw).filter(Boolean)
  });

  const exportPayload = {
    exportSchemaVersion: 1,
    collectionStatus: 'complete',
    replay: {
      id: meta.replayId || 'replay-export',
      accountSnapshotId: meta.snapshotId ?? null,
      runtimeDataId: meta.runtimeDataId ?? null,
      conditions: {
        damageLog: { characterId: damageLogData.characterId },
        roundingPolicy: meta.roundingPolicy ?? 'final_round_even'
      },
      result: {
        damageLog: {
          schemaVersion: DAMAGE_LOG_SCHEMA_VERSION,
          characterId: damageLogData.characterId,
          status: 'complete',
          truncated: false,
          truncationReason: null,
          eventCount: entries.length,
          totalDamage: damageLogData.totalDamage,
          entries
        }
      }
    }
  };

  return JSON.stringify(exportPayload, null, 2);
}

/**
 * Exports damage log to RFC 4180 compliant CSV string matching Backend DamageLogExport.Csv.
 * Columns: recordType,frame,seconds,hitId,shotId,damage,cumulativeDamage,entryJson,metadataJson
 */
export function exportDamageLogToCsv(arg1, arg2) {
  let meta = {};
  let damageLogData = {};
  if (arg1 && (arg1.hits || arg1.totalDamage !== undefined || arg1.characterId)) {
    damageLogData = arg1;
    meta = arg2 || {};
  } else {
    meta = arg1 || {};
    damageLogData = arg2 || {};
  }

  const cell = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const output = [];
  output.push('recordType,frame,seconds,hitId,shotId,damage,cumulativeDamage,entryJson,metadataJson');

  let metadataEnvelope;
  if (meta.rawReplay) {
    const replayClone = JSON.parse(JSON.stringify(meta.rawReplay));
    const log = replayClone.result?.damageLog;
    if (log && log.entries) {
      delete replayClone.result.damageLog.entries;
    }
    metadataEnvelope = {
      exportSchemaVersion: 1,
      collectionStatus: log ? (log.status || 'complete') : 'not_collected',
      replay: replayClone
    };
  } else {
    metadataEnvelope = {
      exportSchemaVersion: 1,
      collectionStatus: 'complete',
      replay: {
        id: meta.replayId || 'replay-export',
        accountSnapshotId: meta.snapshotId ?? null,
        result: {
          damageLog: {
            schemaVersion: DAMAGE_LOG_SCHEMA_VERSION,
            characterId: damageLogData.characterId,
            status: 'complete',
            totalDamage: damageLogData.totalDamage,
            eventCount: damageLogData.totalHits || (damageLogData.hits || []).length
          }
        }
      }
    };
  }

  // Metadata row (line 2)
  output.push(`metadata,,,,,,,,${cell(JSON.stringify(metadataEnvelope))}`);

  // Hit rows (line 3+)
  for (const h of damageLogData.hits || []) {
    const rawEntry = h.rawEntry || {
      hitId: h.hitId,
      shotId: h.shotId,
      frame: h.frame,
      seconds: h.seconds,
      source: h.characterId,
      damage: h.damage,
      cumulativeDamage: h.cumulativeDamage,
      kind: h.kind || 2,
      chargeRatioRaw: h.chargeRatioRaw,
      fullCharge: h.isFullCharge,
      ownBurstEffectActive: h.isSelfBurstActive
    };
    const entryJson = JSON.stringify(rawEntry);
    const shotIdStr = h.shotId != null ? String(h.shotId) : '';
    output.push(`hit,${cell(h.frame)},${cell(h.seconds)},${cell(h.hitId)},${cell(shotIdStr)},${cell(h.damage)},${cell(h.cumulativeDamage)},${cell(entryJson)},`);
  }

  return output.join('\r\n') + '\r\n';
}

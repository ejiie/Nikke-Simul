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
  for (const m of membersWithMeta) {
    allowlist[m.id] = (dto.allowedCharacterIds || []).includes(m.id);
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

/**
 * Maps a single native server/engine DamageLogEntry to the UI hit model.
 */
export function mapServerEntryToHit(entry, defaultRoundingPolicy = 'final_round_even') {
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

  const isCritical = Boolean(hitContext.crit);
  const isCore = Boolean(hitContext.core);
  const isTeamFullBurst = Boolean(hitContext.fullBurst);
  const isSelfBurstActive = Boolean(entry.ownBurstEffectActive);
  const isFullCharge = entry.fullCharge !== undefined ? entry.fullCharge : null; // Preserve nullable

  // chargeRatioRaw / 10000 -> 0~1 ratio
  const chargeRate = (entry.chargeRatioRaw === null || entry.chargeRatioRaw === undefined)
    ? null
    : (entry.chargeRatioRaw / 10000);

  // Numeric kind mapping: NormalHit=2, DirectSkillHit=3, AdditionalHit=4
  const kindNumber = Number(entry.kind);
  const kindLabel = kindNumber === 2 ? '평타' : kindNumber === 3 ? '스킬' : kindNumber === 4 ? '추가타' : '타격';

  const baseAtk = termsMap.baseAttack ?? hitContext.statAttack ?? hitContext.baseAttack ?? hitContext.attack ?? 0;
  const buffedAtk = termsMap.effectiveAttack ?? hitContext.attack ?? hitContext.statAttack ?? 0;
  const effectiveDefense = termsMap.effectiveDefense ?? hitContext.defense ?? 0;
  const statDiff = termsMap.statDifference ?? Math.max(1, buffedAtk - effectiveDefense);

  const skillMultiplier = hitContext.coefficient ?? termsMap.skillMultiplier ?? hitContext.damageRatio ?? 1.0;
  const chargeMultiplier = termsMap.charge ?? hitContext.chargeBase ?? termsMap.chargeMultiplier ?? 1.0;
  const critMultiplier = hitContext.crit ? (1 + (hitContext.critBonus ?? 0.5)) : 1.0;
  const coreMultiplier = hitContext.core ? (1 + (hitContext.coreBonus ?? 1.0)) : 1.0;
  const fullBurstMultiplier = hitContext.fullBurst ? (1 + (hitContext.burstBonus ?? 0.5)) : 1.0;

  const activeBuffs = buffs.map(b => {
    const eff = b.effect || {};
    const dur = eff.expiresAt != null ? (eff.expiresAt - entry.frame) : null;
    let typeName = '효과';
    if (eff.type === 1) typeName = '공격력 증가';
    else if (eff.type === 61) typeName = '차지속도 증가';
    else if (eff.name) typeName = eff.name;

    return {
      source: eff.source ? `니케 #${eff.source}` : (b.burstCastId ? `버스트 시전 #${b.burstCastId}` : (eff.skillId ? `스킬 #${eff.skillId}` : '효과')),
      type: typeName,
      value: typeof eff.value === 'number' ? eff.value : 0,
      remainingFrames: dur && dur > 0 ? dur : null,
      raw: b
    };
  });

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
      baseAtk,
      buffedAtk,
      effectiveDefense,
      statDiff,
      skillMultiplier,
      chargeMultiplier: Number(chargeMultiplier.toFixed(3)),
      critMultiplier: Number(critMultiplier.toFixed(2)),
      coreMultiplier: Number(coreMultiplier.toFixed(2)),
      fullBurstMultiplier: Number(fullBurstMultiplier.toFixed(2)),
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
      const hits = (embeddedLog.entries || []).map(e => mapServerEntryToHit(e, roundingPolicy));
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
          hits
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
          const hits = (serverLog.entries || []).map(e => mapServerEntryToHit(e, roundingPolicy));
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
              hits
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

    const activeBuffs = [
      { source: '리타 스킬1', type: '공격력 증가', value: literBuff, remainingFrames: isTeamFullBurst ? 300 : 120 },
      { source: '누아르 스킬2', type: '공격력 증가', value: noirBuff, remainingFrames: null }
    ];
    if (isSelfBurstActive) {
      activeBuffs.push({
        source: isAlice ? '앨리스 버스트 (마법소녀)' : '모더니아 버스트 (새벽의 눈)',
        type: isAlice ? '차지속도 & 공격력' : '무기 변경 & 명중률',
        value: selfBurstBuff,
        remainingFrames: 450
      });
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
        effect: { source: b.source, type: b.type, value: b.value, expiresAt: currentFrame + (b.remainingFrames || 600) },
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
    hits
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

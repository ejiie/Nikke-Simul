/**
 * Damage Log & Burst Tactics Boundary Adapter (U2 Integration Edition)
 *
 * Provides strict isolation between Desktop UI and upstream Backend (B1) / Engine (E1) APIs.
 *
 * Conforms to:
 * - Backend contract: docs/damage-log-api-contract.ko.md (bf19679)
 * - Engine contract: docs/damage-log-engine-contract.ko.md (908047f)
 *
 * Distinctly separates real API integration from explicit mock fixtures.
 * Never silently disguises uncollected/failed logs as mocks.
 */

export const DAMAGE_LOG_SCHEMA_VERSION = 1;
export const DAMAGE_LOG_PROVISIONAL_NOTICE = '잠정 정확도 · 실게임 관측 대조 전 합성 시뮬레이션';

/**
 * Validates burst tactics against the current formation members.
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
    burst3Rotation = stage3Priority.slice(0, 1);
  } else {
    // alternate mode: all allowed stage 3 priority candidates
    burst3Rotation = stage3Priority.length > 0 ? [...stage3Priority] : [];
  }

  const firstBurst3CharacterId = (tactics.firstCaster && burst3Rotation.includes(tactics.firstCaster))
    ? tactics.firstCaster
    : (burst3Rotation[0] ?? null);

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
  const rotation = dto.burst3Rotation || [];
  const isAlternate = rotation.length > 1;

  return {
    version: 2,
    allowlist,
    priority: {
      stage1: dto.stage1Priority || [],
      stage2: dto.stage2Priority || [],
      stage3: stage3Priority
    },
    stage3Mode: isAlternate ? 'alternate' : 'priority_only',
    firstCaster: dto.firstBurst3CharacterId || rotation[0] || stage3Priority[0] || null,
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
    const res = await api(`/accounts/${accountId}/burst-tactic`);
    if (res && res.saved && res.saved.tactic) {
      const tactics = fromServerTacticDto(res.saved.tactic, membersWithMeta);
      return {
        ok: true,
        tactics,
        stale: Boolean(res.stale),
        executionStatus: res.executionStatus || 'saved',
        savedAt: res.saved.savedAt
      };
    }
    return { ok: true, tactics: null, stale: false, executionStatus: 'legacy' };
  } catch (err) {
    return { ok: false, error: err.message || '서버 전술 조회 실패' };
  }
}

/**
 * Fetches damage log from server with strict distinction between:
 * - Real server log (collected / no_damage)
 * - Server uncollected / legacy replay
 * - Explicit mock fixture (only when user requested mock preview)
 */
export async function fetchDamageLog(api, replayId, characterId, replayData, membersWithMeta, options = {}) {
  const { allowMock = false } = options;

  // 1. If replayData already has embedded damageLogs from new engine/backend:
  if (replayData?.damageLogs?.[characterId]) {
    return {
      isMock: false,
      status: 'collected',
      schemaVersion: replayData.damageLogSchemaVersion || DAMAGE_LOG_SCHEMA_VERSION,
      truncated: Boolean(replayData.damageLogTruncated),
      log: replayData.damageLogs[characterId]
    };
  }

  // 2. Try fetching from dedicated server API endpoint
  if (replayId && api) {
    try {
      const res = await api(`/runtime/skill-replays/${replayId}/damage-log?characterId=${characterId}`);
      if (res && res.hits) {
        return {
          isMock: false,
          status: res.status || 'collected',
          schemaVersion: res.schemaVersion || DAMAGE_LOG_SCHEMA_VERSION,
          truncated: Boolean(res.truncated),
          log: res
        };
      } else if (res && res.status === 'uncollected') {
        return {
          isMock: false,
          status: 'uncollected',
          schemaVersion: null,
          truncated: false,
          log: null,
          message: '과거 실행 결과이거나 대미지 로그가 수집되지 않은 리플레이입니다.'
        };
      } else if (res && res.status === 'no_damage') {
        return {
          isMock: false,
          status: 'no_damage',
          schemaVersion: res.schemaVersion || DAMAGE_LOG_SCHEMA_VERSION,
          truncated: false,
          log: { characterId, totalHits: 0, totalDamage: 0, hits: [] },
          message: '전투 중 해당 니케의 유효 피해 기록이 0입니다.'
        };
      }
    } catch {
      // API call failed or not found (404/501)
    }
  }

  // 3. Fallback behavior: DO NOT silently disguise as mock unless allowMock is explicitly true!
  if (!allowMock) {
    return {
      isMock: false,
      status: 'uncollected',
      schemaVersion: null,
      truncated: false,
      log: null,
      message: '서버 백엔드/엔진에서 시간별 발당 피해 로그를 아직 수집하지 않았습니다 (E1/B1 연동 대기).'
    };
  }

  // 4. Explicit Mock Mode requested
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
  const durationFrames = replayData?.conditions?.combat?.durationFrames ?? 10800; // 180s * 60fps
  const fullBursts = replayData?.result?.teamBurst?.fullBursts ?? [
    { cycle: 1, caster: '5004', startFrame: 650, endFrame: 1250 },
    { cycle: 2, caster: '5044', startFrame: 1850, endFrame: 2750 },
    { cycle: 3, caster: '5004', startFrame: 3350, endFrame: 3950 },
    { cycle: 4, caster: '5044', startFrame: 4550, endFrame: 5450 },
    { cycle: 5, caster: '5004', startFrame: 6050, endFrame: 6650 },
    { cycle: 6, caster: '5044', startFrame: 7250, endFrame: 8150 },
    { cycle: 7, caster: '5004', startFrame: 8750, endFrame: 9350 },
    { cycle: 8, caster: '5044', startFrame: 9950, endFrame: 10800 }
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

    hits.push({
      shotId,
      hitId,
      frame: currentFrame,
      seconds: Number((currentFrame / 60).toFixed(2)),
      characterId,
      targetLabel: 'solo_raid_challenge',
      effectType: isSelfBurstActive ? 'burst_weapon_hit' : 'normal_attack',
      damage: hitDamage,
      cumulativeDamage,
      isFullCharge,
      chargeRate: Number(chargeRate.toFixed(2)),
      chargeFrames,
      isCritical,
      isCore,
      isTeamFullBurst,
      isSelfBurstActive,
      audit: {
        baseAtk,
        buffedAtk,
        effectiveDefense: def,
        statDiff,
        skillMultiplier,
        chargeMultiplier: Number(chargeMultiplier.toFixed(3)),
        critMultiplier,
        coreMultiplier,
        fullBurstMultiplier,
        roundingPolicy: replayData?.conditions?.roundingPolicy ?? 'final_round_even',
        activeBuffs
      }
    });

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
 * Exports damage log to JSON formatted string with full metadata.
 */
export function exportDamageLogToJson(meta, damageLogData) {
  const exportPayload = {
    exportType: 'NikkeSimulDamageLog',
    schemaVersion: DAMAGE_LOG_SCHEMA_VERSION,
    exportedAt: new Date().toISOString(),
    provisionalNotice: DAMAGE_LOG_PROVISIONAL_NOTICE,
    metadata: {
      snapshotId: meta.snapshotId ?? null,
      connectionId: meta.connectionId ?? null,
      characterId: damageLogData.characterId,
      totalDamage: damageLogData.totalDamage,
      totalHits: damageLogData.totalHits,
      durationSeconds: Number(((damageLogData.durationFrames || 10800) / 60).toFixed(1)),
      roundingPolicy: meta.roundingPolicy ?? 'final_round_even'
    },
    burstTactics: meta.tactics ?? null,
    fullBurstWindows: damageLogData.fullBursts ?? [],
    hits: damageLogData.hits
  };

  return JSON.stringify(exportPayload, null, 2);
}

/**
 * Exports damage log to RFC 4180 compliant CSV string with UTF-8 BOM.
 * Matches Backend format (Metadata row + hit rows).
 */
export function exportDamageLogToCsv(damageLogData, meta = {}) {
  const headers = [
    'recordType',
    'time_sec',
    'frame',
    'shot_id',
    'hit_id',
    'character_id',
    'damage',
    'cumulative_damage',
    'is_full_charge',
    'charge_rate',
    'is_critical',
    'is_core',
    'is_team_full_burst',
    'is_self_burst_active',
    'effect_type',
    'base_atk',
    'buffed_atk',
    'enemy_def',
    'charge_mult',
    'crit_mult',
    'core_mult',
    'full_burst_mult',
    'active_buffs'
  ];

  const rows = [headers.join(',')];

  // Metadata row (B1 specification compliance)
  const metaJson = JSON.stringify({
    schemaVersion: DAMAGE_LOG_SCHEMA_VERSION,
    characterId: damageLogData.characterId,
    totalDamage: damageLogData.totalDamage,
    totalHits: damageLogData.totalHits,
    snapshotId: meta.snapshotId ?? null,
    provisionalNotice: DAMAGE_LOG_PROVISIONAL_NOTICE
  }).replace(/"/g, '""');

  rows.push(['metadata', '0.00', '0', '', '', damageLogData.characterId, '0', '0', '0', '0', '0', '0', '0', '0', '"meta"', '', '', '', '', '', '', '', `"${metaJson}"`].join(','));

  for (const h of damageLogData.hits || []) {
    const buffSummary = (h.audit?.activeBuffs ?? []).map(b => `${b.source}(+${Math.round(b.value * 100)}%)`).join(';');
    const row = [
      'hit',
      h.seconds,
      h.frame,
      h.shotId,
      h.hitId,
      h.characterId,
      h.damage,
      h.cumulativeDamage,
      h.isFullCharge ? 1 : 0,
      h.chargeRate,
      h.isCritical ? 1 : 0,
      h.isCore ? 1 : 0,
      h.isTeamFullBurst ? 1 : 0,
      h.isSelfBurstActive ? 1 : 0,
      `"${h.effectType}"`,
      h.audit?.baseAtk ?? '',
      h.audit?.buffedAtk ?? '',
      h.audit?.effectiveDefense ?? '',
      h.audit?.chargeMultiplier ?? 1.0,
      h.audit?.critMultiplier ?? 1.0,
      h.audit?.coreMultiplier ?? 1.0,
      h.audit?.fullBurstMultiplier ?? 1.0,
      `"${buffSummary.replace(/"/g, '""')}"`
    ];
    rows.push(row.join(','));
  }

  return '\uFEFF' + rows.join('\r\n');
}

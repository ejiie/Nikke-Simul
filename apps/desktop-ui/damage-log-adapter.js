/**
 * Damage Log & Burst Tactics Boundary Adapter
 *
 * Provides isolation between the Desktop UI and upstream Engine/Backend APIs.
 * When real Backend (B1) / Engine (E1) endpoints are not yet available or return 404/501,
 * it safely delivers deterministic mock fixtures conforming to the verified specification.
 */

export const DAMAGE_LOG_SCHEMA_VERSION = '2026-09-11.p04.team.2';
export const DAMAGE_LOG_PROVISIONAL_NOTICE = '잠정 정확도 · 실게임 관측 대조 전 합성 시뮬레이션';

/**
 * Validates burst tactics against the current formation members.
 * Returns diagnostic badges and issues.
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

  return {
    valid: issues.every(i => i.level !== 'error'),
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

  // If Alice (5004) is present in Stage 3, default first caster to Alice
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
    fallbackPolicy: 'next_ready' // 'next_ready' (대체 후보 발동) | 'wait_preferred' (우선 후보 대기)
  };
}

/**
 * Fetches damage log from server or falls back to synthetic mock fixture.
 */
export async function fetchDamageLog(api, replayId, characterId, replayData, membersWithMeta) {
  // If replayData already has log embedded from new engine/backend:
  if (replayData?.damageLogs?.[characterId]) {
    return {
      isMock: false,
      schemaVersion: replayData.damageLogSchemaVersion || DAMAGE_LOG_SCHEMA_VERSION,
      truncated: Boolean(replayData.damageLogTruncated),
      log: replayData.damageLogs[characterId]
    };
  }

  // Try fetching dedicated log endpoint if it exists
  if (replayId && api) {
    try {
      const res = await api(`/runtime/skill-replays/${replayId}/damage-log?characterId=${characterId}`);
      if (res && res.hits) {
        return {
          isMock: false,
          schemaVersion: res.schemaVersion || DAMAGE_LOG_SCHEMA_VERSION,
          truncated: Boolean(res.truncated),
          log: res
        };
      }
    } catch {
      // Endpoint not implemented yet; fallback to mock adapter boundary
    }
  }

  // Synthesize deterministic mock log conforming to the verified contract
  const mockLog = createSyntheticDamageLog(characterId, replayData, membersWithMeta);
  return {
    isMock: true,
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
  const isLiter = characterId === '5011';
  const durationFrames = replayData?.conditions?.combat?.durationFrames ?? 10800; // 180s * 60fps
  const totalDamage = replayData?.result?.members?.find(m => m.characterId === characterId)?.damage ?? (isAlice ? 124500000 : 98000000);
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
  let currentFrame = 12; // Initial firing start
  let shotId = 1;
  let hitId = 1;
  let cumulativeDamage = 0;

  // Base stats definition
  const baseAtk = isAlice ? 48500 : isModernia ? 44200 : 38000;
  const def = replayData?.conditions?.combat?.enemyDefense ?? 30925;

  while (currentFrame < durationFrames) {
    // Check if team full burst is active at this frame
    const activeFb = fullBursts.find(fb => currentFrame >= fb.startFrame && (fb.endFrame === null || currentFrame < fb.endFrame));
    const isTeamFullBurst = Boolean(activeFb);

    // Check if self burst effect is active (Alice: active for 600 frames after she casts Burst III)
    let isSelfBurstActive = false;
    if (isAlice) {
      const aliceCasts = fullBursts.filter(fb => fb.caster === '5004');
      isSelfBurstActive = aliceCasts.some(fb => currentFrame >= fb.startFrame && currentFrame < fb.startFrame + 600);
    } else if (isModernia) {
      const moderniaCasts = fullBursts.filter(fb => fb.caster === '5044');
      isSelfBurstActive = moderniaCasts.some(fb => currentFrame >= fb.startFrame && currentFrame < fb.startFrame + 900);
    }

    // Interval & charging logic
    let intervalFrames = 60;
    let isFullCharge = false;
    let chargeRate = 1.0;
    let chargeFrames = 0;

    if (isAlice) {
      // Alice is sniper rifle (charge weapon)
      // During self-burst, Alice has massive charge speed buff (charge time reduced to ~10-18 frames)
      if (isSelfBurstActive) {
        chargeFrames = 12;
        intervalFrames = 15; // 0.25s rapid tap/charge
        isFullCharge = true;
        chargeRate = 1.0;
      } else {
        chargeFrames = 54;
        intervalFrames = 62; // ~1s per shot
        // Occasionally a non-full charge (e.g. 5% of shots)
        isFullCharge = (shotId % 15 !== 0);
        chargeRate = isFullCharge ? 1.0 : 0.65;
      }
    } else if (isModernia) {
      // Machine gun (rapid fire)
      intervalFrames = 6; // 10 shots/sec
      isFullCharge = false;
      chargeRate = 1.0;
    } else {
      intervalFrames = 40;
    }

    // Critical & Core hit determinism
    const isCritical = (shotId % 4 === 0 || (isSelfBurstActive && shotId % 2 === 0));
    const isCore = (shotId % 3 !== 0); // 66% core hit

    // Damage calculation audit
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

    // Reload pause (e.g. every 20 shots for Alice, every 300 for Modernia)
    if (isAlice && shotId % 20 === 0 && !isSelfBurstActive) {
      currentFrame += 90; // 1.5s reload
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
      durationSeconds: Number((damageLogData.durationFrames / 60).toFixed(1)),
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
 */
export function exportDamageLogToCsv(damageLogData) {
  const headers = [
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

  for (const h of damageLogData.hits) {
    const buffSummary = (h.audit?.activeBuffs ?? []).map(b => `${b.source}(+${Math.round(b.value * 100)}%)`).join(';');
    const row = [
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

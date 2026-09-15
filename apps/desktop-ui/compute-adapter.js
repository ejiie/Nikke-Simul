/**
 * Single-deck compute presentation adapter (hardware, batch lifecycle, statistics, OL comparison).
 *
 * Wire format: Backend contract v1, Backend commit f2327e5
 * (docs/single-deck-compute-contract.ko.md, src/Nikke.Contracts/Compute.cs), JSON camelCase.
 * Extra compatible fields are allowed by the contract; unknown values are reported rather than guessed.
 *
 * The UI never invents numbers: anything the payload does not prove reads 미확인 / 미지원 / 표본 없음.
 * A GPU counts as usable only when the payload sets eligible=true, and the effective backend is the
 * truth, so a CPU run is never presented as a GPU success.
 */

export const COMPUTE_CONTRACT_VERSION = 'backend-v1-f2327e5';

export const COMPUTE_ROUTES = {
  hardware: '/compute/hardware',
  experiments: '/compute/experiments',
  experiment: id => `/compute/experiments/${id}`,
  cancel: id => `/compute/experiments/${id}/cancel`,
  resume: id => `/compute/experiments/${id}/resume`,
  results: (id, offset = 0, limit = 100) => `/compute/experiments/${id}/results?offset=${offset}&limit=${limit}`,
  statistics: (id, cut = null) => `/compute/experiments/${id}/statistics${cut === null || cut === '' ? '' : `?cut=${encodeURIComponent(cut)}`}`,
  comparison: id => `/compute/experiments/${id}/comparison`
};

export const RESULTS_PAGE_LIMIT = 100; // contract allows up to 1000
export const UNKNOWN = '미확인';
const NOT_SUPPORTED = '미지원';

const isFiniteNumber = v => typeof v === 'number' && Number.isFinite(v);
const triState = v => v === true ? true : v === false ? false : null;
const text = v => typeof v === 'string' && v.trim() ? v.trim() : null;

/** Formats a number without inventing precision; null-ish stays 미확인. */
export function formatNumber(value, { digits = null, suffix = '' } = {}) {
  if (!isFiniteNumber(value)) return UNKNOWN;
  const clean = Number.isInteger(value) ? value : Number(value.toPrecision(15));
  const options = digits === null ? { maximumFractionDigits: 12 } : { minimumFractionDigits: digits, maximumFractionDigits: digits };
  return clean.toLocaleString('ko-KR', options) + suffix;
}

/** Percent with no invented precision: 0.683 → 68.3%, 0 → 0%. */
export function formatPercent(rate, digits = null) {
  if (!isFiniteNumber(rate)) return UNKNOWN;
  return formatNumber(Number((rate * 100).toPrecision(15)), { digits }) + '%';
}

/** Signed percent for candidate option values (+11.11%); never used for probabilities. */
export function formatSignedPercent(rate, digits = null) {
  if (!isFiniteNumber(rate)) return UNKNOWN;
  return (rate > 0 ? '+' : '') + formatPercent(rate, digits);
}

/** Contract Interval(lower, upper, confidence, method). Both bounds and the method are shown. */
export function describeInterval(interval, { percent = false, digits = null } = {}) {
  const lower = isFiniteNumber(interval?.lower) ? interval.lower : null;
  const upper = isFiniteNumber(interval?.upper) ? interval.upper : null;
  const render = v => percent ? formatPercent(v, digits) : formatNumber(v, { digits });
  return {
    lower, upper,
    confidence: isFiniteNumber(interval?.confidence) ? interval.confidence : null,
    method: text(interval?.method),
    text: lower === null || upper === null ? UNKNOWN : `${render(lower)} ~ ${render(upper)}`,
    // Only an interval that excludes 0 supports a direction claim.
    excludesZero: lower !== null && upper !== null && (lower > 0 || upper < 0)
  };
}

const STAGE_LABELS = {
  passed: '통과', ok: '통과', supported: '지원',
  failed: '실패', unsupported: '미지원', not_implemented: '미구현',
  not_run: '미실행', pending: '대기', skipped: '건너뜀', unknown: UNKNOWN
};

const stageLabel = value => {
  const key = text(value);
  if (!key) return UNKNOWN;
  return STAGE_LABELS[key] ?? `상태 ${key}`;
};

/**
 * HardwareProfile (contract): fingerprint, os, architecture, availableProcessors, physicalCores,
 * memoryLimitBytes, remoteSession, gpus[GpuProfile], probeFailures[string].
 * A discovered name is not usability: only eligible=true devices may be offered.
 */
export function describeHardwareProfile(profile) {
  if (!profile || typeof profile !== 'object') {
    return { present: false, statusLabel: '하드웨어 정보 없음', fingerprint: null, os: null, architecture: null,
      availableProcessors: null, physicalCores: null, memoryLimitBytes: null, remoteSession: null,
      devices: [], usableDevices: [], probeFailures: [] };
  }
  const devices = (Array.isArray(profile.gpus) ? profile.gpus : []).map(gpu => {
    const stages = [
      { key: 'runtime', label: '런타임', status: text(gpu?.runtimeStatus) },
      { key: 'selfTest', label: '자체 검사', status: text(gpu?.selfTestStatus) },
      { key: 'correctness', label: '수치 정확성', status: text(gpu?.correctnessStatus) },
      { key: 'benchmark', label: '성능 실측', status: text(gpu?.benchmarkStatus) }
    ].map(stage => ({ ...stage, statusLabel: stageLabel(stage.status) }));
    const eligible = gpu?.eligible === true;
    const blocking = stages.find(s => s.status && !['passed', 'ok', 'supported'].includes(s.status));
    return {
      id: text(gpu?.deviceId),
      name: text(gpu?.name),
      vendor: text(gpu?.vendor),
      driver: text(gpu?.driver),
      backend: text(gpu?.backend),
      memoryBytes: isFiniteNumber(gpu?.memoryBytes) ? gpu.memoryBytes : null,
      supportsFp64: triState(gpu?.supportsFp64),
      stages,
      eligible,
      usable: eligible,
      stageLabel: eligible ? '전 단계 통과 · 사용 가능' : blocking ? `${blocking.label} ${blocking.statusLabel}` : '검증 단계 미기록',
      reason: text(gpu?.reason)
    };
  });
  const probeFailures = (Array.isArray(profile.probeFailures) ? profile.probeFailures : [])
    .map(f => text(f)).filter(Boolean);
  const statusLabel = probeFailures.length ? '탐지 일부 실패'
    : devices.length === 0 ? 'GPU 없음 · CPU만 탐지'
    : devices.some(d => d.usable) ? '탐지 완료' : '탐지 완료 · 사용 가능 GPU 없음';
  return {
    present: true,
    statusLabel,
    fingerprint: text(profile.fingerprint),
    os: text(profile.os),
    architecture: text(profile.architecture),
    availableProcessors: isFiniteNumber(profile.availableProcessors) ? profile.availableProcessors : null,
    physicalCores: isFiniteNumber(profile.physicalCores) ? profile.physicalCores : null,
    memoryLimitBytes: isFiniteNumber(profile.memoryLimitBytes) ? profile.memoryLimitBytes : null,
    remoteSession: triState(profile.remoteSession),
    devices,
    usableDevices: devices.filter(d => d.usable),
    probeFailures
  };
}

/** ExecutionSelection (contract): requested, backend, deviceId, workers, chunkSize, memoryLimitBytes, … */
export function describeExecutionSelection(selection) {
  if (!selection || typeof selection !== 'object') {
    return { present: false, requested: null, requestedLabel: UNKNOWN, backend: null, backendLabel: UNKNOWN,
      deviceId: null, workers: null, chunkSize: null, memoryLimitBytes: null, reason: null, fallbackReason: null,
      fellBack: false, mismatch: false, validationVersion: null, benchmarkVersion: null, fingerprint: null };
  }
  const requested = text(selection.requested);
  const backend = text(selection.backend);
  const label = value => value === 'cpu' ? 'CPU' : value === 'gpu' ? 'GPU' : value ? `기타 (${value})` : UNKNOWN;
  const fallbackReason = text(selection.fallbackReason);
  return {
    present: true,
    requested,
    requestedLabel: requested === 'auto' ? '자동 선택' : requested ? `${label(requested)} 지정` : UNKNOWN,
    backend,
    backendLabel: label(backend),
    deviceId: text(selection.deviceId),
    workers: isFiniteNumber(selection.workers) ? selection.workers : null,
    chunkSize: isFiniteNumber(selection.chunkSize) ? selection.chunkSize : null,
    memoryLimitBytes: isFiniteNumber(selection.memoryLimitBytes) ? selection.memoryLimitBytes : null,
    reason: text(selection.reason),
    fallbackReason,
    fellBack: fallbackReason !== null || (requested === 'gpu' && backend === 'cpu'),
    mismatch: requested === 'gpu' && backend !== null && backend !== 'gpu',
    validationVersion: text(selection.validationVersion),
    benchmarkVersion: text(selection.benchmarkVersion),
    fingerprint: text(selection.fingerprint)
  };
}

/** ExperimentInput (contract): fixed synchro/duration/phase/defPolicy and the input fingerprint. */
export function describeExperimentInput(input) {
  if (!input || typeof input !== 'object') {
    return { present: false, fingerprint: null, snapshotId: null, characterIds: [], synchroLevel: null,
      durationFrames: null, durationSecondsText: UNKNOWN, phase: null, recordLevel: null, defPolicy: null,
      engineVersion: null, rulesVersion: null, dataVersion: null, gameVerified: null };
  }
  const durationFrames = isFiniteNumber(input.durationFrames) ? input.durationFrames : null;
  return {
    present: true,
    fingerprint: text(input.fingerprint),
    snapshotId: text(input.snapshotId),
    characterIds: (Array.isArray(input.characterIds) ? input.characterIds : []).map(id => text(id)).filter(Boolean),
    synchroLevel: isFiniteNumber(input.synchroLevel) ? input.synchroLevel : null,
    durationFrames,
    durationSecondsText: durationFrames === null ? UNKNOWN : `${formatNumber(durationFrames / 60)}초`,
    phase: text(input.phase),
    recordLevel: text(input.recordLevel),
    defPolicy: text(input.defPolicy),
    engineVersion: text(input.engineVersion),
    rulesVersion: text(input.rulesVersion),
    dataVersion: text(input.dataVersion),
    gameVerified: triState(input.gameVerified)
  };
}

const BATCH_STATES = {
  queued: '대기 중', running: '실행 중', cancelling: '취소 중', cancelled: '취소됨',
  completed: '완료', failed: '실패'
};

/**
 * BatchStatus (contract): id, state, attempt, requested/valid/failed/cancelled counts, partial,
 * input, execution, errorCode. valid/failed are current-index counts; cancelled is unfinished indexes.
 */
export function describeBatch(batch) {
  if (!batch || typeof batch !== 'object') {
    return { present: false, id: null, state: null, stateLabel: '배치 없음',
      counts: { requested: null, valid: null, failed: null, cancelled: null }, progress: null, partial: false,
      canStart: true, canCancel: false, canResume: false, attempt: null, errorCode: null, errorLabel: null,
      input: describeExperimentInput(null), execution: describeExecutionSelection(null) };
  }
  const state = text(batch.state);
  const counts = {
    requested: isFiniteNumber(batch.requested) ? batch.requested : null,
    valid: isFiniteNumber(batch.valid) ? batch.valid : null,
    failed: isFiniteNumber(batch.failed) ? batch.failed : null,
    cancelled: isFiniteNumber(batch.cancelled) ? batch.cancelled : null
  };
  const terminal = state === 'completed' || state === 'failed' || state === 'cancelled';
  const errorCode = text(batch.errorCode);
  return {
    present: true,
    id: text(batch.id),
    state,
    stateLabel: BATCH_STATES[state] ?? (state ? `상태 ${state}` : UNKNOWN),
    counts,
    progress: counts.requested && counts.requested > 0 && isFiniteNumber(counts.valid)
      ? Math.min(1, counts.valid / counts.requested) : null,
    partial: batch.partial === true,
    canStart: state === null || terminal,
    canCancel: state === 'queued' || state === 'running',
    canResume: state === 'cancelled' || state === 'failed',
    attempt: isFiniteNumber(batch.attempt) ? batch.attempt : null,
    errorCode,
    errorLabel: describeComputeError(errorCode),
    input: describeExperimentInput(batch.input),
    execution: describeExecutionSelection(batch.execution)
  };
}

/** Contract error codes surfaced to the user without inventing a cause. */
export function describeComputeError(code) {
  const key = text(code);
  if (!key) return null;
  const known = {
    analysis_not_integrated: '통계 모듈(Analysis) 미연결 · 집계를 제공할 수 없습니다.',
    gpu_unavailable: 'GPU 사용 불가 · 강제 GPU 요청은 실행 전에 거부됩니다.',
    stale_tactic: '저장된 버스트 전술이 현재 스냅샷·편성과 달라 거부되었습니다.'
  };
  return known[key] ?? `오류 코드 ${key}`;
}

function metricValue(value, { percent = false, digits = null, unsupported = false } = {}) {
  if (unsupported) return { value: null, text: NOT_SUPPORTED, unsupported: true };
  return {
    value: isFiniteNumber(value) ? value : null,
    text: percent ? formatPercent(value, digits) : formatNumber(value, { digits }),
    unsupported: false
  };
}

/**
 * MetricStatistics (contract): n, mean, sampleSd, meanCi, median, p5, p95, cut, cutSuccess, cutCi,
 * quantileMethod, unit, unsupportedReason. n=0/1 unknowns are null by contract and stay explicit here.
 */
export function describeMetricStatistics(metrics, { label = null } = {}) {
  const unsupportedReason = text(metrics?.unsupportedReason);
  const n = isFiniteNumber(metrics?.n) ? metrics.n : null;
  const sampleNote = unsupportedReason ? null : n === 0 ? '표본 없음' : n === 1 ? '표본 1건 · 산포/신뢰구간 없음' : null;
  const unsupported = Boolean(unsupportedReason);
  const meanCi = describeInterval(metrics?.meanCi);
  const cutCi = describeInterval(metrics?.cutCi, { percent: true });
  return {
    label,
    present: Boolean(metrics && typeof metrics === 'object'),
    n,
    nText: n === null ? UNKNOWN : formatNumber(n),
    sampleNote,
    unsupportedReason,
    mean: metricValue(metrics?.mean, { unsupported }),
    sampleSd: metricValue(metrics?.sampleSd, { unsupported }),
    meanCi: { ...meanCi, text: unsupported ? NOT_SUPPORTED : sampleNote && meanCi.lower === null ? sampleNote : meanCi.text },
    median: metricValue(metrics?.median, { unsupported }),
    p5: metricValue(metrics?.p5, { unsupported }),
    p95: metricValue(metrics?.p95, { unsupported }),
    cut: metricValue(metrics?.cut, { unsupported }),
    cutSuccess: metricValue(metrics?.cutSuccess, { percent: true, unsupported }),
    cutCi: { ...cutCi, text: unsupported ? NOT_SUPPORTED : cutCi.text },
    quantileMethod: text(metrics?.quantileMethod),
    unit: text(metrics?.unit)
  };
}

/**
 * StatisticsResult (contract): experimentId, partial, team, members{characterId: MetricStatistics},
 * methodVersion, gameVerified. Member order follows the batch input when available.
 */
export function describeStatistics(result, { memberOrder = [], displayNames = null } = {}) {
  if (!result || typeof result !== 'object') {
    return { present: false, experimentId: null, partial: false, methodVersion: null, gameVerified: null,
      team: describeMetricStatistics(null, { label: '팀' }), members: [] };
  }
  const membersSource = result.members && typeof result.members === 'object' ? result.members : {};
  const keys = memberOrder.length
    ? [...memberOrder.filter(id => id in membersSource), ...Object.keys(membersSource).filter(id => !memberOrder.includes(id))]
    : Object.keys(membersSource);
  const name = id => displayNames?.get?.(id) ?? id;
  return {
    present: true,
    experimentId: text(result.experimentId),
    partial: result.partial === true,
    methodVersion: text(result.methodVersion),
    gameVerified: triState(result.gameVerified),
    team: describeMetricStatistics(result.team, { label: '팀' }),
    members: keys.map(id => ({ characterId: id, displayName: name(id), ...describeMetricStatistics(membersSource[id], { label: name(id) }) }))
  };
}

/** OlChange (contract): characterId, slot, lineIndex, optionId, value (normalized ratio). */
export function describeOlChange(change, { displayNames = null } = {}) {
  const characterId = text(change?.characterId);
  const value = typeof change?.value === 'number' ? change.value : Number(change?.value);
  return {
    characterId,
    displayName: displayNames?.get?.(characterId) ?? characterId ?? UNKNOWN,
    slot: text(change?.slot),
    lineIndex: isFiniteNumber(change?.lineIndex) ? change.lineIndex : null,
    optionId: text(change?.optionId),
    value: isFiniteNumber(value) ? value : null,
    valueText: isFiniteNumber(value) ? formatSignedPercent(value) : UNKNOWN
  };
}

/**
 * OlComparison (contract): baselineExperimentId, candidateExperimentId, changes, teamMeanDifference,
 * differenceCi, verdict, phase, methodVersion. The payload's verdict is only shown as a decided
 * direction when the difference interval actually excludes 0.
 */
export function describeOlComparison(comparison, { displayNames = null } = {}) {
  if (!comparison || typeof comparison !== 'object') {
    return { present: false, baselineExperimentId: null, candidateExperimentId: null, changes: [],
      difference: { value: null, text: UNKNOWN }, differenceCi: describeInterval(null),
      verdict: 'undetermined', verdictLabel: '우열 미확정', reportedVerdict: null, phase: null,
      methodVersion: null, gameVerified: null, hasMemberEffects: false };
  }
  const differenceCi = describeInterval(comparison.differenceCi);
  const difference = isFiniteNumber(comparison.teamMeanDifference) ? comparison.teamMeanDifference : null;
  const reportedVerdict = text(comparison.verdict);
  const decided = differenceCi.excludesZero && difference !== null;
  const verdict = !decided ? 'undetermined' : difference > 0 ? 'improve' : 'regress';
  return {
    present: true,
    baselineExperimentId: text(comparison.baselineExperimentId),
    candidateExperimentId: text(comparison.candidateExperimentId),
    changes: (Array.isArray(comparison.changes) ? comparison.changes : []).map(change => describeOlChange(change, { displayNames })),
    difference: { value: difference, text: formatNumber(difference) },
    differenceCi,
    verdict,
    verdictLabel: verdict === 'improve' ? '개선' : verdict === 'regress' ? '악화' : '우열 미확정',
    reportedVerdict,
    // A decided payload verdict without a zero-excluding interval is reported, not trusted.
    verdictConflict: reportedVerdict !== null && reportedVerdict !== 'undetermined' && !decided,
    phase: text(comparison.phase),
    methodVersion: text(comparison.methodVersion),
    gameVerified: triState(comparison.gameVerified),
    hasMemberEffects: Boolean(comparison.memberAndCycleEffects)
  };
}

/**
 * Builds the contract ExperimentRequest body. Combat conditions keep the engine's own field names —
 * the defense field is `enemyDefense` (the contract example's targetDefense is a documentation typo
 * Backend is correcting), duration is in frames, synchro stays 400 and recordLevel stays summary.
 */
export function buildExperimentRequest({ snapshotId, characterIds, conditions = {}, runs = 1000, phase = 'final',
  execution = {}, olChanges = null, baselineExperimentId = null, useSavedTactic = true } = {}) {
  const combat = { ...(conditions.combat ?? {}) };
  if (combat.targetDefense !== undefined) { // never send the documented typo
    if (combat.enemyDefense === undefined) combat.enemyDefense = combat.targetDefense;
    delete combat.targetDefense;
  }
  const request = {
    snapshotId: snapshotId ?? null,
    characterIds: Array.isArray(characterIds) ? characterIds : [],
    conditions: { ...conditions, combat },
    runs: isFiniteNumber(runs) && runs > 0 ? Math.floor(runs) : 1000,
    phase,
    recordLevel: 'summary',
    execution: {
      requested: text(execution.requested) ?? 'auto',
      maxWorkers: isFiniteNumber(execution.maxWorkers) ? execution.maxWorkers : null,
      memoryLimitBytes: isFiniteNumber(execution.memoryLimitBytes) ? execution.memoryLimitBytes : null,
      deviceId: text(execution.deviceId),
      retune: execution.retune === true
    },
    useSavedTactic: useSavedTactic !== false
  };
  if (olChanges?.length) request.olChanges = olChanges;
  if (baselineExperimentId) request.baselineExperimentId = baselineExperimentId;
  return request;
}

/**
 * Single-deck compute presentation adapter (hardware, batch lifecycle, statistics, OL comparison).
 *
 * The wire format is owned by Backend (docs/single-deck-compute-contract.ko.md). That document does
 * not exist yet, so every field name and route used here is PROVISIONAL and kept in this one module:
 * when the contract lands only this file changes. The UI never invents numbers — anything the payload
 * does not prove is reported as 미확인 / 미지원 / 표본 없음, and a GPU is only called usable when the
 * payload says it passed the real self-test, accuracy and benchmark stages.
 */

export const COMPUTE_CONTRACT_STATUS = 'provisional_pending_backend_contract';

// Provisional endpoints; not called against a real server until the Backend contract is published.
export const COMPUTE_ROUTES = {
  hardware: '/compute/hardware',
  selection: '/compute/execution-selection',
  batches: '/compute/batches',
  batch: id => `/compute/batches/${id}`,
  batchCancel: id => `/compute/batches/${id}/cancel`,
  batchResume: id => `/compute/batches/${id}/resume`,
  batchResults: id => `/compute/batches/${id}/results`,
  olComparison: id => `/compute/batches/${id}/overload-comparison`
};

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

/** Confidence intervals always print both bounds with their stated method. */
export function formatInterval(interval, { percent = false, digits = null } = {}) {
  const low = interval?.low ?? interval?.lower ?? null;
  const high = interval?.high ?? interval?.upper ?? null;
  if (!isFiniteNumber(low) || !isFiniteNumber(high)) return UNKNOWN;
  const render = v => percent ? formatPercent(v, digits) : formatNumber(v, { digits });
  return `${render(low)} ~ ${render(high)}`;
}

const DEVICE_STAGES = [
  ['inventory', '이름만 탐지', false],
  ['runtime', '런타임 확인', false],
  ['self_test', '자체 검사 통과', false],
  ['accuracy', '수치 정확성 통과', false],
  ['benchmark', '성능 검증 통과 · 사용 가능', true],
  ['eligible', '성능 검증 통과 · 사용 가능', true]
];

/**
 * Detection stage → label. Only the benchmark/eligible stages may be offered as a usable device;
 * a name that was merely discovered is never presented as GPU support.
 */
export function describeDeviceStage(stage) {
  const found = DEVICE_STAGES.find(([key]) => key === stage);
  if (!found) return { stage: stage ?? null, label: stage ? `알 수 없는 단계 (${stage})` : '탐지 단계 미기록', usable: false, known: false };
  return { stage: found[0], label: found[1], usable: found[2], known: true };
}

/** HardwareProfile → view model. Unknown counts stay null, failures keep their reason. */
export function describeHardwareProfile(profile) {
  if (!profile || typeof profile !== 'object') {
    return { status: 'missing', statusLabel: '하드웨어 정보 없음', os: null, architecture: null, cpu: null,
      memoryLimitBytes: null, devices: [], usableDevices: [], failures: [], detectedAt: null };
  }
  const status = text(profile.status) ?? (profile.failures?.length ? 'failed' : 'ok');
  const cpuSource = profile.cpu ?? null;
  const cpu = cpuSource ? {
    model: text(cpuSource.model),
    logicalProcessors: isFiniteNumber(cpuSource.logicalProcessors) ? cpuSource.logicalProcessors : null,
    physicalCores: isFiniteNumber(cpuSource.physicalCores) ? cpuSource.physicalCores : null,
    availableParallelism: isFiniteNumber(cpuSource.availableParallelism) ? cpuSource.availableParallelism : null
  } : null;
  const devices = (Array.isArray(profile.gpus) ? profile.gpus : []).map(device => {
    const stage = describeDeviceStage(text(device?.stage));
    const failure = text(device?.failureReason);
    return {
      id: text(device?.deviceId) ?? null,
      vendor: text(device?.vendor),
      name: text(device?.name),
      backend: text(device?.backend),
      driver: text(device?.driverVersion),
      memoryBytes: isFiniteNumber(device?.memoryBytes) ? device.memoryBytes : null,
      doublePrecision: triState(device?.doublePrecision),
      stage: stage.stage,
      stageLabel: stage.label,
      stageKnown: stage.known,
      usable: stage.usable && failure === null,
      failureReason: failure
    };
  });
  const failures = (Array.isArray(profile.failures) ? profile.failures : [])
    .map(f => ({ scope: text(f?.scope) ?? '탐지', reason: text(f?.reason) ?? UNKNOWN }));
  const statusLabel = status === 'ok' ? (devices.length ? '탐지 완료' : 'GPU 없음 · CPU만 탐지')
    : status === 'failed' ? '탐지 실패'
    : status === 'measuring' ? '측정 중'
    : status === 'missing' ? '하드웨어 정보 없음' : `상태 ${status}`;
  return {
    status, statusLabel,
    os: text(profile.os), architecture: text(profile.architecture), cpu,
    memoryLimitBytes: isFiniteNumber(profile.memoryLimitBytes) ? profile.memoryLimitBytes : null,
    devices, usableDevices: devices.filter(d => d.usable), failures,
    detectedAt: text(profile.detectedAt)
  };
}

/**
 * ExecutionSelection → view model. The effective backend is the truth: a CPU run is never labelled
 * as a GPU success, and a forced GPU request that fell back is reported as a mismatch.
 */
export function describeExecutionSelection(selection) {
  if (!selection || typeof selection !== 'object') {
    return { requested: null, requestedLabel: UNKNOWN, effectiveBackend: null, effectiveLabel: UNKNOWN,
      deviceId: null, workers: null, chunkSize: null, memoryLimitBytes: null, reason: null,
      fallbackReason: null, fellBack: null, mismatch: false, benchmarkVersion: null, validationVersion: null };
  }
  const requested = text(selection.requested);
  const effectiveBackend = text(selection.effectiveBackend ?? selection.backend);
  const label = backend => backend === 'cpu' ? 'CPU' : backend === 'gpu' ? 'GPU' : backend ? `기타 (${backend})` : UNKNOWN;
  const fallbackReason = text(selection.fallbackReason);
  return {
    requested,
    requestedLabel: requested === 'auto' ? '자동 선택' : requested ? label(requested) + ' 지정' : UNKNOWN,
    effectiveBackend,
    effectiveLabel: label(effectiveBackend),
    deviceId: text(selection.deviceId),
    deviceLabel: text(selection.deviceLabel) ?? text(selection.deviceId),
    workers: isFiniteNumber(selection.workers) ? selection.workers : null,
    chunkSize: isFiniteNumber(selection.chunkSize) ? selection.chunkSize : null,
    memoryLimitBytes: isFiniteNumber(selection.memoryLimitBytes) ? selection.memoryLimitBytes : null,
    reason: text(selection.reason),
    fallbackReason,
    fellBack: fallbackReason !== null || (requested === 'gpu' && effectiveBackend === 'cpu'),
    mismatch: requested === 'gpu' && effectiveBackend !== null && effectiveBackend !== 'gpu',
    benchmarkVersion: text(selection.benchmarkVersion),
    validationVersion: text(selection.validationVersion)
  };
}

const BATCH_STATES = {
  queued: '대기 중', running: '실행 중', cancelling: '취소 중', cancelled: '취소됨',
  completed: '완료', failed: '실패'
};

/** Batch lifecycle → view model with the counts kept separate (requested/valid/failed/cancelled). */
export function describeBatch(batch) {
  if (!batch || typeof batch !== 'object') {
    return { id: null, state: null, stateLabel: '배치 없음', counts: { requested: null, valid: null, failed: null, cancelled: null },
      progress: null, partial: false, canStart: true, canCancel: false, canResume: false, attempt: null, message: null, incompleteExcluded: null };
  }
  const state = text(batch.state);
  const counts = {
    requested: isFiniteNumber(batch.requestedRuns) ? batch.requestedRuns : null,
    valid: isFiniteNumber(batch.validRuns) ? batch.validRuns : null,
    failed: isFiniteNumber(batch.failedRuns) ? batch.failedRuns : null,
    cancelled: isFiniteNumber(batch.cancelledRuns) ? batch.cancelledRuns : null
  };
  const progress = counts.requested && counts.requested > 0 && isFiniteNumber(counts.valid)
    ? Math.min(1, counts.valid / counts.requested) : null;
  const terminal = state === 'completed' || state === 'failed' || state === 'cancelled';
  return {
    id: text(batch.batchId ?? batch.id),
    state,
    stateLabel: BATCH_STATES[state] ?? (state ? `상태 ${state}` : UNKNOWN),
    counts,
    progress,
    partial: batch.partial === true || (state === 'cancelled' && (counts.valid ?? 0) > 0),
    canStart: state === null || terminal,
    canCancel: state === 'queued' || state === 'running',
    canResume: state === 'cancelled' || state === 'failed',
    attempt: isFiniteNumber(batch.attempt) ? batch.attempt : null,
    message: text(batch.message),
    // Interrupted runs are not samples; the payload reports them separately from valid ones.
    incompleteExcluded: isFiniteNumber(batch.incompleteExcluded) ? batch.incompleteExcluded : null
  };
}

function metric(value, { digits = null, percent = false } = {}) {
  return { value: isFiniteNumber(value) ? value : null, text: percent ? formatPercent(value, digits) : formatNumber(value, { digits }) };
}

/**
 * Statistics → view model. Mean CI and quantiles stay separate, n=0/1 report their own limits,
 * and a metric the payload marks unsupported is never rendered as a number.
 */
export function describeStatistics(stats) {
  const unsupported = new Set(Array.isArray(stats?.unsupported) ? stats.unsupported.filter(v => typeof v === 'string') : []);
  const n = isFiniteNumber(stats?.n) ? stats.n : null;
  const pick = (key, value, options) => unsupported.has(key)
    ? { value: null, text: NOT_SUPPORTED, unsupported: true }
    : { ...metric(value, options), unsupported: false };
  const sampleNote = n === 0 ? '표본 없음' : n === 1 ? '표본 1건 · 산포/신뢰구간 없음' : null;
  const interval = (key, value, options) => unsupported.has(key)
    ? { text: NOT_SUPPORTED, unsupported: true, low: null, high: null }
    : {
      text: sampleNote && key === 'meanCi' ? sampleNote : formatInterval(value, options),
      unsupported: false,
      low: isFiniteNumber(value?.low ?? value?.lower) ? (value.low ?? value.lower) : null,
      high: isFiniteNumber(value?.high ?? value?.upper) ? (value.high ?? value.upper) : null
    };
  return {
    n,
    nText: n === null ? UNKNOWN : formatNumber(n),
    sampleNote,
    mean: pick('mean', stats?.mean),
    sd: pick('sd', stats?.sampleStandardDeviation ?? stats?.sd),
    meanCi: interval('meanCi', stats?.meanConfidenceInterval ?? stats?.meanCi),
    median: pick('median', stats?.median),
    p5: pick('p5', stats?.p5),
    p95: pick('p95', stats?.p95),
    quantileMethod: text(stats?.quantileMethod),
    ciMethod: text(stats?.confidenceIntervalMethod ?? stats?.ciMethod),
    unit: text(stats?.unit),
    cut: stats?.cut && typeof stats.cut === 'object' ? {
      threshold: metric(stats.cut.threshold),
      successRate: pick('cutSuccessRate', stats.cut.successRate, { percent: true }),
      ci: interval('cutSuccessCi', stats.cut.confidenceInterval ?? stats.cut.ci, { percent: true })
    } : null,
    perMember: (Array.isArray(stats?.perMember) ? stats.perMember : []).map(member => ({
      characterId: text(member?.characterId),
      displayName: text(member?.displayName) ?? text(member?.characterId) ?? UNKNOWN,
      mean: metric(member?.mean),
      meanCi: { text: formatInterval(member?.meanConfidenceInterval ?? member?.meanCi) },
      share: metric(member?.share, { percent: true })
    })),
    unsupportedKeys: [...unsupported]
  };
}

/**
 * OL comparison → view model. A candidate is only called better or worse when its difference
 * interval excludes 0; otherwise it stays 우열 미확정. Module cost/보유량 is not modelled here.
 */
export function describeOlComparison(comparison) {
  const candidates = (Array.isArray(comparison?.candidates) ? comparison.candidates : []).map(candidate => {
    const delta = isFiniteNumber(candidate?.teamMeanDelta) ? candidate.teamMeanDelta : null;
    const ciSource = candidate?.deltaConfidenceInterval ?? candidate?.deltaCi ?? null;
    const low = isFiniteNumber(ciSource?.low ?? ciSource?.lower) ? (ciSource.low ?? ciSource.lower) : null;
    const high = isFiniteNumber(ciSource?.high ?? ciSource?.upper) ? (ciSource.high ?? ciSource.upper) : null;
    const decided = low !== null && high !== null && (low > 0 || high < 0);
    return {
      candidateId: text(candidate?.candidateId),
      characterId: text(candidate?.characterId),
      displayName: text(candidate?.displayName) ?? text(candidate?.characterId) ?? UNKNOWN,
      part: text(candidate?.part),
      line: isFiniteNumber(candidate?.line) ? candidate.line : null,
      optionType: text(candidate?.optionType),
      optionLabel: text(candidate?.optionLabel) ?? text(candidate?.optionType) ?? UNKNOWN,
      value: candidate?.value ?? null,
      valueText: isFiniteNumber(candidate?.value)
        ? (candidate?.valueUnit === 'ratio' ? formatSignedPercent(candidate.value) : formatNumber(candidate.value)) : UNKNOWN,
      delta, deltaText: formatNumber(delta),
      deltaCiText: low === null || high === null ? UNKNOWN : formatInterval({ low, high }),
      verdict: !decided ? 'undetermined' : low > 0 ? 'improve' : 'regress',
      verdictLabel: !decided ? '우열 미확정' : low > 0 ? '개선' : '악화',
      sampleSize: isFiniteNumber(candidate?.n) ? candidate.n : null,
      stage: text(candidate?.stage)
    };
  });
  return {
    baselineExperimentId: text(comparison?.baselineExperimentId),
    candidateExperimentId: text(comparison?.candidateExperimentId),
    virtualOnly: comparison?.virtualOnly !== false,
    candidates,
    undeterminedCount: candidates.filter(c => c.verdict === 'undetermined').length,
    note: text(comparison?.note)
  };
}

/** ExperimentInput summary: fixed synchro 400, duration, fingerprints; nothing is defaulted silently. */
export function describeExperimentInput(input) {
  return {
    snapshotId: text(input?.snapshotId),
    engineVersion: text(input?.engineVersion),
    rulesVersion: text(input?.rulesVersion),
    fingerprint: text(input?.fingerprint),
    synchroLevel: isFiniteNumber(input?.synchroLevel) ? input.synchroLevel : null,
    durationSeconds: isFiniteNumber(input?.durationSeconds) ? input.durationSeconds : null,
    enemyDefense: isFiniteNumber(input?.enemyDefense) ? input.enemyDefense : null,
    requestedRuns: isFiniteNumber(input?.requestedRuns) ? input.requestedRuns : null,
    recordLevel: text(input?.recordLevel),
    members: (Array.isArray(input?.members) ? input.members : []).map(m => ({
      characterId: text(m?.characterId), displayName: text(m?.displayName) ?? text(m?.characterId) ?? UNKNOWN,
      burstStep: isFiniteNumber(m?.burstStep) ? m.burstStep : null
    }))
  };
}

/**
 * Single-deck batch statistics screen: deck/tactic summary, run control, device selection and
 * overload (OL) candidate comparison.
 *
 * Wire mapping lives in compute-adapter.js because Backend still owns the contract
 * (docs/single-deck-compute-contract.ko.md). Until that document exists this screen is verified with
 * fixtures and mocked routes only; the header states whether the payload came from a real endpoint.
 * Nothing here recomputes damage or statistics — it renders what the payload proves and marks the
 * rest 미확인 / 미지원 / 표본 없음.
 */
import {
  COMPUTE_ROUTES,
  describeHardwareProfile,
  describeExecutionSelection,
  describeBatch,
  describeStatistics,
  describeOlComparison,
  describeExperimentInput,
  formatNumber,
  formatPercent,
  UNKNOWN
} from './compute-adapter.js';

const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const BATCH_STORAGE_KEY = 'nikke-single-deck-batch';
export const FIXED_SYNCHRO_LEVEL = 400;
export const DEFAULT_DURATION_SECONDS = 180;
export const DEFAULT_RUNS = 1000;

function bytes(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return UNKNOWN;
  const gib = value / (1024 ** 3);
  return `${formatNumber(Number(gib.toFixed(2)), { digits: 2 })} GiB`;
}

function metricCard(label, value, sub = '') {
  return `<div class="metric-card"><span>${esc(label)}</span><strong>${esc(value)}</strong>${sub ? `<small class="compute-sub">${esc(sub)}</small>` : ''}</div>`;
}

function deckSection(model) {
  const input = model.experiment;
  const members = input.members.length ? input.members : model.deckMembers;
  const rows = members.length
    ? members.map(m => `<li><strong>${esc(m.displayName)}</strong> <span class="pill-badge gray">#${esc(m.characterId ?? UNKNOWN)}</span>${m.burstStep ? ` <span class="pill-badge cyan">버스트 ${esc(['I', 'II', 'III'][m.burstStep - 1] ?? m.burstStep)}</span>` : ''}</li>`).join('')
    : '<li>편성이 비어 있습니다. 솔로 레이드에서 5인을 저장하세요.</li>';
  return `
    <article class="surface">
      <h3>덱과 실행 조건</h3>
      <ul class="compute-deck-list">${rows}</ul>
      <div class="summary-metrics-grid">
        ${metricCard('싱크로 레벨', formatNumber(input.synchroLevel ?? FIXED_SYNCHRO_LEVEL), '고정')}
        ${metricCard('전투 시간', `${formatNumber(input.durationSeconds ?? DEFAULT_DURATION_SECONDS)}초`, '기본값')}
        ${metricCard('적 방어력', formatNumber(input.enemyDefense), '현행 고정 DEF 정책')}
        ${metricCard('버스트 전술', model.tacticSummary || UNKNOWN, '솔로 레이드 저장 설정')}
        ${metricCard('입력 fingerprint', input.fingerprint ?? UNKNOWN, input.rulesVersion ? `규칙 ${input.rulesVersion}` : '')}
      </div>
      <p class="microcopy">자동 DEF 전환은 적용하지 않습니다. 결과는 현재 모델 기반 실험이며 실게임 검증 완료 추천이 아닙니다.</p>
    </article>`;
}

function controlSection(model) {
  const batch = model.batch;
  const counts = batch.counts;
  const progress = batch.progress === null ? UNKNOWN : formatPercent(batch.progress, 1);
  const partial = batch.partial ? '<span class="status-pill warning">부분 결과</span>' : '';
  const incomplete = batch.incompleteExcluded !== null && batch.incompleteExcluded > 0
    ? `<p class="microcopy">중단된 불완전 전투 ${esc(formatNumber(batch.incompleteExcluded))}건은 표본에서 제외했습니다.</p>` : '';
  return `
    <article class="surface">
      <h3>반복 실행</h3>
      <div class="form-grid">
        <label>실행 횟수<input id="compute-runs" type="number" min="1" max="200000" step="1" value="${esc(String(model.requestedRuns))}"${batch.canStart ? '' : ' disabled'}></label>
      </div>
      <div class="action-row">
        <button id="compute-start" class="primary" type="button"${batch.canStart ? '' : ' disabled'}>실행</button>
        <button id="compute-cancel" type="button"${batch.canCancel ? '' : ' disabled'}>취소</button>
        <button id="compute-resume" type="button"${batch.canResume ? '' : ' disabled'}>재개</button>
        <span class="status-pill ${batch.state === 'completed' ? 'green' : batch.state === 'failed' ? 'red' : 'neutral'}" id="compute-batch-state">${esc(batch.stateLabel)}</span>
        ${partial}
        ${model.recovered ? '<span class="status-pill cyan">재시작 복구</span>' : ''}
      </div>
      <progress id="compute-progress" max="1" ${batch.progress === null ? '' : `value="${batch.progress}"`}></progress>
      <div class="summary-metrics-grid">
        ${metricCard('완료 표본', formatNumber(counts.valid), '유효 run')}
        ${metricCard('요청 수', formatNumber(counts.requested))}
        ${metricCard('진행률', progress)}
        ${metricCard('실패', formatNumber(counts.failed))}
        ${metricCard('취소', formatNumber(counts.cancelled))}
      </div>
      ${incomplete}
      ${batch.message ? `<p class="microcopy">${esc(batch.message)}</p>` : ''}
    </article>`;
}

function deviceSection(model) {
  const hardware = model.hardware;
  const selection = model.selection;
  const deviceRows = hardware.devices.length
    ? hardware.devices.map(device => `
      <tr>
        <td>${esc(device.name ?? UNKNOWN)}<br><small class="compute-sub">${esc(device.vendor ?? UNKNOWN)} · ${esc(device.id ?? 'ID 미확인')}</small></td>
        <td>${esc(device.backend ?? UNKNOWN)}<br><small class="compute-sub">driver ${esc(device.driver ?? UNKNOWN)}</small></td>
        <td>${esc(device.stageLabel)}</td>
        <td>${device.usable ? '<span class="pill-badge green">사용 가능</span>' : '<span class="pill-badge gray">사용 불가</span>'}
          ${device.failureReason ? `<br><small class="compute-sub">${esc(device.failureReason)}</small>` : ''}</td>
      </tr>`).join('')
    : '<tr><td colspan="4">탐지된 GPU가 없습니다. CPU로 실행합니다.</td></tr>';
  const options = ['<option value="auto">자동 선택 (권장)</option>', '<option value="cpu">CPU</option>']
    .concat(hardware.usableDevices.map(d => `<option value="gpu:${esc(d.id ?? '')}">GPU · ${esc(d.name ?? d.id ?? UNKNOWN)}</option>`))
    .join('');
  const failures = hardware.failures.length
    ? `<ul class="compute-failures">${hardware.failures.map(f => `<li>${esc(f.scope)}: ${esc(f.reason)}</li>`).join('')}</ul>` : '';
  const mismatch = selection.mismatch
    ? '<p class="compute-warning">GPU 지정 실행이 불가능해 요청과 다른 backend로 실행되었습니다. GPU 성공으로 표시하지 않습니다.</p>' : '';
  const fallback = selection.fellBack && selection.fallbackReason
    ? `<p class="microcopy">CPU fallback 원인: ${esc(selection.fallbackReason)}</p>` : '';
  return `
    <article class="surface">
      <h3>실행 장치</h3>
      <div class="summary-metrics-grid">
        ${metricCard('탐지 상태', hardware.statusLabel, hardware.detectedAt ? `탐지 ${hardware.detectedAt}` : '')}
        ${metricCard('요청', selection.requestedLabel)}
        ${metricCard('실제 backend', selection.effectiveLabel, selection.deviceLabel ? `장치 ${selection.deviceLabel}` : 'CPU 실행')}
        ${metricCard('worker 수', formatNumber(selection.workers))}
        ${metricCard('chunk 크기', formatNumber(selection.chunkSize))}
        ${metricCard('메모리 상한', bytes(selection.memoryLimitBytes))}
      </div>
      ${selection.reason ? `<p class="microcopy">선택 근거: ${esc(selection.reason)}</p>` : ''}
      ${fallback}${mismatch}
      <div class="summary-metrics-grid">
        ${metricCard('OS', hardware.os ?? UNKNOWN, hardware.architecture ?? '')}
        ${metricCard('CPU 병렬도', formatNumber(hardware.cpu?.availableParallelism ?? hardware.cpu?.logicalProcessors ?? null), hardware.cpu?.model ?? '')}
        ${metricCard('물리 코어', formatNumber(hardware.cpu?.physicalCores ?? null))}
        ${metricCard('메모리 한도', bytes(hardware.memoryLimitBytes))}
      </div>
      ${failures}
      <div class="table-scroll">
        <table class="compute-device-table">
          <thead><tr><th>장치</th><th>backend</th><th>검증 단계</th><th>사용 가능</th></tr></thead>
          <tbody>${deviceRows}</tbody>
        </table>
      </div>
      <details class="compute-advanced">
        <summary>고급 · 장치와 자원 상한</summary>
        <div class="form-grid">
          <label>실행 장치<select id="compute-device">${options}</select></label>
          <label>worker 상한<input id="compute-worker-limit" type="number" min="1" max="4096" placeholder="자동"></label>
          <label>메모리 상한 (GiB)<input id="compute-memory-limit" type="number" min="1" max="4096" placeholder="자동"></label>
        </div>
        <div class="action-row">
          <button id="compute-remeasure" type="button">장치 재측정</button>
        </div>
        <p class="microcopy">검증 단계를 통과하지 않은 GPU는 선택할 수 없습니다. 자동 선택은 실제 가용 자원과 짧은 벤치마크 결과를 사용합니다.</p>
      </details>
    </article>`;
}

function statisticsSection(model) {
  const stats = model.statistics;
  const cut = stats.cut;
  const memberRows = stats.perMember.length
    ? stats.perMember.map(m => `<tr><td>${esc(m.displayName)}</td><td>${esc(m.mean.text)}</td><td>${esc(m.meanCi.text)}</td><td>${esc(m.share.text)}</td></tr>`).join('')
    : '<tr><td colspan="4">니케별 결과가 없습니다.</td></tr>';
  return `
    <article class="surface">
      <h3>통계</h3>
      ${stats.sampleNote ? `<p class="compute-warning">${esc(stats.sampleNote)}</p>` : ''}
      <div class="summary-metrics-grid">
        ${metricCard('표본 수 n', stats.nText)}
        ${metricCard('평균 팀 피해', stats.mean.text, stats.unit ?? '')}
        ${metricCard('표본 표준편차', stats.sd.text, '한 판 결과의 산포')}
        ${metricCard('평균 95% CI', stats.meanCi.text, stats.ciMethod ?? '')}
        ${metricCard('중앙값', stats.median.text, stats.quantileMethod ?? '')}
        ${metricCard('P5', stats.p5.text, stats.quantileMethod ?? '')}
        ${metricCard('P95', stats.p95.text, stats.quantileMethod ?? '')}
        ${cut ? metricCard('컷 초과확률', cut.successRate.text, `기준 ${cut.threshold.text}`) : metricCard('컷 초과확률', UNKNOWN, '기준 미지정')}
        ${cut ? metricCard('컷 확률 CI', cut.ci.text, stats.ciMethod ?? '') : ''}
      </div>
      <p class="microcopy">평균 CI는 평균의 불확실성이고 P5·P95는 한 판 결과의 분포입니다. 서로 바꿔 읽지 않습니다.</p>
      <div class="table-scroll">
        <table class="compute-member-table">
          <thead><tr><th>니케</th><th>평균 피해</th><th>평균 95% CI</th><th>비중</th></tr></thead>
          <tbody>${memberRows}</tbody>
        </table>
      </div>
    </article>`;
}

function olSection(model) {
  const ol = model.olComparison;
  if (!ol || !ol.candidates.length) {
    return `<article class="surface"><h3>오버로드 후보 비교</h3><p class="microcopy">비교 결과가 없습니다. 가상 후보 평가 결과가 오면 여기에 표시합니다.</p></article>`;
  }
  const rows = ol.candidates.map(c => `
    <tr>
      <td>${esc(c.displayName)}</td>
      <td>${esc(c.part ?? UNKNOWN)} · ${c.line === null ? UNKNOWN : esc(String(c.line))}번째 줄</td>
      <td>${esc(c.optionLabel)} ${esc(c.valueText)}</td>
      <td>${esc(c.deltaText)}</td>
      <td>${esc(c.deltaCiText)}</td>
      <td><span class="pill-badge ${c.verdict === 'improve' ? 'green' : c.verdict === 'regress' ? 'red' : 'gray'}">${esc(c.verdictLabel)}</span></td>
      <td>${esc(formatNumber(c.sampleSize))}</td>
    </tr>`).join('');
  return `
    <article class="surface">
      <h3>오버로드 후보 비교</h3>
      <p class="microcopy">원본 장비를 바꾸지 않는 가상 변경 평가입니다. 실제 장비는 수정되지 않습니다.${ol.undeterminedCount ? ` 우열 미확정 ${esc(String(ol.undeterminedCount))}건.` : ''}</p>
      <div class="table-scroll">
        <table class="compute-ol-table">
          <thead><tr><th>니케</th><th>부위·줄</th><th>옵션·수치</th><th>팀 평균 차이</th><th>차이 95% CI</th><th>판정</th><th>표본</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="microcopy">CI가 0을 포함하면 우열을 확정하지 않습니다. 모듈 비용·확률 자료가 확인되지 않아 비용 효율 추천은 제공하지 않습니다.</p>
    </article>`;
}

/** Pure renderer; every dynamic string is escaped. Used by both the app and the node test. */
export function renderSingleDeckStats(model) {
  const source = model.endpointStatus === 'connected'
    ? '<span class="status-pill green">실제 API 응답</span>'
    : model.endpointStatus === 'unavailable'
      ? '<span class="status-pill warning">배치 API 미연결 · 계약 확정 전</span>'
      : '<span class="status-pill neutral">연결 확인 중</span>';
  const errors = model.errors.length
    ? `<div class="surface compute-errors"><h3>오류</h3><ul>${model.errors.map(e => `<li>${esc(e)}</li>`).join('')}</ul></div>` : '';
  return `
    <div class="section-heading">
      <div>
        <p class="eyebrow">SINGLE DECK STATISTICS</p>
        <h2>단일 덱 반복 실행 통계</h2>
        <p>현재 덱을 반복 실행해 평균·분포·신뢰구간을 확인하고, 오버로드 가상 후보 비교 결과를 봅니다.</p>
      </div>
      ${source}
    </div>
    ${errors}
    ${deckSection(model)}
    ${controlSection(model)}
    ${deviceSection(model)}
    ${statisticsSection(model)}
    ${olSection(model)}`;
}

/** Builds the view model from raw payloads; missing payloads degrade to explicit unknown states. */
export function buildStatsModel({ hardware, selection, batch, statistics, olComparison, experiment,
  deckMembers = [], tacticSummary = '', requestedRuns = DEFAULT_RUNS, endpointStatus = 'unknown', errors = [], recovered = false } = {}) {
  return {
    endpointStatus,
    recovered,
    requestedRuns,
    deckMembers,
    tacticSummary,
    hardware: describeHardwareProfile(hardware),
    selection: describeExecutionSelection(selection),
    batch: describeBatch(batch),
    statistics: describeStatistics(statistics),
    olComparison: describeOlComparison(olComparison),
    experiment: describeExperimentInput(experiment),
    errors: errors.filter(Boolean).map(String)
  };
}

/**
 * Screen controller. `api` is the app's fetch wrapper; every compute call is guarded so a missing
 * endpoint (contract not published yet) shows "미연결" instead of a broken screen.
 */
export function createSingleDeckStatsView({ api, getSnapshot, getMembersWithMeta, getTacticSummary, getConditions, status, storage } = {}) {
  const store = storage ?? (typeof localStorage === 'undefined' ? null : localStorage);
  let state = {
    endpointStatus: 'unknown', requestedRuns: DEFAULT_RUNS, recovered: false, errors: [],
    hardware: null, selection: null, batch: null, statistics: null, olComparison: null, experiment: null
  };
  let containerId = 'stats-content';
  let pollTimer = null;
  let disposed = false;

  const model = () => buildStatsModel({
    ...state,
    deckMembers: (getMembersWithMeta?.() ?? []).map(m => ({ characterId: m.id, displayName: m.displayName, burstStep: m.burstStep })),
    tacticSummary: getTacticSummary?.() ?? ''
  });

  async function call(path, method = 'GET', body) {
    try {
      const result = await api(path, method, body);
      state.endpointStatus = 'connected';
      return { ok: true, data: result };
    } catch (error) {
      state.endpointStatus = 'unavailable';
      return { ok: false, error: error?.message ?? String(error) };
    }
  }

  function note(message) {
    if (!message) return;
    state.errors = [...new Set([...state.errors, message])].slice(-5);
    status?.(message);
  }

  async function loadHardware() {
    const response = await call(COMPUTE_ROUTES.hardware);
    if (response.ok) {
      state.hardware = response.data?.hardware ?? response.data ?? null;
      state.selection = response.data?.selection ?? state.selection;
    } else note(`하드웨어 탐지 결과를 불러오지 못했습니다. ${response.error}`);
    render();
  }

  async function loadBatch(batchId) {
    const response = await call(COMPUTE_ROUTES.batch(batchId));
    if (!response.ok) { note(`배치 상태를 불러오지 못했습니다. ${response.error}`); render(); return null; }
    applyBatchPayload(response.data);
    render();
    return response.data;
  }

  function applyBatchPayload(payload) {
    state.batch = payload?.batch ?? payload ?? null;
    if (payload?.selection) state.selection = payload.selection;
    if (payload?.experiment) state.experiment = payload.experiment;
    if (payload?.statistics) state.statistics = payload.statistics;
    if (payload?.olComparison) state.olComparison = payload.olComparison;
    const id = state.batch?.batchId ?? state.batch?.id ?? null;
    if (id && store) { try { store.setItem(BATCH_STORAGE_KEY, id); } catch { /* storage disabled */ } }
  }

  function schedulePoll() {
    if (disposed) return;
    clearTimeout(pollTimer);
    const described = describeBatch(state.batch);
    if (!described.id || !described.canCancel) return; // only queued/running keep polling
    pollTimer = setTimeout(async () => {
      const payload = await loadBatch(described.id);
      const next = describeBatch(payload?.batch ?? payload);
      if (next.canCancel) schedulePoll(); else await loadResults(described.id);
    }, 1000);
  }

  async function loadResults(batchId) {
    const results = await call(COMPUTE_ROUTES.batchResults(batchId));
    if (results.ok) {
      state.statistics = results.data?.statistics ?? state.statistics;
      state.olComparison = results.data?.olComparison ?? state.olComparison;
    } else note(`결과를 불러오지 못했습니다. ${results.error}`);
    const comparison = await call(COMPUTE_ROUTES.olComparison(batchId));
    if (comparison.ok && comparison.data) state.olComparison = comparison.data?.olComparison ?? comparison.data;
    render();
  }

  async function start() {
    const snapshot = getSnapshot?.();
    if (!snapshot) { note('계정을 먼저 연결하세요.'); render(); return; }
    const members = (getMembersWithMeta?.() ?? []).map(m => m.id);
    if (!members.length) { note('편성을 먼저 저장하세요.'); render(); return; }
    const conditions = getConditions?.() ?? {};
    const payload = {
      snapshotId: snapshot.id,
      characterIds: members,
      synchroLevel: FIXED_SYNCHRO_LEVEL,
      durationSeconds: conditions.durationSeconds ?? DEFAULT_DURATION_SECONDS,
      enemyDefense: conditions.enemyDefense ?? null,
      requestedRuns: state.requestedRuns,
      recordLevel: 'summary',
      execution: { requested: state.requestedDevice ?? 'auto', workerLimit: state.workerLimit ?? null, memoryLimitBytes: state.memoryLimitBytes ?? null }
    };
    const response = await call(COMPUTE_ROUTES.batches, 'POST', payload);
    if (!response.ok) { note(`배치를 시작하지 못했습니다. ${response.error}`); render(); return; }
    state.recovered = false;
    applyBatchPayload(response.data);
    render();
    schedulePoll();
  }

  async function cancel() {
    const id = describeBatch(state.batch).id;
    if (!id) return;
    const response = await call(COMPUTE_ROUTES.batchCancel(id), 'POST', {});
    if (!response.ok) { note(`취소 요청이 실패했습니다. ${response.error}`); render(); return; }
    applyBatchPayload(response.data);
    render();
    schedulePoll();
  }

  async function resume() {
    const id = describeBatch(state.batch).id;
    if (!id) return;
    const response = await call(COMPUTE_ROUTES.batchResume(id), 'POST', {});
    if (!response.ok) { note(`재개 요청이 실패했습니다. ${response.error}`); render(); return; }
    applyBatchPayload(response.data);
    render();
    schedulePoll();
  }

  /** After a restart the last batch id is re-read and its real state is shown, never assumed. */
  async function recover() {
    let id = null;
    try { id = store?.getItem(BATCH_STORAGE_KEY) ?? null; } catch { id = null; }
    if (!id) return;
    state.recovered = true;
    const payload = await loadBatch(id);
    if (payload) { schedulePoll(); if (!describeBatch(payload?.batch ?? payload).canCancel) await loadResults(id); }
  }

  function bind(container) {
    const byId = id => container.querySelector('#' + id);
    const runs = byId('compute-runs');
    if (runs) runs.onchange = () => {
      const value = Number(runs.value);
      state.requestedRuns = Number.isFinite(value) && value > 0 ? Math.floor(value) : DEFAULT_RUNS;
    };
    const device = byId('compute-device');
    if (device) device.onchange = () => { state.requestedDevice = device.value; };
    const workerLimit = byId('compute-worker-limit');
    if (workerLimit) workerLimit.onchange = () => {
      const value = Number(workerLimit.value);
      state.workerLimit = workerLimit.value === '' || !Number.isFinite(value) ? null : Math.floor(value);
    };
    const memoryLimit = byId('compute-memory-limit');
    if (memoryLimit) memoryLimit.onchange = () => {
      const value = Number(memoryLimit.value);
      state.memoryLimitBytes = memoryLimit.value === '' || !Number.isFinite(value) ? null : Math.floor(value * (1024 ** 3));
    };
    if (byId('compute-start')) byId('compute-start').onclick = () => start();
    if (byId('compute-cancel')) byId('compute-cancel').onclick = () => cancel();
    if (byId('compute-resume')) byId('compute-resume').onclick = () => resume();
    if (byId('compute-remeasure')) byId('compute-remeasure').onclick = () => loadHardware();
  }

  function render(id = containerId) {
    containerId = id;
    const container = typeof document === 'undefined' ? null : document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = renderSingleDeckStats(model());
    bind(container);
  }

  async function mount(id = containerId) {
    containerId = id;
    render(id);
    await loadHardware();
    await recover();
  }

  return {
    mount, render, start, cancel, resume,
    refreshHardware: loadHardware,
    getModel: model,
    dispose() { disposed = true; clearTimeout(pollTimer); }
  };
}

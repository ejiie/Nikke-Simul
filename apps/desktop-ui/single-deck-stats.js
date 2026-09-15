/**
 * Single-deck batch statistics screen: deck/tactic summary, run control, device selection and
 * overload (OL) virtual candidate comparison.
 *
 * Wire mapping lives in compute-adapter.js (Backend contract v1, Backend commit f2327e5). This screen
 * renders what the payload proves and marks the rest 미확인 / 미지원 / 표본 없음. It never recomputes
 * damage or statistics, never shows a CPU run as a GPU success, and keeps an OL candidate
 * 우열 미확정 unless the difference interval excludes zero.
 */
import {
  COMPUTE_ROUTES,
  describeHardwareProfile,
  describeBatch,
  describeStatistics,
  describeOlComparison,
  describeComputeError,
  buildExperimentRequest,
  formatNumber,
  formatPercent,
  UNKNOWN
} from './compute-adapter.js';

const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const EXPERIMENT_STORAGE_KEY = 'nikke-single-deck-experiment';
export const FIXED_SYNCHRO_LEVEL = 400;
export const DEFAULT_DURATION_FRAMES = 10800;
export const DEFAULT_RUNS = 1000;
export const PHASES = [['pilot', '파일럿'], ['final', '최종'], ['exploration', '탐색']];

function bytes(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return UNKNOWN;
  return `${formatNumber(Number((value / (1024 ** 3)).toFixed(2)), { digits: 2 })} GiB`;
}

function metricCard(label, value, sub = '') {
  return `<div class="metric-card"><span>${esc(label)}</span><strong>${esc(value)}</strong>${sub ? `<small class="compute-sub">${esc(sub)}</small>` : ''}</div>`;
}

function deckSection(model) {
  const input = model.batch.input;
  const members = model.deckMembers.length ? model.deckMembers : input.characterIds.map(id => ({ characterId: id, displayName: id }));
  const rows = members.length
    ? members.map(m => `<li><strong>${esc(m.displayName ?? m.characterId ?? UNKNOWN)}</strong> <span class="pill-badge gray">#${esc(m.characterId ?? UNKNOWN)}</span>${m.burstStep ? ` <span class="pill-badge cyan">버스트 ${esc(['I', 'II', 'III'][m.burstStep - 1] ?? m.burstStep)}</span>` : ''}</li>`).join('')
    : '<li>편성이 비어 있습니다. 솔로 레이드에서 5인을 저장하세요.</li>';
  return `
    <article class="surface">
      <h3>덱과 실행 조건</h3>
      <ul class="compute-deck-list">${rows}</ul>
      <div class="summary-metrics-grid">
        ${metricCard('싱크로 레벨', formatNumber(input.synchroLevel ?? FIXED_SYNCHRO_LEVEL), '고정')}
        ${metricCard('전투 시간', input.present ? input.durationSecondsText : `${formatNumber(DEFAULT_DURATION_FRAMES / 60)}초`,
          input.present ? `${formatNumber(input.durationFrames)}프레임` : '기본값 10,800프레임')}
        ${metricCard('DEF 정책', input.defPolicy ?? '현행 고정 DEF 정책', '자동 20억 전환 없음')}
        ${metricCard('버스트 전술', model.tacticSummary || UNKNOWN, '솔로 레이드 저장 설정')}
        ${metricCard('표본 단계', input.phase ?? model.phase, 'warmup은 표본으로 저장하지 않음')}
        ${metricCard('입력 fingerprint', input.fingerprint ?? UNKNOWN, input.rulesVersion ? `규칙 ${input.rulesVersion}` : '')}
      </div>
      <p class="microcopy">결과는 현재 모델 기반 실험이며 실게임 검증 완료 추천이 아닙니다.${input.gameVerified === false ? ' 저장 입력도 gameVerified=false입니다.' : ''}</p>
    </article>`;
}

function controlSection(model) {
  const batch = model.batch;
  const counts = batch.counts;
  const phaseOptions = PHASES.map(([value, label]) =>
    `<option value="${esc(value)}"${model.phase === value ? ' selected' : ''}>${esc(label)}</option>`).join('');
  return `
    <article class="surface">
      <h3>반복 실행</h3>
      <div class="form-grid">
        <label>실행 횟수<input id="compute-runs" type="number" min="1" max="200000" step="1" value="${esc(String(model.requestedRuns))}"${batch.canStart ? '' : ' disabled'}></label>
        <label>표본 단계<select id="compute-phase"${batch.canStart ? '' : ' disabled'}>${phaseOptions}</select></label>
        <label>컷 기준 (선택)<input id="compute-cut" type="number" min="0" step="1" placeholder="예: 150000000" value="${model.cut === null ? '' : esc(String(model.cut))}"></label>
      </div>
      <div class="action-row">
        <button id="compute-start" class="primary" type="button"${batch.canStart ? '' : ' disabled'}>실행</button>
        <button id="compute-cancel" type="button"${batch.canCancel ? '' : ' disabled'}>취소</button>
        <button id="compute-resume" type="button"${batch.canResume ? '' : ' disabled'}>재개</button>
        <span class="status-pill ${batch.state === 'completed' ? 'green' : batch.state === 'failed' ? 'red' : 'neutral'}" id="compute-batch-state">${esc(batch.stateLabel)}</span>
        ${batch.partial ? '<span class="status-pill warning">부분 결과</span>' : ''}
        ${batch.attempt !== null && batch.attempt > 1 ? `<span class="status-pill cyan">attempt ${esc(String(batch.attempt))}</span>` : ''}
        ${model.recovered ? '<span class="status-pill cyan">재시작 복구</span>' : ''}
      </div>
      <progress id="compute-progress" max="1" ${batch.progress === null ? '' : `value="${batch.progress}"`}></progress>
      <div class="summary-metrics-grid">
        ${metricCard('완료 표본', formatNumber(counts.valid), '유효 run')}
        ${metricCard('요청 수', formatNumber(counts.requested))}
        ${metricCard('진행률', batch.progress === null ? UNKNOWN : formatPercent(batch.progress, 1))}
        ${metricCard('실패', formatNumber(counts.failed), '실패는 정상 0 표본이 아님')}
        ${metricCard('취소 시 미완료', formatNumber(counts.cancelled), '표본에서 제외')}
      </div>
      ${batch.errorLabel ? `<p class="compute-warning">${esc(batch.errorLabel)}</p>` : ''}
      <p class="microcopy">재개는 실패·취소 index만 새 attempt로 실행하며 기존 유효 결과를 중복 집계하지 않습니다.</p>
    </article>`;
}

function deviceSection(model) {
  const hardware = model.hardware;
  const selection = model.batch.execution;
  const deviceRows = hardware.devices.length
    ? hardware.devices.map(device => `
      <tr>
        <td>${esc(device.name ?? UNKNOWN)}<br><small class="compute-sub">${esc(device.vendor ?? UNKNOWN)} · ${esc(device.id ?? 'ID 미확인')}</small></td>
        <td>${esc(device.backend ?? UNKNOWN)}<br><small class="compute-sub">driver ${esc(device.driver ?? UNKNOWN)}</small></td>
        <td>${device.stages.map(s => `${esc(s.label)} ${esc(s.statusLabel)}`).join('<br>')}</td>
        <td>${device.usable ? '<span class="pill-badge green">사용 가능</span>' : '<span class="pill-badge gray">사용 불가</span>'}
          ${device.reason ? `<br><small class="compute-sub">${esc(device.reason)}</small>` : ''}</td>
      </tr>`).join('')
    : '<tr><td colspan="4">탐지된 GPU가 없습니다. CPU로 실행합니다.</td></tr>';
  const options = ['<option value="auto">자동 선택 (권장)</option>', '<option value="cpu">CPU</option>']
    .concat(hardware.usableDevices.map(d => `<option value="${esc(d.id ?? '')}">GPU · ${esc(d.name ?? d.id ?? UNKNOWN)}</option>`))
    .join('');
  const failures = hardware.probeFailures.length
    ? `<ul class="compute-failures">${hardware.probeFailures.map(f => `<li>${esc(f)}</li>`).join('')}</ul>` : '';
  return `
    <article class="surface">
      <h3>실행 장치</h3>
      <div class="summary-metrics-grid">
        ${metricCard('탐지 상태', hardware.statusLabel, hardware.fingerprint ? `fingerprint ${hardware.fingerprint}` : '')}
        ${metricCard('요청', selection.requestedLabel)}
        ${metricCard('실제 backend', selection.backendLabel, selection.deviceId ? `장치 ${selection.deviceId}` : '')}
        ${metricCard('worker 수', formatNumber(selection.workers))}
        ${metricCard('chunk 크기', formatNumber(selection.chunkSize))}
        ${metricCard('메모리 상한', bytes(selection.memoryLimitBytes))}
      </div>
      ${selection.reason ? `<p class="microcopy">선택 근거: ${esc(selection.reason)}</p>` : ''}
      ${selection.fellBack && selection.fallbackReason ? `<p class="microcopy">CPU fallback 원인: ${esc(selection.fallbackReason)}</p>` : ''}
      ${selection.mismatch ? '<p class="compute-warning">GPU 지정 실행이 불가능해 요청과 다른 backend로 실행되었습니다. GPU 성공으로 표시하지 않습니다.</p>' : ''}
      <div class="summary-metrics-grid">
        ${metricCard('OS', hardware.os ?? UNKNOWN, hardware.architecture ?? '')}
        ${metricCard('CPU 병렬도', formatNumber(hardware.availableProcessors))}
        ${metricCard('물리 코어', formatNumber(hardware.physicalCores))}
        ${metricCard('메모리 한도', bytes(hardware.memoryLimitBytes))}
        ${metricCard('원격 세션', hardware.remoteSession === null ? UNKNOWN : hardware.remoteSession ? '예' : '아니오')}
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
          <label><input id="compute-retune" type="checkbox"> 다음 실행에서 재튜닝</label>
        </div>
        <p class="microcopy">검증(eligible)을 통과하지 않은 GPU는 선택할 수 없습니다. 강제 GPU 요청은 Backend가 실행 전에 거부합니다.</p>
      </details>
    </article>`;
}

function metricRow(label, metrics) {
  return `<tr><td>${esc(label)}</td><td>${esc(metrics.nText)}</td><td>${esc(metrics.mean.text)}</td><td>${esc(metrics.meanCi.text)}</td><td>${esc(metrics.median.text)}</td><td>${esc(metrics.p5.text)}</td><td>${esc(metrics.p95.text)}</td></tr>`;
}

function statisticsSection(model) {
  if (model.analysisStatus === 'not_integrated') {
    return `<article class="surface"><h3>통계</h3><p class="compute-warning">${esc(describeComputeError('analysis_not_integrated'))}</p>
      <p class="microcopy">Backend가 Analysis 연결을 끝내면 이 화면이 같은 계약으로 집계를 표시합니다.</p></article>`;
  }
  const stats = model.statistics;
  if (!stats.present) {
    return '<article class="surface"><h3>통계</h3><p class="microcopy">집계 결과가 아직 없습니다. 실행을 완료하면 표시합니다.</p></article>';
  }
  const team = stats.team;
  return `
    <article class="surface">
      <h3>통계 ${stats.partial ? '<span class="status-pill warning">부분 결과</span>' : ''}</h3>
      ${team.sampleNote ? `<p class="compute-warning">${esc(team.sampleNote)}</p>` : ''}
      ${team.unsupportedReason ? `<p class="compute-warning">${esc(team.unsupportedReason)}</p>` : ''}
      <div class="summary-metrics-grid">
        ${metricCard('표본 수 n', team.nText, stats.methodVersion ? `방식 ${stats.methodVersion}` : '')}
        ${metricCard('평균 팀 피해', team.mean.text, team.unit ?? '')}
        ${metricCard('표본 표준편차', team.sampleSd.text, '한 판 결과의 산포')}
        ${metricCard('평균 CI', team.meanCi.text, team.meanCi.method ?? '')}
        ${metricCard('중앙값', team.median.text, team.quantileMethod ?? '')}
        ${metricCard('P5', team.p5.text, team.quantileMethod ?? '')}
        ${metricCard('P95', team.p95.text, team.quantileMethod ?? '')}
        ${metricCard('컷 초과확률', team.cutSuccess.text, team.cut.value === null ? '기준 미지정' : `기준 ${team.cut.text}`)}
        ${metricCard('컷 확률 CI', team.cutCi.text, team.cutCi.method ?? '')}
      </div>
      <p class="microcopy">평균 CI는 평균의 불확실성이고 P5·P95는 한 판 결과의 분포입니다. 서로 바꿔 읽지 않습니다.</p>
      <div class="table-scroll">
        <table class="compute-member-table">
          <thead><tr><th>니케</th><th>n</th><th>평균</th><th>평균 CI</th><th>중앙값</th><th>P5</th><th>P95</th></tr></thead>
          <tbody>${stats.members.length ? stats.members.map(m => metricRow(m.displayName, m)).join('')
            : '<tr><td colspan="7">니케별 결과가 없습니다.</td></tr>'}</tbody>
        </table>
      </div>
    </article>`;
}

function olSection(model) {
  if (model.analysisStatus === 'not_integrated') {
    return `<article class="surface"><h3>오버로드 후보 비교</h3><p class="compute-warning">${esc(describeComputeError('analysis_not_integrated'))}</p></article>`;
  }
  const ol = model.comparison;
  if (!ol.present) {
    return '<article class="surface"><h3>오버로드 후보 비교</h3><p class="microcopy">비교 결과가 없습니다. 기준 실험과 후보 실험이 준비되면 표시합니다.</p></article>';
  }
  const rows = ol.changes.length
    ? ol.changes.map(change => `<tr><td>${esc(change.displayName)}</td><td>${esc(change.slot ?? UNKNOWN)} · ${change.lineIndex === null ? UNKNOWN : esc(String(change.lineIndex))}번째 줄</td><td>${esc(change.optionId ?? UNKNOWN)} ${esc(change.valueText)}</td></tr>`).join('')
    : '<tr><td colspan="3">변경 항목이 없습니다.</td></tr>';
  return `
    <article class="surface">
      <h3>오버로드 후보 비교</h3>
      <div class="summary-metrics-grid">
        ${metricCard('팀 평균 차이', ol.difference.text, ol.phase ? `단계 ${ol.phase}` : '')}
        ${metricCard('차이 CI', ol.differenceCi.text, ol.differenceCi.method ?? '')}
        ${metricCard('판정', ol.verdictLabel, ol.verdict === 'undetermined' ? 'CI가 0을 포함' : '')}
        ${metricCard('기준 실험', ol.baselineExperimentId ?? UNKNOWN, ol.candidateExperimentId ? `후보 ${ol.candidateExperimentId}` : '')}
      </div>
      ${ol.verdictConflict ? `<p class="compute-warning">응답 판정(${esc(ol.reportedVerdict ?? UNKNOWN)})이 신뢰구간과 맞지 않아 우열 미확정으로 표시합니다.</p>` : ''}
      <div class="table-scroll">
        <table class="compute-ol-table">
          <thead><tr><th>니케</th><th>부위·줄</th><th>옵션·수치</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="microcopy">원본 장비를 바꾸지 않는 가상 변경 평가입니다. CI가 0을 포함하면 우열을 확정하지 않으며, 모듈 비용·확률 자료가 확인되지 않아 비용 효율 추천은 제공하지 않습니다.</p>
    </article>`;
}

/** Pure renderer; every dynamic string is escaped. Used by both the app and the node test. */
export function renderSingleDeckStats(model) {
  const source = model.endpointStatus === 'connected'
    ? '<span class="status-pill green">실제 API 응답</span>'
    : model.endpointStatus === 'unavailable'
      ? '<span class="status-pill warning">compute API 미연결</span>'
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

/** Builds the view model from contract payloads; missing payloads degrade to explicit unknown states. */
export function buildStatsModel({ hardware, batch, statistics, comparison, deckMembers = [], tacticSummary = '',
  requestedRuns = DEFAULT_RUNS, phase = 'final', cut = null, endpointStatus = 'unknown', analysisStatus = 'unknown',
  errors = [], recovered = false } = {}) {
  const described = describeBatch(batch);
  const displayNames = new Map(deckMembers.map(m => [m.characterId, m.displayName ?? m.characterId]));
  return {
    endpointStatus,
    analysisStatus,
    recovered,
    requestedRuns,
    phase,
    cut,
    deckMembers,
    tacticSummary,
    hardware: describeHardwareProfile(hardware),
    batch: described,
    statistics: describeStatistics(statistics, { memberOrder: described.input.characterIds, displayNames }),
    comparison: describeOlComparison(comparison, { displayNames }),
    errors: errors.filter(Boolean).map(String)
  };
}

/**
 * Screen controller. `api` is the app's fetch wrapper. Every compute call is guarded: a missing
 * endpoint shows "미연결", and 409 analysis_not_integrated is reported as an explicit state rather
 * than an empty statistics panel.
 */
export function createSingleDeckStatsView({ api, getSnapshot, getMembersWithMeta, getTacticSummary, getConditions, status, storage } = {}) {
  const store = storage ?? (typeof localStorage === 'undefined' ? null : localStorage);
  const state = {
    endpointStatus: 'unknown', analysisStatus: 'unknown', requestedRuns: DEFAULT_RUNS, phase: 'final', cut: null,
    recovered: false, errors: [], hardware: null, batch: null, statistics: null, comparison: null,
    requestedDevice: 'auto', workerLimit: null, memoryLimitBytes: null, retune: false
  };
  let containerId = 'stats-content';
  let pollTimer = null;
  let disposed = false;

  const deckMembers = () => (getMembersWithMeta?.() ?? []).map(m => ({ characterId: m.id, displayName: m.displayName, burstStep: m.burstStep }));
  const model = () => buildStatsModel({ ...state, deckMembers: deckMembers(), tacticSummary: getTacticSummary?.() ?? '' });

  async function call(path, method = 'GET', body) {
    try {
      const result = await api(path, method, body);
      state.endpointStatus = 'connected';
      return { ok: true, data: result };
    } catch (error) {
      const message = error?.message ?? String(error);
      if (message.includes('analysis_not_integrated')) state.analysisStatus = 'not_integrated';
      else state.endpointStatus = 'unavailable';
      return { ok: false, error: message };
    }
  }

  function note(message) {
    if (!message) return;
    state.errors = [...new Set([...state.errors, message])].slice(-5);
    status?.(message);
  }

  function applyBatch(payload) {
    if (!payload) return;
    state.batch = payload;
    const id = payload.id ?? null;
    if (id && store) { try { store.setItem(EXPERIMENT_STORAGE_KEY, id); } catch { /* storage disabled */ } }
  }

  async function loadHardware() {
    const response = await call(COMPUTE_ROUTES.hardware);
    if (response.ok) state.hardware = response.data ?? null;
    else note(`하드웨어 탐지 결과를 불러오지 못했습니다. ${response.error}`);
    render();
  }

  async function loadAnalysis(id) {
    const statistics = await call(COMPUTE_ROUTES.statistics(id, state.cut));
    if (statistics.ok) { state.statistics = statistics.data ?? null; state.analysisStatus = 'integrated'; }
    else if (state.analysisStatus !== 'not_integrated') note(`통계를 불러오지 못했습니다. ${statistics.error}`);
    const comparison = await call(COMPUTE_ROUTES.comparison(id));
    if (comparison.ok) state.comparison = comparison.data ?? null;
    render();
  }

  async function loadBatch(id) {
    const response = await call(COMPUTE_ROUTES.experiment(id));
    if (!response.ok) { note(`실험 상태를 불러오지 못했습니다. ${response.error}`); render(); return null; }
    applyBatch(response.data);
    render();
    return response.data;
  }

  function schedulePoll() {
    if (disposed) return;
    clearTimeout(pollTimer);
    const described = describeBatch(state.batch);
    if (!described.id || !described.canCancel) return; // only queued/running keep polling
    pollTimer = setTimeout(async () => {
      const payload = await loadBatch(described.id);
      if (describeBatch(payload).canCancel) schedulePoll();
      else if (payload) await loadAnalysis(described.id);
    }, 1000);
  }

  async function start() {
    const snapshot = getSnapshot?.();
    if (!snapshot) { note('계정을 먼저 연결하세요.'); render(); return; }
    const members = (getMembersWithMeta?.() ?? []).map(m => m.id);
    if (!members.length) { note('편성을 먼저 저장하세요.'); render(); return; }
    const request = buildExperimentRequest({
      snapshotId: snapshot.id,
      characterIds: members,
      conditions: getConditions?.() ?? {},
      runs: state.requestedRuns,
      phase: state.phase,
      execution: {
        requested: state.requestedDevice === 'auto' || state.requestedDevice === 'cpu' ? state.requestedDevice : 'gpu',
        deviceId: state.requestedDevice === 'auto' || state.requestedDevice === 'cpu' ? null : state.requestedDevice,
        maxWorkers: state.workerLimit,
        memoryLimitBytes: state.memoryLimitBytes,
        retune: state.retune
      }
    });
    const response = await call(COMPUTE_ROUTES.experiments, 'POST', request);
    if (!response.ok) { note(`실험을 시작하지 못했습니다. ${response.error}`); render(); return; }
    state.recovered = false;
    state.statistics = null;
    state.comparison = null;
    applyBatch(response.data);
    render();
    schedulePoll();
  }

  async function transition(routeFactory, label) {
    const id = describeBatch(state.batch).id;
    if (!id) return;
    const response = await call(routeFactory(id), 'POST', {});
    if (!response.ok) { note(`${label} 요청이 실패했습니다. ${response.error}`); render(); return; }
    applyBatch(response.data);
    render();
    const described = describeBatch(response.data);
    if (described.canCancel) schedulePoll(); else await loadAnalysis(id);
  }

  /** After a restart the stored experiment id is re-read and its real state is shown, never assumed. */
  async function recover() {
    let id = null;
    try { id = store?.getItem(EXPERIMENT_STORAGE_KEY) ?? null; } catch { id = null; }
    if (!id) return;
    state.recovered = true;
    const payload = await loadBatch(id);
    if (!payload) return;
    if (describeBatch(payload).canCancel) schedulePoll();
    else await loadAnalysis(id);
  }

  function bind(container) {
    const byId = id => container.querySelector('#' + id);
    const number = (element, apply) => { if (element) element.onchange = () => apply(element.value === '' ? null : Number(element.value)); };
    number(byId('compute-runs'), value => { state.requestedRuns = Number.isFinite(value) && value > 0 ? Math.floor(value) : DEFAULT_RUNS; });
    number(byId('compute-cut'), value => { state.cut = Number.isFinite(value) ? value : null; });
    number(byId('compute-worker-limit'), value => { state.workerLimit = Number.isFinite(value) ? Math.floor(value) : null; });
    number(byId('compute-memory-limit'), value => { state.memoryLimitBytes = Number.isFinite(value) ? Math.floor(value * (1024 ** 3)) : null; });
    const phase = byId('compute-phase');
    if (phase) phase.onchange = () => { state.phase = phase.value; };
    const device = byId('compute-device');
    if (device) device.onchange = () => { state.requestedDevice = device.value; };
    const retune = byId('compute-retune');
    if (retune) retune.onchange = () => { state.retune = retune.checked; };
    if (byId('compute-start')) byId('compute-start').onclick = () => start();
    if (byId('compute-cancel')) byId('compute-cancel').onclick = () => transition(COMPUTE_ROUTES.cancel, '취소');
    if (byId('compute-resume')) byId('compute-resume').onclick = () => transition(COMPUTE_ROUTES.resume, '재개');
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
    mount, render, start,
    cancel: () => transition(COMPUTE_ROUTES.cancel, '취소'),
    resume: () => transition(COMPUTE_ROUTES.resume, '재개'),
    refreshHardware: loadHardware,
    getModel: model,
    dispose() { disposed = true; clearTimeout(pollTimer); }
  };
}

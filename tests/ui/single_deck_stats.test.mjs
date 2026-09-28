// Single-deck statistics screen: pure model/rendering checks against Backend contract v1 (f2327e5).
// No browser, no network, no product mutation. Fixtures are synthetic payloads in the contract shape.
// Usage: node tests/ui/single_deck_stats.test.mjs [output-dir]
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = path.resolve(import.meta.dirname, '../..');
const adapter = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/compute-adapter.js')));
const view = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/single-deck-stats.js')));
const fixtureDir = path.join(import.meta.dirname, 'fixtures/single-deck-compute');
const load = name => JSON.parse(fs.readFileSync(path.join(fixtureDir, name), 'utf8'));
const hardware = load('hardware-profiles.json');
const selections = load('execution-selections.json');
const batches = load('batches.json');
const statistics = load('statistics.json');
const comparisons = load('ol-comparison.json');
const [outputDir] = process.argv.slice(2);

const members = [
  { id: '5011', displayName: '리타', burstStep: 1 }, { id: '5008', displayName: '블랑', burstStep: 2 },
  { id: '5009', displayName: '누아르', burstStep: 3 }, { id: '5004', displayName: '앨리스', burstStep: 3 },
  { id: '5044', displayName: '모더니아', burstStep: 3 }
];
const deckMembers = members.map(m => ({ characterId: m.id, displayName: m.displayName, burstStep: m.burstStep }));
const html = extra => view.renderSingleDeckStats(view.buildStatsModel({ deckMembers, ...extra }));

const checks = [];
async function check(name, fn) {
  try { await fn(); checks.push({ name, passed: true }); }
  catch (error) { checks.push({ name, passed: false, error: String(error.message).split('\n').slice(0, 6).join(' | ') }); }
}

await check('contract_routes_match_backend_v1', () => {
  assert.equal(adapter.COMPUTE_CONTRACT_VERSION, 'backend-v1-f2327e5');
  assert.equal(adapter.COMPUTE_ROUTES.hardware, '/compute/hardware');
  assert.equal(adapter.COMPUTE_ROUTES.experiments, '/compute/experiments');
  assert.equal(adapter.COMPUTE_ROUTES.experiment('e1'), '/compute/experiments/e1');
  assert.equal(adapter.COMPUTE_ROUTES.cancel('e1'), '/compute/experiments/e1/cancel');
  assert.equal(adapter.COMPUTE_ROUTES.resume('e1'), '/compute/experiments/e1/resume');
  assert.equal(adapter.COMPUTE_ROUTES.results('e1'), '/compute/experiments/e1/results?offset=0&limit=100');
  assert.equal(adapter.COMPUTE_ROUTES.statistics('e1'), '/compute/experiments/e1/statistics');
  assert.equal(adapter.COMPUTE_ROUTES.statistics('e1', 150000000), '/compute/experiments/e1/statistics?cut=150000000');
  assert.equal(adapter.COMPUTE_ROUTES.comparison('e1'), '/compute/experiments/e1/comparison');
  assert.ok(adapter.RESULTS_PAGE_LIMIT <= 1000);
});

await check('gpu_usable_only_when_eligible', () => {
  const pending = adapter.describeHardwareProfile(hardware.gpuNotImplemented);
  assert.deepEqual(pending.devices.map(d => d.usable), [false, false]);
  assert.equal(pending.usableDevices.length, 0);
  assert.equal(pending.devices[0].stageLabel, '런타임 미구현');
  assert.equal(pending.devices[1].stageLabel, '수치 정확성 미지원');
  assert.equal(pending.statusLabel, '탐지 완료 · 사용 가능 GPU 없음');
  const eligible = adapter.describeHardwareProfile(hardware.gpuEligible);
  assert.deepEqual(eligible.usableDevices.map(d => d.id), ['gpu-synthetic-verified']);
  assert.equal(eligible.devices[0].stageLabel, '전 단계 통과 · 사용 가능');
  // Only an eligible device may become a selectable option.
  const pendingMarkup = html({ hardware: hardware.gpuNotImplemented });
  assert.ok(!pendingMarkup.includes('<option value="gpu-synthetic-0">'));
  assert.ok(!pendingMarkup.includes('<option value="gpu-synthetic-1">'));
  assert.ok(pendingMarkup.includes('사용 불가'));
  assert.ok(pendingMarkup.includes('full battle GPU provider가 아직 구현되지 않았습니다.'));
  assert.ok(html({ hardware: hardware.gpuEligible }).includes('<option value="gpu-synthetic-verified">'));
});

await check('hardware_cpu_only_and_probe_failures', () => {
  const cpuOnly = adapter.describeHardwareProfile(hardware.cpuOnly);
  assert.equal(cpuOnly.statusLabel, 'GPU 없음 · CPU만 탐지');
  assert.equal(cpuOnly.availableProcessors, 8);
  assert.equal(cpuOnly.remoteSession, false);
  const failed = adapter.describeHardwareProfile(hardware.probeFailed);
  assert.equal(failed.statusLabel, '탐지 일부 실패');
  assert.equal(failed.probeFailures.length, 2);
  assert.equal(failed.physicalCores, null);
  assert.equal(failed.remoteSession, true);
  assert.equal(adapter.describeHardwareProfile(null).statusLabel, '하드웨어 정보 없음');
  const markup = html({ hardware: hardware.probeFailed });
  assert.ok(markup.includes('probe timeout') && markup.includes('탐지된 GPU가 없습니다'));
});

await check('cpu_run_never_reported_as_gpu', () => {
  const fallback = adapter.describeExecutionSelection(selections.autoGpuFallback);
  assert.equal(fallback.backendLabel, 'CPU');
  assert.equal(fallback.fellBack, true);
  assert.equal(fallback.mismatch, false); // auto + fallback is legitimate
  const forced = adapter.describeExecutionSelection(selections.forcedGpuMismatch);
  assert.equal(forced.mismatch, true);
  const gpu = adapter.describeExecutionSelection(selections.gpuEligible);
  assert.equal(gpu.backendLabel, 'GPU');
  assert.equal(gpu.mismatch, false);
  assert.equal(adapter.describeExecutionSelection(null).backendLabel, adapter.UNKNOWN);
  const markup = html({ batch: { ...batches.gpuFallback } });
  assert.ok(markup.includes('gpu_not_implemented'));
  const mismatchMarkup = html({ batch: { ...batches.running, execution: selections.forcedGpuMismatch } });
  assert.ok(mismatchMarkup.includes('GPU 성공으로 표시하지 않습니다'));
});

await check('batch_lifecycle_counts_and_controls', () => {
  const running = adapter.describeBatch(batches.running);
  assert.equal(running.stateLabel, '실행 중');
  assert.deepEqual([running.canStart, running.canCancel, running.canResume], [false, true, false]);
  assert.ok(Math.abs(running.progress - 0.32) < 1e-9);
  assert.equal(running.input.synchroLevel, 400);
  assert.equal(running.input.durationSecondsText, '180초');
  assert.equal(running.execution.backendLabel, 'CPU');
  const cancelled = adapter.describeBatch(batches.cancelledPartial);
  assert.deepEqual([cancelled.canStart, cancelled.canCancel, cancelled.canResume], [true, false, true]);
  assert.equal(cancelled.partial, true);
  assert.equal(cancelled.counts.cancelled, 486);
  const resumed = adapter.describeBatch(batches.resumedAttempt);
  assert.equal(resumed.attempt, 2);
  const failed = adapter.describeBatch(batches.failed);
  assert.equal(failed.canResume, true);
  assert.equal(failed.errorLabel, '오류 코드 engine_run_failed');
  const unknown = adapter.describeBatch(batches.unknownState);
  assert.equal(unknown.stateLabel, adapter.UNKNOWN);
  assert.equal(unknown.progress, null);
  assert.equal(unknown.input.present, false);
  assert.equal(unknown.execution.present, false);
  assert.equal(adapter.describeBatch(null).stateLabel, '배치 없음');
});

await check('contract_error_codes', () => {
  assert.match(adapter.describeComputeError('analysis_not_integrated'), /Analysis\) 미연결/);
  assert.match(adapter.describeComputeError('gpu_unavailable'), /강제 GPU 요청은 실행 전에 거부/);
  assert.equal(adapter.describeComputeError('unknown_code'), '오류 코드 unknown_code');
  assert.equal(adapter.describeComputeError(null), null);
  const markup = html({ analysisStatus: 'not_integrated', batch: batches.completed });
  assert.ok(markup.includes('통계 모듈(Analysis) 미연결'));
  assert.ok(!markup.includes('평균 CI는 평균의 불확실성'), 'statistics panel must not claim numbers while unintegrated');
});

await check('statistics_team_members_and_order', () => {
  const stats = adapter.describeStatistics(statistics.normal, {
    memberOrder: batches.completed.input.characterIds,
    displayNames: new Map(deckMembers.map(m => [m.characterId, m.displayName]))
  });
  assert.deepEqual(stats.members.map(m => m.characterId), ['5011', '5008', '5009', '5004', '5044']);
  assert.deepEqual(stats.members.map(m => m.displayName), ['리타', '블랑', '누아르', '앨리스', '모더니아']);
  assert.equal(stats.team.nText, '1,000');
  assert.equal(stats.team.meanCi.text, '152,083,461.2 ~ 152,681,125.6');
  assert.equal(stats.team.meanCi.method, 'student_t');
  assert.equal(stats.team.cutSuccess.text, '68.3%');
  assert.equal(stats.team.cutCi.text, '65.4% ~ 71.1%');
  assert.equal(stats.team.quantileMethod, 'type7');
  const markup = html({ batch: batches.completed, statistics: statistics.normal });
  assert.ok(markup.includes('평균 CI는 평균의 불확실성이고'));
  assert.ok(markup.includes('앨리스'));
  assert.ok(!/NaN|undefined|Infinity/.test(markup));
});

await check('statistics_zero_one_partial_unsupported', () => {
  const empty = adapter.describeStatistics(statistics.empty);
  assert.equal(empty.team.sampleNote, '표본 없음');
  assert.equal(empty.team.mean.text, adapter.UNKNOWN);
  assert.equal(empty.team.meanCi.text, '표본 없음');
  const single = adapter.describeStatistics(statistics.single);
  assert.equal(single.team.sampleNote, '표본 1건 · 산포/신뢰구간 없음');
  assert.equal(single.team.sampleSd.text, adapter.UNKNOWN);
  const zero = adapter.describeStatistics(statistics.zeroDamage);
  assert.equal(zero.team.mean.text, '0');          // a real zero is not unknown
  assert.equal(zero.team.cutSuccess.text, '0%');
  assert.equal(zero.team.sampleNote, null);
  const partial = adapter.describeStatistics(statistics.partialUnsupported, { memberOrder: ['5004'] });
  assert.equal(partial.partial, true);
  assert.equal(partial.team.median.text, adapter.UNKNOWN);
  assert.equal(partial.members[0].mean.text, '미지원');
  assert.match(partial.members[0].unsupportedReason, /부분 결과/);
  const markup = html({ batch: batches.cancelledPartial, statistics: statistics.partialUnsupported });
  assert.ok(markup.includes('부분 결과') && markup.includes('미지원'));
  assert.ok(html({ statistics: statistics.empty }).includes('표본 없음'));
});

await check('ol_comparison_verdicts_and_conflict', () => {
  const names = new Map(deckMembers.map(m => [m.characterId, m.displayName]));
  assert.equal(adapter.describeOlComparison(comparisons.improved, { displayNames: names }).verdict, 'improve');
  assert.equal(adapter.describeOlComparison(comparisons.regressed).verdict, 'regress');
  assert.equal(adapter.describeOlComparison(comparisons.undetermined).verdict, 'undetermined');
  const conflict = adapter.describeOlComparison(comparisons.conflictingVerdict);
  assert.equal(conflict.verdict, 'undetermined');       // interval contains 0
  assert.equal(conflict.reportedVerdict, 'improve');
  assert.equal(conflict.verdictConflict, true);
  const missing = adapter.describeOlComparison(comparisons.missingInterval);
  assert.equal(missing.difference.text, adapter.UNKNOWN);
  assert.equal(missing.verdict, 'undetermined');
  const change = adapter.describeOlComparison(comparisons.improved, { displayNames: names }).changes[0];
  assert.equal(change.displayName, '앨리스');
  assert.equal(change.slot, 'head');
  assert.equal(change.lineIndex, 2);
  assert.equal(change.valueText, '+11.11%');
  const markup = html({ comparison: comparisons.conflictingVerdict });
  assert.ok(markup.includes('우열 미확정'));
  assert.ok(markup.includes('신뢰구간과 맞지 않아'));
  assert.ok(markup.includes('원본 장비를 바꾸지 않는 가상 변경'));
  assert.ok(markup.includes('비용 효율 추천은 제공하지 않습니다'));
});

await check('experiment_request_uses_enemy_defense', () => {
  const request = adapter.buildExperimentRequest({
    snapshotId: 'snap-1', characterIds: ['5011', '5008', '5009', '5004', '5044'],
    conditions: { roundingPolicy: 'legacy_term_floor', combat: { durationFrames: 10800, targetDefense: 30925, critMode: 'off' } },
    runs: 1000.7, phase: 'pilot', execution: { requested: 'auto', maxWorkers: 4 }
  });
  // The contract example's targetDefense is a documentation typo; the engine field is enemyDefense.
  assert.equal(request.conditions.combat.enemyDefense, 30925);
  assert.ok(!('targetDefense' in request.conditions.combat));
  assert.equal(request.conditions.combat.durationFrames, 10800);
  assert.equal(request.conditions.combat.critMode, 'off');
  assert.equal(request.recordLevel, 'summary');
  assert.equal(request.runs, 1000);
  assert.equal(request.phase, 'pilot');
  assert.equal(request.useSavedTactic, true);
  assert.deepEqual(request.execution, { requested: 'auto', maxWorkers: 4, memoryLimitBytes: null, deviceId: null, retune: false });
  assert.ok(!('olChanges' in request));
  const explicit = adapter.buildExperimentRequest({
    snapshotId: 's', characterIds: [], conditions: { combat: { enemyDefense: 31784 } },
    olChanges: [{ characterId: '5004', slot: 'head', lineIndex: 1, optionId: 'StatAtk', value: 0.1111 }],
    baselineExperimentId: 'exp-base', useSavedTactic: false
  });
  assert.equal(explicit.conditions.combat.enemyDefense, 31784);
  assert.equal(explicit.olChanges.length, 1);
  assert.equal(explicit.baselineExperimentId, 'exp-base');
  assert.equal(explicit.useSavedTactic, false);
});

await check('endpoint_status_and_escape', () => {
  assert.ok(html({ endpointStatus: 'unknown' }).includes('연결 확인 중'));
  assert.ok(html({ endpointStatus: 'unavailable' }).includes('compute API 미연결'));
  assert.ok(html({ endpointStatus: 'connected' }).includes('실제 API 응답'));
  const evil = '<img src=x onerror=alert(1)>';
  const markup = view.renderSingleDeckStats(view.buildStatsModel({
    endpointStatus: 'connected', errors: [evil], tacticSummary: evil,
    deckMembers: [{ characterId: evil, displayName: evil, burstStep: 3 }],
    hardware: { os: evil, gpus: [{ deviceId: evil, name: evil, vendor: evil, eligible: true }], probeFailures: [evil] },
    batch: { id: evil, state: 'running', requested: 10, valid: 1, input: { fingerprint: evil, characterIds: [evil] },
      execution: { requested: 'auto', backend: 'cpu', reason: evil } },
    statistics: { experimentId: evil, team: { n: 2, mean: 1, unit: evil }, members: {} },
    comparison: { baselineExperimentId: evil, changes: [{ characterId: evil, slot: evil, lineIndex: 1, optionId: evil, value: 0.1 }],
      teamMeanDifference: 1, differenceCi: { lower: 0.5, upper: 1.5, method: evil } }
  }));
  assert.ok(!markup.includes('<img src=x'), 'unescaped markup leaked');
  assert.ok(markup.includes('&lt;img src=x onerror=alert(1)&gt;'));
});

await check('controller_start_cancel_resume_and_recovery', async () => {
  const calls = [];
  let batch = batches.queued;
  const api = async (path, method = 'GET', body) => {
    calls.push(`${method} ${path}`);
    if (path === adapter.COMPUTE_ROUTES.hardware) return hardware.gpuNotImplemented;
    if (path === adapter.COMPUTE_ROUTES.experiments && method === 'POST') {
      assert.equal(body.conditions.combat.enemyDefense, 30925);
      assert.equal(body.recordLevel, 'summary');
      batch = batches.queued; return batch;
    }
    if (path === adapter.COMPUTE_ROUTES.cancel('exp-synthetic-1')) { batch = batches.cancelledPartial; return batch; }
    if (path === adapter.COMPUTE_ROUTES.resume('exp-synthetic-1')) { batch = batches.resumedAttempt; return batch; }
    if (path === adapter.COMPUTE_ROUTES.experiment('exp-synthetic-1')) return batch;
    if (path.startsWith('/compute/experiments/exp-synthetic-1/statistics')) return statistics.partialUnsupported;
    if (path === adapter.COMPUTE_ROUTES.comparison('exp-synthetic-1')) return comparisons.undetermined;
    throw new Error('unexpected ' + path);
  };
  const saved = new Map();
  const controller = view.createSingleDeckStatsView({
    api, getSnapshot: () => ({ id: 'snap-1' }), getMembersWithMeta: () => members,
    getTacticSummary: () => '앨리스 → 모더니아', status: () => {},
    getConditions: () => ({ roundingPolicy: 'legacy_term_floor', combat: { durationFrames: 10800, enemyDefense: 30925 } }),
    storage: { getItem: k => saved.get(k) ?? null, setItem: (k, v) => saved.set(k, v) }
  });
  await controller.refreshHardware();
  await controller.start();
  assert.equal(controller.getModel().batch.stateLabel, '대기 중');
  assert.equal(saved.get('nikke-single-deck-experiment'), 'exp-synthetic-1');
  await controller.cancel();
  let model = controller.getModel();
  assert.equal(model.batch.stateLabel, '취소됨');
  assert.equal(model.batch.partial, true);
  assert.equal(model.statistics.partial, true);
  assert.equal(model.comparison.verdict, 'undetermined');
  await controller.resume();
  model = controller.getModel();
  assert.equal(model.batch.stateLabel, '실행 중');
  assert.equal(model.batch.attempt, 2);
  assert.equal(model.endpointStatus, 'connected');
  assert.ok(calls.includes('POST ' + adapter.COMPUTE_ROUTES.experiments));
  controller.dispose();
});

await check('controller_reports_analysis_and_gpu_rejection', async () => {
  const api = async (path, method = 'GET') => {
    if (path === adapter.COMPUTE_ROUTES.hardware) return hardware.cpuOnly;
    if (path === adapter.COMPUTE_ROUTES.experiments && method === 'POST') throw new Error('요청 실패 (409): gpu_unavailable');
    if (path === adapter.COMPUTE_ROUTES.experiment('exp-synthetic-1')) return batches.completed;
    if (path.startsWith('/compute/experiments/exp-synthetic-1/statistics')) throw new Error('요청 실패 (409): analysis_not_integrated');
    if (path === adapter.COMPUTE_ROUTES.comparison('exp-synthetic-1')) throw new Error('요청 실패 (409): analysis_not_integrated');
    throw new Error('unexpected ' + path);
  };
  const controller = view.createSingleDeckStatsView({
    api, getSnapshot: () => ({ id: 'snap-1' }), getMembersWithMeta: () => members,
    getTacticSummary: () => '', status: () => {}, getConditions: () => ({ combat: { enemyDefense: 30925 } }),
    storage: { getItem: () => 'exp-synthetic-1', setItem: () => {} }
  });
  await controller.refreshHardware();
  await controller.start();
  let model = controller.getModel();
  assert.ok(model.errors.some(e => e.includes('gpu_unavailable')));
  await controller.mount('stats-content'); // no document in node: render is a no-op, state still loads
  model = controller.getModel();
  assert.equal(model.recovered, true);
  assert.equal(model.analysisStatus, 'not_integrated');
  assert.equal(model.batch.stateLabel, '완료');
  const markup = view.renderSingleDeckStats(model);
  assert.ok(markup.includes('통계 모듈(Analysis) 미연결'));
  controller.dispose();
});

const failed = checks.filter(c => !c.passed);
const summary = { kind: 'single_deck_stats_unit', contract: adapter.COMPUTE_CONTRACT_VERSION,
  passed: failed.length === 0, total: checks.length, failed: failed.length, checks };
if (outputDir) {
  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(path.join(outputDir, 'unit-summary.json'), JSON.stringify(summary, null, 2));
}
console.log(JSON.stringify(summary, null, 2));
if (failed.length) process.exit(1);

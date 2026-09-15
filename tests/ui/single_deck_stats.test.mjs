// Single-deck statistics screen: pure model/rendering checks (no browser, no network, no product mutation).
// Payload shapes are the provisional contract in apps/desktop-ui/compute-adapter.js; fixtures are synthetic.
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
const olFixtures = load('ol-comparison.json');
const [outputDir] = process.argv.slice(2);

const checks = [];
async function check(name, fn) {
  try { await fn(); checks.push({ name, passed: true }); }
  catch (error) { checks.push({ name, passed: false, error: String(error.message).split('\n').slice(0, 6).join(' | ') }); }
}
const html = extra => view.renderSingleDeckStats(view.buildStatsModel(extra));

await check('gpu_usable_only_after_verification', () => {
  const profile = adapter.describeHardwareProfile(hardware.multiGpu);
  assert.equal(profile.devices.length, 3);
  assert.deepEqual(profile.devices.map(d => d.usable), [true, false, false]);
  assert.deepEqual(profile.usableDevices.map(d => d.id), ['gpu-verified-0']);
  assert.equal(profile.devices[1].stageLabel, '이름만 탐지');
  assert.match(profile.devices[2].failureReason, /FP64/);
  const markup = html({ hardware: hardware.multiGpu, selection: selections.autoCpu });
  // Only the verified device may appear as a selectable GPU option.
  assert.ok(markup.includes('<option value="gpu:gpu-verified-0">'));
  assert.ok(!markup.includes('gpu-name-only-1') || !markup.includes('<option value="gpu:gpu-name-only-1">'));
  assert.ok(!markup.includes('<option value="gpu:gpu-accuracy-fail-2">'));
  assert.ok(markup.includes('사용 불가'));
});

await check('hardware_states_cpu_only_failed_measuring', () => {
  const cpuOnly = adapter.describeHardwareProfile(hardware.cpuOnly);
  assert.equal(cpuOnly.statusLabel, 'GPU 없음 · CPU만 탐지');
  assert.equal(cpuOnly.usableDevices.length, 0);
  const failed = adapter.describeHardwareProfile(hardware.detectionFailed);
  assert.equal(failed.statusLabel, '탐지 실패');
  assert.equal(failed.failures.length, 2);
  assert.equal(failed.cpu.logicalProcessors, null);
  const measuring = adapter.describeHardwareProfile(hardware.measuring);
  assert.equal(measuring.statusLabel, '측정 중');
  assert.equal(adapter.describeHardwareProfile(null).statusLabel, '하드웨어 정보 없음');
  const markup = html({ hardware: hardware.detectionFailed });
  assert.ok(markup.includes('탐지 실패') && markup.includes('probe timeout'));
  assert.ok(markup.includes('탐지된 GPU가 없습니다'));
});

await check('cpu_run_never_reported_as_gpu', () => {
  const fallback = adapter.describeExecutionSelection(selections.gpuFallback);
  assert.equal(fallback.effectiveLabel, 'CPU');
  assert.equal(fallback.mismatch, true);
  assert.equal(fallback.fellBack, true);
  const markup = html({ selection: selections.gpuFallback, hardware: hardware.cpuOnly });
  assert.ok(markup.includes('GPU 성공으로 표시하지 않습니다'));
  assert.ok(markup.includes('gpu_backend_not_implemented'));
  const verified = adapter.describeExecutionSelection(selections.gpuVerified);
  assert.equal(verified.mismatch, false);
  assert.equal(verified.effectiveLabel, 'GPU');
  const unknown = adapter.describeExecutionSelection(selections.unknownSelection);
  assert.equal(unknown.effectiveLabel, adapter.UNKNOWN);
  assert.equal(unknown.workers, null);
});

await check('batch_lifecycle_controls_and_counts', () => {
  const running = adapter.describeBatch(batches.running);
  assert.equal(running.stateLabel, '실행 중');
  assert.deepEqual([running.canStart, running.canCancel, running.canResume], [false, true, false]);
  assert.ok(Math.abs(running.progress - 0.32) < 1e-9);
  assert.equal(running.incompleteExcluded, 1);
  const cancelled = adapter.describeBatch(batches.cancelledPartial);
  assert.deepEqual([cancelled.canStart, cancelled.canCancel, cancelled.canResume], [true, false, true]);
  assert.equal(cancelled.partial, true);
  const failed = adapter.describeBatch(batches.failed);
  assert.equal(failed.canResume, true);
  const completed = adapter.describeBatch(batches.completed);
  assert.deepEqual([completed.canStart, completed.canCancel, completed.canResume], [true, false, false]);
  const unknown = adapter.describeBatch(batches.unknownState);
  assert.equal(unknown.progress, null);
  assert.equal(unknown.stateLabel, adapter.UNKNOWN);
  assert.equal(adapter.describeBatch(null).stateLabel, '배치 없음');
  const resumed = adapter.describeBatch(batches.resumedAttempt);
  assert.equal(resumed.attempt, 2);
  const markup = html({ batch: batches.cancelledPartial, statistics: statistics.partialUnsupported });
  assert.ok(markup.includes('부분 결과'));
  assert.ok(markup.includes('표본에서 제외'));
});

await check('statistics_separate_mean_ci_from_quantiles', () => {
  const stats = adapter.describeStatistics(statistics.normal);
  assert.equal(stats.nText, '1,000');
  assert.equal(stats.meanCi.text, '152,083,461.2 ~ 152,681,125.6');
  assert.equal(stats.p5.text, '144,512,900');
  assert.equal(stats.cut.successRate.text, '68.3%');
  assert.equal(stats.cut.ci.text, '65.4% ~ 71.1%');
  assert.equal(stats.perMember.length, 5);
  const markup = html({ statistics: statistics.normal });
  assert.ok(markup.includes('평균 CI는 평균의 불확실성이고'));
  assert.ok(markup.includes('앨리스'));
});

await check('statistics_zero_one_and_unsupported', () => {
  const empty = adapter.describeStatistics(statistics.empty);
  assert.equal(empty.sampleNote, '표본 없음');
  assert.equal(empty.mean.text, adapter.UNKNOWN);
  assert.equal(empty.meanCi.text, '표본 없음');
  const single = adapter.describeStatistics(statistics.single);
  assert.equal(single.sampleNote, '표본 1건 · 산포/신뢰구간 없음');
  assert.equal(single.sd.text, adapter.UNKNOWN);
  const zero = adapter.describeStatistics(statistics.zeroDamage);
  assert.equal(zero.mean.text, '0');       // a real zero is not "unknown"
  assert.equal(zero.cut.successRate.text, '0%');
  assert.equal(zero.sampleNote, null);
  const unsupported = adapter.describeStatistics(statistics.partialUnsupported);
  assert.equal(unsupported.median.text, '미지원');
  assert.equal(unsupported.p95.text, '미지원');
  assert.equal(unsupported.cut.successRate.text, '미지원');
  assert.equal(unsupported.mean.text, '151,884,220.7');
  const markup = html({ statistics: statistics.empty });
  assert.ok(markup.includes('표본 없음'));
  assert.ok(!/NaN|undefined|Infinity/.test(markup));
});

await check('ol_verdict_undetermined_when_ci_spans_zero', () => {
  const ol = adapter.describeOlComparison(olFixtures.mixedVerdicts);
  assert.deepEqual(ol.candidates.map(c => c.verdict), ['improve', 'undetermined', 'regress', 'undetermined']);
  assert.equal(ol.undeterminedCount, 2);
  assert.equal(ol.candidates[0].valueText, '+11.11%');
  assert.equal(ol.candidates[3].deltaText, adapter.UNKNOWN);
  const markup = html({ olComparison: olFixtures.mixedVerdicts });
  assert.ok(markup.includes('우열 미확정'));
  assert.ok(markup.includes('원본 장비를 바꾸지 않는 가상 변경'));
  assert.ok(markup.includes('비용 효율 추천은 제공하지 않습니다'));
  assert.ok(!/모듈 \d/.test(markup), 'module cost numbers must not be invented');
  const empty = adapter.describeOlComparison(olFixtures.empty);
  assert.equal(empty.candidates.length, 0);
  assert.ok(html({ olComparison: olFixtures.empty }).includes('비교 결과가 없습니다'));
});

await check('experiment_input_and_fixed_level', () => {
  const experiment = {
    snapshotId: 'snap-1', engineVersion: 'p03.skills.2', rulesVersion: 'p04.team.2', fingerprint: 'fp-abc',
    synchroLevel: 400, durationSeconds: 180, enemyDefense: 30925, requestedRuns: 1000, recordLevel: 'summary',
    members: [{ characterId: '5004', displayName: '앨리스', burstStep: 3 }]
  };
  const described = adapter.describeExperimentInput(experiment);
  assert.equal(described.synchroLevel, 400);
  assert.equal(described.members[0].displayName, '앨리스');
  const markup = html({ experiment, statistics: statistics.normal });
  assert.ok(markup.includes('싱크로 레벨') && markup.includes('400'));
  assert.ok(markup.includes('고정 DEF 정책'));
  assert.ok(markup.includes('실게임 검증 완료 추천이 아닙니다'));
  assert.equal(view.FIXED_SYNCHRO_LEVEL, 400);
});

await check('endpoint_status_is_explicit', () => {
  assert.ok(html({ endpointStatus: 'unknown' }).includes('연결 확인 중'));
  assert.ok(html({ endpointStatus: 'unavailable' }).includes('배치 API 미연결 · 계약 확정 전'));
  assert.ok(html({ endpointStatus: 'connected' }).includes('실제 API 응답'));
  assert.equal(adapter.COMPUTE_CONTRACT_STATUS, 'provisional_pending_backend_contract');
});

await check('html_escape', () => {
  const evil = '<img src=x onerror=alert(1)>';
  const markup = html({
    endpointStatus: 'connected',
    errors: [evil],
    tacticSummary: evil,
    deckMembers: [{ characterId: evil, displayName: evil, burstStep: 3 }],
    hardware: { status: 'ok', os: evil, gpus: [{ deviceId: evil, vendor: evil, name: evil, stage: 'benchmark' }] },
    selection: { requested: 'auto', effectiveBackend: 'cpu', reason: evil },
    batch: { batchId: evil, state: 'running', requestedRuns: 10, validRuns: 1, message: evil },
    statistics: { n: 2, unit: evil, perMember: [{ characterId: evil, displayName: evil, mean: 1 }] },
    olComparison: { candidates: [{ candidateId: evil, displayName: evil, part: evil, line: 1, optionLabel: evil, teamMeanDelta: 1, deltaConfidenceInterval: { low: 0.5, high: 1.5 } }] }
  });
  assert.ok(!markup.includes('<img src=x'), 'unescaped markup leaked');
  assert.ok(markup.includes('&lt;img src=x onerror=alert(1)&gt;'));
});

await check('controller_guards_missing_endpoints', async () => {
  const calls = [];
  const failing = async (path, method = 'GET') => { calls.push(`${method} ${path}`); throw new Error('404 없음'); };
  const controller = view.createSingleDeckStatsView({
    api: failing, getSnapshot: () => ({ id: 'snap-1' }),
    getMembersWithMeta: () => [{ id: '5004', displayName: '앨리스', burstStep: 3 }],
    getTacticSummary: () => '앨리스 우선', status: () => {}, storage: null
  });
  await controller.refreshHardware();
  let model = controller.getModel();
  assert.equal(model.endpointStatus, 'unavailable');
  assert.ok(model.errors.some(e => e.includes('하드웨어')));
  await controller.start();
  model = controller.getModel();
  assert.ok(calls.includes('GET ' + adapter.COMPUTE_ROUTES.hardware));
  assert.ok(calls.includes('POST ' + adapter.COMPUTE_ROUTES.batches));
  assert.ok(model.errors.some(e => e.includes('배치를 시작하지 못했습니다')));
  assert.equal(model.batch.stateLabel, '배치 없음');
  controller.dispose();
});

await check('controller_start_cancel_resume_flow', async () => {
  const sequence = [];
  const api = async (path, method = 'GET') => {
    sequence.push(`${method} ${path}`);
    if (path === adapter.COMPUTE_ROUTES.hardware) return { hardware: hardware.cpuOnly, selection: selections.autoCpu };
    if (path === adapter.COMPUTE_ROUTES.batches && method === 'POST') return { batch: batches.queued, selection: selections.autoCpu };
    if (path === adapter.COMPUTE_ROUTES.batchCancel('batch-synthetic-1')) return { batch: batches.cancelledPartial, statistics: statistics.partialUnsupported };
    if (path === adapter.COMPUTE_ROUTES.batchResume('batch-synthetic-1')) return { batch: batches.resumedAttempt };
    if (path === adapter.COMPUTE_ROUTES.batch('batch-synthetic-1')) return { batch: batches.running };
    throw new Error('unexpected ' + path);
  };
  const saved = new Map();
  const controller = view.createSingleDeckStatsView({
    api, getSnapshot: () => ({ id: 'snap-1' }),
    getMembersWithMeta: () => [{ id: '5004', displayName: '앨리스', burstStep: 3 }],
    getTacticSummary: () => '앨리스 우선', status: () => {},
    storage: { getItem: k => saved.get(k) ?? null, setItem: (k, v) => saved.set(k, v) }
  });
  await controller.refreshHardware();
  await controller.start();
  assert.equal(controller.getModel().batch.stateLabel, '대기 중');
  assert.equal(saved.get('nikke-single-deck-batch'), 'batch-synthetic-1');
  await controller.cancel();
  let model = controller.getModel();
  assert.equal(model.batch.stateLabel, '취소됨');
  assert.equal(model.batch.partial, true);
  assert.equal(model.statistics.median.text, '미지원');
  await controller.resume();
  model = controller.getModel();
  assert.equal(model.batch.stateLabel, '실행 중');
  assert.equal(model.batch.attempt, 2);
  assert.equal(model.endpointStatus, 'connected');
  controller.dispose();
});

const failed = checks.filter(c => !c.passed);
const summary = { kind: 'single_deck_stats_unit', passed: failed.length === 0, total: checks.length, failed: failed.length, checks };
if (outputDir) {
  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(path.join(outputDir, 'unit-summary.json'), JSON.stringify(summary, null, 2));
}
console.log(JSON.stringify(summary, null, 2));
if (failed.length) process.exit(1);

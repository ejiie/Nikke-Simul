// Q3 boundary acceptance: real freshly generated engine result, synthetic HTTP envelope.
// No browser, network, account data, or product mutation. Exit 1 means NOT accepted.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { pathToFileURL } from 'node:url';
import { createHash, randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';

const root = path.resolve(import.meta.dirname, '../..');
const [resultPath, outputRoot = path.join(root, 'artifacts/q3')] = process.argv.slice(2);
if (!resultPath) throw new Error('Usage: node tests/q3/check_ui_contract.mjs <fresh engine result.json> [output-root]');
const out = path.join(outputRoot, `ui-${randomUUID()}`);
fs.mkdirSync(out, { recursive: true });
const adapter = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/damage-log-adapter.js')));
const result = JSON.parse(fs.readFileSync(resultPath, 'utf8'));
const saved = { id: 'q3-synthetic-wrapper', result };
const envelope = value => ({ exportSchemaVersion: 1, collectionStatus: value.result.damageLog?.status ?? 'not_collected', replay: value });
const members = ['i', 'ii', '5004', '5044', '5009'].map((id, i) => ({ id, burstStep: Math.min(i + 1, 3) }));
const checks = [];
async function check(name, fn) {
  try { await fn(); checks.push({ name, passed: true }); }
  catch (e) { checks.push({ name, passed: false, error: e.message }); }
}
const fetch = (value, id = '5004') => adapter.fetchDamageLog(async () => envelope(value), value.id, id, null, members);
const log = result.damageLog;
await check('fresh_engine_log_sum_ids_and_180_seconds', () => {
  assert.equal(result.conditions.combat.durationFrames, 10800);
  assert.equal(log.schemaVersion, 1); assert.equal(log.status, 'complete'); assert.equal(log.truncated, false);
  assert.equal(log.entries.length, log.eventCount);
  assert.equal(new Set(log.entries.map(e => e.hitId)).size, log.eventCount);
  let sum = 0, previous = 0;
  for (const e of log.entries) {
    assert.equal(e.source, log.characterId); assert.ok(e.frame >= previous && e.frame <= 10800);
    assert.equal(e.seconds, e.frame / 60); assert.equal(e.calculation.damage, e.damage);
    sum += e.damage; assert.equal(e.cumulativeDamage, sum); previous = e.frame;
  }
  assert.ok(previous > 10700); assert.equal(sum, log.totalDamage);
  const member = result.members.find(m => m.characterId === log.characterId);
  assert.equal(sum, member.damage);
  assert.equal(new Set(log.entries.filter(e => e.shotId !== null).map(e => e.shotId)).size, member.shots);
  assert.ok(log.entries.some(e => e.ownBurstEffectActive && !e.hit.fullBurst));
  assert.ok(log.entries.some(e => !e.ownBurstEffectActive && e.hit.fullBurst));
  const gauge = result.teamBurst.timeline.filter(e => e.kind === 'gauge' && e.characterId === '5004');
  assert.ok(gauge.length); assert.ok(gauge.every(e => e.requestedRaw === 196000));
});
await check('actual_wire_envelope_is_collected', async () => {
  const actual = await fetch(saved); assert.equal(actual.status, 'collected');
  assert.equal(actual.log.totalDamage, log.totalDamage); assert.equal(actual.log.hits.length, log.eventCount);
});
await check('direct_saved_result_is_collected', async () => {
  const actual = await adapter.fetchDamageLog(null, null, '5004', saved, members);
  assert.equal(actual.status, 'collected'); assert.equal(actual.log.hits.length, log.eventCount);
});
await check('wire_hit_context_and_charge_mapping', async () => {
  const actual = await fetch(saved);
  assert.ok(actual.log?.hits?.length, 'actual wire entries must reach UI');
  for (let i = 0; i < log.eventCount; i++) {
    const e = log.entries[i], h = actual.log.hits[i];
    for (const key of ['hitId', 'shotId', 'frame', 'damage', 'cumulativeDamage']) assert.equal(h[key], e[key]);
    assert.equal(h.characterId, e.source); assert.equal(h.chargeRate, e.chargeRatioRaw === null ? null : e.chargeRatioRaw / 10000);
    assert.equal(h.isFullCharge, e.fullCharge); assert.equal(h.isCritical, e.hit.crit);
    assert.equal(h.isCore, e.hit.core); assert.equal(h.isSelfBurstActive, e.ownBurstEffectActive);
    assert.equal(h.isTeamFullBurst, e.hit.fullBurst);
  }
});
function withLog(value) { return { ...saved, result: { ...result, damageLog: value } }; }
await check('complete_zero_is_no_damage', async () => {
  const actual = await fetch(withLog({ ...log, totalDamage: 0, eventCount: 0, entries: [] }));
  assert.equal(actual.status, 'no_damage'); assert.equal(actual.log.totalDamage, 0);
});
await check('null_and_legacy_are_uncollected_without_mock', async () => {
  const legacy = structuredClone(saved); delete legacy.result.damageLog;
  for (const value of [withLog(null), legacy]) {
    const actual = await fetch(value); assert.equal(actual.status, 'uncollected'); assert.equal(actual.isMock, false); assert.equal(actual.log, null);
  }
});
await check('different_character_is_uncollected', async () => {
  assert.equal((await fetch(saved, '5044')).status, 'uncollected');
});
await check('truncated_is_not_uncollected', async () => {
  const actual = await fetch(withLog({ ...log, status: 'truncated', truncated: true, truncationReason: 'q3-test' }));
  assert.equal(actual.truncated, true); assert.notEqual(actual.status, 'uncollected');
});
await check('unknown_schema_is_explicit', async () => {
  const actual = await fetch(withLog({ ...log, schemaVersion: 999 }));
  assert.ok(['unsupported_schema', 'unsupported'].includes(actual.status), actual.status);
});
await check('api_failure_is_not_uncollected', async () => {
  const actual = await adapter.fetchDamageLog(async () => { throw new Error('HTTP 500 Q3'); }, 'q3', '5004', null, members);
  assert.ok(['error', 'api_error'].includes(actual.status), actual.status);
});
const base = { schemaVersion: 1, allowedCharacterIds: members.map(m => m.id), stage1Priority: ['i'], stage2Priority: ['ii'], stage3Priority: ['5004','5044','5009'], burst3Rotation: ['5004','5044','5009'], firstBurst3CharacterId: '5004', unavailablePolicy: 'next_ready' };
for (const [name, changes] of [
  ['standard_roundtrip', {}], ['rotation_order', { burst3Rotation: ['5009','5044','5004'] }],
  ['rotation_subset', { burst3Rotation: ['5044','5009'], firstBurst3CharacterId: '5044' }],
  ['single_nonpriority_rotation', { burst3Rotation: ['5009'], firstBurst3CharacterId: '5009' }],
  ['null_first_caster', { firstBurst3CharacterId: null }], ['wait_policy', { unavailablePolicy: 'wait_preferred' }]
]) await check(`tactic_${name}`, () => {
  const dto = { ...base, ...changes };
  assert.deepEqual(adapter.toServerTacticDto(adapter.fromServerTacticDto(dto, members), members), dto);
});
await check('priority_only_conflicting_first_caster_is_rejected', () => {
  const ui = { ...adapter.createDefaultTactics(members), stage3Mode: 'priority_only', firstCaster: '5044' };
  let rejected = !adapter.auditBurstTactics(members, ui).valid;
  try { adapter.toServerTacticDto(ui, members); } catch { rejected = true; }
  assert.ok(rejected, 'conflicting first caster was silently replaced');
});
await check('stale_id_diagnosed', () => {
  const ui = adapter.createDefaultTactics(members); ui.priority.stage3.push('removed');
  assert.equal(adapter.auditBurstTactics(members, ui).executionStatus, 'stale');
});
await check('server_restore_keeps_null_and_subset', async () => {
  const dto = { ...base, burst3Rotation: ['5044'], firstBurst3CharacterId: null };
  const actual = await adapter.loadBurstTacticFromServer(async () => ({ saved: { tactic: dto }, stale: false, executionStatus: 'requires_execution_validation' }), 'q3-account', members);
  assert.equal(actual.ok, true); assert.deepEqual(adapter.toServerTacticDto(actual.tactics, members), dto);
});
// Execute the checked-in submit callback with a minimal DOM/API harness; no copied request builder.
const app = fs.readFileSync(path.join(root, 'apps/desktop-ui/app.js'), 'utf8');
async function captureRequest(policy = 'next_ready') {
  const start = app.indexOf("$('replay-form').onsubmit=async e=>{");
  const end = app.indexOf('\nfunction renderReplay', start);
  assert.ok(start >= 0 && end > start, 'submit harness needs adaptation to new app layout');
  const callback = app.slice(start, end).trim().replace(/\}\s*$/, '');
  const nodes = new Map(); const get = id => { if (!nodes.has(id)) nodes.set(id, {}); return nodes.get(id); };
  const form = new Map(Object.entries({ burst:'auto', seconds:'180', burstAt:'10', burstRotation:'', burstUnavailable:policy, level:'', rounding:'legacy_term_floor', defense:'10', crit:'off', pellet:'per_trigger', manualCharacter:'5004', manualStyle:'full_charge' }));
  let captured;
  const context = { $:get, snapshot:{id:'q3-synthetic'}, status:()=>{}, formation:{members:()=>members.map(m=>m.id)}, tacticsManager:{getTactics:()=>adapter.createDefaultTactics(members)}, getMembersWithMeta:()=>members, toServerTacticDto:adapter.toServerTacticDto, FormData:class { get(k){return form.get(k)??null;} has(k){return form.has(k);} }, api:async (_p,_m,r)=>{captured=r;return {};}, renderReplay:()=>{}, lastReplay:null };
  vm.runInNewContext(callback, context);
  await get('replay-form').onsubmit({preventDefault(){}, currentTarget:{}});
  assert.ok(captured, 'submit did not reach API'); return captured;
}
await check('request_selects_damage_log_character', async () => {
  const request = await captureRequest(); assert.equal(request.conditions.damageLog?.characterId, '5004');
});
for (const policy of ['next_ready','wait_preferred']) await check(`request_has_no_legacy_tactic_mix_${policy}`, async () => {
  const request = await captureRequest(policy); const auto = request.conditions.autoBurst;
  assert.ok(auto.tactic); assert.equal((auto.burst3Rotation ?? []).length, 0); assert.equal(auto.unavailablePolicy ?? 'next_ready', 'next_ready');
});
const viewer = fs.readFileSync(path.join(root, 'apps/desktop-ui/damage-log.js'), 'utf8');
await check('direct_skill_only_UI_shot_count_is_zero', () => {
  const expression = viewer.match(/const uniqueShots = ([^;]+);/)?.[1];
  assert.ok(expression, 'shot count harness needs adaptation to new viewer layout');
  const count = vm.runInNewContext(expression, { hits:[{ shotId:null }, { shotId:null }] });
  assert.equal(count, 0, 'direct skill hits were counted as fired shots');
});
const { createBurstTacticsManager, normalizeVisibleBurstTactics } = await import(pathToFileURL(path.join(root, 'apps/desktop-ui/burst-tactics.js')));
await check('compact_tactics_ignore_hidden_legacy_choices', () => {
  const ui = adapter.fromServerTacticDto({ ...base, burst3Rotation:['5009'], firstBurst3CharacterId:'5009', unavailablePolicy:'wait_preferred' }, members);
  normalizeVisibleBurstTactics(ui, members);
  assert.deepEqual(adapter.toServerTacticDto(ui, members), base);
  ui.allowlist['5004'] = false;
  normalizeVisibleBurstTactics(ui, members);
  assert.deepEqual(ui.burst3Rotation, ['5044', '5009']);
  assert.equal(ui.firstCaster, '5044');
  ui.priority.stage3 = ['5009', '5004', '5044'];
  normalizeVisibleBurstTactics(ui, members);
  assert.deepEqual(ui.burst3Rotation, ['5009', '5044']);
  assert.equal(ui.firstCaster, '5009');
  ui.allowlist['5044'] = false;
  ui.allowlist['5009'] = false;
  normalizeVisibleBurstTactics(ui, members);
  assert.deepEqual(ui.burst3Rotation, []);
  assert.equal(ui.firstCaster, null);
  assert.equal(adapter.auditBurstTactics(members, ui).valid, false);
});
for (const scenario of ['account_switch', 'local_edit']) await check(`late_server_restore_preserves_${scenario}`, async () => {
  const priorDocument = globalThis.document, priorStorage = globalThis.localStorage;
  const cache = new Map();
  globalThis.document = { getElementById:()=>null };
  globalThis.localStorage = { getItem:k=>cache.get(k) ?? null, setItem:(k,v)=>cache.set(k,v) };
  try {
    let snapshot = { id:'snapshot-a', accountId:'account-a' };
    const pending = [];
    const manager = createBurstTacticsManager({ api:()=>new Promise(resolve=>pending.push(resolve)), getSnapshot:()=>snapshot,
      getMembersWithMeta:()=>members, getFormationSlots:()=>members.map(m=>m.id) });
    manager.loadTactics();
    pending.shift()({ saved:{tactic:base}, stale:false, executionStatus:'requires_execution_validation' });
    await new Promise(resolve=>setImmediate(resolve));
    const late = manager.syncFromServer();
    const resolveOld = pending.shift();
    if (scenario === 'account_switch') {
      snapshot = { id:'snapshot-b', accountId:'account-b' };
      manager.loadTactics();
      pending.shift()({ saved:{tactic:{...base, stage3Priority:['5044','5004','5009'], burst3Rotation:['5044','5004','5009'], firstBurst3CharacterId:'5044'}}, stale:false });
      await new Promise(resolve=>setImmediate(resolve));
    } else {
      manager.getTactics().priority.stage3 = ['5044','5004','5009'];
      normalizeVisibleBurstTactics(manager.getTactics(), members);
    }
    assert.equal(manager.getTactics().firstCaster, '5044', 'race precondition');
    resolveOld({ saved:{tactic:base}, stale:false }); await late;
    assert.equal(manager.getTactics().firstCaster, '5044', 'late response overwrote newer selection');
  } finally {
    globalThis.document = priorDocument; globalThis.localStorage = priorStorage;
  }
});
const summary = { commit:execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(), evidence:'fresh_actual_engine_result_with_synthetic_envelope_and_submit_harness_no_HTTP_or_browser', gameVerified:false, input:path.resolve(resultPath), inputSha256:createHash('sha256').update(fs.readFileSync(resultPath)).digest('hex'), checks, passed:checks.filter(c=>c.passed).length, failed:checks.filter(c=>!c.passed).length };
fs.writeFileSync(path.join(out,'summary.json'), JSON.stringify(summary,null,2));
console.log(JSON.stringify({output:out,passed:summary.passed,failed:summary.failed,failures:checks.filter(c=>!c.passed).map(c=>c.name)},null,2));
process.exitCode = summary.failed ? 1 : 0;

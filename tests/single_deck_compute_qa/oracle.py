"""Independent QA evidence predicates. This is NOT a Backend DTO or API contract.

Adapters must be tied to a confirmed Backend contract before product acceptance.
No engine, account, hardware probe, server, database or production RNG is invoked.
"""
from fractions import Fraction
import math
from statistics import NormalDist


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    require(type(value) in (int, float) and math.isfinite(value), 'nonfinite_or_missing_number')
    return value


def count(value):
    require(type(value) is int and value >= 0, 'invalid_count')
    return value


def stats(values, cutoff):
    """Exact rational mean/variance reference, HF type 7 quantiles, Wilson 95% CI.

    Mean CI intentionally unsupported here until Analysis specifies its method.
    Fractions avoid cancellation with integer damage above binary64 exact range.
    """
    values = sorted(Fraction(number(v)) for v in values)
    cutoff = Fraction(number(cutoff))
    n = len(values)
    base = dict(n=n, mean=None, sampleSd=None, median=None, p5=None, p95=None,
                meanCi=None, meanCiMethod='pending_analysis_contract', cutSuccess=None,
                cutCi=None, quantileMethod='HF7', cutCiMethod='Wilson95', unit='damage')
    if not n:
        return base
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1) if n > 1 else None
    def quantile(p):
        pos = (n - 1) * p
        lo = pos.numerator // pos.denominator
        return float(values[lo] + (values[min(lo + 1, n - 1)] - values[lo]) * (pos - lo))
    wins = sum(v > cutoff for v in values)  # strictly exceeds cutoff
    p = wins / n
    z = NormalDist().inv_cdf(.975)
    denominator = 1 + z*z/n
    center = (p + z*z/(2*n)) / denominator
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
    base.update(mean=float(mean), meanExact=str(mean), sampleSd=math.sqrt(variance) if variance is not None else None,
                median=quantile(Fraction(1, 2)), p5=quantile(Fraction(1, 20)), p95=quantile(Fraction(19, 20)),
                cutSuccess=p, cutCi=[max(0., center-half), min(1., center+half)])
    return base


def hardware(profile, selection):
    """Check evidence for the selection, never infer GPU eligibility from its name."""
    require(profile['os'] and profile['architecture'], 'missing_platform')
    cpu = profile['cpu']
    require(count(cpu['availableWorkers']) >= 1, 'no_cpu_capacity')
    for key in ('physicalCores', 'logicalCores'):
        require(cpu[key] is None or count(cpu[key]) > 0, 'invalid_topology')
    limit = profile['memoryLimitBytes']
    require(limit is None or number(limit) > 0, 'invalid_memory')
    require(profile['probeStatus'] in ('ok', 'partial', 'failed', 'timeout'), 'invalid_probe_status')
    require(profile['probeStatus'] == 'ok' or bool(profile['probeReason']), 'missing_probe_reason')
    require(selection['requested'] in ('auto', 'cpu', 'gpu'), 'invalid_requested_backend')
    require(selection['reason'], 'missing_selection_reason')
    require(selection['cacheFingerprint'] is None or selection['cacheFingerprint'] == profile['fingerprint'], 'stale_cache')
    ids = [g['deviceId'] for g in profile['gpus']]
    require(len(ids) == len(set(ids)) and all(ids), 'unstable_or_duplicate_device_id')
    eligible = []
    for gpu in profile['gpus']:
        require(gpu['memoryBytes'] is None or number(gpu['memoryBytes']) > 0, 'invalid_gpu_memory')
        proven = all(gpu[key] is True for key in ('runtimeAvailable', 'fp64', 'kernelExecuted', 'numericPassed', 'distributionPassed', 'endToEndPassed'))
        require(not gpu['eligible'] or proven, 'gpu_inventory_is_not_execution')
        if gpu['eligible']:
            require(all(gpu[key] for key in ('driver', 'backend', 'kernelVersion', 'benchmarkVersion')), 'missing_gpu_provenance')
            eligible.append(gpu['deviceId'])
        else:
            require(gpu['reason'], 'missing_gpu_unavailable_reason')
    if selection['error'] is not None:
        require(selection['requested'] == 'gpu' and selection['effective'] is None, 'invalid_preflight_failure')
        require(not selection['started'], 'forced_gpu_started_before_error')
        return
    require(1 <= count(selection['workers']) <= cpu['availableWorkers'], 'worker_cap_exceeded')
    require(count(selection['chunkSize']) > 0 and number(selection['memoryCapBytes']) > 0, 'invalid_resource_budget')
    require(limit is None or selection['memoryCapBytes'] <= limit, 'memory_cap_exceeded')
    if selection['effective'] == 'gpu':
        require(selection['requested'] != 'cpu' and selection['deviceId'] in eligible, 'unproven_gpu_selection')
    else:
        require(selection['effective'] == 'cpu' and selection['deviceId'] is None, 'cpu_mislabeled_as_gpu')
        require(selection['requested'] != 'gpu', 'forced_gpu_silent_fallback')
        require(selection['requested'] != 'auto' or bool(selection['fallbackReason']), 'missing_auto_cpu_reason')


def batch(snapshot):
    """Validate normalized terminal attempt ledger and count only latest valid runs.

    Discarded attempts remain auditable; no silent deduplication of valid records.
    A failed GPU attempt must have zero accepted rows before CPU retry.
    """
    requested = count(snapshot['requested'])
    require(snapshot['status'] in ('queued', 'running', 'cancelling', 'cancelled', 'completed', 'failed'), 'bad_lifecycle')
    require(snapshot['input']['synchro'] == 400 and snapshot['input']['defPolicy'] == 'fixed', 'changed_combat_policy')
    require(snapshot['input']['durationSeconds'] > 0, 'invalid_duration')
    require(all(snapshot['input'][k] for k in ('snapshotFingerprint', 'dataVersion', 'engineVersion', 'rulesVersion', 'tacticFingerprint', 'buildFingerprint')), 'missing_input_provenance')
    require(len(snapshot['input']['members']) == 5 and len(set(snapshot['input']['members'])) == 5, 'invalid_team')
    rows = snapshot['attempts']
    keys, latest = set(), {}
    for row in rows:
        key = (row['runId'], count(row['attempt']))
        require(row['runId'] and row['attempt'] > 0 and key not in keys, 'duplicate_attempt')
        keys.add(key)
        latest[row['runId']] = max(latest.get(row['runId'], 0), row['attempt'])
    require(len(latest) <= requested, 'too_many_run_ids')
    totals = dict(valid=0, failed=0, cancelled=0)
    backends = set()
    valid = []
    for row in rows:
        require(row['status'] in ('valid', 'failed', 'cancelled', 'discarded'), 'nonterminal_attempt')
        require(row['phase'] in ('warmup', 'pilot', 'final'), 'missing_sampling_phase')
        if row['status'] == 'discarded':
            require(not row['accepted'] and row['reason'], 'discarded_counted')
            continue
        require(row['attempt'] == latest[row['runId']], 'stale_attempt_counted')
        if row['status'] != 'valid':
            require(not row['accepted'] and row['damage'] is None, 'incomplete_battle_is_not_zero')
            totals[row['status']] += 1
            continue
        require(row['accepted'] and row['completedBattle'], 'incomplete_accepted')
        require(row['phase'] == snapshot['phase'], 'pilot_holdout_contamination')
        require(row['inputFingerprint'] == snapshot['input']['buildFingerprint'], 'mixed_input')
        require(row['numericalModel'] == snapshot['numericalModel'], 'mixed_numeric_semantics')
        require(row['backend'] in ('cpu', 'gpu'), 'missing_actual_backend')
        require(set(row['memberDamage']) == set(snapshot['input']['members']), 'wrong_member_ids')
        require(number(row['damage']) >= 0 and all(number(v) >= 0 for v in row['memberDamage'].values()), 'invalid_damage')
        require(Fraction(row['damage']) == sum(Fraction(v) for v in row['memberDamage'].values()), 'team_member_sum')
        backends.add(row['backend'])
        valid.append(row)
        totals['valid'] += 1
    require(len(backends) <= 1, 'mixed_backend_sample')
    require(all(snapshot[k] == v for k, v in totals.items()), 'incorrect_counts')
    require(snapshot['partial'] is (totals['valid'] < requested), 'incorrect_partial')
    if snapshot['status'] == 'completed':
        require(sum(totals.values()) == requested, 'completed_with_missing_runs')
    return valid


def equivalent(left, right, *, bounds, mean_margin, cdf_margin=.05, family_size=36, alpha=.05):
    """Predeclared, conservative independent-sample equivalence gates.

    Bounded Hoeffding mean intervals and two DKW uniform CDF bands.
    Union bound covers two gates per metric across family_size metrics.
    Insufficient samples -> inconclusive, never 'equal because p > .05'.
    Bounds/margins must be fixed before observing the evaluated samples.
    """
    require(len(left) >= 2 and len(right) >= 2, 'insufficient_samples')
    lo, hi = bounds
    require(number(lo) < number(hi) and mean_margin > 0 and 0 < cdf_margin < 1, 'invalid_preregistration')
    require(type(family_size) is int and family_size > 0 and 0 < alpha < 1, 'invalid_family')
    require(all(lo <= number(x) <= hi for x in left + right), 'observation_outside_preregistered_bounds')
    a, b = sorted(left), sorted(right)
    gate_alpha = alpha / (2 * family_size)
    radius = math.sqrt(math.log(4/gate_alpha)/(2*len(a))) + math.sqrt(math.log(4/gate_alpha)/(2*len(b)))
    mean_delta = float(sum(map(Fraction, b))/len(b) - sum(map(Fraction, a))/len(a))
    half = (hi-lo)*radius
    i = j = 0
    distance = 0.
    for value in sorted(set(a+b)):
        while i < len(a) and a[i] <= value: i += 1
        while j < len(b) and b[j] <= value: j += 1
        distance = max(distance, abs(i/len(a)-j/len(b)))
    passed = abs(mean_delta)+half <= mean_margin and distance+radius <= cdf_margin
    return dict(verdict='equivalent_within_declared_bounds' if passed else 'inconclusive_or_outside_margin',
                meanDelta=mean_delta, meanInterval=[mean_delta-half, mean_delta+half],
                cdfDistance=distance, cdfUpperBound=min(1.,distance+radius), familySize=family_size,
                method='bounded_Hoeffding_plus_DKW_union_bound', paired=False)


def portable(record):
    require(record['schema'] == 'qa-portable-evidence-v1', 'unsupported_qa_schema')
    require(record['evidence'] in ('actual', 'synthetic'), 'missing_evidence_type')
    require(all(record[k] for k in ('productCommit', 'contractVersion', 'engineVersion', 'workloadFingerprint', 'policyVersion')), 'missing_portable_provenance')
    hardware(record['hardware'], record['selection'])
    for measurement in record['measurements']:
        require(measurement['thermalState'] in ('cold', 'warm'), 'missing_warm_cold')
        for key in ('elapsedSeconds', 'peakMemoryBytes', 'storageBytes', 'allocatedBytes', 'gcCollections', 'uiP95Milliseconds', 'cancelMilliseconds'):
            metric = measurement[key]
            if metric['value'] is None:
                require(metric['reason'], 'missing_measurement_reason')
            else:
                require(number(metric['value']) >= 0, 'invalid_measurement')
        require(count(measurement['validRuns']) <= count(measurement['requestedRuns']), 'invalid_throughput_count')
        require(measurement['exclusiveBenchmarkWindow'], 'concurrent_benchmark_not_comparable')
        require(measurement['elapsedSeconds']['value'] is None or measurement['elapsedSeconds']['value'] > 0, 'zero_elapsed_time')
    require(record['measurements'], 'no_measurements')
    return 'synthetic_schema_only' if record['evidence'] == 'synthetic' else 'evidence_shape_only_not_product_acceptance'


def exact_engine(before, after):
    """Only for fixed, nonrandom conditions or explicitly test-only RNG streams."""
    require(before['comparisonMode'] == after['comparisonMode'] == 'controlled_test_only', 'not_a_deterministic_comparison')
    for result in (before, after):
        require(result['inputBeforeHash'] == result['inputAfterHash'], 'input_mutated')
    for field in ('inputBeforeHash','teamDamage','memberDamage','shots','hits','crits','reloads','bursts','remainingAmmo','eventOrder','randomCalls'):
        require(before[field] == after[field], 'engine_difference_'+field)


def ol_holdout(record):
    require(record['originalBeforeHash'] == record['originalAfterHash'], 'original_build_mutated')
    require(record['fullCombatRerun'] is True and record['pairedSeeds'] is False, 'invalid_OL_experiment_design')
    search, baseline, candidate = (set(record[k]) for k in ('searchRunIds','baselineFinalRunIds','candidateFinalRunIds'))
    require(search and baseline and candidate, 'missing_holdout_samples')
    require(not (search & baseline or search & candidate or baseline & candidate), 'holdout_contamination')
    low, high = map(number, record['independentDifferenceCi'])
    require(low <= high, 'invalid_difference_CI')
    expected = 'improved' if low > 0 else 'worse' if high < 0 else 'inconclusive'
    require(record['verdict'] == expected, 'OL_verdict_disagrees_with_CI')
    require(record['gameVerified'] is False, 'model_is_not_game_verification')
    require(record['costEfficiency'] is None, 'unverified_cost_policy')

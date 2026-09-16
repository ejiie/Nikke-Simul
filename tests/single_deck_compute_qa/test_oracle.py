"""Synthetic positive and deliberately corrupted evidence; no product acceptance."""
from copy import deepcopy
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest
import uuid
from oracle import batch, equivalent, exact_engine, hardware, ol_holdout, portable, stats


def profile():
    return dict(os='Windows', architecture='x64', cpu=dict(availableWorkers=8, physicalCores=4, logicalCores=8),
                memoryLimitBytes=1024**3, probeStatus='ok', probeReason=None, fingerprint='machine-driver-engine-workload-v1', gpus=[])


def gpu(vendor='Intel', device='synthetic-device-0'):
    return dict(deviceId=device, vendor=vendor, name='synthetic '+vendor, memoryBytes=1024**3,
                driver='fixture-driver', backend='fixture-kernel', kernelVersion='v1', benchmarkVersion='v1',
                runtimeAvailable=True, fp64=True, kernelExecuted=True, numericPassed=True,
                distributionPassed=True, endToEndPassed=True, eligible=True, reason=None)


def selection():
    return dict(requested='auto', effective='cpu', deviceId=None, workers=2, chunkSize=8,
                memoryCapBytes=1024**2, reason='bounded_cpu_fixture', fallbackReason='no_eligible_gpu',
                cacheFingerprint=None, started=True, error=None)


def sample():
    members = ['liter', 'blanc', 'alice', 'noir', 'modernia']
    return dict(requested=1, valid=1, failed=0, cancelled=0, partial=False, status='completed', phase='final',
                numericalModel='fixed-def-legacy-floor',
                input=dict(synchro=400, defPolicy='fixed', defense=30925, durationSeconds=180,
                           snapshotFingerprint='synthetic-not-account', dataVersion='fixture-v1', engineVersion='fixture-v1',
                           rulesVersion='p04.team.2', tacticFingerprint='synthetic-tactic', buildFingerprint='fixture-build', members=members),
                attempts=[dict(runId='run-0', attempt=1, status='valid', accepted=True, completedBattle=True,
                               phase='final', inputFingerprint='fixture-build', numericalModel='fixed-def-legacy-floor',
                               backend='cpu', damage=0, memberDamage=dict.fromkeys(members, 0))])


def portable_record():
    metric = lambda value: dict(value=value, reason=None if value is not None else 'not_measured')
    return dict(schema='qa-portable-evidence-v1', evidence='synthetic', productCommit='fixture-sha',
                contractVersion='QA_fixture_NOT_Backend_contract', engineVersion='fixture-v1',
                workloadFingerprint='fixture-5-person', policyVersion='fixture-v1', hardware=profile(), selection=selection(),
                measurements=[dict(thermalState='warm', requestedRuns=1000, validRuns=1000, exclusiveBenchmarkWindow=True,
                                   elapsedSeconds=metric(1), peakMemoryBytes=metric(1024), storageBytes=metric(512),
                                   allocatedBytes=metric(None), gcCollections=metric(None), uiP95Milliseconds=metric(None), cancelMilliseconds=metric(None))])


class HardwareTests(unittest.TestCase):
    def test_cpu_only_and_unknown_topology(self):
        p = profile(); hardware(p, selection())
        p['cpu'].update(physicalCores=None, logicalCores=None)
        p['memoryLimitBytes'] = None
        hardware(p, selection())

    def test_synthetic_three_vendors_multi_gpu(self):
        p = profile(); p['gpus'] = [gpu(v, str(i)) for i,v in enumerate(('Intel','AMD','NVIDIA'))]
        for g in p['gpus']:
            with self.subTest(vendor=g['vendor']):
                s=selection(); s.update(effective='gpu', deviceId=g['deviceId'])
                hardware(p,s)

    def test_driver_runtime_fp64_kernel_numeric_distribution_and_benchmark_gates(self):
        for gate in ('runtimeAvailable','fp64','kernelExecuted','numericPassed','distributionPassed','endToEndPassed'):
            with self.subTest(gate=gate):
                p=profile(); g=gpu(); g[gate]=False; p['gpus']=[g]
                with self.assertRaises(ValueError): hardware(p,selection())
                g.update(eligible=False,reason=gate+'_unavailable')
                hardware(p,selection())
        p=profile(); p['gpus']=[gpu()]; p['gpus'][0]['driver']=None
        with self.assertRaises(ValueError): hardware(p,selection())

    def test_probe_denied_exception_timeout_and_remote_disconnect(self):
        for state,reason in [('partial','permission_denied'),('failed','probe_exception'),('timeout','probe_timeout'),('partial','remote_disconnected')]:
            with self.subTest(reason=reason):
                p=profile(); p.update(probeStatus=state,probeReason=reason)
                hardware(p,selection())
                p['probeReason']=None
                with self.assertRaises(ValueError): hardware(p,selection())

    def test_forced_gpu_is_preflight_error(self):
        s=selection(); s.update(requested='gpu',effective=None,started=False,error='gpu_unavailable')
        hardware(profile(),s)
        s['started']=True
        with self.assertRaises(ValueError): hardware(profile(),s)
        s=selection(); s['requested']='gpu'
        with self.assertRaises(ValueError): hardware(profile(),s)

    def test_inventory_never_cpu_disguised_as_gpu(self):
        s=selection(); s.update(effective='gpu',deviceId='name-only')
        with self.assertRaises(ValueError): hardware(profile(),s)

    def test_resource_caps_and_nonfinite_memory(self):
        for field,value in [('workers',9),('workers',0),('chunkSize',0),('memoryCapBytes',2**40)]:
            with self.subTest(field=field,value=value):
                s=selection(); s[field]=value
                with self.assertRaises(ValueError): hardware(profile(),s)
        for bad in (-1,0,float('nan'),float('inf')):
            p=profile(); p['memoryLimitBytes']=bad
            with self.assertRaises(ValueError): hardware(p,selection())

    def test_stale_cache_driver_machine_engine_workload_policy(self):
        for changed in ('machine','driver','runtime','engine','kernel','workload','policy'):
            s=selection(); s['cacheFingerprint']='stale-'+changed
            with self.assertRaises(ValueError): hardware(profile(),s)
        s['cacheFingerprint']=profile()['fingerprint']; hardware(profile(),s)

    def test_duplicate_device_identifier(self):
        p=profile(); p['gpus']=[gpu(),gpu('AMD')]
        with self.assertRaises(ValueError): hardware(p,selection())


class BatchTests(unittest.TestCase):
    def test_real_zero_kept_and_counts_exact(self):
        self.assertEqual(len(batch(sample())),1)

    def test_duplicate_and_conflicting_storage_rows(self):
        for damage in (0,10):
            x=sample(); extra=deepcopy(x['attempts'][0]); extra['damage']=damage; x['attempts'].append(extra)
            with self.assertRaisesRegex(ValueError,'duplicate_attempt'): batch(x)

    def test_resume_discards_gpu_attempt_before_cpu_result(self):
        x=sample(); old=deepcopy(x['attempts'][0]); old.update(backend='gpu',status='discarded',accepted=False,reason='gpu_failure')
        x['attempts'][0]['attempt']=2; x['attempts'].insert(0,old)
        self.assertEqual(len(batch(x)),1)
        old.update(status='valid',accepted=True)
        with self.assertRaisesRegex(ValueError,'stale_attempt'): batch(x)

    def test_cancel_and_failed_not_accepted_as_zero(self):
        for state in ('cancelled','failed'):
            x=sample(); x.update(status=state,valid=0,partial=True); x[state]=1
            x['attempts'][0].update(status=state,accepted=False,damage=None,completedBattle=False)
            self.assertEqual(batch(x),[])
            x['attempts'][0]['damage']=0
            with self.assertRaises(ValueError): batch(x)

    def test_incomplete_not_normal_sample(self):
        x=sample(); x['attempts'][0]['completedBattle']=False
        with self.assertRaises(ValueError): batch(x)

    def test_queued_running_cancelling_and_partial(self):
        for state in ('queued','running','cancelling','cancelled','failed'):
            x=sample(); x.update(requested=2,status=state,partial=True)
            self.assertEqual(len(batch(x)),1)
        x['status']='completed'
        with self.assertRaises(ValueError): batch(x)

    def test_model_input_phase_and_team_mismatch(self):
        for field,value in [('phase','pilot'),('inputFingerprint','different'),('numericalModel','float32'),('damage',1)]:
            x=sample(); x['attempts'][0][field]=value
            with self.assertRaises(ValueError): batch(x)
        x=sample(); x['input']['synchro']=200
        with self.assertRaises(ValueError): batch(x)

    def test_mixed_gpu_cpu_population_rejected(self):
        x=sample(); x.update(requested=2,valid=2)
        extra=deepcopy(x['attempts'][0]); extra.update(runId='run-1',backend='gpu'); x['attempts'].append(extra)
        with self.assertRaises(ValueError): batch(x)

    def test_wrong_partial_and_missing_count(self):
        x=sample(); x['partial']=True
        with self.assertRaises(ValueError): batch(x)
        x=sample(); x['valid']=0
        with self.assertRaises(ValueError): batch(x)


class StatisticsTests(unittest.TestCase):
    def test_empty_single_zero(self):
        self.assertIsNone(stats([],0)['mean'])
        zero=stats([0],0)
        self.assertEqual(zero['n'],1); self.assertEqual(zero['mean'],0)
        self.assertIsNone(zero['sampleSd']); self.assertIsNone(zero['meanCi'])
        self.assertEqual(zero['cutSuccess'],0)

    def test_independent_closed_form_fixture(self):
        s=stats([0,1,2,3,4],2)
        self.assertEqual(s['mean'],2); self.assertEqual(s['sampleSd'],math.sqrt(2.5))
        self.assertEqual((s['median'],s['p5'],s['p95']),(2,.2,3.8))
        self.assertEqual(s['cutSuccess'],.4)

    def test_large_damage_variance_does_not_cancel(self):
        base=2**60; s=stats([base,base+1,base+2],base)
        self.assertEqual(s['meanExact'],str(base+1)); self.assertEqual(s['sampleSd'],1)

    def test_nonfinite_missing_not_zero(self):
        for bad in (None,True,float('nan'),float('inf')):
            with self.assertRaises(ValueError): stats([bad],0)

    def test_wilson_extremes_not_zero_width(self):
        a=stats([0]*10,0)['cutCi']; b=stats([1]*10,0)['cutCi']
        self.assertAlmostEqual(a[0],0); self.assertGreater(a[1],0)
        self.assertLess(b[0],1); self.assertAlmostEqual(b[1],1)

    def test_team_quantile_not_sum_of_member_quantiles(self):
        a,b=[0,100],[100,0]
        team=stats([x+y for x,y in zip(a,b)],0)['p95']
        self.assertEqual(team,100); self.assertNotEqual(team,stats(a,0)['p95']+stats(b,0)['p95'])

    def test_identical_small_sample_is_not_equivalence(self):
        r=equivalent([0,1],[0,1],bounds=(0,1),mean_margin=.01)
        self.assertEqual(r['verdict'],'inconclusive_or_outside_margin')

    def test_equivalence_bounds_and_shift_rejection(self):
        a=[0,1]*10000
        good=equivalent(a,a,bounds=(0,1),mean_margin=.05)
        self.assertEqual(good['verdict'],'equivalent_within_declared_bounds')
        bad=equivalent([0]*20000,[1]*20000,bounds=(0,1),mean_margin=.05)
        self.assertEqual(bad['verdict'],'inconclusive_or_outside_margin')
        with self.assertRaises(ValueError): equivalent([0,2],[0,1],bounds=(0,1),mean_margin=.05)


class PortableTests(unittest.TestCase):
    def test_schema_only_is_never_product_acceptance(self):
        self.assertEqual(portable(portable_record()),'synthetic_schema_only')

    def test_missing_metric_has_reason_and_busy_window_rejected(self):
        x=portable_record(); x['measurements'][0]['allocatedBytes']['reason']=None
        with self.assertRaises(ValueError): portable(x)
        x=portable_record(); x['measurements'][0]['exclusiveBenchmarkWindow']=False
        with self.assertRaises(ValueError): portable(x)

    def test_missing_commit_or_false_throughput_rejected(self):
        x=portable_record(); x['productCommit']=''
        with self.assertRaises(ValueError): portable(x)
        x=portable_record(); x['measurements'][0]['validRuns']=1001
        with self.assertRaises(ValueError): portable(x)


class EngineAndOlTests(unittest.TestCase):
    def test_exact_order_rounding_rng_and_state(self):
        before=dict(comparisonMode='controlled_test_only',inputBeforeHash='fixed-input',inputAfterHash='fixed-input',
                    teamDamage=196000,memberDamage=[196000],shots=1,hits=1,crits=0,reloads=0,bursts=1,
                    remainingAmmo=5,eventOrder=['hit','gauge','cast'],randomCalls=2)
        exact_engine(before,deepcopy(before))
        for field,value in [('teamDamage',195999),('eventOrder',['cast','hit','gauge']),('randomCalls',3),('inputAfterHash','changed')]:
            after=deepcopy(before); after[field]=value
            with self.assertRaises(ValueError): exact_engine(before,after)

    def test_holdout_and_uncertain_OL(self):
        record=dict(originalBeforeHash='unchanged',originalAfterHash='unchanged',fullCombatRerun=True,pairedSeeds=False,
                    searchRunIds=['s'],baselineFinalRunIds=['b'],candidateFinalRunIds=['c'],
                    independentDifferenceCi=[-1,2],verdict='inconclusive',gameVerified=False,costEfficiency=None)
        ol_holdout(record)
        for field,value in [('candidateFinalRunIds',['s']),('verdict','winner'),('pairedSeeds',True),('fullCombatRerun',False),('costEfficiency',1),('originalAfterHash','edited')]:
            bad=deepcopy(record); bad[field]=value
            with self.assertRaises(ValueError): ol_holdout(bad)
        for interval,verdict in [([1,2],'improved'),([-2,-1],'worse'),([0,1],'inconclusive')]:
            good=deepcopy(record);good.update(independentDifferenceCi=interval,verdict=verdict)
            ol_holdout(good)


class CliTests(unittest.TestCase):
    def test_real_cli_preserves_input_and_does_not_claim_acceptance(self):
        from test_backend_v1 import pages
        root=Path(__file__).resolve().parents[2]
        run=root/'artifacts/single-deck-qa'/('cli-fixture-'+uuid.uuid4().hex)
        run.mkdir(parents=True)
        for kind,document,expected in [('portable',portable_record(),0),('batch',dict(sample(),cutoff=0),0),('batch',{},2),('backend-results-v1',pages(),0)]:
            path=run/(uuid.uuid4().hex+'.json')
            raw=json.dumps(document).encode('utf-8');path.write_bytes(raw)
            process=subprocess.run([sys.executable,str(Path(__file__).with_name('check_evidence.py')),str(path),'--kind',kind],
                                   cwd=root,capture_output=True,text=True,encoding='utf-8',timeout=30)
            self.assertEqual(process.returncode,expected,process.stderr)
            self.assertEqual(path.read_bytes(),raw)
            result=json.loads(process.stdout)
            self.assertEqual(result['productAcceptance'],'not_evaluated')
            self.assertTrue(Path(result['artifact']).resolve().is_relative_to((root/'artifacts/single-deck-qa').resolve()))


if __name__ == '__main__':
    root=Path(__file__).resolve().parents[2]
    run=root/'artifacts/single-deck-qa'/('oracle-'+uuid.uuid4().hex)
    run.mkdir(parents=True)
    output=io.StringIO()
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__)),
                              unittest.defaultTestLoader.loadTestsFromModule(__import__('test_backend_v1')),
                              unittest.defaultTestLoader.loadTestsFromModule(__import__('test_actual_statistics'))])
    result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    (run/'tests.log').write_text(output.getvalue(),encoding='utf-8')
    report=dict(evidence='synthetic_QA_oracle_self_tests',productAcceptance='not_evaluated',
                commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
                tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful())
    (run/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(report,artifact=str(run)),ensure_ascii=True))
    raise SystemExit(0 if result.wasSuccessful() else 1)

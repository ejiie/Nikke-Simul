"""Read-only report of calibration/admission and any completed 10K blocks. No engine calls."""
import argparse,json
from pathlib import Path
from public_fixture import read,digest

p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();run=a.run
pr=read(run/'preregistration.json');summary=read(run/'summary.json');decision=read(run/'admission.json');harness=read(run/'harness-summary.json')
assert pr['order']==[4,8,15] and pr['runsPerBlock']==10000 and pr['warmupPerBlock']==64 and pr['calibrationPerWorker']==128
assert summary['preserved'] and summary['inputFileUnchanged'] and harness['activeAfter']==0
calibrations=[];main=[];allIds=set()
for index,w in enumerate(pr['order']):
    id=f'calibration-w{w}';t=read(run/(id+'-timing.json'));audit=read(run/(id+'-independent-audit.json'));rows=read(run/(id+'-rows.json'))
    assert audit['passed'] and len(rows)==128 and audit['valid']==128 and t['checksum']==digest(run/(id+'-rows.json'))
    for r in rows:assert r['runId'] not in allIds;allIds.add(r['runId'])
    calibrations.append(dict(worker=w,n=128,kind='calibration_excluded_from_10000',timing=t,statistics=audit['statistics'],qaObservations=audit['qaObservations'],normalZero=audit['normalZero'],predicted10000Seconds=t['timing']['wallSeconds']/128*10000))
    block=f'block-{index+1}-w{w}'
    if (run/(block+'-independent-audit.json')).exists():
        b=read(run/(block+'-independent-audit.json'));main.append(dict(worker=w,completed=b['valid'],audit=b,timing=read(run/(block+'-timing.json'))))
    else:main.append(dict(worker=w,requestedPlan=10000,completed=0,state='not_started_admission_denied' if not decision['allowed'] else 'not_completed',actualSeconds=None,statistics=None))
if not decision['allowed']:
    assert not list(run.glob('block-*-rows.json')) and harness['status']=='admission_denied' and harness['blocks']==[]
ts=[json.loads(x) for x in (run/'telemetry.jsonl').read_text(encoding='utf-8').splitlines()]
out=dict(status=summary['status'],product=pr['product'],qaBase=pr['qaBase'],startedAt=summary['startedAt'],endedAt=summary['endedAt'],calibrations=calibrations,main=main,admission=decision,
    preparation=read(run/'preparation.json'),powerBefore=read(run/'environment-before.json'),powerAfter=read(run/'environment-after.json'),
    telemetry=dict(samples=len(ts),maxGap=max(x['intervalSeconds'] or 0 for x in ts),maxSystemCpu=max(x['systemCpuPercent'] or 0 for x in ts),maxExternalCpu=max(x['externalSystemCpuPercent'] for x in ts),minimumAvailableMemory=min(x['availablePhysical'] for x in ts),minimumDiskFree=min(x['diskFreeBytes'] for x in ts),externalComputeObservations=sum(bool(x['externalCompute']) for x in ts),unreadableProcessRange=[min(x['unreadableProcesses'] for x in ts),max(x['unreadableProcesses'] for x in ts)]),
    checks=dict(allCalibrationResultsIndependentlyAudited=True,calibrationUniqueIds=len(allIds),mainStarted=bool(harness['blocks']),activeAfter=harness['activeAfter'],inputPreserved=harness['inputUnchanged'],sourceAndLockPreserved=summary['preserved']),
    performanceRank='unconfirmed_single_measurement_per_candidate',distributionEquivalence='not_evaluated_bounds_margins_not_preregistered',
    unavailable=pr['missingMetrics'],artifactHashes={f.name:digest(f) for f in run.glob('*.json') if f.name!='final-audit.json'})
(run/'final-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(status=out['status'],calibration=[dict(worker=c['worker'],seconds=c['timing']['timing']['wallSeconds'],maxActive=c['timing']['timing']['maxActive'],cpuSeconds=c['timing']['timing']['cpuSeconds'],mean=c['statistics']['team']['mean'],sd=c['statistics']['team']['sampleSd'],median=c['statistics']['team']['median'],p5=c['statistics']['team']['p5'],p95=c['statistics']['team']['p95'],meanCi=c['statistics']['team']['meanCi'],cut=c['statistics']['team']['cutSuccess'],cutCi=c['statistics']['team']['cutCi'],observations=c['qaObservations']['team'],predicted10000Seconds=c['predicted10000Seconds']) for c in calibrations],admission=decision,telemetry=out['telemetry']),ensure_ascii=False,indent=2))

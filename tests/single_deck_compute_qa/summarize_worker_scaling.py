"""Read-only post-run scope/concurrency/warmup audit and descriptive scaling table."""
import argparse,json,statistics
from pathlib import Path
from datetime import datetime
from public_fixture import read,digest
from backend_v1 import results

p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();run=a.run
pr=read(run/'preregistration.json');summary=read(run/'summary.json');harness=read(run/'harness-summary.json')
assert summary['status']=='passed_six_block_harness_only' and harness['status']=='completed' and harness['activeAfter']==0
assert summary['preserved'] and summary['inputFileUnchanged'] and harness['inputUnchanged']
telemetry=[json.loads(x) for x in (run/'telemetry.jsonl').read_text(encoding='utf-8').splitlines()]
allIds=set();blocks=[]
for i,w in enumerate(pr['order']):
    id=f'block-{i+1}-w{w}';b=read(run/(id+'-batch.json'));audit=read(run/(id+'-independent-audit.json'));timing=read(run/(id+'-timing.json'));t=timing['timing'];rows=read(run/(id+'-rows.json'))
    assert audit['passed'] and len(rows)==1000 and b['valid']==1000 and b['failed']==b['cancelled']==0 and not b['partial']
    assert t['workers']==w and t['activeAfter']==0 and t['maxActive']<=w
    assert timing['checksum']==digest(run/(id+'-rows.json'))
    for r in rows:assert r['runId'] not in allIds;allIds.add(r['runId'])
    warmId=id+'-warmup';warm=read(run/(warmId+'-rows.json'));warmTiming=read(run/(warmId+'-timing.json'))
    wb=dict(b,id=warmId,requested=32,valid=32);results([dict(batch=wb,offset=0,limit=1000,runs=warm)])
    assert len(warm)==32 and warmTiming['checksum']==digest(run/(warmId+'-rows.json'))
    for r in warm:assert r['runId'] not in allIds;allIds.add(r['runId'])
    start,end=(datetime.fromisoformat(t[k]).timestamp() for k in ('startedAt','endedAt'));samples=[s for s in telemetry if start<=s['epoch']<=end]
    own=[x for s in samples for x in s['processes'] if x['pid']==summary['pid']]
    blocks.append(dict(ordinal=i+1,id=id,workers=w,actualMaxActive=t['maxActive'],n=1000,failed=0,cancelled=0,normalZero=audit['normalZero'],seconds=t['wallSeconds'],runsPerSecond=t['runsPerSecond'],cpuSeconds=t['cpuSeconds'],
        warmupSeconds=warmTiming['timing']['wallSeconds'],outputSeconds=timing['outputSeconds'],productAnalysisAndValidationSeconds=read(run/(id+'-audit-cost.json'))['seconds'],independentAuditSeconds=audit['independentAuditSeconds'],
        checksum=timing['checksum'],start=t['startedAt'],end=t['endedAt'],team=audit['statistics']['team'],members=audit['statistics']['members'],
        telemetry=dict(samples=len(samples),batteryFirst=samples[0]['batteryPercent'] if samples else None,batteryLast=samples[-1]['batteryPercent'] if samples else None,
            maxExternalCpu=max((s['externalSystemCpuPercent'] for s in samples),default=None),sampledPeakPrivateBytes=max((x.get('privateBytes',0) for x in own),default=None),
            lifetimePeakWorkingSet=t['lifetimePeakWorkingSet'],workingSetAtEnd=t['workingSet'],privateBytesAtEnd=t['privateBytes'])))
assert len(allIds)==6192
groups=[]
for w in (2,4,8):
    seconds=[b['seconds'] for b in blocks if b['workers']==w];mean=statistics.mean(seconds)
    groups.append(dict(workers=w,seconds=seconds,meanSeconds=mean,rangeOverMeanPercent=100*(max(seconds)-min(seconds))/mean))
forward=min(blocks[:3],key=lambda x:x['seconds'])['workers'];reverse=min(blocks[3:],key=lambda x:x['seconds'])['workers']
largeSpread=any(g['rangeOverMeanPercent']>10 for g in groups)
verdict='superiority_unconfirmed_order_or_variation' if largeSpread or forward!=reverse else 'same_observed_fastest_in_this_battery_window_only'
out=dict(status='six_blocks_and_excluded_warmups_audited',scope=pr['scope'],startedAt=summary['startedAt'],endedAt=summary['endedAt'],preparation=read(run/'preparation.json'),
    blocks=blocks,groups=groups,forwardFastest=forward,reverseFastest=reverse,largeSpreadOver10Percent=largeSpread,verdict=verdict,distributionEquivalence='not_evaluated_no_preregistered_bounds_margins',
    actualApiPolicy='unchanged_cpu_policy_3_plan_1_2',hardwareMaximum='not_tested_8_is_not_hardware_maximum',
    batteryStart=read(run/'environment-before.json')['batteryPercent'],batteryEnd=read(run/'environment-after.json')['batteryPercent'],
    telemetry=dict(samples=len(telemetry),powerStable=all(s['ac']==0 and s['powerScheme']==pr['guards']['powerScheme'] and s['desktop']=='Default' for s in telemetry),
        maxGap=max(s['intervalSeconds'] or 0 for s in telemetry),minimumAvailableMemory=min(s['availablePhysical'] for s in telemetry),minimumDiskFree=min(s['diskFreeBytes'] for s in telemetry),
        maximumExternalCpu=max(s['externalSystemCpuPercent'] for s in telemetry),externalComputeObservations=sum(bool(s['externalCompute']) for s in telemetry),
        unreadableProcessesRange=[min(s['unreadableProcesses'] for s in telemetry),max(s['unreadableProcesses'] for s in telemetry)]),
    missingMetrics=pr['missingMetrics'],checks=dict(all6000IndependentlyAudited=True,all192WarmupsExcludedAndValidated=True,allUniqueRunIds=True,inputAndLockPreserved=summary['preserved'],sixBlockOrder=pr['order'],noRemainingCalls=harness['activeAfter']==0),
    evidenceHashes={f.name:digest(f) for f in sorted(run.glob('*.json')) if f.name!='final-audit.json'})
(run/'final-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(verdict=verdict,groups=groups,battery=[out['batteryStart'],out['batteryEnd']],telemetry=out['telemetry'],blocks=[{k:b[k] for k in ('ordinal','workers','actualMaxActive','seconds','runsPerSecond','cpuSeconds','warmupSeconds','outputSeconds')} for b in blocks]),ensure_ascii=False,indent=2))

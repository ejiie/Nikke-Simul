"""Battery-window supervisor and independent audit for the QA-only 2/4/8 engine harness."""
import argparse,json,os,subprocess,threading,time,uuid
from pathlib import Path
from datetime import datetime
from copy import deepcopy
from public_fixture import read,digest
from win_telemetry import Sampler,environment
from actual_stats import metric
from backend_v1 import results
from oracle import stats as independent_stats

ROOT=Path(__file__).resolve().parents[2]
DEADLINE=datetime.fromisoformat('2026-09-18T10:58:00+09:00').timestamp()
SCHEME='ab6534a3-bc02-4c44-94d1-a8535b2eb070'
ORCA='C:/Users/user/AppData/Local/Programs/orca/resources/bin/orca.exe'
FLAGS=getattr(subprocess,'CREATE_NO_WINDOW',0)
def now():return datetime.now().astimezone().isoformat()
def main():
    global DEADLINE
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--dotnet',required=True);p.add_argument('--mode',choices=['scale','cpu-10k'],default='scale');a=p.parse_args()
    tenK=a.mode=='cpu-10k';deadlineText='2026-09-18T11:40:00+09:00' if tenK else '2026-09-18T10:58:00+09:00';DEADLINE=datetime.fromisoformat(deadlineText).timestamp()
    assert time.time()<DEADLINE-180
    run=ROOT/'artifacts/single-deck-qa'/(('worker-10k-' if tenK else 'worker-scale-')+uuid.uuid4().hex[:12]);run.mkdir(parents=True);print(run,flush=True)
    def save(name,v):
        target=run/(name+'.json');temporary=run/(name+'.tmp');temporary.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(target)
    original=a.fixture/'prepared-synthetic.json';originalHash=digest(original);obj=read(original);pilot=deepcopy(obj);pilot['input']['phase']='pilot';save('prepared-pilot',pilot)
    assert {k:v for k,v in obj.items() if k!='input'}=={k:v for k,v in pilot.items() if k!='input'}
    baseline=environment();save('environment-before',baseline)
    assert baseline['ac']==0 and baseline['powerScheme']==SCHEME and baseline['desktop']=='Default' and baseline['batteryPercent']>30
    memoryLimit=baseline['totalPhysical']//4;assert memoryLimit>=(15 if tenK else 8)*64*1024**2
    order=[4,8,15] if tenK else [2,4,8,8,4,2];count=10000 if tenK else 1000;ids=[f'block-{i+1}-w{w}' for i,w in enumerate(order)]
    save('preregistration',dict(at=now(),deadline=deadlineText,qaBase='8871f3860c1d97411a8beba610e933584016654c' if tenK else '4c0c06ae0847c0464e35df08533aef1105092b21',product='40078d06a3d236ec7de5987d6be3c96d2a34ec86',order=order,runsPerBlock=count,warmupPerBlock=64 if tenK else 32,calibrationPerWorker=128 if tenK else 0,smokeRuns=0 if tenK else 64,fixedCut=855466067 if tenK else None,
        scope='PreparedCompute summary + QA Parallel.ForEachAsync; no API SQLite UI policy or cache',memoryLimit=memoryLimit,
        memoryRule='physical/4, same conservative default reference; at least 64MiB per requested worker',
        inputHash=digest(run/'prepared-pilot.json'),sourcePreparedHash=originalHash,input=pilot['input'],
        timeAdmission='sum(each calibration wall/128*10064)*1.5+180 < remaining; projected battery >=35 using max(current observed,5/284.6 %p per second)' if tenK else 'smoke wall/64 *6192 *1.5 +180 < remaining; no reduction or repeat selection',
        guards=dict(batteryStop=30,ac=0,powerScheme=SCHEME,desktop='Default',gapSeconds=20,availablePhysicalMin=256*1024**2,diskMin=1024**3,externalCpuHostPercent=35,externalCpuConsecutive5sSamples=3,externalComputeCores=.10,externalComputeConsecutive5sSamples=2),
        winnerRule='one performance observation per worker; no rank confirmation; damage N is not performance replicate N' if tenK else 'report both repetitions; if directional order winners differ or spread>10%, superiority unconfirmed; no equivalence claim without preregistered bounds',
        missingMetrics={k:dict(value=None,reason=v) for k,v in dict(GC='no runtime exporter',allocations='no allocation profiler',temperature='no sensor collector',UI='not in harness').items()}))
    prior=read(a.fixture/'final-audit.json');save('source-fixed-fingerprints',prior['fixedFingerprints'])
    lockBefore=digest(ROOT/'package-lock.json')
    def orca():
        states=[]
        for name in ('Backend','UI','덱-육성-최적화-및-통계-담당','시뮬레이션-엔진-담당'):
            raw=subprocess.check_output([ORCA,'terminal','list','--worktree','path:'+str(ROOT.parent/name),'--json'],creationflags=FLAGS,timeout=10)
            response=json.loads(raw);assert response['ok'];states.append(dict(name=name,terminals=[t['handle'] for t in response['result']['terminals']]))
        return states
    states=orca();save('orca-before',states);assert all(not x['terminals'] for x in states)
    sampler=Sampler();pre=sampler.sample(storage=run);save('host-before',pre)
    computeNames={'dotnet.exe','python.exe','pythonw.exe','msbuild.exe','testhost.exe','vstest.console.exe'}
    assert not [x for x in pre['processes'] if x['pid']!=os.getpid() and x['name'].lower() in computeNames]
    dll=ROOT/'tests/single_deck_compute_qa/ScaleProbe/bin/Release/net10.0/ScaleProbe.dll'
    currentHashes={f.name:digest(f) for f in dll.parent.glob('Nikke.*.dll')};save('build-hashes',currentHashes)
    priorHashes=read(a.fixture/'build-hashes.json')
    assert all(priorHashes.get(name)==value for name,value in currentHashes.items()),'product DLL mismatch from accepted load baseline'
    samples=[];audits=[];reason=None;done=threading.Event();process=None
    def stop(why):
        nonlocal reason
        if reason:return
        reason=why;save('stop',dict(at=now(),reason=why));print('STOP '+why,flush=True)
    def monitor():
        previous=time.monotonic();nextSample=0;outside=0;otherCompute=0
        try:
            while not done.wait(1):
                t=time.monotonic();gap=t-previous;previous=t;e=environment()
                why='deadline' if time.time()>=DEADLINE else 'monitor_gap' if gap>20 else 'battery' if e['batteryPercent'] is None or e['batteryPercent']<=30 else 'power_changed' if e['ac']!=0 or e['powerScheme']!=SCHEME or e['batterySaver']!=baseline['batterySaver'] else 'locked_or_unavailable_desktop' if e['desktop']!='Default' else None
                if why:stop(why)
                if t>=nextSample:
                    s=sampler.sample(process.pid,run);s['at']=now();own=next((x for x in s['processes'] if x['pid']==process.pid),{})
                    s['externalSystemCpuPercent']=max(0,(s['systemCpuPercent'] or 0)-100*(own.get('cpuCores') or 0)/s['logicalProcessors'])
                    external=[x for x in s['processes'] if x['pid'] not in (os.getpid(),process.pid) and x['name'].lower() in computeNames and (x['cpuCores'] or 0)>.10]
                    s['externalCompute']=external;outside=outside+1 if s['externalSystemCpuPercent']>35 else 0;otherCompute=otherCompute+1 if external else 0
                    samples.append(s)
                    with (run/'telemetry.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(s,ensure_ascii=False)+'\n')
                    if outside>=3 or otherCompute>=2:stop('sustained_competing_load')
                    if s['availablePhysical']<256*1024**2 or own.get('privateBytes',0)>memoryLimit:stop('memory_guard')
                    if s['diskFreeBytes']<1024**3:stop('disk_guard')
                    nextSample=t+5
        except Exception as ex:stop('telemetry_error:'+repr(ex))
    start=now();exitCode=None;error=None
    def audit_batch(id,expected):
        started=time.perf_counter();batch=read(run/(id+'-batch.json'));rows=[r for r in read(run/(id+'-rows.json')) if r is not None]
        pages=[dict(batch=batch,offset=i,limit=1000,runs=rows[i:i+1000]) for i in range(0,max(1,len(rows)),1000)];results(pages)
        assert len(rows)==expected and [r['index'] for r in rows]==list(range(expected))
        st=read(run/(id+'-statistics.json'));cut=855466067 if tenK else None;values=[r['teamDamage'] for r in rows];metric(st['team'],values,cut)
        extra={}
        def describe(key,v):
            oracle=independent_stats(v,855466067);extra[key]=dict(observedMin=min(v),observedMax=max(v),qaFixedCut=855466067,strictCutProbability=oracle['cutSuccess'],wilson95=oracle['cutCi'],quantileCi=None,sampleSdCi=None,unavailableReason='product does not implement quantile or SD confidence intervals')
        describe('team',values)
        for member in batch['input']['characterIds']:
            v=[next(m['damage'] for m in r['members'] if m['characterId']==member) for r in rows];metric(st['members'][member],v);describe(member,v)
        timing=read(run/(id+'-timing.json'));assert timing['timing']['activeAfter']==0 and timing['timing']['maxActive']<=batch['execution']['workers']
        assert timing['checksum']==digest(run/(id+'-rows.json'))
        audit=dict(id=id,valid=len(rows),normalZero=sum(r['teamDamage']==0 for r in rows),statistics=st,qaObservations=extra,independentAuditSeconds=time.perf_counter()-started,passed=True)
        save(id+'-independent-audit',audit);return timing
    with (run/'harness.log').open('w',encoding='utf-8') as log:
      try:
        process=subprocess.Popen([a.dotnet,str(dll),str(run),str(run/'prepared-pilot.json'),str(memoryLimit)]+(['cpu-10k'] if tenK else []),cwd=ROOT,stdout=log,stderr=log,creationflags=FLAGS)
        watcher=threading.Thread(target=monitor,daemon=True);watcher.start();seen=set()
        while process.poll() is None:
            if tenK and (run/'calibration.ready').exists() and not (run/'admission.json').exists():
                cal=read(run/'calibrations.json')
                for item in cal:audit_batch(item['id'],128)
                expected=sum(x['seconds']/128*10064 for x in cal);conservative=expected*1.5+180;remaining=DEADLINE-time.time();current=environment();elapsed=time.time()-datetime.fromisoformat(start).timestamp()
                observed=max(0,baseline['batteryPercent']-current['batteryPercent'])/max(elapsed,1);rate=max(observed,5/284.6);projected=current['batteryPercent']-rate*conservative
                decision=dict(at=now(),calibrations=cal,expectedSeconds=expected,conservativeSeconds=conservative,remainingSeconds=remaining,batteryStart=baseline['batteryPercent'],batteryNow=current['batteryPercent'],observedDrainPercentagePointsPerSecond=observed,historicalDrainPercentagePointsPerSecond=5/284.6,usedDrainPercentagePointsPerSecond=rate,projectedEndBattery=projected,requiredStartingBattery=35+rate*conservative,timeAccepted=conservative<remaining,batteryAccepted=projected>=35,allowed=conservative<remaining and projected>=35 and reason is None)
                save('admission',decision);print('ADMISSION '+json.dumps(decision),flush=True)
            for id in ids:
                if id in seen or not (run/(id+'.ready')).exists():continue
                timing=audit_batch(id,count);audits.append(dict(id=id,passed=True));save('audit-progress',audits)
                seen.add(id);(run/(id+'.ack')).write_text('passed',encoding='utf-8');print(id+' independent PASS '+str(timing['timing']['wallSeconds'])+'s',flush=True)
            time.sleep(.2)
        exitCode=process.returncode
      except Exception as ex:
        error=repr(ex);stop('independent_audit_error:'+error)
        # Cooperative frame cancellation, no foreign process termination.
        if process:
            try:exitCode=process.wait(timeout=30)
            except subprocess.TimeoutExpired:error+='; own harness did not exit within30s; cancellation file remains'
      finally:
        done.set()
        if 'watcher' in locals():watcher.join(timeout=12)
        after=environment();save('environment-after',after);save('orca-after',orca())
        preserved=originalHash==digest(original) and lockBefore==digest(ROOT/'package-lock.json')
        denied=tenK and (run/'admission.json').exists() and not read(run/'admission.json')['allowed'] and exitCode==0
        summary=dict(startedAt=start,endedAt=now(),pid=None if process is None else process.pid,exitCode=exitCode,reason=reason,error=error,audits=audits,telemetrySamples=len(samples),
            preserved=preserved,inputFileUnchanged=digest(run/'prepared-pilot.json')==read(run/'preregistration.json')['inputHash'],
            status='calibration_only_admission_denied' if denied and preserved and reason is None else ('passed_10k_three_blocks' if tenK else 'passed_six_block_harness_only') if len(audits)==len(order) and exitCode==0 and reason is None and preserved else 'incomplete_or_failed')
        save('summary',summary);print('FINAL '+summary['status']+' '+str(run),flush=True)
    return 0 if summary['status'] in ('passed_six_block_harness_only','passed_10k_three_blocks','calibration_only_admission_denied') else 1
if __name__=='__main__':raise SystemExit(main())

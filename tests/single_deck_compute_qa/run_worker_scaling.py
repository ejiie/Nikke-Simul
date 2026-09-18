"""Battery-window supervisor and independent audit for the QA-only 2/4/8 engine harness."""
import argparse,json,os,subprocess,threading,time,uuid
from pathlib import Path
from datetime import datetime
from copy import deepcopy
from public_fixture import read,digest
from win_telemetry import Sampler,environment
from actual_stats import metric
from backend_v1 import results

ROOT=Path(__file__).resolve().parents[2]
DEADLINE=datetime.fromisoformat('2026-09-18T10:58:00+09:00').timestamp()
SCHEME='ab6534a3-bc02-4c44-94d1-a8535b2eb070'
ORCA='C:/Users/user/AppData/Local/Programs/orca/resources/bin/orca.exe'
FLAGS=getattr(subprocess,'CREATE_NO_WINDOW',0)
def now():return datetime.now().astimezone().isoformat()
def main():
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--dotnet',required=True);a=p.parse_args()
    assert time.time()<DEADLINE-180
    run=ROOT/'artifacts/single-deck-qa'/('worker-scale-'+uuid.uuid4().hex[:12]);run.mkdir(parents=True);print(run,flush=True)
    def save(name,v):(run/(name+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
    original=a.fixture/'prepared-synthetic.json';originalHash=digest(original);obj=read(original);pilot=deepcopy(obj);pilot['input']['phase']='pilot';save('prepared-pilot',pilot)
    assert {k:v for k,v in obj.items() if k!='input'}=={k:v for k,v in pilot.items() if k!='input'}
    baseline=environment();save('environment-before',baseline)
    assert baseline['ac']==0 and baseline['powerScheme']==SCHEME and baseline['desktop']=='Default' and baseline['batteryPercent']>30
    memoryLimit=baseline['totalPhysical']//4;assert memoryLimit>=8*64*1024**2
    order=[2,4,8,8,4,2];ids=[f'block-{i+1}-w{w}' for i,w in enumerate(order)]
    save('preregistration',dict(at=now(),deadline='2026-09-18T10:58:00+09:00',qaBase='4c0c06ae0847c0464e35df08533aef1105092b21',product='40078d06a3d236ec7de5987d6be3c96d2a34ec86',order=order,runsPerBlock=1000,warmupPerBlock=32,smokeRuns=64,
        scope='PreparedCompute summary + QA Parallel.ForEachAsync; no API SQLite UI policy or cache',memoryLimit=memoryLimit,
        memoryRule='physical/4, same conservative default reference; at least 64MiB per requested worker',
        inputHash=digest(run/'prepared-pilot.json'),sourcePreparedHash=originalHash,input=pilot['input'],
        timeAdmission='smoke wall/64 *6192 *1.5 +180 < remaining; no reduction or repeat selection',
        guards=dict(batteryStop=30,ac=0,powerScheme=SCHEME,desktop='Default',gapSeconds=20,availablePhysicalMin=256*1024**2,diskMin=1024**3,externalCpuHostPercent=35,externalCpuConsecutive5sSamples=3,externalComputeCores=.10,externalComputeConsecutive5sSamples=2),
        winnerRule='report both repetitions; if directional order winners differ or spread>10%, superiority unconfirmed; no equivalence claim without preregistered bounds',
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
    with (run/'harness.log').open('w',encoding='utf-8') as log:
      try:
        process=subprocess.Popen([a.dotnet,str(dll),str(run),str(run/'prepared-pilot.json'),str(memoryLimit)],cwd=ROOT,stdout=log,stderr=log,creationflags=FLAGS)
        watcher=threading.Thread(target=monitor,daemon=True);watcher.start();seen=set()
        while process.poll() is None:
            for id in ids:
                if id in seen or not (run/(id+'.ready')).exists():continue
                started=time.perf_counter();batch=read(run/(id+'-batch.json'));rows=[r for r in read(run/(id+'-rows.json')) if r is not None]
                results([dict(batch=batch,offset=0,limit=1000,runs=rows)])
                assert len(rows)==1000 and [r['index'] for r in rows]==list(range(1000))
                st=read(run/(id+'-statistics.json'));metric(st['team'],[r['teamDamage'] for r in rows])
                for member in batch['input']['characterIds']:metric(st['members'][member],[next(m['damage'] for m in r['members'] if m['characterId']==member) for r in rows])
                timing=read(run/(id+'-timing.json'));assert timing['timing']['activeAfter']==0 and timing['timing']['maxActive']<=batch['execution']['workers']
                assert timing['checksum']==digest(run/(id+'-rows.json'))
                audit=dict(id=id,valid=len(rows),normalZero=sum(r['teamDamage']==0 for r in rows),statistics=st,independentAuditSeconds=time.perf_counter()-started,passed=True)
                save(id+'-independent-audit',audit);audits.append(dict(id=id,passed=True));save('audit-progress',audits)
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
        summary=dict(startedAt=start,endedAt=now(),pid=None if process is None else process.pid,exitCode=exitCode,reason=reason,error=error,audits=audits,telemetrySamples=len(samples),
            preserved=preserved,inputFileUnchanged=digest(run/'prepared-pilot.json')==read(run/'preregistration.json')['inputHash'],
            status='passed_six_block_harness_only' if len(audits)==6 and exitCode==0 and reason is None and preserved else 'incomplete_or_failed')
        save('summary',summary);print('FINAL '+summary['status']+' '+str(run),flush=True)
    return 0 if summary['status']=='passed_six_block_harness_only' else 1
if __name__=='__main__':raise SystemExit(main())

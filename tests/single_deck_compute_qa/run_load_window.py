"""Authorized battery-only Q-LOAD-1000 window. Never starts more than 1000 pilot runs."""
import argparse,json,os,socket,sqlite3,subprocess,threading,time,urllib.request,uuid,math
from pathlib import Path
from datetime import datetime
from public_fixture import create,digest
from actual_stats import metric
from backend_v1 import results
from win_telemetry import Sampler,environment

ROOT=Path(__file__).resolve().parents[2]
DEADLINE=datetime.fromisoformat('2026-09-18T10:30:00+09:00').timestamp()
SCHEME='ab6534a3-bc02-4c44-94d1-a8535b2eb070'
ORCA='C:/Users/user/AppData/Local/Programs/orca/resources/bin/orca.exe'
NOCONSOLE=getattr(subprocess,'CREATE_NO_WINDOW',0)
def stamp():return datetime.now().astimezone().isoformat()
def main():
    p=argparse.ArgumentParser();p.add_argument('--source-data',type=Path,required=True);p.add_argument('--dotnet',required=True);a=p.parse_args()
    assert time.time()<DEADLINE-180,'authorized window lacks preparation margin'
    run=ROOT/'artifacts/single-deck-qa'/('load1000-'+uuid.uuid4().hex[:12]);data=run/'data';data.mkdir(parents=True)
    def save(name,value):(run/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(run,flush=True)
    report=dict(startedAt=stamp(),status='preparing',product='40078d06a3d236ec7de5987d6be3c96d2a34ec86',qaBase='606b5685c237446616efd909339c58b28508182e',checks=[],distributionAcceptance='not_evaluated_no_preregistered_bounds_margins',finalRecommendation=False)
    policy=dict(deadline='2026-09-18T10:30:00+09:00',batteryMinimumExclusive=30,powerScheme=SCHEME,acRequired=0,maxWorkers=2,calibration=20,pilot=1000,
        cpuGuard='external total system CPU minus own API >35% of host for 3 consecutive 5s samples; external dotnet/msbuild/testhost/vstest/python active >0.10 core for 2 samples; any such process blocks preflight',
        memoryGuard='available physical <256MiB or own private bytes > selected memoryLimitBytes',desktopGuard='OpenInputDesktop unavailable or not Default',gapGuardSeconds=20,
        admission='1.5 * (conservative normal-batch time /20 *1000) + cold overhead +180s < remaining; projected battery >=40%',
        cut='floor(calibration team median), recorded before pilot request',pollSeconds=2,telemetrySeconds=5,watchdogSeconds=1,
        missingMetrics=dict(allocations='no allocation profiler',GC='no runtime exporter',temperature='no sensor collector',UI_p95='API only; no browser'))
    save('preregistration',policy);lockHash=digest(ROOT/'package-lock.json')
    hashes,game,snapshot,ids=create(a.source_data,data);save('source-hashes-before',hashes)
    def orca_state():
        states=[]
        for name in ('Backend','UI','덱-육성-최적화-및-통계-담당','시뮬레이션-엔진-담당'):
            raw=subprocess.check_output([ORCA,'terminal','list','--worktree','path:'+str(ROOT.parent/name),'--json'],creationflags=NOCONSOLE,timeout=10)
            obj=json.loads(raw);assert obj['ok'];terms=obj['result']['terminals'];states.append(dict(worktree=name,terminals=[dict(handle=t['handle'],connected=t.get('connected')) for t in terms]))
        return states
    states=orca_state();save('orca-preflight',states);assert all(not s['terminals'] for s in states),'other owner terminal became active'
    baseline=environment();save('power-before',baseline)
    assert baseline['ac']==0 and baseline['powerScheme']==SCHEME and baseline['desktop']=='Default' and baseline['batteryPercent']>30
    sampler=Sampler();pre=sampler.sample(storage=data);save('host-before',pre)
    benchmark={'dotnet.exe','msbuild.exe','testhost.exe','vstest.console.exe','python.exe','pythonw.exe'}
    assert not [x for x in pre['processes'] if x['pid']!=os.getpid() and x['name'].lower() in benchmark],'preexisting compute process'
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    assert port not in (5180,5181)
    env=dict(os.environ,NIKKE_PROJECT_ROOT=str(ROOT),NIKKE_DATA_ROOT=str(data),NIKKE_PORT=str(port),NIKKE_TEST_FIXTURE='1');env.pop('NIKKE_GAME_CATALOG',None)
    process=None;token='';active=None;reason=None;latencies=[];done=threading.Event();samples=[];memoryLimit=None
    def call(path,payload=None,method=None):
        start=time.perf_counter();req=urllib.request.Request(f'http://127.0.0.1:{port}/api/'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Nikke-Token':token},method=method)
        with urllib.request.urlopen(req,timeout=10) as res:ret=json.load(res)
        latencies.append(dict(path=path,ms=1000*(time.perf_counter()-start),at=stamp()));return ret
    def stop_for(why):
        nonlocal reason
        if reason:return
        reason=why;save('stop',dict(reason=why,at=stamp(),active=active));print('STOP '+why,flush=True)
        if active:
            try:save('cancel-response',call(f'compute/experiments/{active}/cancel',{}))
            except Exception as ex:save('cancel-error',dict(error=repr(ex)))
    def monitor():
        last=time.monotonic();nextSample=0;outside=0;compute=0
        try:
            while not done.wait(1):
                now=time.monotonic();gap=now-last;last=now;e=environment()
                why=('window_end' if time.time()>=DEADLINE else 'suspend_or_monitor_gap' if gap>20 else 'battery_low_or_unknown' if e['batteryPercent'] is None or e['batteryPercent']<=30 else 'power_changed' if e['ac']!=0 or e['powerScheme']!=SCHEME or e['batterySaver']!=baseline['batterySaver'] else 'locked_or_input_desktop_unavailable' if e['desktop']!='Default' else None)
                if why:stop_for(why)
                if now>=nextSample:
                    sample=sampler.sample(process.pid,data/'compute');sample['at']=stamp();sample['active']=active
                    own=next((x for x in sample['processes'] if x['pid']==process.pid),{})
                    outsideCpu=max(0,(sample['systemCpuPercent'] or 0)-100*(own.get('cpuCores') or 0)/sample['logicalProcessors'])
                    sample['externalSystemCpuPercent']=outsideCpu
                    external=[x for x in sample['processes'] if x['pid'] not in (process.pid,os.getpid()) and x['name'].lower() in benchmark and (x['cpuCores'] or 0)>.10]
                    outside=outside+1 if outsideCpu>35 else 0;compute=compute+1 if external else 0
                    sample['externalCompute']=external;samples.append(sample)
                    with (run/'telemetry.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(sample,ensure_ascii=False)+'\n')
                    if outside>=3 or compute>=2:stop_for('sustained_competing_load')
                    if sample['availablePhysical']<256*1024**2 or (memoryLimit and own.get('privateBytes',0)>memoryLimit):stop_for('qa_memory_guard')
                    if sample['diskFreeBytes']<1024**3:stop_for('disk_free_under_1GiB')
                    nextSample=now+5
        except Exception as ex:stop_for('telemetry_error:'+repr(ex))
    def run_batch(label,request):
        nonlocal active,memoryLimit
        if reason:raise RuntimeError(reason)
        before=time.time();b=call('compute/experiments',request);active=b['id'];save(label+'-created',b);obs=[];firstRunning=None;lastQueued=None
        while True:
            if reason:call(f'compute/experiments/{active}/cancel',{})
            s=call('compute/experiments/'+active);now=time.time();memoryLimit=s['execution']['memoryLimitBytes'];obs.append(dict(epoch=now,status=s))
            with (run/(label+'-status.jsonl')).open('a',encoding='utf-8') as f:f.write(json.dumps(obs[-1])+'\n')
            if s['state']=='running' and firstRunning is None:firstRunning=now
            if s['state']=='queued':lastQueued=now
            if s['failed'] or s.get('errorCode') not in (None,'cancelled'):stop_for('batch_result_error')
            if s['state'] in ('completed','cancelled','failed'):break
            if len(obs)%5==0:print(label+f": {s['valid']}/{s['requested']} {s['state']}",flush=True)
            time.sleep(2)
        finished=time.time();active=None
        timing=dict(startEpoch=before,endEpoch=finished,wallSeconds=finished-before,createSeconds=obs[0]['epoch']-before,firstRunningEpoch=firstRunning,lastQueuedEpoch=lastQueued,normalObservedSeconds=None if firstRunning is None else finished-firstRunning,
            preparationMs=(s['execution'].get('tuning') or {}).get('preparationMilliseconds'),tuning=(s['execution'].get('tuning') or {}))
        save(label+'-timing',timing);save(label+'-final',s)
        return s,timing
    def audit(label,s,cut):
        pages=[call(f"compute/experiments/{s['id']}/results?offset={i}&limit=100") for i in range(0,max(1,s['valid']),100)]
        save(label+'-pages',pages);results(pages);rows=[r for page in pages for r in page['runs']]
        assert [r['index'] for r in rows]==list(range(s['valid'])) if s['state']=='completed' else True
        assert all(r['attempt']==1 for r in rows)
        stats=call(f"compute/experiments/{s['id']}/statistics?cut={cut}");save(label+'-statistics',stats)
        metric(stats['team'],[r['teamDamage'] for r in rows],cut)
        for member in ids:metric(stats['members'][member],[next(m['damage'] for m in r['members'] if m['characterId']==member) for r in rows])
        assert stats['partial']==(len(rows)<s['requested'])
        with sqlite3.connect(data/'compute/batches.db') as db:
            stored=db.execute('SELECT idx,attempt,payload,error FROM batch_runs WHERE batch=? ORDER BY idx',(s['id'],)).fetchall()
            assert sum(x[2] is not None for x in stored)==len(rows) and sum(x[2] is None for x in stored)==s['failed']
        evidence=dict(valid=len(rows),normalZero=sum(r['teamDamage']==0 for r in rows),failed=s['failed'],cancelled=s['cancelled'],partial=stats['partial'],phase=s['input']['phase'],team=stats['team'],members=stats['members'],allPages=True,storedRows=len(stored),independentStatistics=True)
        save(label+'-audit',evidence);report['checks'].append(dict(name=label,detail=evidence));return rows
    with (run/'api.log').open('w',encoding='utf-8') as log:
      try:
        dll=ROOT/'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll';save('build-hashes',{f.name:digest(f) for f in dll.parent.glob('Nikke.*.dll')})
        process=subprocess.Popen([a.dotnet,str(dll)],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=NOCONSOLE);report.update(port=port,apiPid=process.pid,runnerPid=os.getpid())
        watcher=threading.Thread(target=monitor,daemon=True);watcher.start()
        for _ in range(100):
            try:token=call('bootstrap')['token'];break
            except OSError:time.sleep(.1)
        original=call('snapshots/'+snapshot['id']);save('hardware',call('compute/hardware'))
        call('accounts/synthetic-account/formation',dict(slots=ids),'PUT')
        tactic=dict(schemaVersion=1,allowedCharacterIds=ids,stage1Priority=[ids[0]],stage2Priority=[ids[1]],stage3Priority=ids[2:],burst3Rotation=[ids[2],ids[4]],firstBurst3CharacterId=None,unavailablePolicy='next_ready')
        call('accounts/synthetic-account/burst-tactic',dict(snapshotId=snapshot['id'],formationSlots=ids,tactic=tactic),'PUT')
        req=dict(snapshotId=snapshot['id'],characterIds=ids,runs=20,phase='exploration',conditions=dict(roundingPolicy='final_round_even',combat=dict(durationFrames=10800,enemyDefense=30925,critMode='sample',core=True,pelletCoefficientPolicy='per_trigger',manualCharacterId=ids[2])),execution=dict(requested='auto',maxWorkers=2))
        save('calibration-request',req);cal,ct=run_batch('calibration',req);cr=audit('calibration',cal,0)
        assert cal['state']=='completed' and cal['valid']==20 and not reason
        assert cal['input']['fingerprint']=='f9cfbd31c4e250690a804b7fac2a7f1ab71d30c3c9bb0324fab74b2c1c57a70e'
        assert cal['input']['engineVersion']=='cpu-summary.1' and cal['input']['synchroLevel']==400 and cal['input']['durationFrames']==10800 and cal['input']['defPolicy']=='fixed:30925' and cal['input']['characterIds']==ids
        with sqlite3.connect(data/'compute/batches.db') as db:frozen,stored=db.execute('SELECT prepared,request FROM experiments WHERE id=?',(cal['id'],)).fetchone()
        frozen=json.loads(frozen);stored=json.loads(stored);assert stored['conditions']['autoBurst']['tactic']==tactic
        save('prepared-synthetic',frozen);save('fixed-provenance',dict(input=cal['input'],snapshotHash=digest(data/'accounts.db'),tactic=tactic,request=stored))
        sortedDamage=sorted(r['teamDamage'] for r in cr);cut=math.floor((sortedDamage[9]+sortedDamage[10])/2)
        normalUpper=ct['endEpoch']-(ct['lastQueuedEpoch'] or ct['startEpoch']);overhead=max(0,ct['wallSeconds']-normalUpper)
        estimate1000=normalUpper/20*1000;remaining=DEADLINE-time.time();battery=environment()['batteryPercent'];elapsed=time.time()-datetime.fromisoformat(report['startedAt']).timestamp();drain=max(0,baseline['batteryPercent']-battery)/max(elapsed,1)
        admission=dict(at=stamp(),cut=cut,cutRelation='strict >',calibrationId=cal['id'],normal20UpperSeconds=normalUpper,coldOverheadSeconds=overhead,predicted1000Seconds=estimate1000,conservative1000Seconds=1.5*estimate1000+overhead+180,remainingSeconds=remaining,batteryNow=battery,projectedBattery=battery-drain*(1.5*estimate1000+overhead+180),
            predicted10000Seconds=estimate1000*10,predicted50000Seconds=estimate1000*50)
        admission['allowed']=not reason and admission['conservative1000Seconds']<remaining and admission['projectedBattery']>=40
        save('pilot-admission',admission);report['admission']=admission;print('ADMISSION '+json.dumps(admission),flush=True)
        if admission['allowed']:
            pilotReq=dict(req,runs=1000,phase='pilot');save('pilot-request',pilotReq);pilot,pt=run_batch('pilot',pilotReq)
            assert pilot['id']!=cal['id'] and pilot['input']['fingerprint']==cal['input']['fingerprint']
            audit('pilot',pilot,cut);report['pilot']=dict(final=pilot,timing=pt)
            report['status']='passed_pilot_functional' if pilot['state']=='completed' and pilot['valid']==1000 and not reason else 'partial_stopped'
        else:report['status']='calibration_only_no_window_margin'
        assert call('snapshots/'+snapshot['id'])==original
        save('snapshot-unchanged',dict(unchanged=True));save('orca-after',orca_state())
      except Exception as ex:
        report['error']=repr(ex);report['status']='failed_or_stopped';stop_for('qa_error:'+repr(ex))
        if active:
            for _ in range(15):
                try:
                    s=call('compute/experiments/'+active)
                    if s['state'] in ('completed','cancelled','failed'):save('stopped-final',s);audit('stopped',s,report.get('admission',{}).get('cut',0));break
                except Exception as recovery:save('stop-audit-error',dict(error=repr(recovery)))
                time.sleep(1)
      finally:
        done.set()
        if 'watcher' in locals():watcher.join(timeout=12)
        report['stopReason']=reason;report['endedAt']=stamp();save('power-after',environment())
        if process:
            report['finalHost']=sampler.sample(process.pid,data/'compute');process.terminate();process.wait(timeout=20)
        report['sourceChanges']=[r for r,h in hashes.items() if digest(a.source_data/r)!=h];report['packageLockUnchanged']=digest(ROOT/'package-lock.json')==lockHash
        if report['sourceChanges'] or not report['packageLockUnchanged']:report['status']='failed_preservation'
        save('latencies',latencies);poll=[x['ms'] for x in latencies if x['path'].startswith('compute/experiments/') and x['path'].count('/')==2]
        if poll:poll.sort();report['statusApiP95Ms']=poll[math.ceil(.95*len(poll))-1];report['statusApiSamples']=len(poll)
        report['telemetrySamples']=len(samples);report['unavailableMetrics']=policy['missingMetrics'];save('summary',report);print('FINAL '+report['status']+' '+str(run),flush=True)
    return 0 if report['status'] in ('passed_pilot_functional','calibration_only_no_window_margin','partial_stopped') else 1
if __name__=='__main__':raise SystemExit(main())

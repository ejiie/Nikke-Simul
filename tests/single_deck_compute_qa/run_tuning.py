"""Q-TUNE-1 independent small real API acceptance; no throughput claims or OL calls."""
import argparse,json,os,socket,sqlite3,subprocess,time,urllib.request,uuid
from pathlib import Path
from public_fixture import create,digest
from actual_stats import metric
from backend_v1 import results

root=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--source-data',type=Path,required=True);p.add_argument('--dotnet',required=True);a=p.parse_args()
run=root/'artifacts/single-deck-qa'/('tune-api-'+uuid.uuid4().hex[:12]);data=run/'data';data.mkdir(parents=True)
hashes,game,snapshot,ids=create(a.source_data,data)
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
assert port not in (5180,5181)
env=dict(os.environ,NIKKE_PROJECT_ROOT=str(root),NIKKE_DATA_ROOT=str(data),NIKKE_PORT=str(port),NIKKE_TEST_FIXTURE='1');env.pop('NIKKE_GAME_CATALOG',None)
report=dict(status='aborted',product='40078d06a3d236ec7de5987d6be3c96d2a34ec86',kind='actual_public_180_CPU_new_synthetic_account',port=port,checks=[],performanceAcceptance=False)
token='';process=log=None;observations={};latencies=[]
def save(name,value):(run/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def call(path,payload=None,method=None):
    start=time.perf_counter();req=urllib.request.Request(f'http://127.0.0.1:{port}/api/'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Nikke-Token':token},method=method)
    with urllib.request.urlopen(req,timeout=40) as res:ret=json.load(res)
    latencies.append(dict(path=path,ms=1000*(time.perf_counter()-start)));return ret
def start():
    global token,process,log
    log=(run/f'api-{time.time_ns()}.log').open('w',encoding='utf-8')
    process=subprocess.Popen([a.dotnet,str(root/'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],cwd=root,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    for _ in range(200):
        try:token=call('bootstrap')['token'];return
        except OSError:time.sleep(.1)
    raise AssertionError('startup timeout')
def stop():
    global process,log
    if process:process.terminate();process.wait(timeout=30);process=None
    if log:log.close();log=None
def status(id):
    s=call('compute/experiments/'+id);observations.setdefault(id,[]).append(s);return s
def wait(id,predicate=lambda s:s['state'] in ('completed','cancelled','failed')):
    end=time.monotonic()+140
    while time.monotonic()<end:
        s=status(id)
        if predicate(s):return s
        time.sleep(.04)
    raise AssertionError('small API timeout')
def done(name,detail):report['checks'].append(dict(name=name,passed=True,detail=detail));save('summary',report);print(name+': PASS',flush=True)
try:
    start();original=call('snapshots/'+snapshot['id']);save('hardware',call('compute/hardware'))
    call('accounts/synthetic-account/formation',dict(slots=ids),'PUT')
    tactic=dict(schemaVersion=1,allowedCharacterIds=ids,stage1Priority=[ids[0]],stage2Priority=[ids[1]],stage3Priority=ids[2:],burst3Rotation=[ids[2],ids[4]],firstBurst3CharacterId=None,unavailablePolicy='next_ready')
    call('accounts/synthetic-account/burst-tactic',dict(snapshotId=snapshot['id'],formationSlots=ids,tactic=tactic),'PUT')
    req=dict(snapshotId=snapshot['id'],characterIds=ids,runs=2,phase='final',conditions=dict(roundingPolicy='final_round_even',combat=dict(durationFrames=10800,enemyDefense=30925,critMode='sample',core=True,pelletCoefficientPolicy='per_trigger',manualCharacterId=ids[2])),execution=dict(requested='auto',maxWorkers=2))
    save('request',req)
    b=call('compute/experiments',dict(req,execution=dict(req['execution'],retune=True)));id=b['id']
    warm=wait(id,lambda s:(s['execution'].get('tuning') or {}).get('status')=='warmup')
    assert warm['valid']==0 and warm['state']=='queued'
    t=time.perf_counter();call(f'compute/experiments/{id}/cancel',{});ack=1000*(time.perf_counter()-t);cancelled=wait(id)
    assert cancelled['state']=='cancelled' and cancelled['valid']==0 and cancelled['execution']['tuning']['stopReason']=='external_cancelled'
    cs=call(f'compute/experiments/{id}/statistics');assert cs['team']['n']==0 and cs['partial']
    done('observed_warmup_cancel_valid0',dict(ackMs=ack,terminalMs=1000*(time.perf_counter()-t),final=cancelled))
    b=call('compute/experiments',req);id=b['id'];end=wait(id);assert end['state']=='completed' and end['valid']==2
    tuning=end['execution']['tuning'];assert tuning['status']=='measured' and tuning['plannedWorkers']==[1,2]
    assert tuning['preparationMilliseconds']>=0 and tuning['totalBudgetMilliseconds']==50000
    assert all(s['completed']==2 and s['interrupted']==0 and s['requested']==2 and s['budgetMilliseconds']==24000 for s in tuning['stages'][1:])
    assert end['input']['engineVersion']=='cpu-summary.1' and end['input']['synchroLevel']==400 and end['input']['defPolicy']=='fixed:30925' and end['input']['characterIds']==ids
    with sqlite3.connect(data/'compute/batches.db') as db:frozen,stored=db.execute('SELECT prepared,request FROM experiments WHERE id=?',(id,)).fetchone()
    prepared=json.loads(frozen);stored=json.loads(stored);assert stored['conditions']['autoBurst']['tactic']==tactic and prepared['conditions']['combat']['enemyDefense']==30925
    save('prepared-synthetic',prepared);save('baseline-status',end)
    pages=[call(f'compute/experiments/{id}/results?offset={i}&limit=1') for i in range(2)];results(pages);rows=[x for page in pages for x in page['runs']];save('baseline-pages',pages)
    cut=rows[0]['teamDamage'];stats=call(f'compute/experiments/{id}/statistics?cut={cut}');metric(stats['team'],[r['teamDamage'] for r in rows],cut)
    for member in ids:metric(stats['members'][member],[next(m['damage'] for m in r['members'] if m['characterId']==member) for r in rows])
    assert stats['team']['n']==2 and not stats['partial'];save('baseline-statistics',stats)
    done('real_limited_tuning_full_results_statistics_exclude_tuning',end)
    reuse=call('compute/experiments',req);rs=wait(reuse['id']);assert rs['valid']==2 and rs['execution']['reason']=='measured_cache' and rs['execution']['tuning']['status']=='cache_reused'
    # Exact Run0 is observed in independent C# wrapper, not inferred from short API elapsed time.
    done('API_cache_reuse',rs)
    stop();start();restored=status(id);assert restored==end
    assert call(f'compute/experiments/{id}/statistics?cut={cut}')==stats
    done('completed_selection_rows_statistics_restart',restored)
    crash=call('compute/experiments',dict(req,execution=dict(req['execution'],retune=True)));crid=crash['id']
    wait(crid,lambda s:(s['execution'].get('tuning') or {}).get('status')=='warmup');stop();start();recovered=status(crid)
    assert recovered['state']=='cancelled' and recovered['errorCode']=='process_interrupted' and recovered['valid']==0
    call(f'compute/experiments/{crid}/resume',{});resumed=wait(crid);assert resumed['state']=='completed' and resumed['attempt']==2 and resumed['valid']==2
    done('interrupted_tuning_restart_resume',dict(recovered=recovered,resumed=resumed))
    assert call('snapshots/'+snapshot['id'])==original;done('synthetic_snapshot_unchanged',True)
    report['status']='passed'
except Exception as ex:
    report['error']=repr(ex);raise
finally:
    stop();report['sourceChanges']=[r for r,h in hashes.items() if digest(a.source_data/r)!=h]
    if report['sourceChanges']:report['status']='failed'
    save('source-hashes',hashes);save('observations',observations);save('latencies',latencies);save('summary',report);print(run,flush=True)

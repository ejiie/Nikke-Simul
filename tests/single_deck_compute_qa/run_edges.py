"""Tiny one-frame API evidence for zero, cache TTL and tuning cancellation, never throughput."""
import argparse,json,os,socket,subprocess,time,urllib.request,urllib.error,uuid
from pathlib import Path
from public_fixture import create,digest
from actual_stats import metric

root=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--source-data',type=Path,required=True);p.add_argument('--dotnet',required=True);a=p.parse_args()
run=root/'artifacts/single-deck-qa'/('edges-'+uuid.uuid4().hex[:12]);data=run/'data';data.mkdir(parents=True)
hashes,game,snapshot,ids=create(a.source_data,data)
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
assert port not in (5180,5181)
env=dict(os.environ,NIKKE_PROJECT_ROOT=str(root),NIKKE_DATA_ROOT=str(data),NIKKE_PORT=str(port),NIKKE_TEST_FIXTURE='1');env.pop('NIKKE_GAME_CATALOG',None)
token='';report=dict(kind='actual_API_one_frame_synthetic_account_not_performance',port=port,status='aborted')
def call(path,payload=None):
    req=urllib.request.Request(f'http://127.0.0.1:{port}/api/'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Nikke-Token':token})
    with urllib.request.urlopen(req,timeout=30) as res:return json.load(res)
def wait(id):
    for _ in range(600):
        s=call('compute/experiments/'+id)
        if s['state'] in ('completed','cancelled','failed'):return s
        time.sleep(.05)
    raise AssertionError('timeout')
with (run/'api.log').open('w',encoding='utf-8') as log:
    process=subprocess.Popen([a.dotnet,str(root/'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],cwd=root,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for _ in range(200):
            try:token=call('bootstrap')['token'];break
            except OSError:time.sleep(.1)
        original=call('snapshots/'+snapshot['id'])
        req=dict(snapshotId=snapshot['id'],characterIds=ids,runs=2,phase='final',useSavedTactic=False,execution=dict(requested='auto',maxWorkers=1),conditions=dict(roundingPolicy='final_round_even',combat=dict(durationFrames=1,enemyDefense=30925,critMode='sample',pelletCoefficientPolicy='per_trigger')))
        b=call('compute/experiments',req);id=b['id'];first=call(f'compute/experiments/{id}/statistics?cut=0');final=wait(id)
        immediate=call(f'compute/experiments/{id}/statistics?cut=0');time.sleep(2.2);fresh=call(f'compute/experiments/{id}/statistics?cut=0')
        rows=call(f'compute/experiments/{id}/results')['runs']
        assert final['state']=='completed' and fresh['team']['n']==2 and not fresh['partial']
        metric(fresh['team'],[r['teamDamage'] for r in rows],0)
        for s in (first,immediate,fresh):assert s['partial']==(s['team']['n']<2)
        report['cache']=dict(first=first,immediate=immediate,fresh=fresh,rows=rows)
        assert all(r['teamDamage']==0 for r in rows),'one-frame fixture expected no fired damage'
        report['normalZeroActualAPI']=True
        # Same physical input, fresh experiment: exercise actual measured cache reuse.
        reused=call('compute/experiments',req);rs=wait(reused['id']);assert rs['execution']['reason']=='measured_cache',rs
        report['cacheReuse']=rs['execution']
        changed=json.loads(json.dumps(req));changed['conditions']['combat']['enemyDefense']=30926
        cb=call('compute/experiments',changed);cs=wait(cb['id'])
        assert cs['input']['fingerprint']!=final['input']['fingerprint'] and cs['execution']['fingerprint']!=final['execution']['fingerprint']
        assert cs['execution']['reason']!='measured_cache';report['changedDEFInvalidates']=cs['execution']
        warm=call('compute/experiments',dict(req,phase='warmup'))
        try:call(f"compute/experiments/{warm['id']}/statistics")
        except urllib.error.HTTPError as error:assert error.code==409 and 'warmup_excluded' in error.read().decode()
        else:raise AssertionError('warmup included')
        wait(warm['id']);report['warmupExcluded']=True
        longreq=json.loads(json.dumps(req));longreq['conditions']['combat']['durationFrames']=10800;longreq['execution']['retune']=True
        long=call('compute/experiments',longreq);time.sleep(.15);start=time.perf_counter();cancel=call(f"compute/experiments/{long['id']}/cancel",{});ack=1000*(time.perf_counter()-start);cancelled=wait(long['id'])
        report['cancelBeforeRunning']=dict(ackMs=ack,totalMs=1000*(time.perf_counter()-start),final=cancelled,phaseVisibility='API queued covers hardware probe and tuning; precise internal phase unknown')
        assert cancelled['state']=='cancelled' and cancelled['valid']==0 and cancelled['partial']
        assert call('snapshots/'+snapshot['id'])==original
        report['status']='passed'
    finally:
        process.terminate();process.wait(timeout=30)
        report['sourceChanges']=[r for r,h in hashes.items() if digest(a.source_data/r)!=h];assert not report['sourceChanges']
        (run/'source-hashes.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
        (run/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(str(run),flush=True)

"""B-TUNE-1 API diagnostics only. Uses new synthetic probe output, never source accounts/caches."""
import argparse,json,os,socket,sqlite3,subprocess,time,urllib.request,urllib.error
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def main():
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--dotnet',required=True);args=p.parse_args()
    run=args.fixture.resolve();data=run/'public';snapshot=read(run/'snapshot-synthetic.json');request=read(run/'request-synthetic.json')
    assert snapshot['accountId']=='synthetic' and snapshot['id']=='synthetic-tuning'
    assert not (data/'accounts.db').exists(),'use fresh probe output only'
    with sqlite3.connect(data/'accounts.db') as db:
        db.execute('CREATE TABLE snapshots(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL)')
        db.execute('CREATE TABLE accounts(id TEXT PRIMARY KEY,current_id TEXT NOT NULL REFERENCES snapshots(id))')
        db.execute('INSERT INTO snapshots VALUES(?,?,?,?)',(snapshot['id'],snapshot['accountId'],1,json.dumps(snapshot)))
        db.execute('INSERT INTO accounts VALUES(?,?)',(snapshot['accountId'],snapshot['id']))
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    assert port not in (5180,5181)
    env=dict(os.environ,NIKKE_DATA_ROOT=str(data),NIKKE_PROJECT_ROOT=str(ROOT),NIKKE_PORT=str(port),NIKKE_TEST_FIXTURE='1')
    env.pop('NIKKE_GAME_CATALOG',None);token='';report={'status':'failed','port':port,'checks':[]};process=None
    def call(path,payload=None):
        req=urllib.request.Request(f'http://127.0.0.1:{port}/api/'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Nikke-Token':token})
        with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
    def status(id):return call('compute/experiments/'+id)
    def wait(id,predicate):
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            value=status(id)
            if predicate(value):return value
            time.sleep(.03)
        raise AssertionError('state deadline')
    try:
        with (run/'tuning-api.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen([args.dotnet,str(ROOT/'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            for _ in range(300):
                try:token=call('bootstrap')['token'];break
                except (OSError,urllib.error.URLError):time.sleep(.1)
            else:raise AssertionError('startup failed')
            original=call('snapshots/'+snapshot['id'])
            request['execution']['retune']=True
            first=call('compute/experiments',request)
            active=wait(first['id'],lambda s:(s['execution'].get('tuning') or {}).get('status')=='warmup')
            assert active['state']=='queued';assert active['execution']['tuning']['preparationMilliseconds'] is not None
            call('compute/experiments/'+first['id']+'/cancel',{})
            cancelled=wait(first['id'],lambda s:s['state']=='cancelled')
            assert cancelled['valid']==0 and cancelled['execution']['tuning']['status']=='cancelled'
            report['cancelled']=cancelled;report['checks'].append('queued warmup observed and cancelled with no normal sample')
            batch=call('compute/experiments',request);done=wait(batch['id'],lambda s:s['state'] in ('completed','failed'))
            assert done['state']=='completed' and done['valid']==2,done
            tuning=done['execution']['tuning'];assert tuning['status']=='measured',tuning
            assert all(s['completed']==2 and s['interrupted']==0 for s in tuning['stages'] if s['name']=='candidate')
            report['measured']=done;report['checks'].append('complete equal-work candidates reported through API')
            request['execution']['retune']=False
            reused=call('compute/experiments',request);cached=wait(reused['id'],lambda s:s['state'] in ('completed','failed'))
            assert cached['state']=='completed' and cached['valid']==2
            assert cached['execution']['reason']=='measured_cache' and cached['execution']['tuning']['status']=='cache_reused'
            report['cached']=cached;report['checks'].append('validated new-policy cache reused')
            statistics=call('compute/experiments/'+reused['id']+'/statistics');assert statistics['team']['n']==2
            rows=call('compute/experiments/'+reused['id']+'/results')['runs'];assert len(rows)==2 and all(r['phase']=='final' for r in rows)
            assert call('snapshots/'+snapshot['id'])==original
            report['checks'].append('tuning excluded from statistics and synthetic snapshot unchanged');report['status']='passed'
    finally:
        if process is not None:process.terminate();process.wait(timeout=30)
        (run/'tuning-api-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(run/'tuning-api-summary.json')
if __name__=='__main__':main()

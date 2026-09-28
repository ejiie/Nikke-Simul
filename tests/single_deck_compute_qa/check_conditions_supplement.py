"""Additional acceptance on QA-created stage1 data only. Malformed runtime isolation, no product edits."""
import argparse,json,os,socket,sqlite3,subprocess,time,urllib.request,urllib.error,hashlib
from copy import deepcopy
from pathlib import Path
from public_fixture import read,digest
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--dotnet',required=True);a=p.parse_args();run=Path(a.run).resolve();assert run.is_relative_to((ROOT/'artifacts/single-deck-qa').resolve());data=run/'data'
 report=dict(checks=[],scope='own isolated data supplemental; corrupt runtime scenarios explicit');http=[]
 def save(name,value):(run/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
 def check(name,ok,detail=None):report['checks'].append(dict(name=name,passed=bool(ok),detail=detail));print(name+(': PASS' if ok else ': FAIL'),flush=True)
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 assert port not in(5180,5181);report['port']=port
 env=dict(os.environ,NIKKE_PROJECT_ROOT=str(ROOT),NIKKE_DATA_ROOT=str(data),NIKKE_PORT=str(port),NIKKE_TEST_FIXTURE='1');env.pop('NIKKE_GAME_CATALOG',None)
 process=None;log=None;token='';pointer=data/'runtime/current.json';original_pointer=pointer.read_bytes();catalog=read(data/'runtime'/read(pointer)['id']/'catalog.json');snapshot=read(run/'old-replay.json')['accountSnapshotId'];ids=list(read(run/'old-replay.json')['appliedLevels'])
 with sqlite3.connect(data/'accounts.db') as db:original_snapshot=db.execute('SELECT payload FROM snapshots WHERE id=?',(snapshot,)).fetchone()[0]
 def call(path,payload=None):
  req=urllib.request.Request(f'http://127.0.0.1:{port}/api/'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Nikke-Token':token})
  try:
   with urllib.request.urlopen(req,timeout=90) as r:status=r.status;body=r.read().decode()
  except urllib.error.HTTPError as e:status=e.code;body=e.read().decode()
  try:value=json.loads(body)
  except ValueError:value=body
  http.append(dict(path=path,request=payload,status=status,response=value));return status,value
 def start():
  nonlocal process,log,token
  log=(run/f'supplement-api-{time.time_ns()}.log').open('w',encoding='utf-8');process=subprocess.Popen([a.dotnet,str(ROOT/'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],env=env,cwd=ROOT,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));report.setdefault('ownedPids',[]).append(process.pid)
  for _ in range(300):
   try:token=call('bootstrap')[1]['token'];return
   except OSError:time.sleep(.1)
  raise AssertionError('startup')
 def stop():
  nonlocal process,log
  if process:process.terminate();process.wait(timeout=30);process=None
  if log:log.close();log=None
 def publish(c):
  content=json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();id=hashlib.sha256(content).hexdigest();folder=data/'runtime'/id;folder.mkdir(exist_ok=True);(folder/'catalog.json').write_bytes(content);pointer.write_text(json.dumps(dict(id=id,file='catalog.json',schemaVersion=1)),encoding='utf-8')
 def replay(c):return dict(snapshotId=snapshot,characterIds=ids,scenarioLevel=400,conditions=dict(roundingPolicy='client_f32',combat=dict(durationFrames=120,enemyDefense=30925,critMode='off',pelletCoefficientPolicy='per_trigger',**c)))
 try:
  record=next(x for x in read(ROOT/'docs/p03-source-manifest.json') if x.get('inputKey')=='sourceRoles');raw=read(Path(record['sourceRoot'])/record['path'])['roster']
  check('all192 prepared profiles independently match raw',all((p['bonusRangeMin'],p['bonusRangeMax'],p['element'],p['weaponType'])==(raw[id]['bonusrange_min'],raw[id]['bonusrange_max'],raw[id]['element'],raw[id]['shot']['weapon_type']) for id,p in catalog['combatProfiles']['characters'].items()) and len(catalog['combatProfiles']['characters'])==len(raw))
  start();status,off=call('runtime/skill-replays',replay(dict(properDistance=False,elementAdvantage=False)));status2,empty=call('runtime/skill-replays',replay(dict(bossDistance=None,bossWeakElement=None)))
  check('legacy false and explicit null same damage different mode',status==status2==200 and off['result']['members']==empty['result']['members'] and off['conditionCompatibility']['mode']!=empty['conditionCompatibility']['mode'])
  req=replay(dict(properDistance=False,elementAdvantage=False));req.pop('scenarioLevel');req.update(runs=1,phase='pilot',execution=dict(requested='cpu',maxWorkers=1,memoryLimitBytes=268435456))
  status,b=call('compute/experiments',req);assert status==202
  for _ in range(600):
   _,b=call('compute/experiments/'+b['id'])
   if b['state'] in ['completed','failed','cancelled']:break
   time.sleep(.05)
  assert b['state']=='completed';_,rows=call('compute/experiments/'+b['id']+'/results');previous=read(run/'batch-empty.json');save('legacy-off',dict(batch=b,results=rows))
  check('equal damage modes distinct fingerprints and caches',rows['runs'][0]['teamDamage']==previous['rows'][0]['teamDamage'] and b['input']['fingerprint']!=previous['batch']['input']['fingerprint'] and b['execution']['fingerprint']!=previous['batch']['execution']['fingerprint'])
  for label in ['legacy','empty','fire','water','distance']:
   saved=read(run/('batch-'+label+'.json'));_,rows=call('compute/experiments/'+saved['batch']['id']+'/results');check('restart saved results unchanged '+label,rows['runs']==saved['rows'] and all(sum(m['damage'] for m in row['members'])==row['teamDamage'] for row in rows['runs']))
  stop()
  # Valid hash but malformed metadata must not become a guessed range or element.
  for field in ['bonusRangeMin','bonusRangeMax','element','whole-member']:
   corrupted=deepcopy(catalog)
   if field=='whole-member':del corrupted['combatProfiles']['characters']['5004']
   else:del corrupted['combatProfiles']['characters']['5004'][field]
   publish(corrupted);start();status,value=call('snapshots/'+snapshot+'/combat-conditions?characterIds=5004');rs,rv=call('runtime/skill-replays',replay(dict(bossDistance=35,bossWeakElement='Fire')))
   save('malformed-'+field,dict(profileStatus=status,profile=value,replayStatus=rs,replay=rv))
   check('unknown profile field rejected '+field,status>=400 and rs>=400,dict(profileStatus=status,replayStatus=rs,profile=value));stop()
  report['status']='passed' if all(c['passed'] for c in report['checks']) else 'failed'
 finally:
  stop();pointer.write_bytes(original_pointer)
  with sqlite3.connect(data/'accounts.db') as db:unchanged=db.execute('SELECT payload FROM snapshots WHERE id=?',(snapshot,)).fetchone()[0]==original_snapshot
  report['snapshotUnchanged']=unchanged;report['runtimePointerRestored']=pointer.read_bytes()==original_pointer;report['ownApiStopped']=True;save('supplement-http',http);save('supplement-summary',report)
 return 0 if report['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())

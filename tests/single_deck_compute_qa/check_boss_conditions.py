"""F-COND-Q own API/oracle checks; no Backend/engine tests or expected outputs imported."""
import argparse,json,os,socket,sqlite3,subprocess,time,urllib.request,urllib.error,uuid
from pathlib import Path
from copy import deepcopy
from collections import defaultdict
from public_fixture import create,read,digest
from check_f32_b1 import normalized
from check_client_f32 import context
from actual_stats import metric
ROOT=Path(__file__).resolve().parents[2]

def main():
 p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args()
 run=ROOT/'artifacts/single-deck-qa'/('conditions-'+uuid.uuid4().hex[:12]);data=run/'data';data.mkdir(parents=True)
 source=ROOT/'artifacts/single-deck-qa/load1000-3db71912a601/data'
 hashes,game,snapshot,ids=create(source,data)
 manifest=read(ROOT/'docs/p03-source-manifest.json');record=next(x for x in manifest if x.get('inputKey')=='sourceRoles');rosterpath=Path(record['sourceRoot'])/record['path']
 assert digest(rosterpath)==record['sha256'];roster=read(rosterpath)['roster']
 # All five get synthetic T10/one attack line for independent OL eligibility coverage.
 for char in snapshot['characters']:char['equipment'][0]=deepcopy(snapshot['characters'][2]['equipment'][0])
 with sqlite3.connect(data/'accounts.db') as db:db.execute('UPDATE snapshots SET payload=?',(json.dumps(snapshot),))
 snapshot_hash=digest(data/'accounts.db')
 report=dict(status='running',checks=[],scope='F-COND-Q stage1 synthetic API; resolver boundary supplemental',sourceRosterHash=record['sha256'])
 def save(name,value):(run/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
 def check(name,ok,detail=None):
  report['checks'].append(dict(name=name,passed=bool(ok),detail=detail));save('summary',report);print(name+(': PASS' if ok else ': FAIL'),flush=True)
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 assert port not in (5180,5181);report['port']=port
 env=dict(os.environ,NIKKE_PROJECT_ROOT=str(ROOT),NIKKE_DATA_ROOT=str(data),NIKKE_PORT=str(port),NIKKE_TEST_FIXTURE='1');env.pop('NIKKE_GAME_CATALOG',None)
 process=None;log=None;token='';http=[]
 def call(path,payload=None,method=None,code=200):
  req=urllib.request.Request(f'http://127.0.0.1:{port}/api/'+path,data=None if payload is None else json.dumps(payload).encode(),method=method,headers={'Content-Type':'application/json','X-Nikke-Token':token})
  try:
   with urllib.request.urlopen(req,timeout=90) as res:status=res.status;body=res.read().decode()
  except urllib.error.HTTPError as e:status=e.code;body=e.read().decode()
  val=json.loads(body) if body else None;http.append(dict(path=path,method=req.get_method(),request=payload,status=status,response=val));save('http',http)
  assert status==code,(path,status,code,val)
  return val
 def start(binary,label):
  nonlocal process,log,token
  log=(run/(label+'.log')).open('w',encoding='utf-8');process=subprocess.Popen([a.dotnet,str(binary)],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));report.setdefault('ownedPids',[]).append(process.pid)
  for _ in range(300):
   try:token=call('bootstrap')['token'];return
   except OSError:time.sleep(.1)
  raise AssertionError('startup')
 def stop():
  nonlocal process,log
  if process:process.terminate();process.wait(timeout=30);process=None
  if log:log.close();log=None
 def replay(combat,id=None,frames=120):
  req=dict(snapshotId=snapshot['id'],characterIds=ids,scenarioLevel=400,conditions=dict(roundingPolicy='client_f32',casts=[],damageLog=dict(characterId=id or ids[2]),combat=dict(durationFrames=frames,enemyDefense=30925,critMode='off',pelletCoefficientPolicy='per_trigger',**combat)))
  return call('runtime/skill-replays',req)
 def request(combat):return dict(snapshotId=snapshot['id'],characterIds=ids,runs=1,phase='pilot',conditions=dict(combat=dict(durationFrames=120,enemyDefense=30925,critMode='off',pelletCoefficientPolicy='per_trigger',**combat)),execution=dict(requested='cpu',maxWorkers=1,memoryLimitBytes=268435456))
 def batch(combat):
  b=call('compute/experiments',request(combat),code=202)
  for _ in range(600):
   b=call('compute/experiments/'+b['id'])
   if b['state'] in ['completed','failed','cancelled']:break
   time.sleep(.05)
  assert b['state']=='completed',b
  rows=call('compute/experiments/'+b['id']+'/results')['runs'];st=call('compute/experiments/'+b['id']+'/statistics?cut=0');metric(st['team'],[r['teamDamage'] for r in rows],0)
  for id in ids:metric(st['members'][id],[next(m['damage'] for m in r['members'] if m['characterId']==id) for r in rows])
  check('independent statistics '+b['id'],st['team']['n']==1 and len(rows)==1 and all(r['inputFingerprint']==b['input']['fingerprint'] for r in rows))
  return dict(batch=b,rows=rows,statistics=st)
 try:
  legacy=dict(properDistance=True,elementAdvantage=True)
  start(ROOT/'artifacts/single-deck-qa/cond-stage1/baseline-api/Nikke.Api.dll','old-api')
  call('accounts/synthetic-account/formation',dict(slots=ids),'PUT')
  tactic=dict(schemaVersion=1,allowedCharacterIds=ids,stage1Priority=[ids[0]],stage2Priority=[ids[1]],stage3Priority=ids[2:],burst3Rotation=ids[2:],unavailablePolicy='next_ready')
  call('accounts/synthetic-account/burst-tactic',dict(snapshotId=snapshot['id'],formationSlots=ids,tactic=tactic),'PUT')
  oldreplay=replay(legacy);oldbatch=batch(legacy);save('old-replay',oldreplay);save('old-batch',oldbatch)
  oldfile=next((data/'skill-replays').rglob(oldreplay['id']+'.json'));oldhash=digest(oldfile)
  stop()
  current=ROOT/'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll'
  start(current,'new-with-old-runtime');missing=call('runtime/combat-conditions',code=409)
  check('old runtime explicit409', 'combat_profile_catalog_missing' in str(missing));check('old runtime legacy replay preserved',replay(legacy)['result']['members']==oldreplay['result']['members']);stop()
  before=read(data/'runtime/current.json')['id'];oldcatalog=read(data/'runtime'/before/'catalog.json');cataloghash=digest(data/'runtime'/before/'catalog.json')
  import sys
  cmd=[sys.executable,str(ROOT/'tools/data-pipeline/prepare_combat_conditions.py'),'--runtime-root',str(data/'runtime'),'--source-roster',str(rosterpath)]
  prepared=subprocess.run(cmd,capture_output=True,text=True,check=True);save('prepare-output',dict(stdout=prepared.stdout,stderr=prepared.stderr))
  after=read(data/'runtime/current.json')['id'];catalog=read(data/'runtime'/after/'catalog.json');without=deepcopy(catalog);without.pop('combatProfiles')
  subprocess.run(cmd,capture_output=True,text=True,check=True)
  check('runtime graph immutable and idempotent',without==oldcatalog and digest(data/'runtime'/before/'catalog.json')==cataloghash and read(data/'runtime/current.json')['id']==after)
  start(current,'new-api');api=call('runtime/combat-conditions');save('catalog-api',api)
  expected=defaultdict(lambda:defaultdict(list))
  for id,r in roster.items():expected[r['shot']['weapon_type']][(r['bonusrange_min'],r['bonusrange_max'])].append(id)
  groups={g['weaponType']:g for g in api['weaponRanges']}
  check('all weapon groups independently aggregated',set(groups)==set(expected) and sum(g['characterCount'] for g in groups.values())==len(roster))
  for weapon,ranges in expected.items():
   g=groups[weapon];typical=sorted(ranges,key=lambda k:(-len(ranges[k]),k))[0]
   check('roster ranges exceptions '+weapon,{(r['min'],r['max']):sorted(r['characterIds']) for r in g['ranges']}=={k:sorted(v) for k,v in ranges.items()} and all(r['count']==len(r['characterIds']) and r['isTypical']==((r['min'],r['max'])==typical) for r in g['ranges']) and {x['characterId'] for x in g['exceptions']}=={id for k,v in ranges.items() if k!=typical for id in v})
  check('catalog source and provisional rules',api['source']['sha256']==record['sha256'] and api['gameVerified']==False and api['rangeRule']=='inclusive_character_range_normal_only' and {e['value'] for e in api['elements']}=={r['element'] for r in roster.values()})
  profiles=call('snapshots/'+snapshot['id']+'/combat-conditions?characterIds='+','.join(reversed(ids)))['members']
  check('requested member order and source fields',[m['characterId'] for m in profiles]==list(reversed(ids)) and all((m['bonusRangeMin'],m['bonusRangeMax'],m['element'],m['weaponType'])==(roster[m['characterId']]['bonusrange_min'],roster[m['characterId']]['bonusrange_max'],roster[m['characterId']]['element'],roster[m['characterId']]['shot']['weapon_type']) for m in profiles))
  for bad in [ids+['5042'],[ids[0],ids[0]],['5042']]:check('invalid ownership/count '+str(bad),bool(call('snapshots/'+snapshot['id']+'/combat-conditions?characterIds='+','.join(bad),code=400)))
  # Boundary oracle generated directly from raw roster, independent from product aggregation/resolver.
  cases=[];expectedflags={}
  for id,r in roster.items():
   lo,hi=r['bonusrange_min'],r['bonusrange_max']
   for distance in sorted({max(0,lo-1),lo,hi,min(100,hi+1)}):
    for normal in [True,False]:
     key=f'{id}:{distance}:{normal}';cases.append(dict(id=key,member=dict(characterId=id,weapon=dict(weaponType=r['shot']['weapon_type']),hit=None,buffs=None,bonusRangeMin=lo,bonusRangeMax=hi,element=r['element']),conditions=dict(bossDistance=distance,bossWeakElement=r['element']),normal=normal));expectedflags[key]=(normal and lo<=distance<=hi and not(r['shot']['weapon_type']=='RL' and lo==hi==0),True)
  for field,value,code in [('bonusRangeMin',None,'member_bonus_range_unknown'),('bonusRangeMax',None,'member_bonus_range_unknown'),('element',None,'member_element_unknown_or_invalid')]:
   case=deepcopy(cases[0]);case['id']=field+'-unknown';case['member'][field]=value;cases.append(case);expectedflags[case['id']]=code
  save('resolver-cases',cases);subprocess.run([a.dotnet,str(ROOT/'tests/single_deck_compute_qa/ConditionBoundary/bin/Release/net10.0/ConditionBoundary.dll'),str(run/'resolver-cases.json'),str(run/'resolver-results.json')],check=True)
  results=read(run/'resolver-results.json');bad=[]
  for r in results:
   e=expectedflags[r['id']]
   if not ((e in r.get('error','')) if isinstance(e,str) else (r.get('result',{}).get('properDistance'),r.get('result',{}).get('elementAdvantage'))==e):bad.append(r)
  check('raw-roster independent resolver boundaries RL SR unknown',not bad,dict(count=len(results),failures=bad[:10]))
  # New vs own pre-change execution, not Backend published totals.
  newold=replay(legacy);save('new-legacy-replay',newold)
  check('legacy exact member and logged-hit replay',newold['result']['members']==oldreplay['result']['members'] and newold['result']['damageLog']==oldreplay['result']['damageLog'])
  oldget=call('runtime/skill-replays/'+oldreplay['id']);compat=call('runtime/skill-replays/'+oldreplay['id']+'/condition-compatibility');export=call('runtime/skill-replays/'+oldreplay['id']+'/export.json')
  check('old replay mode and immutable GET export',compat['mode']=='legacy_global' and compat['legacyProperDistance'] and compat['legacyElementAdvantage'] and oldget==export==oldreplay and digest(oldfile)==oldhash)
  oldid=oldbatch['batch']['id'];check('old batch query compatibility',call('compute/experiments/'+oldid+'/condition-compatibility')['mode']=='legacy_global' and call('compute/experiments/'+oldid+'/results')['runs']==oldbatch['rows'])
  check('old batch resume refuses version', 'engine_or_rules_version_changed' in str(call('compute/experiments/'+oldid+'/resume',{},code=409)))
  # Five mixed-deck logs include normal and skill effects; replace flags from raw roster before arithmetic oracle.
  nonnormal=0;hits=0
  for id in ids:
   r=replay(dict(bossDistance=35,bossWeakElement='Fire'),id,1200);save('mixed-'+id,r);errors=[]
   for e in r['result']['damageLog']['entries']:
    h=normalized(e['hit']);normal=h['damageType']=='normal';raw=roster[id];distance=normal and raw['bonusrange_min']<=35<=raw['bonusrange_max'] and not(raw['shot']['weapon_type']=='RL' and raw['bonusrange_min']==raw['bonusrange_max']==0);element=raw['element']=='Fire'
    flags=(h['properDistance'],h['elementAdvantage']);h['properDistance']=distance;h['elementAdvantage']=element
    if flags!=(distance,element) or context(h)['damage']!=e['damage']:errors.append(e['hitId'])
    nonnormal+=not normal;hits+=1
   check('mixed flags and independent damage '+id,not errors and len(r['result']['damageLog']['entries'])>0,dict(hits=len(r['result']['damageLog']['entries']),errors=errors[:10]))
  check('skill damage actually covered',nonnormal>0,dict(nonNormal=nonnormal,total=hits))
  for id in ids:
   raw=roster[id]
   for d in sorted({max(0,raw['bonusrange_min']-1),raw['bonusrange_min'],raw['bonusrange_max'],min(100,raw['bonusrange_max']+1)}):
    r=replay(dict(bossDistance=d,bossWeakElement=None),id);entries=r['result']['damageLog']['entries'];want=raw['bonusrange_min']<=d<=raw['bonusrange_max']
    check('API boundary '+id+':'+str(d),bool(entries) and all(e['hit']['properDistance']==(want and e['hit']['damageType']=='normal') and not e['hit']['elementAdvantage'] for e in entries))
  modes=dict(legacy=legacy,empty=dict(bossDistance=None,bossWeakElement=None),fire=dict(bossDistance=35,bossWeakElement='Fire'),water=dict(bossDistance=35,bossWeakElement='Water'),distance=dict(bossDistance=45,bossWeakElement='Fire'))
  batches={}
  for label,c in modes.items():
   b=batch(c);batches[label]=b;save('batch-'+label,b);compat=call('compute/experiments/'+b['batch']['id']+'/condition-compatibility')
   check('batch compatibility '+label,compat==b['batch']['input']['conditionCompatibility'] and compat['mode']==('legacy_global' if label=='legacy' else 'per_member'))
   candidates=call('compute/experiments/'+b['batch']['id']+'/ol-candidates');save('ol-'+label,candidates)
   observed={x['after']['characterId'] for x in candidates['candidates'] if x['after']['optionId']=='IncElementDmg'};wanted=set(ids) if label=='legacy' else {id for id in ids if roster[id]['element']==c['bossWeakElement']}
   check('OL eligible members '+label,observed==wanted,dict(observed=sorted(observed),expected=sorted(wanted)))
  check('legacy batch exact numerical replay',batches['legacy']['rows'][0]['teamDamage']==oldbatch['rows'][0]['teamDamage'] and batches['legacy']['rows'][0]['members']==oldbatch['rows'][0]['members'])
  check('five mode fingerprints and tuning keys separate',len({b['batch']['input']['fingerprint'] for b in batches.values()})==5 and len({b['batch']['execution']['fingerprint'] for b in batches.values()})==5 and all(b['batch']['execution']['tuning']['cacheSource']=='miss' for b in batches.values()))
  repeated=batch(modes['fire']);check('same mode validated cache reuse',repeated['batch']['input']['fingerprint']==batches['fire']['batch']['input']['fingerprint'] and repeated['batch']['execution']['tuning']['cacheSource']=='validated_policy_cache')
  empty=replay(modes['empty']);save('empty-replay',empty);check('null new mode persisted',empty['conditionCompatibility']['mode']=='per_member' and call('runtime/skill-replays/'+empty['id']+'/condition-compatibility')['mode']=='per_member' and all(not e['hit']['properDistance'] and not e['hit']['elementAdvantage'] for e in empty['result']['damageLog']['entries']))
  invalid=[dict(bossDistance=-1),dict(bossDistance=101),dict(bossDistance=1.5),dict(bossWeakElement='Electric'),dict(bossWeakElement='fire'),dict(bossWeakElement=''),dict(bossDistance=None,properDistance=False),dict(bossWeakElement=None,elementAdvantage=False),dict(bossDistance=35,properDistance=True)]
  for index,c in enumerate(invalid):
   q=request(c);check('compute invalid400 '+str(index),bool(call('compute/experiments',q,code=400)))
   q.pop('runs');q.pop('phase');q.pop('execution');q['scenarioLevel']=400;check('replay invalid400 '+str(index),bool(call('runtime/skill-replays',q,code=400)))
  save('batch-map',batches);report['status']='passed' if all(c['passed'] for c in report['checks']) else 'failed'
 except Exception as ex:report['status']='aborted';report['error']=repr(ex);raise
 finally:
  stop();report['ownApiStopped']=True;report['sourceChanges']=[str(k) for k,h in hashes.items() if digest(source/k)!=h];report['rosterUnchanged']=digest(rosterpath)==record['sha256'];save('summary',report);save('source-hashes',hashes);print('EVIDENCE '+str(run),flush=True)
 return 0 if report['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())

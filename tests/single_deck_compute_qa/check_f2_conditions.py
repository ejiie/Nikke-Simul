"""F2-Q own real API/browser acceptance. No owner tests, oracle, or response mock.
Only public allowlisted inputs and a newly authored synthetic account are used.
"""
import argparse,hashlib,json,os,re,shutil,socket,sqlite3,subprocess,sys,time,uuid
from copy import deepcopy
from pathlib import Path
from playwright.sync_api import sync_playwright
from public_fixture import create,read,digest
from check_client_f32 import context as reference
from check_f32_b1 import normalized
from actual_stats import metric
ROOT=Path(__file__).resolve().parents[2]
PREP=ROOT/'artifacts/single-deck-qa/f2-preparation'

def clean_hit(hit):
 h=deepcopy(hit)
 for field in ['attackBuffs','runtimeAttackBuffs']:
  for b in h.get(field,[]):
   if b.get('rawRate10000') is None:b.pop('rawRate10000',None)
 for b in h.get('attackFlatBuffs',[]):
  if b.get('exactAmount') is None:b.pop('exactAmount',None)
 return normalized(h)

class Session:
 def __init__(self,dotnet):
  self.dotnet=dotnet;self.run=ROOT/'artifacts/single-deck-qa'/('f2-ufix5-'+uuid.uuid4().hex[:12]);self.data=self.run/'data';self.data.mkdir(parents=True)
  self.source=ROOT/'artifacts/single-deck-qa/load1000-3db71912a601/data';self.hashes,self.game,self.snapshot,self.ids=create(self.source,self.data)
  rec=next(r for r in read(ROOT/'docs/p03-source-manifest.json') if r.get('inputKey')=='sourceRoles');self.rosterpath=Path(rec['sourceRoot'])/rec['path'];self.rosterhash=digest(self.rosterpath);assert self.rosterhash==rec['sha256'];self.roster=read(self.rosterpath)['roster']
  subprocess.run([sys.executable,str(ROOT/'tools/data-pipeline/prepare_combat_conditions.py'),'--runtime-root',str(self.data/'runtime'),'--source-roster',str(self.rosterpath)],check=True,capture_output=True)
  shutil.copytree(PREP/'presentation',self.data/'presentation')
  public=ROOT/'artifacts/image-collection-qa/fixed-a2f67a4db2b94cbe8c3661dfbcaec694/origin/presentation'
  self.publichash={}
  for f in [public/'presentation.json',*(public/'assets/ui').glob('*.png')]:
   relative=f.relative_to(public);self.publichash[str(f)]=digest(f);dest=self.data/'presentation'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
  rawid=uuid.uuid4().hex;self.snapshot['rawManifestId']=rawid
  connection=dict(id='qa-f2-connection',accountId=self.snapshot['accountId'],status='ready',nickname='QA synthetic',area=1,updatedAt='2026-09-29T00:00:00Z',choices=[dict(area=1,label='QA synthetic',characterCount=5,openId='synthetic')])
  with sqlite3.connect(self.data/'accounts.db') as db:
   db.execute('UPDATE snapshots SET payload=?',(json.dumps(self.snapshot),));db.execute('CREATE TABLE connections(id TEXT PRIMARY KEY,payload TEXT NOT NULL)');db.execute('INSERT INTO connections VALUES(?,?)',(connection['id'],json.dumps(connection)))
  rawdir=self.data/'raw'/rawid;rawdir.mkdir(parents=True);raw=json.dumps(dict(source='QA_SYNTHETIC',characters=[dict(name_code=i,combat=0) for i in self.ids]));(rawdir/'envelope.json').write_text(raw,encoding='utf-8');(rawdir/'manifest.json').write_text(json.dumps(dict(envelopeHash=hashlib.sha256(raw.encode()).hexdigest())),encoding='utf-8')
  with socket.socket() as s:s.bind(('127.0.0.1',0));self.port=s.getsockname()[1]
  assert self.port not in(5180,5181);self.base=f'http://127.0.0.1:{self.port}';self.process=None;self.log=None;self.token='';self.traffic=[]
  self.report=dict(status='running',checks=[],errors=[],port=self.port,responseMocks=False,product='1168819',scope='synthetic small functional acceptance; U-FIX-4/5 readmission')
  self.env=dict(os.environ,NIKKE_PROJECT_ROOT=str(ROOT),NIKKE_DATA_ROOT=str(self.data),NIKKE_PORT=str(self.port),NIKKE_TEST_FIXTURE='1');self.env.pop('NIKKE_GAME_CATALOG',None)
 def save(self,name,value):(self.run/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
 def check(self,name,ok,detail=None):
  self.report['checks'].append(dict(name=name,passed=bool(ok),detail=detail));self.save('summary',self.report);print(name+(': PASS' if ok else ': FAIL'),flush=True)
 def start(self,api,baseline=False):
  self.api=api;dll=PREP/'baseline-api/Nikke.Api.dll' if baseline else ROOT/'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll'
  self.log=(self.run/f'api-{time.time_ns()}.log').open('w',encoding='utf-8');self.process=subprocess.Popen([self.dotnet,str(dll)],cwd=ROOT,env=self.env,stdout=self.log,stderr=self.log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.report.setdefault('ownedPids',[]).append(self.process.pid)
  for _ in range(300):
   try:self.token=api.get(self.base+'/api/bootstrap').json()['token'];return
   except Exception:time.sleep(.1)
  raise AssertionError('API startup')
 def stop(self):
  if self.process:self.process.terminate();self.process.wait(timeout=30);self.process=None
  if self.log:self.log.close();self.log=None
 def call(self,path,body=None,method=None):
  r=self.api.fetch(self.base+'/api/'+path,method=method or ('GET' if body is None else 'POST'),data=body,headers={'X-Nikke-Token':self.token},timeout=60000)
  try:v=r.json()
  except Exception:v=r.text()
  self.traffic.append(dict(path=path,status=r.status,request=body,response=v));return r,v
 def replay(self,req,label):
  if getattr(self,'reuse',False) and (self.run/(label+'.json')).exists():
   saved=read(self.run/(label+'.json'));assert saved['request']==req;return saved['response']
  r,v=self.call('runtime/skill-replays',req);self.save(label,dict(status=r.status,request=req,response=v));assert r.status==200,v;return v
 def batch(self,req,label):
  # Match the explicit replay AutoBurst input. API otherwise injects the account's
  # separately saved tactic, producing a different rotation even when POST JSON matches.
  request=dict(req,runs=2,phase='pilot',useSavedTactic=False,execution=dict(requested='cpu',maxWorkers=1));request.pop('scenarioLevel',None)
  r,b=self.call('compute/experiments',request);assert r.status in (200,202),b
  for _ in range(600):
   _,b=self.call('compute/experiments/'+b['id'])
   if b['state'] in ['completed','failed','cancelled']:break
   time.sleep(.1)
  self.check(label+' completed two',b['state']=='completed' and b['valid']==2,b)
  _,rows=self.call('compute/experiments/'+b['id']+'/results');_,stats=self.call('compute/experiments/'+b['id']+'/statistics');metric(stats['team'],[x['teamDamage'] for x in rows['runs']]);self.check(label+' independent statistics',True)
  self.save(label,dict(request=request,batch=b,results=rows,statistics=stats));return b,rows,stats
 def finish(self):
  self.stop();self.report['ownApiStopped']=True;self.check('public input hashes preserved',all(digest(self.source/k)==v for k,v in self.hashes.items()) and digest(self.rosterpath)==self.rosterhash and all(digest(Path(k))==v for k,v in self.publichash.items()))
  self.check('package-lock preserved',digest(ROOT/'package-lock.json')=='2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767')
  if self.report['status']!='aborted':self.report['status']='passed' if all(c['passed'] for c in self.report['checks']) else 'failed'
  self.report['passed']=sum(c['passed'] for c in self.report['checks']);self.report['failed']=[c for c in self.report['checks'] if not c['passed']]
  self.save('source-hashes',dict(public=self.hashes,presentation=self.publichash,roster=self.rosterhash));self.save('traffic',self.traffic);self.save('summary',self.report);print('EVIDENCE '+str(self.run),flush=True)

def api_checks(s,api):
 check=s.check;ids=s.ids
 s.start(api,baseline=True)
 assert s.call('accounts/synthetic-account/formation',dict(slots=ids),'PUT')[0].ok
 tactic=dict(schemaVersion=1,allowedCharacterIds=ids,stage1Priority=[ids[0]],stage2Priority=[ids[1]],stage3Priority=ids[2:],burst3Rotation=ids[2:],unavailablePolicy='next_ready')
 assert s.call('accounts/synthetic-account/burst-tactic',dict(snapshotId=s.snapshot['id'],formationSlots=ids,tactic=tactic),'PUT')[0].ok
 oldreq=dict(snapshotId=s.snapshot['id'],characterIds=ids,scenarioLevel=400,conditions=dict(roundingPolicy='client_f32',combat=dict(durationFrames=120,enemyDefense=31784,critMode='off',pelletCoefficientPolicy='per_pellet',properDistance=True,elementAdvantage=False)))
 old=s.replay(oldreq,'baseline-pre-F2');oldpath=s.data/'skill-replays'/(old['id']+'.json');oldbytes=oldpath.read_bytes();s.stop();s.start(api)
 legacy=s.replay(dict(oldreq,conditionProfile='legacy'),'legacy-reproduction')
 check('pre-F2 fixed legacy exact team/member/effects',legacy['result']['totalDamage']==old['result']['totalDamage'] and legacy['result']['members']==old['result']['members'])
 check('legacy preserved duration DEF pellet crit',legacy['battleConditions']['profile']=='legacy' and all(legacy['result']['conditions']['combat'][k]==v for k,v in oldreq['conditions']['combat'].items()))
 for suffix in ['', '/export.json']:
  r,_=s.call('runtime/skill-replays/'+old['id']+suffix);check('old raw bytes '+suffix,r.body()==oldbytes and oldpath.read_bytes()==oldbytes)
 _,bc=s.call('runtime/skill-replays/'+old['id']+'/battle-conditions');check('old display does not rewrite',bc['profile']=='legacy' and bc['initialDefense']==31784 and bc['durationFrames']==120 and oldpath.read_bytes()==oldbytes)
 default=dict(snapshotId=s.snapshot['id'],characterIds=ids,scenarioLevel=400,conditions=dict(combat={}))
 new=s.replay(default,'default-new');c=new['result']['conditions']['combat'];bc=new['battleConditions']
 check('new omitted defaults 180s auto sample per_trigger',all(c[k]==v for k,v in dict(durationFrames=10800,enemyDefense=30925,defenseMode='team_damage_threshold',critMode='sample',pelletCoefficientPolicy='per_trigger').items()))
 check('battleConditions saved and GET',bc['profile']=='solo_raid' and s.call('runtime/skill-replays/'+new['id']+'/battle-conditions')[1]==bc)
 check('dummy default',new['boss']['id']=='dummy')
 # Deterministic public synthetic formation; attack window is QA supplied, not a real user deck.
 req=deepcopy(default);req['conditions']=dict(roundingPolicy='client_f32',autoBurst=dict(stageDelayMinFrames=1,stageDelayMaxFrames=1),combat=dict(critMode='off',bossDistance=35,bossWeakElement='Fire',attackBuffWindows=[dict(characterId=i,buff=dict(source='QA synthetic +6300%',rate=63),startFrame=1,endFrame=10801) for i in ids]))
 logs=[];first=None
 for id in ids:
  rr=deepcopy(req);rr['conditions']['damageLog']=dict(characterId=id);v=s.replay(rr,'crossing-'+id)
  if first is None:first=v
  check('deterministic logged run '+id,v['result']['totalDamage']==first['result']['totalDamage'] and v['result']['defense']==first['result']['defense'])
  log=v['result']['damageLog'];check('all hits untruncated '+id,not log['truncated'] and log['eventCount']==len(log['entries']));logs.extend(dict(e,characterId=id) for e in log['entries'])
 logs.sort(key=lambda e:e['hitId']);total=0;transition=None;bad=[];by={}
 for ordinal,e in enumerate(logs,1):
  defense=30925 if total<=2000000000 else 31784;h=clean_hit(e['hit']);h['defense']=defense;damage=reference(h)['damage']
  if damage!=e['damage'] or e['hit']['defense']!=defense:bad.append(dict(hit=e['hitId'],expected=damage,actual=e['damage'],expectedDefense=defense))
  total+=damage;by[e['characterId']]=by.get(e['characterId'],0)+damage
  if transition is None and total>2000000000:transition=dict(frame=e['frame'],hitTraceId=e['hitId'],hitOrdinal=ordinal,characterId=e['characterId'],effect=e['effect'],cumulativeDamage=total,previousDefense=30925,newDefense=31784)
 s.save('independent-prefix-audit',dict(hits=len(logs),errors=bad,total=total,members=by,transition=transition))
 check('independent all API hits arithmetic and prefix DEF',not bad,dict(hits=len(logs),errors=bad[:4]))
 check('independent API transition metadata',transition is not None and transition==first['result']['defense']['switchAfterHit'],transition)
 check('independent team = every member = every hit',total==first['result']['totalDamage']==sum(m['damage'] for m in first['result']['members']) and all(by[m['characterId']]==m['damage'] for m in first['result']['members']))
 a,rows,_=s.batch(req,'automatic-batch');check('replay=CPU compute transition/damage',all(r['teamDamage']==total and r['defense']==first['result']['defense'] for r in rows['runs']))
 check('compute saved battleConditions/get',a['input']['battleConditions']==first['battleConditions'] and s.call('compute/experiments/'+a['id']+'/battle-conditions')[1]==a['input']['battleConditions'])
 named=deepcopy(req);named['bossId']='solo-raid-42';b,rows2,_=s.batch(named,'boss-only-batch')
 check('boss-only metadata persists',b['input']['boss']['name']=='앨트루이아' and b['input']['boss']['id']=='solo-raid-42')
 check('boss-only fingerprint tuning key damage identical',a['input']['fingerprint']==b['input']['fingerprint'] and a['execution']['fingerprint']==b['execution']['fingerprint'] and [r['teamDamage'] for r in rows['runs']]==[r['teamDamage'] for r in rows2['runs']])
 fixed=deepcopy(req);fixed['conditionProfile']='legacy';fixed['conditions']['combat'].update(durationFrames=10800,enemyDefense=30925,pelletCoefficientPolicy='per_trigger')
 f,_,_=s.batch(fixed,'fixed-batch');check('fixed/automatic fingerprint and tuning separation',f['input']['fingerprint']!=a['input']['fingerprint'] and f['execution']['fingerprint']!=a['execution']['fingerprint'] and f['input']['defPolicy']!=a['input']['defPolicy'])
 # Cache reuse on worker1 is policy acceptance, no timing comparison or optimization claim.
 s.save('keys',dict(auto=a['execution'],boss=b['execution'],fixed=f['execution']))
 r,bosses=s.call('presentation/solo-raid-bosses');s.save('boss-list',bosses)
 names=['마더 웨일','블랙스미스','하베스터','알트아이젠','화이트 스미스','모더니아','울트라','토커티브','마테리얼 H','크리스탈 체임버','스톰브링어','니힐리스타','인디빌리아','그레이브 디거','황금 크라켄','미러 컨테이너','거대 질량체','랜드 이터','베히모스','백빙룡','모더니아','마테리얼 H','거대 질량체 Q','검은 뱀','글러트니','프로비던스','환영 크라켄','지즈','마더 웨일','차가운 심판자','퀸 001','알트아이젠','온리 원','앨트루이아','크리스탈 체임버','에고비스타','울트라','애니힐리오','아일랜드 이터','사치스러운 거미','리버렐리오 바디','앨트루이아']
 check('43 Korean cards no exclusions',r.status==200 and bosses['complete'] and not bosses['diagnostics'] and len(bosses['bosses'])==43 and all(x['name']==names[x['season']-1] for x in bosses['bosses'] if x['season']))
 check('public boss shape excludes English/source/monster ids',all(set(x)=={'id','name','imageUrl','season'} and (x['id']=='dummy' or x['id']=='solo-raid-'+str(x['season'])) for x in bosses['bosses']))
 for x in bosses['bosses']:
  if x['imageUrl']:
   rr=api.get(s.base+x['imageUrl']);path=s.data/'presentation'/x['imageUrl'].removeprefix('/editor/');check('boss image '+str(x['season']),rr.status==200 and rr.body()==path.read_bytes() and re.fullmatch(r'/editor/assets/bosses/[0-9a-f]{32}\.png',x['imageUrl']) is not None)
 for path in ['/editor/solo-raid-bosses.manifest.json','/editor/boss-sources/enikk.json','/api/presentation/solo-raid-bosses.manifest.json']:
  check('private boss source inaccessible '+path,api.get(s.base+path).status==404)
 def counts():
  with sqlite3.connect(s.data/'compute/batches.db') as db:n=db.execute('select count(*) from experiments').fetchone()[0]
  return n,{str(p):digest(p) for p in (s.data/'skill-replays').glob('*.json')}
 before=counts();invalid=[]
 for field,values in [('durationFrames',[120,None,'10800',10801]),('pelletCoefficientPolicy',['per_pellet',None,1]),('defenseMode',['fixed',None,'auto']),('enemyDefense',[-1,.5,None,'30925']),('critMode',['invalid']),('DurationFrames',[10800])]:
  for value in values:rr=deepcopy(default);rr['conditions']['combat'][field]=value;invalid.append((field+repr(value),rr))
 invalid.extend([('unknown boss',dict(default,bossId='no-such-boss')),('unknown profile',dict(default,conditionProfile='invalid'))])
 for label,rr in invalid:
  for path in ['runtime/skill-replays','compute/experiments']:
   body=rr if path.startswith('runtime') else dict(rr,runs=1,phase='pilot',execution=dict(requested='cpu',maxWorkers=1))
   r,error=s.call(path,body);check('reject '+label+' '+path,r.status==400,error)
 check('invalid requests no storage',counts()==before)
 canonical=deepcopy(default);canonical['conditions']['combat']['enemyDefense']=31784;canon=s.replay(canonical,'canonical-defense');check('supplied numeric defense canonicalized',canon['result']['conditions']['combat']['enemyDefense']==30925)
 s.req=req;s.first=first;s.old=old;s.legacyRequest=dict(oldreq,conditionProfile='legacy');s.bosses=bosses

def main():
 p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);p.add_argument('--api-only',action='store_true');p.add_argument('--reuse',type=Path);args=p.parse_args()
 if args.reuse:
  s=object.__new__(Session);s.dotnet=args.dotnet;s.run=args.reuse.resolve();assert s.run.is_relative_to(ROOT/'artifacts/single-deck-qa');s.data=s.run/'data';s.source=ROOT/'artifacts/single-deck-qa/load1000-3db71912a601/data'
  hashes=read(s.run/'source-hashes.json');s.hashes=hashes['public'];s.publichash=hashes['presentation'];s.rosterhash=hashes['roster'];rec=next(r for r in read(ROOT/'docs/p03-source-manifest.json') if r.get('inputKey')=='sourceRoles');s.rosterpath=Path(rec['sourceRoot'])/rec['path'];s.roster=read(s.rosterpath)['roster'];s.game=read(s.data/'game-catalog.json')
  with sqlite3.connect(s.data/'accounts.db') as db:s.snapshot=json.loads(db.execute('select payload from snapshots').fetchone()[0])
  s.ids=[x['characterId'] for x in s.snapshot['characters']];s.report=read(s.run/'summary.json')
  assert subprocess.run(['git','diff','--quiet',s.report['product'],'--','src','apps','tools'],cwd=ROOT).returncode==0,'reuse requires the same product tree'
  s.save('prior-attempt-'+str(time.time_ns()),s.report);s.report.update(status='running',checks=[],errors=[],ownApiStopped=False);s.report.pop('error',None)
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));s.port=sock.getsockname()[1]
  assert s.port not in(5180,5181);s.report['port']=s.port;s.base=f'http://127.0.0.1:{s.port}';s.process=None;s.log=None;s.token='';s.traffic=read(s.run/'traffic.json');s.reuse=True
  s.env=dict(os.environ,NIKKE_PROJECT_ROOT=str(ROOT),NIKKE_DATA_ROOT=str(s.data),NIKKE_PORT=str(s.port),NIKKE_TEST_FIXTURE='1');s.env.pop('NIKKE_GAME_CATALOG',None)
 else:s=Session(args.dotnet)
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport=dict(width=1500,height=1000));ctx.tracing.start(screenshots=True,snapshots=True,sources=True)
   api_checks(s,ctx.request)
   if not args.api_only:
    from check_f2_browser import browser_checks
    browser_checks(s,ctx)
    from check_f2_profile_regression import verify
    verify(s,ctx)
   ctx.tracing.stop(path=str(s.run/'trace.zip'));browser.close();s.report['status']='passed' if all(c['passed'] for c in s.report['checks']) else 'failed'
 except Exception as ex:s.report['status']='aborted';s.report['error']=repr(ex);raise
 finally:s.finish()
 return 0 if s.report['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())

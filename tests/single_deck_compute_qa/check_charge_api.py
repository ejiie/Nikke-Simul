"""E-BUG-1 QA: actual old/new API, own account, old records, cache and browser."""
import argparse,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
from copy import deepcopy
from playwright.sync_api import sync_playwright
from check_f2_conditions import Session,ROOT
from public_fixture import read,digest

OUT=ROOT/'artifacts/single-deck-qa/ebug1'
class ChargeSession(Session):
 def start_binary(self,api,folder):
  self.api=api;self.log=(self.run/('api-'+folder.name+'.log')).open('w',encoding='utf-8')
  self.process=subprocess.Popen([self.dotnet,str(folder/'Nikke.Api.dll')],cwd=ROOT,env=self.env,stdout=self.log,stderr=self.log,creationflags=subprocess.CREATE_NO_WINDOW)
  self.report.setdefault('ownedPids',[]).append(self.process.pid)
  for _ in range(300):
   try:self.token=api.get(self.base+'/api/bootstrap').json()['token'];return
   except Exception:time.sleep(.1)
  raise AssertionError('API startup')

def main():
 p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args();s=ChargeSession(a.dotnet)
 s.report.update(product='d932716',scope='E-BUG-1 independent QA')
 (OUT/'api-evidence.txt').write_text(str(s.run),encoding='utf-8')
 # Replace ONLY public table copies in our own data root with today's authorized tables.
 before=read(OUT/'public-hashes-before.json');public=OUT/'public-copy'
 for relative in before:
  target=s.data/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(public/relative,target)
 s.snapshot['gameSnapshotId']=read(public/'game-catalog.json')['id']
 for member in s.snapshot['characters']:
  for equipment in member['equipment']:
   equipment['tier']=0;equipment['lines']=[dict(lineIndex=i,presence='absent') for i in range(1,4)]
 with sqlite3.connect(s.data/'accounts.db') as db:db.execute('UPDATE snapshots SET payload=?',(json.dumps(s.snapshot),))
 s.save('synthetic-account',s.snapshot)
 tactic=dict(schemaVersion=1,allowedCharacterIds=s.ids,stage1Priority=[s.ids[0]],stage2Priority=[s.ids[1]],stage3Priority=s.ids[2:],burst3Rotation=s.ids[2:],unavailablePolicy='next_ready')
 request=dict(snapshotId=s.snapshot['id'],characterIds=s.ids,scenarioLevel=400,conditionProfile='legacy',conditions=dict(roundingPolicy='final_round_even',autoBurst=dict(tactic=tactic),combat=dict(durationFrames=10800,enemyDefense=30925,critMode='sample',core=True,pelletCoefficientPolicy='per_trigger',manualCharacterId='5004',manualStyle='full_charge',trace=True,traceLimit=4000),damageLog=dict(characterId='5004')))
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport=dict(width=1550,height=1100));ctx.tracing.start(screenshots=True,snapshots=True,sources=True)
   s.start_binary(ctx.request,OUT/'baseline-api')
   assert s.call('accounts/synthetic-account/formation',dict(slots=s.ids),'PUT')[0].ok
   old=s.replay(request,'old-manual');(OUT/'public-input.json').write_text(json.dumps(old),encoding='utf-8')
   oldbytes=(s.data/'skill-replays'/(old['id']+'.json')).read_bytes()
   oldbatch,oldrows,oldstats=s.batch(request,'old-batch')
   tuning=s.data/'compute/tuning';oldcache={str(f.relative_to(tuning)):digest(f) for f in tuning.rglob('*') if f.is_file()}
   s.stop();s.start_binary(ctx.request,ROOT/'src/Nikke.Api/bin/Release/net10.0')
   new=s.replay(request,'new-manual')
   s.check('same public members and conditions across API versions',old['inputs']==new['inputs'] and old['result']['conditions']==new['result']['conditions'])
   for suffix in ['', '/export.json']:
    r,_=s.call('runtime/skill-replays/'+old['id']+suffix);s.check('old replay bytes preserved '+suffix,r.body()==oldbytes)
   for suffix,expected in [('/results',oldrows),('/statistics',oldstats)]:
    r,v=s.call('compute/experiments/'+oldbatch['id']+suffix);s.check('old compute readable '+suffix,r.status==200 and v==expected)
   r,v=s.call('compute/experiments/'+oldbatch['id']+'/resume',{},'POST');s.check('old compute resume refused',r.status==409 and 'engine_or_rules_version_changed' in json.dumps(v),dict(status=r.status,response=v))
   newbatch,_,_=s.batch(request,'new-batch')
   s.check('rules implementation and fingerprint separated',all(oldbatch['input'][k]!=newbatch['input'][k] for k in ['engineVersion','rulesVersion','summaryVersion','fingerprint']) and oldbatch['execution']['fingerprint']!=newbatch['execution']['fingerprint'])
   s.check('old tuning cache bytes retained',all((tuning/k).exists() and digest(tuning/k)==v for k,v in oldcache.items()),oldcache)
   s.save('cache-separation',dict(old=oldcache,new={str(f.relative_to(tuning)):digest(f) for f in tuning.rglob('*') if f.is_file()},oldExecution=oldbatch['execution'],newExecution=newbatch['execution']))
   last={};bad=[]
   for e in new['result']['events']:
    expected=None
    if e['kind']=='shot':
     if e['source'] in last:expected=e['frame']-last[e['source']]
     last[e['source']]=e['frame']
    if e.get('shotIntervalFrames')!=expected:bad.append(e)
   s.check('all actual API trace intervals match same-character frame differences',not bad and len(last)==5,dict(events=len(new['result']['events']),bad=bad[:2]))
   # UI controls are exercised separately by check_charge_browser.py, without interception.
   ctx.tracing.stop(path=str(s.run/'trace.zip'));browser.close()
 except Exception as ex:s.report.update(status='aborted',error=repr(ex));raise
 finally:
  original=Path('C:/Users/user/Documents/GitHub/Nikke-Simul/data/local');after={k:digest(original/k) for k in before};s.save('original-public-hashes',dict(before=before,after=after));s.check('authorized original public tables hashes preserved',before==after)
  s.finish()
 return int(s.report['status']!='passed')
if __name__=='__main__':raise SystemExit(main())

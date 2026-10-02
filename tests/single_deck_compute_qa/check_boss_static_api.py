"""B-DATA-1 independent live API mutation and before/after regression suite."""
import argparse,json,sqlite3,shutil
from copy import deepcopy
from pathlib import Path
from playwright.sync_api import sync_playwright
from check_charge_api import ChargeSession
from check_f2_conditions import ROOT
from public_fixture import read,digest
OUT=ROOT/'artifacts/single-deck-qa/bdata1'
def stripnull(x):
 if isinstance(x,dict):return {k:stripnull(v) for k,v in x.items() if v is not None}
 if isinstance(x,list):return [stripnull(v) for v in x]
 return x
def get(x,path):
 for k in path:x=x[k]
 return x
def numbers(x,path=()):
 if isinstance(x,dict):
  for k,v in x.items():yield from numbers(v,path+(k,))
 elif isinstance(x,list):
  if x:yield from numbers(x[0],path+(0,))
 elif type(x)==int:yield path,x
def main():
 p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args();s=ChargeSession(a.dotnet);s.report.update(product='2c41185',scope='B-DATA-1 independent API')
 (OUT/'api-evidence.txt').write_text(str(s.run),encoding='utf-8');catalog=read(OUT/'presentation/solo-raid-boss-attributes.json');file=s.data/'presentation/solo-raid-boss-attributes.json';endpoint='presentation/solo-raid-bosses/attributes'
 # Reuse only our own publicly hashed E-PREC inputs, never original presentation/account files.
 public=ROOT/'artifacts/single-deck-qa/precision1/public-copy';hashes=read(ROOT/'artifacts/single-deck-qa/precision1/public-hashes-before.json')
 for rel,h in hashes.items():
  assert digest(public/rel)==h;dest=s.data/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(public/rel,dest)
 s.snapshot['gameSnapshotId']=read(public/'game-catalog.json')['id']
 with sqlite3.connect(s.data/'accounts.db') as db:db.execute('UPDATE snapshots SET payload=?',(json.dumps(s.snapshot),))
 def write(c):file.write_text(json.dumps(c,ensure_ascii=False),encoding='utf-8')
 def mutate(label,path,value=None,delete=False,expected=409):
  c=deepcopy(catalog);parent=get(c,path[:-1])
  if delete:del parent[path[-1]]
  else:parent[path[-1]]=value
  write(c);r,v=s.call(endpoint);s.check(label,r.status==expected,dict(status=r.status,path=path,response=v if r.status!=expected else None))
  if r.status!=expected:s.save('failure-'+str(len(s.report['checks'])),dict(label=label,input=c,status=r.status,response=v))
  return v
 tactic=dict(schemaVersion=1,allowedCharacterIds=s.ids,stage1Priority=[s.ids[0]],stage2Priority=[s.ids[1]],stage3Priority=s.ids[2:],burst3Rotation=['5004','5044'],unavailablePolicy='next_ready')
 req=dict(snapshotId=s.snapshot['id'],characterIds=s.ids,scenarioLevel=400,conditionProfile='legacy',conditions=dict(roundingPolicy='client_f32',autoBurst=dict(tactic=tactic,stageDelayMinFrames=1,stageDelayMaxFrames=1),combat=dict(durationFrames=10800,enemyDefense=30925,critMode='off',core=True,pelletCoefficientPolicy='per_trigger',manualCharacterId='5004',manualStyle='full_charge')))
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport=dict(width=1550,height=1050));api=ctx.request
   s.start_binary(api,OUT/'baseline-api');r,oldlist=s.call('presentation/solo-raid-bosses');oldlistbytes=r.body();old=s.replay(req,'before-replay');batch,rows,stats=s.batch(req,'before-compute');oldfile=s.data/'skill-replays'/(old['id']+'.json');saved=oldfile.read_bytes();s.stop()
   s.start_binary(api,ROOT/'src/Nikke.Api/bin/Release/net10.0');r,v=s.call(endpoint);s.check('not prepared explicit',r.status==200 and v['bosses']==[] and any(d['code']=='boss_attributes_not_prepared' for d in v['diagnostics']))
   write(catalog);r,v=s.call(endpoint);s.save('valid-wire',v);s.check('production prepared file exact wire',r.status==200 and stripnull(v)==stripnull(catalog));s.check('40 zero defenceRatioRate values preserved',sum(b.get('defenceRatioRate')==0 for b in v['bosses'])==40)
   s.check('existing boss list exact bytes unchanged',s.call('presentation/solo-raid-bosses')[0].body()==oldlistbytes)
   after=s.replay(req,'after-replay');s.check('180s five-member prepared inputs and conditions exact',old['result']['conditions']==after['result']['conditions'] and old['inputs']==after['inputs']);s.check('old saved replay bytes and export',all(s.call('runtime/skill-replays/'+old['id']+suffix)[0].body()==saved for suffix in ['','/export.json']) and oldfile.read_bytes()==saved)
   # APIs do not take an RNG seed: skill chance procs remain random with crit off.
   # Full same-seed result equality is covered by our PrecisionProbe, not an unseeded comparison here.
   batch2,rows2,stats2=s.batch(req,'after-compute');s.check('compute fingerprint execution unchanged',batch['input']['fingerprint']==batch2['input']['fingerprint'] and batch['execution']['fingerprint']==batch2['execution']['fingerprint']);s.check('historical compute results statistics retained',s.call('compute/experiments/'+batch['id']+'/results')[1]==rows and s.call('compute/experiments/'+batch['id']+'/statistics')[1]==stats)
   for boss in ['solo-raid-1','solo-raid-33','solo-raid-41','solo-raid-42']:
    r=s.replay(dict(req,bossId=boss),'metadata-'+boss);s.check('boss attributes not used in prepared inputs '+boss,r['result']['conditions']==after['result']['conditions'] and r['inputs']==after['inputs'])
   # Mutate one field per request, including all nested numeric DTO kinds.
   for path,value in numbers(catalog):
    # Top-level nullable attributes are validated separately. Strict nested DTO numbers have no defaults.
    if path[:2]==('bosses',0) and len(path)==3:continue
    label='/'.join(map(str,path))
    for mode,replacement,delete in [('missing',None,True),('null',None,False),('string',str(value),False),('fraction',.25,False),('overflow',2**64,False)]:
     if mode=='missing' and isinstance(path[-1],int):continue
     if mode=='null' and (path[-1] in ('rangeTo','records') or path==('diagnostics',0,'season')):continue
     mutate('strict '+label+' '+mode,path,replacement,delete)
   for label,path in [('challenge',('bosses',0,'challenge','stats')),('step',('bosses',0,'challenge','levelChange','steps',0,'stats'))]:
    mutate('undeclared null '+label,path)
    c=deepcopy(catalog);get(c,path[:-1])[path[-1]]=None;c['bosses'][0]['unconfirmed'].append('challenge_level_stats' if label=='challenge' else 'level_change_step_'+str(c['bosses'][0]['challenge']['levelChange']['steps'][0]['step'])+'_stats');write(c);r,v=s.call(endpoint);s.check('declared null '+label+' retains other values',r.status==200 and get(v,path) is None and v['bosses'][0]['parts']==catalog['bosses'][0]['parts'])
   for path in [('bosses',0,'element'),('bosses',0,'element','weakKey')]:
    mutate('undeclared null '+str(path),path)
    c=deepcopy(catalog);get(c,path[:-1])[path[-1]]=None;c['bosses'][0]['unconfirmed'].append('element' if path[-1]=='element' else 'weak_element');write(c);r,v=s.call(endpoint);s.check('declared element null '+str(path),r.status==200 and get(v,path) is None)
   for path in [('bosses',0),('bosses',0,'parts',0),('bosses',0,'ladder',0),('bosses',0,'challenge','levelChange','steps',0),('diagnostics',0),('fields',0),('bosses',0,'unconfirmed',0)]:
    # JSON nullable annotations do not enforce collection item nullability; verify behavior explicitly.
    if isinstance(get(catalog,path[:-1]),list) and not get(catalog,path[:-1]):continue
    mutate('reject null collection member '+str(path),path)
   c=deepcopy(catalog);c['bosses'][0]['challenge']['stats'].update(hp=0,attack=0,defence=0);c['bosses'][0]['parts'][0].update(hpRatio=0,damageHpRatio=0,defenceRatio=0);write(c);r,v=s.call(endpoint);s.check('actual zero nested values preserved',r.status==200 and v['bosses'][0]['challenge']['stats']==c['bosses'][0]['challenge']['stats'] and v['bosses'][0]['parts']==c['bosses'][0]['parts'])
   for text in ['{','null','[]']:
    file.write_text(text,encoding='utf-8');r,v=s.call(endpoint);s.check('malformed root '+text,r.status==409,dict(status=r.status,response=v))
   write(catalog);page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(s.base+'/editor/');page.wait_for_timeout(1800);page.screenshot(path=str(s.run/'editor.png'),full_page=True);s.save('browser',dict(errors=errors,text=page.locator('body').inner_text()));s.check('actual editor module load',not errors and '솔로' in page.locator('body').inner_text(),errors)
   # Even a corrupt display-only file must not poison independent existing APIs or execution.
   file.write_text('{',encoding='utf-8');r=s.replay(req,'corrupt-display-replay');s.check('corrupt display catalog cannot change prepared calculation inputs',r['result']['conditions']==after['result']['conditions'] and r['inputs']==after['inputs']);s.check('corrupt display catalog cannot change boss list',s.call('presentation/solo-raid-bosses')[0].body()==oldlistbytes);write(catalog)
   browser.close()
 except Exception as ex:s.report.update(status='aborted',error=repr(ex));raise
 finally:s.finish()
 return int(s.report['status']!='passed')
if __name__=='__main__':raise SystemExit(main())

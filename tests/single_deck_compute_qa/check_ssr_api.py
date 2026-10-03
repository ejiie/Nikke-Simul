"""S-SKILL-1 actual isolated API runs with a new ten-member synthetic account."""
import argparse,json,sqlite3,shutil,math
from fractions import Fraction
from copy import deepcopy
from pathlib import Path
from playwright.sync_api import sync_playwright
from check_charge_api import ChargeSession
from check_f2_conditions import ROOT,clean_hit
from check_client_f32 import context as damage_reference
from public_fixture import read,digest
OUT=ROOT/'artifacts/single-deck-qa/ssr1'
def main(product='20a0609',summary_changed=False,extension=None):
 p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args();s=ChargeSession(a.dotnet);s.report.update(product=product,scope='S-SKILL-1 own actual API')
 (OUT/'api-evidence.txt').write_text(str(s.run),encoding='utf-8');public=ROOT/'artifacts/single-deck-qa/precision1/public-copy'
 for rel,h in read(ROOT/'artifacts/single-deck-qa/precision1/public-hashes-before.json').items():
  assert digest(public/rel)==h;target=s.data/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(public/rel,target)
 s.snapshot['gameSnapshotId']=read(public/'game-catalog.json')['id'];template=deepcopy(s.snapshot['characters'][0])
 for m in s.snapshot['characters']:
  for eq in m['equipment']:eq.update(tier=0,lines=[dict(lineIndex=i,presence='absent') for i in range(1,4)])
 template=deepcopy(s.snapshot['characters'][0])
 for id in ['5012','5001','5129','5105','5101']:
  m=deepcopy(template);m.update(characterId=id,name=s.game['names'][id]);s.snapshot['characters'].append(m)
 def account(lv=10):
  for m in s.snapshot['characters']:m['skills']={str(i):lv for i in [1,2,3]}
  with sqlite3.connect(s.data/'accounts.db') as db:db.execute('UPDATE snapshots SET payload=?',(json.dumps(s.snapshot),))
 account();s.save('synthetic-account',s.snapshot)
 oracle=read(OUT/'independent-oracle.json');newid=read(OUT/'runtime/current.json')['id']
 req=dict(snapshotId=s.snapshot['id'],characterIds=s.ids,scenarioLevel=400,conditionProfile='legacy',conditions=dict(roundingPolicy='client_f32',combat=dict(durationFrames=10800,enemyDefense=30925,critMode='off',core=True,pelletCoefficientPolicy='per_trigger')))
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport=dict(width=1500,height=1000));api=ctx.request
   s.start_binary(api,ROOT/'artifacts/single-deck-qa/bdata1/baseline-api');old=s.replay(req,'director-baseline');ob,orr,ost=s.batch(req,'director-batch');s.stop()
   s.start_binary(api,ROOT/'src/Nikke.Api/bin/Release/net10.0');same=s.replay(req,'new-engine-old-catalog');nb,_,_=s.batch(req,'new-engine-old-catalog-batch')
   # Adding WeaponChange:null to SkillBody changes graph serialization and thus fingerprint even for old catalogs.
   unchanged=['rulesVersion','dataVersion'] if summary_changed else ['rulesVersion','engineVersion','summaryVersion','dataVersion']
   s.check('old catalog unchanged versions and dataVersion retained',all(ob['input'][k]==nb['input'][k] for k in unchanged))
   if summary_changed:s.check('summary version intentionally raised',ob['input']['summaryVersion']=='cpu-summary.6-precision-1' and nb['input']['summaryVersion']=='cpu-summary.7-run-policies')
   s.check('new graph shape safely splits old fingerprint',ob['input']['fingerprint']!=nb['input']['fingerprint'] and ob['execution']['fingerprint']!=nb['execution']['fingerprint']);s.stop()
   shutil.copytree(OUT/'runtime',s.data/'runtime',dirs_exist_ok=True);s.start_binary(api,ROOT/'src/Nikke.Api/bin/Release/net10.0');rr,summary=s.call('runtime/catalog');s.save('catalog-support',summary);support={c['characterId']:c['support'] for c in summary['characters']}
   s.check('new catalog version and ten entries',rr.status==200 and summary['runtimeDataId']==newid and len(support)==10)
   for id in ['5012','5001']:s.check('supported ten levels '+id,support[id]['allLevelsExecutable'] and all(not l['unsupported'] for l in support[id]['levels']))
   for id in ['5129','5105','5101']:s.check('unsupported ten levels '+id,not support[id]['allLevelsExecutable'] and all(l['unsupported'] for l in support[id]['levels']))
   cb,_,_=s.batch(req,'new-catalog-batch');s.check('new catalog dataVersion and fingerprints separate',cb['input']['dataVersion']!=nb['input']['dataVersion'] and cb['input']['fingerprint']!=nb['input']['fingerprint'] and cb['execution']['fingerprint']!=nb['execution']['fingerprint']);s.check('rules unchanged for expanded catalog',all(cb['input'][k]==nb['input'][k] for k in ['rulesVersion','engineVersion','summaryVersion']))
   s.check('old replay and compute results survive catalog switch',s.call('runtime/skill-replays/'+old['id'])[1]==old and s.call('compute/experiments/'+ob['id']+'/results')[1]==orr and s.call('compute/experiments/'+ob['id']+'/statistics')[1]==ost)
   for lv in [1,5,10]:
    account(lv)
    for id in ['5012','5001']:
     facts=next(x for x in oracle[id]['profiles'] if x['level']==lv);body=facts['body'];coefficient=body['skill_value_data'][0]['skill_value']/10000;sid=oracle[id]['skills']['burst']['levels'][str(lv)]['skill_id']
     for control in ['auto','manual']:
      r=dict(snapshotId=s.snapshot['id'],characterIds=[id],scenarioLevel=400,conditionProfile='legacy',conditions=dict(roundingPolicy='client_f32',casts=[dict(frame=11,characterId=id)],combat=dict(durationFrames=1200,enemyDefense=30925,critMode='off',core=True,pelletCoefficientPolicy='per_trigger',trace=True,traceLimit=12000),damageLog=dict(characterId=id)))
      if control=='manual':r['conditions']['combat'].update(manualCharacterId=id,manualStyle='full_charge')
      label=id+'-'+str(lv)+'-'+control;v=s.replay(r,label);(OUT/('input-'+label+'.json')).write_text(json.dumps(v),encoding='utf-8');result=v['result'];events=result['events'];log=result['damageLog']['entries'];hits=[e for e in log if e.get('skillId')==sid and e['hit']['damageType']=='normal'];replacement=[e for e in events if e['kind']=='replacement_weapon'];restore=[e for e in events if e['kind']=='weapon_restored']
      s.check('one replacement shot '+label,len(hits)==1 and len(replacement)==1 and len(restore)==1)
      if hits:
       h=hits[0];expectedFrame=11+math.ceil(float(facts['chargeSeconds'])*60)-1
       s.check('provisional immediate full-charge frame '+label,h['frame']==expectedFrame,dict(expected=expectedFrame,actual=h['frame']))
       s.check('raw coefficient charge pierce '+label,h['hit']['coefficient']==coefficient and h['hit']['chargeBase']==float(Fraction(facts['fullChargeMultiplier'])))
       s.check('charged and pierce flag '+label,h['hit']['fullCharge'] and h['hit']['chargeApplicable'] and h['hit']['pierce'])
      s.check('every replacement trace labelled '+label,replacement and all(e['basis'].startswith('provisional_motion_policy:') for e in replacement))
      s.check('partial support explicit limitation '+label,any('provisional policy' in x and 'pierce multi-hit on parts is not modelled' in x for x in result['limitations']))
      bad=[e['hitId'] for e in log if damage_reference(clean_hit(e['hit']))['damage']!=e['damage']];s.check('independent all logged hit damage '+label,not bad,dict(hits=len(log),bad=bad[:3]))
      saved=s.data/'skill-replays'/(v['id']+'.json');before=saved.read_bytes();s.check('saved reload and export bytes '+label,all(s.call('runtime/skill-replays/'+v['id']+suffix)[0].body()==before for suffix in ['','/export.json']) and saved.read_bytes()==before)
     # Trace disabled still has the provisional/partial limitation; manual tap cannot silently become full charge.
     r['conditions']['combat'].update(trace=False);v=s.replay(r,'untraced-'+id+'-'+str(lv));s.check('untraced result retains limitation '+id+str(lv),any('provisional policy' in x for x in v['result']['limitations']))
     r['conditions']['combat'].update(manualCharacterId=id,manualStyle='tap');before=set((s.data/'skill-replays').glob('*.json'));rr,error=s.call('runtime/skill-replays',r);s.check('manual tap rejected with no partial result '+id+str(lv),rr.status==400 and '미지원 교체 무기 조작' in json.dumps(error,ensure_ascii=False) and before==set((s.data/'skill-replays').glob('*.json')),error)
    for id in ['5129','5105','5101']:
     r=deepcopy(req);r['characterIds']=[id];before=set((s.data/'skill-replays').glob('*.json'));rr,error=s.call('runtime/skill-replays',r);text=json.dumps(error,ensure_ascii=False);expected=next(x['unsupported'] for x in support[id]['levels'] if x['level']==lv)
     s.check('unsupported rejects no storage '+id+str(lv),rr.status==400 and before==set((s.data/'skill-replays').glob('*.json')),error)
     s.check('unsupported execution agrees catalog flag '+id+str(lv),not support[id]['allLevelsExecutable'] and bool(expected) and rr.status==400)
     if id=='5129':s.check('skill diagnostics match catalog first twelve '+str(lv),all(x in text for x in expected[:12]))
   account();newteam=deepcopy(req);newteam['characterIds']=['5011','5008','5009','5012','5001'];newteam['conditions']['casts']=[dict(frame=30,characterId='5012'),dict(frame=400,characterId='5001')];b,rows,stats=s.batch(newteam,'new-members-compute');s.check('new members compute saved',b['state']=='completed')
   text=json.dumps([b,rows,stats]).lower()
   s.check('compute exposes replacement provisional and pierce limitation','provisional' in text and 'pierce multi-hit' in text)
   if extension:extension(s,ctx,req,newteam,b,rows,stats)
   page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(s.base+'/editor/');page.wait_for_selector('body[data-ready="true"]');page.locator('[data-tab="raid"]').click();page.screenshot(path=str(s.run/'raid.png'),full_page=True);s.save('browser',dict(errors=errors,text=page.locator('body').inner_text()));s.check('actual editor loads after expanded catalog',not errors,errors)
   browser.close()
 except Exception as ex:s.report.update(status='aborted',error=repr(ex));raise
 finally:s.finish()
 return int(s.report['status']!='passed')
if __name__=='__main__':raise SystemExit(main())

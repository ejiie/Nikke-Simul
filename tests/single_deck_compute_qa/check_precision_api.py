"""Independent actual API preparation, version isolation and historical reads for E-PREC-1."""
import argparse,json,sqlite3,shutil
from copy import deepcopy
from pathlib import Path
from playwright.sync_api import sync_playwright
from check_charge_api import ChargeSession
from check_f2_conditions import ROOT
from public_fixture import create,read,digest
OUT=ROOT/'artifacts/single-deck-qa/precision1'
p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args();s=ChargeSession(a.dotnet);s.report.update(product='2b16883',scope='E-PREC-1 actual API')
(OUT/'api-evidence.txt').write_text(str(s.run),encoding='utf-8');source=Path('C:/Users/user/Documents/GitHub/Nikke-Simul/data/local');public=OUT/'public-copy';public.mkdir(exist_ok=True)
if (OUT/'public-hashes-before.json').exists():
 hashes=read(OUT/'public-hashes-before.json');game=read(public/'game-catalog.json');assert all(digest(source/k)==v==digest(public/k) for k,v in hashes.items())
else:
 hashes,game,_,_=create(source,public);(OUT/'public-hashes-before.json').write_text(json.dumps(hashes),encoding='utf-8')
for rel in hashes:
 target=s.data/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(public/rel,target)
base=deepcopy(s.snapshot);base['gameSnapshotId']=game['id']
for m in base['characters']:
 for e in m['equipment']:e.update(tier=0,lines=[dict(lineIndex=i,presence='absent') for i in range(1,4)])
def account(rate=0):
 s.snapshot=deepcopy(base)
 if rate:
  for m in s.snapshot['characters']:m['equipment'][0].update(tier=10,lines=[dict(lineIndex=1,presence='present',optionType='StatAmmoLoad',normalizedValue=rate,unit='ratio'),dict(lineIndex=2,presence='absent'),dict(lineIndex=3,presence='absent')])
 with sqlite3.connect(s.data/'accounts.db') as db:db.execute('UPDATE snapshots SET payload=?',(json.dumps(s.snapshot),))
tactic=dict(schemaVersion=1,allowedCharacterIds=s.ids,stage1Priority=[s.ids[0]],stage2Priority=[s.ids[1]],stage3Priority=s.ids[2:],burst3Rotation=['5004','5044'],unavailablePolicy='next_ready')
req=dict(snapshotId=base['id'],characterIds=s.ids,scenarioLevel=400,conditionProfile='legacy',conditions=dict(roundingPolicy='client_f32',autoBurst=dict(tactic=tactic),combat=dict(durationFrames=10800,enemyDefense=30925,critMode='sample',core=True,pelletCoefficientPolicy='per_trigger',manualCharacterId='5004',manualStyle='full_charge')))
try:
 with sync_playwright() as pw:
  api=pw.request.new_context();old={}
  for phase,binaries in [('old',OUT/'baseline-api'),('new',ROOT/'src/Nikke.Api/bin/Release/net10.0')]:
   for label,rate,target in [('base',0,False),('interruption',0,True),('ammo145',.145,False),('ammo1181',.1181,False)]:
    account(rate);s.start_binary(api,binaries);r=deepcopy(req);r['conditions']['interruptionTarget']=target;v=s.replay(r,phase+'-'+label)
    if phase=='old':old[label]=v;(OUT/('team-input-'+label+'.json')).write_text(json.dumps(v),encoding='utf-8')
    else:
     previous=deepcopy(old[label]['inputs'])
     for member in previous:member['weapon']['hit'].update(interruptionTarget=False,interruptionDamage=0)
     s.check('identical prepared public input plus neutral additive fields '+label,previous==v['inputs'] and old[label]['result']['conditions']==v['result']['conditions'])
    if label=='base':
     if phase=='old':oldbatch,oldrows,oldstats=s.batch(req,'old-batch');oldhit=s.call('calculations/hit',dict(inputSchemaVersion=3,input=dict(statAttack=10,damageType='true',defenceRatioRate=.6),roundingPolicy='client_f32'))[1]
     else:
      for label0,saved in old.items():
       path=s.data/'skill-replays'/(saved['id']+'.json');before=path.read_bytes();rr,value=s.call('runtime/skill-replays/'+saved['id']);s.check('old saved result readable bytes '+label0,rr.status==200 and rr.body()==before and value==saved)
      s.check('old hit true damage stays historical 4',s.call('calculations/hit/'+oldhit['id'])[1]==oldhit and oldhit['selectedCandidate']['damage']==4)
      _,h=s.call('calculations/hit',dict(inputSchemaVersion=3,input=dict(statAttack=10,damageType='true',defenceRatioRate=.6),roundingPolicy='client_f32'));s.check('new actual true damage ignores defence ratio',h['selectedCandidate']['damage']==10)
      rr,h=s.call('calculations/hit',dict(inputSchemaVersion=3,input=dict(statAttack=100,interruptionTarget=True,interruptionDamage=.5),roundingPolicy='client_f32'));s.check('new hit contract additive interruption fields',rr.status==200 and h['selectedCandidate']['damage']==150)
      rr,h=s.call('calculations/hit',dict(inputSchemaVersion=3,input=dict(statAttack=100),roundingPolicy='client_f32_dprod'));s.check('single hit API candidate not exposed',rr.status==400,h)
      candidate=deepcopy(req);candidate['conditions']['roundingPolicy']='client_f32_dprod';rr,cv=s.call('runtime/skill-replays',candidate);s.save('candidate-replay-api',dict(status=rr.status,response=cv));s.check('replay candidate routing observed',rr.status==200 and cv['result']['conditions']['roundingPolicy']=='client_f32_dprod',dict(status=rr.status))
      for suffix,expected in [('/results',oldrows),('/statistics',oldstats)]:s.check('old compute preserved '+suffix,s.call('compute/experiments/'+oldbatch['id']+suffix)[1]==expected)
      rr,error=s.call('compute/experiments/'+oldbatch['id']+'/resume',{});s.check('old rules resume rejected',rr.status==409 and 'engine_or_rules_version_changed' in json.dumps(error))
      newbatch,_,_=s.batch(req,'new-batch');s.check('version fingerprint isolation',all(oldbatch['input'][k]!=newbatch['input'][k] for k in ['engineVersion','rulesVersion','summaryVersion','fingerprint']) and oldbatch['execution']['fingerprint']!=newbatch['execution']['fingerprint'])
      candidateBatch,_,_=s.batch(candidate,'candidate-batch');s.check('candidate policy fingerprint isolation',candidateBatch['input']['roundingPolicy']=='client_f32_dprod' and candidateBatch['input']['fingerprint']!=newbatch['input']['fingerprint'] and candidateBatch['execution']['fingerprint']!=newbatch['execution']['fingerprint'])
    s.stop()
  api.dispose()
except Exception as ex:s.report.update(status='aborted',error=repr(ex));raise
finally:
 after={k:digest(source/k) for k in hashes};s.save('authorized-public-hashes',dict(before=hashes,after=after));s.check('original public tables unchanged',hashes==after);s.finish()
raise SystemExit(s.report['status']!='passed')

"""Independent source arithmetic and trigger oracle for actual fixed-random probe runs."""
import json,math,os
from pathlib import Path
from fractions import Fraction
OUT=Path(os.environ.get('QA_SSR_OUTPUT',Path(__file__).resolve().parents[2]/'artifacts/single-deck-qa/ssr1'))
facts=json.loads((OUT/'independent-oracle.json').read_text(encoding='utf-8'))
cat=json.loads((OUT/'runtime'/json.loads((OUT/'runtime/current.json').read_text())['id']/'catalog.json').read_text(encoding='utf-8'))
rows=list(map(json.loads,(OUT/'effects.jsonl').read_text(encoding='utf-8-sig').splitlines()));checks=[]
def check(name,b,detail=None):checks.append(dict(name=name,passed=bool(b),detail=detail))
def halfup(v):return (v.numerator*2//v.denominator+1)//2
for row in rows:
 if row['kind']=='fingerprint':
  check('data graph conditions each separate fingerprint',len({row[k]['fingerprint'] for k in ['baseline','dataChange','graphChange','conditionChange']})==4)
  for key,v in row['mutations'].items():check('restore rejects '+key+' tampering',v)
  continue
 if row['kind']=='targets':
  e=row['result']['events'];targets={x['target'] for x in e if x['kind']=='buff_on' and x['functionId']==110211003}
  check('Maxwell attack top two targets',targets=={'5012','5001'},sorted(targets));continue
 id=row['id'];key=str((id,row['speed'],row['window']));r=row['result'];events=r['events'];log=r['damageLog']['entries'];profile=next(x for x in facts[id]['profiles'] if x['level']==10);sid=facts[id]['skills']['burst']['levels']['10']['skill_id'];replacement=[e for e in log if e.get('skillId')==sid and e['hit']['damageType']=='normal']
 chargeCs=Fraction(profile['chargeSeconds'])*100;reduction=halfup(chargeCs*Fraction(str(row['speed'])))
 if id=='5001' and row['window']:reduction+=halfup(chargeCs*Fraction(-cat['functions']['110211002']['function_value'],10000))
 frames=math.ceil((chargeCs-reduction)*Fraction(3,5));check('integer charge reduction '+key,len(replacement)==1 and replacement[0]['frame']==11+frames-1 and replacement[0]['actualChargeFrames']==frames)
 check('fixed replacement magazine vs integer base ammo '+key,r['members'][0]['maxAmmo']==115 and replacement[0]['shot']['ammoBefore']==1 and replacement[0]['shot']['ammoAfter']==0)
 check('replacement trace policy and limits '+key,any(e['kind']=='replacement_weapon' and e['basis'].startswith('provisional_motion_policy:') for e in events) and any('provisional policy' in x and 'pierce multi-hit' in x for x in r['limitations']))
 if id=='5012':
  native=[e for e in log if e['hit']['damageType']=='normal'];f1=facts[id]['skills']['skill1']['levels']['10']['function_ids'];damage=cat['functions'][str(f1[0])];buff=cat['functions'][str(f1[1])];every=damage['timing_trigger_value'];expected=[e['frame'] for e in native[every-1::every]]
  hits=[e for e in log if e.get('functionId')==f1[0]];check('OnHitNum raw cadence '+key,[e['frame'] for e in hits]==expected and all(e['hit']['coefficient']==damage['function_value']/10000 for e in hits))
  applied=[e for e in events if e['kind'] in ['buff_on','buff_refresh'] and e['functionId']==f1[1]];check('attack buff raw duration and value '+key,[e['frame'] for e in applied]==expected and all(e['value']==buff['function_value']/10000 and e['expiresAt']==e['frame']+buff['duration_value']*3//5 for e in applied))
  sk=facts[id]['skills']['skill2']['levels']['10'];casts=[e for e in log if e.get('skillId')==sk['skill_id']];period=sk['skill']['skill_cooltime']*3//5;check('skill2 cooldown and direct coefficient '+key,[e['frame'] for e in casts]==list(range(period,r['conditions']['combat']['durationFrames']+1,period)) and all(e['hit']['coefficient']==sk['skill']['skill_value_data'][0]['skill_value']/10000 for e in casts))
  fid=sk['function_phases']['after_use'][0];f=cat['functions'][str(fid)];on=[e for e in events if e['kind']=='buff_on' and e['functionId']==fid]
  check('full burst gates crit buff '+key,len(on)==int(row['window']) and all(e['value']==f['function_value']/10000 and e['expiresAt']==e['frame']+f['duration_value']*3//5 for e in on))
  check('fixed RNG actual crit interval '+key,all(e['hit']['crit']==any(e['hitId']>b['id'] and e['frame']<b['expiresAt'] for b in on) for e in log))
 else:
  ids=facts[id]['skills']['skill2']['levels']['10']['function_ids'];check('single boss spawn skill remains inactive '+key,not any(e.get('functionId') in ids for e in events))
  buffs=[e for e in events if e['kind']=='buff_on' and e['functionId'] in [110211002,110211003]];check('full burst triggers Maxwell source buffs '+key,len(buffs)==(2 if row['window'] else 0) and all(e['frame']==1 and e['expiresAt']==601 for e in buffs))
report=dict(checks=checks,passed=sum(x['passed'] for x in checks),failed=[x for x in checks if not x['passed']]);(OUT/'effects-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(dict(passed=report['passed'],failed=report['failed']),ensure_ascii=False));assert not report['failed']

"""QA-owned Fraction oracle: IEEE binary32 operands, rounded binary64 product chain."""
import json,random,sys
from fractions import Fraction as Q
from pathlib import Path
from check_client_f32 import f32,nearest,away,add,mul,DEFAULT,NAMES,calc as old_calc
OUT=Path(__file__).resolve().parents[2]/'artifacts/single-deck-qa/precision1'
def f64(x):
 x=Q(x)
 if not x:return Q(0)
 sign=-1 if x<0 else 1;x=abs(x);e=x.numerator.bit_length()-x.denominator.bit_length()
 if x<Q(2)**e:e-=1
 step=Q(2)**max(-1074,e-52);v=nearest(x/step)*step
 if v>=Q(2)**1024:raise OverflowError()
 return sign*v
def product(a,d,r,double):
 r={k:f32(v) for k,v in r.items()};rounder=f64 if double else f32;base=rounder(a-d)
 for k in NAMES[:3]:base=rounder(base*r[k])
 bonus=Q(1)
 for k in NAMES[3:7]:bonus=add(bonus,add(r[k],-1))
 extra=add(add(r['breakRate'],r['addDamageRate']),-1);red=add(1,-r['damageReductionRate']);defence=add(1,-r['defenceRatioRate']);candidate=base
 for v in [bonus,extra,red,defence,r['elementRate']]:candidate=rounder(candidate*v)
 return dict(damage=max(1,away(candidate)),base=float(base),bonus=float(bonus),extra=float(extra),reductionFactor=float(red),defenceFactor=float(defence),beforeRound=float(candidate))
def generate():
 OUT.mkdir(parents=True,exist_ok=True);rows=[];want={}
 def case(kind,body,expected=None,error=None):
  id=kind+'-'+str(len(rows));rows.append(dict(id=id,kind=kind,**body));want[id]=dict(error=error) if error else dict(result=expected)
 rng=random.Random(31003)
 rates=[]
 for _ in range(240):
  r=DEFAULT|dict(damageRatio=rng.randrange(1,900000)/10000,statDamageRatio=rng.randrange(1,17000)/10000,chargeDamageRate=rng.choice([1,3.5,1.07]),criticalDamageRate=1.73,coreDamageRate=2,burstDamageRate=1.5,bonusRangeRate=1.3,breakRate=1.1669,addDamageRate=1.145,damageReductionRate=-.2246,defenceRatioRate=rng.choice([0,.6,1]),elementRate=1.948)
  rates.append((rng.randrange(1,900000000),rng.randrange(0,50000),r))
 for a,d in [(1,0),(5,0),(2**24+1,0),(2**24+3,0),(2**53,0),(1,3),(0,1),(2**63-1,2**63-18)]:
  for rate in [.5,1,1.5]:rates.append((a,d,DEFAULT|dict(damageRatio=rate)))
 for a,d,r in rates:
  for policy in ['client_f32','client_f32_dprod']:case('direct',dict(attack=a,defence=d,rates=r,policy=policy),product(a,d,r,policy.endswith('dprod')))
 for a,d,r,error in [(2**53+1,0,DEFAULT,'ArgumentException'),(2**53,0,DEFAULT|dict(damageRatio=1024),'OverflowException'),(2**53,0,DEFAULT|dict(damageRatio=1023),'OK'),(100,0,DEFAULT|dict(defenceRatioRate=1.01),'ArgumentException')]:
  case('direct',dict(attack=a,defence=d,rates=r,policy='client_f32_dprod'),product(a,d,r,True) if error=='OK' else None,error=None if error=='OK' else error)
 for policy in ['client_f32','client_f32_dprod','legacy_term_floor','final_round_even','nested_floor']:
  for typ in ['normal','skill','true']:
   for ratio in [0,.6,1,1.5]:
    expected=10 if typ=='true' or policy not in ['client_f32','client_f32_dprod'] else max(1,away(10*add(1,-ratio)))
    error='ArgumentException' if ratio>1 and typ!='true' and policy.startswith('client_') else None
    case('context',dict(context=dict(statAttack=10,defense=0,damageType=typ,defenceRatioRate=ratio),policy=policy),expected,error)
  for target in [False,True]:
   for parts in [False,True]:
    c=dict(statAttack=100,attackDamage=.2,interruptionDamage=.5,interruptionTarget=target,parts=parts,partsDamage=.3)
    case('context',dict(context=c,policy=policy),100+20+(50 if target else 0)+(30 if parts else 0))
  for target in [False,True]:
   for enabled in [False,True]:
    functions=[dict(id=9901,groupId=9901,functionType=96,functionTarget=1,functionValueType=2,functionValue=5000,timingTriggerType=1,durationType=1,durationValue=10000)] if enabled else []
    case('runtime',dict(functions=functions,target=target,policy=policy),dict(damage=150+(50 if target and enabled else 0),interruption=.5 if enabled else 0,attackDamage=.2,maxAmmo=100))
 for native,raw,stacks in [(100,1450,1),(100,-50,1),(100,50,1),(100,1450,2),(35,1181,1),(2**63-1,0,1)]+[(rng.randrange(1,100001),rng.randrange(0,90001),rng.randrange(1,10)) for _ in range(90)]:
  b=dict(source='QA',rate=raw/10000,rawRate10000=raw,stacks=stacks);case('ammo',dict(native=native,groups=[[b]]),native+away(Q(native*raw*stacks,10000)))
 for groups in [[[dict(source='a',rate=.005),dict(source='b',rate=.005)]],[[dict(source='a',rate=.005)],[dict(source='b',rate=.005)]],[[dict(source='a',rate=.005),dict(source='b',rate=.015)]]]:
  counts={}
  for b in sum(groups,[]):raw=round(b['rate']*10000);counts[raw]=counts.get(raw,0)+1
  case('ammo',dict(native=100,groups=groups),100+sum(away(Q(100*r*n,10000)) for r,n in counts.items()))
 for body,error in [(dict(native=100,groups=[[dict(source='off-grid',rate=.14501)]]),'ArgumentException'),(dict(native=100,groups=[[dict(source='conflict',rate=.145,rawRate10000=1451)]]),'ArgumentException'),(dict(native=2**63-1,groups=[[dict(source='over',rate=1,rawRate10000=10000)]]),'OverflowException')]:case('ammo',body,error=error)
 for raw in [1450,50,-50]:
  f=dict(id=9914,groupId=9914,functionType=14,functionTarget=1,functionValueType=2,functionValue=raw,timingTriggerType=1,durationType=1,durationValue=10000)
  case('runtime',dict(functions=[f],target=False,policy='client_f32'),dict(damage=150,interruption=0,attackDamage=.2,maxAmmo=100+away(Q(100*raw,10000))))
 (OUT/'cases.jsonl').write_text('\n'.join(json.dumps(r) for r in rows),encoding='utf-8');(OUT/'expected.json').write_text(json.dumps(want),encoding='utf-8');print(len(rows))
def verify():
 want=json.loads((OUT/'expected.json').read_text());cases={r['id']:r for r in map(json.loads,(OUT/'cases.jsonl').read_text().splitlines())};actual=list(map(json.loads,(OUT/'math-new.jsonl').read_text(encoding='utf-8-sig').splitlines()));old={r['id']:r for r in map(json.loads,(OUT/'math-old.jsonl').read_text(encoding='utf-8-sig').splitlines())};checks=[];nonfloat=[]
 def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail))
 for r in actual:
  c=cases[r['id']];w=want[r['id']];got=r.get('result');ok=False
  if 'error' in w:ok=r.get('error')==w['error']
  elif c['kind']=='direct' and got:
   ok=got['damage']==w['result']['damage'] and all((f32(got[k])==f32(v) if k in ['bonus','extra','reductionFactor','defenceFactor'] or c['policy']=='client_f32' else got[k]==v) for k,v in w['result'].items() if k!='damage')
   if c['policy']=='client_f32_dprod' and f32(got['damage'])!=got['damage']:nonfloat.append(dict(id=r['id'],damage=got['damage']))
  elif c['kind']=='context' and got:ok=got['damage']==got['audit']['damage']==w['result']
  elif c['kind']=='ammo':ok=got==w['result']
  elif c['kind']=='runtime' and got:
   hits=[e for e in got['damageLog']['entries'] if e['kind']==2];v=w['result'];ok=bool(hits) and got['members'][0]['maxAmmo']==v['maxAmmo'] and all(e['damage']==v['damage'] and e['hit']['attackDamage']==v['attackDamage'] and e['hit'].get('interruptionDamage',0)==v['interruption'] for e in hits)
  check(r['id']+' independent',ok,None if ok else dict(input=c,expected=w,actual=r))
  if c['kind']=='direct' and c['policy']=='client_f32':check(r['id']+' default exact previous',r==old[r['id']])
 check('non-float32 representable integer results exist',len(nonfloat)>30,nonfloat[:8]);check('all generated cases present',len(actual)==len(want))
 result=dict(checks=checks,total=len(checks),passed=sum(c['passed'] for c in checks),failed=[c for c in checks if not c['passed']],nonRepresentable=len(nonfloat));(OUT/'math-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(dict(total=result['total'],passed=result['passed'],failed=result['failed'][:4]),ensure_ascii=False)[:6000]);assert not result['failed']
if __name__=='__main__':{'generate':generate,'verify':verify}[sys.argv[1]]()

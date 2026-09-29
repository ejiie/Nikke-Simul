"""Strict threshold oracle uses integer prefix sums and independent Fraction binary32 arithmetic."""
import json,sys
from pathlib import Path
from check_client_f32 import context
rows=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'));checks=[]
def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail))
for row in rows:
 label=row['label'];result=row['result'];hits=[e for e in result['events'] if e['kind']=='damage'];total=0;switch=None;by={}
 for i,e in enumerate(hits):
  defense=30925 if label.startswith('fixed') or total<=2000000000 else 31784
  h=dict(e['hit'],defense=defense)
  # Simple fixed synthetic hits have unit coefficient and no rates/flags.
  expected=context(h)['damage'] if row['conditions']['roundingPolicy']=='client_f32' else h['statAttack']-defense
  check(label+f' hit{i+1} independent damage/DEF',e['value']==expected and e['hit']['defense']==defense,dict(actual=e['value'],expected=expected,defense=defense))
  total+=expected;by[e['source']]=by.get(e['source'],0)+expected
  if switch is None and total>2000000000 and not label.startswith('fixed'):
   switch=dict(frame=e['frame'],hitTraceId=e['id'],hitOrdinal=i+1,characterId=e['source'],effect=e['effect'],cumulativeDamage=total,previousDefense=30925,newDefense=31784)
 check(label+' independently accumulated team/members',result['totalDamage']==total==sum(m['damage'] for m in result['members']) and all(by.get(m['characterId'],0)==m['damage'] for m in result['members']))
 check(label+' exact transition metadata',result['defense']['switchAfterHit']==switch,dict(actual=result['defense']['switchAfterHit'],expected=switch))
 check(label+' replay/summary parity',row['summary']['teamDamage']==total and row['summary']['defense']==result['defense'])
 check(label+' single transition trace',sum(e['kind']=='defense_switch' for e in result['events'])==int(switch is not None))
 if label=='equal':check('exact 2000000000 no switch',total==2000000000 and switch is None)
 if label=='below':check('below no switch',total==1999999872 and switch is None)
 if label=='plus-one-same-frame':check('exact +1 and next same-frame member',switch is not None and switch['cumulativeDamage']==2000000001 and len(hits)==3 and len({e['frame'] for e in hits})==1 and hits[-1]['value']==141)
 if label=='sg-six-pellets':check('pellet4 exact, pellet5 crossing, pellet6 switched',len(hits)==6 and switch['hitOrdinal']==5 and len({e['parentId'] for e in hits})==1)
 if label=='extra-before-normal':check('additional attack participates in same-frame prefix',any(e['effect']=='function:991' for e in hits) and switch is not None and hits[switch['hitOrdinal']-1]['effect']=='function:991')
 if label=='frame-zero-skill':check('frame-zero crossing',switch is not None and switch['frame']==0)
report=dict(status='passed' if all(c['passed'] for c in checks) else 'failed',checks=checks,passed=sum(c['passed'] for c in checks),failed=[c for c in checks if not c['passed']],cases=len(rows),hits=sum(len([e for e in r['result']['events'] if e['kind']=='damage']) for r in rows))
Path(sys.argv[1]).with_name('engine-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report['failed']));print(report['passed'],len(checks));raise SystemExit(bool(report['failed']))

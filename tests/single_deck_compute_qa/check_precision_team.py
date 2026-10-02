"""Compare independent 5-member runs; report candidate differences without owner answers."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parents[2]/'artifacts/single-deck-qa/precision1'
def load(name):return list(map(json.loads,(OUT/name).read_text(encoding='utf-8-sig').splitlines()))
def norm(x):
 if isinstance(x,list):return [norm(v) for v in x]
 if isinstance(x,dict):return {k:norm(v) for k,v in x.items() if k!='rulesVersion'}
 return x
old=load('team-old.jsonl');new=load('team-new.jsonl');key=lambda r:(r['scenario'],r['policy'],r['seed']);before={key(r):r for r in old};after={key(r):r for r in new};checks=[];comparisons=[]
def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail))
check('40 baseline and 60 candidate runs',len(before)==40 and len(after)==60)
for k,v in before.items():check('previous result exact '+str(k),norm(v)==norm(after[k]))
for scenario in sorted({r['scenario'] for r in new}):
 rows=[]
 for seed in range(1,6):
  c=after[scenario,'client_f32',seed];d=after[scenario,'client_f32_dprod',seed]
  rows.append(dict(seed=seed,client=c['totalDamage'],dprod=d['totalDamage'],delta=d['totalDamage']-c['totalDamage']))
  check('candidate firing unchanged '+scenario+str(seed),[(m['characterId'],m['shots'],m['maxAmmo'],m['remainingAmmo']) for m in c['members']]==[(m['characterId'],m['shots'],m['maxAmmo'],m['remainingAmmo']) for m in d['members']])
 comparisons.append(dict(scenario=scenario,rows=rows))
for policy in ['client_f32','legacy_term_floor','client_f32_dprod']:
 for seed in range(1,6):
  a=after['team-input-base',policy,seed];b=after['team-input-interruption',policy,seed]
  check('no active 96 base vs target '+policy+str(seed),a['members']==b['members'] and a['totalDamage']==b['totalDamage'])
report=dict(checks=checks,total=len(checks),passed=sum(c['passed'] for c in checks),failed=[c for c in checks if not c['passed']],comparisons=comparisons)
(OUT/'team-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2)[-4000:]);assert not report['failed']

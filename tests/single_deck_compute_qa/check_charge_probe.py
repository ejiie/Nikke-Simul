"""Independent integer-frame arithmetic and differential audit of QA probe output."""
import json,statistics,sys
from pathlib import Path
OUT=Path(__file__).resolve().parents[2]/'artifacts/single-deck-qa/ebug1'
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8-sig'))
checks=[]
def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail));print(name, 'PASS' if ok else 'FAIL')
old=read('timing-old.json');new=read('timing-new.json')
for a,b in zip(old['rows'],new['rows']):
 label=b['label'];check('two firing models '+label,b['legacy']==b['skill'])
 if label.startswith('manual-'):
  w=b['weapon'];aim=round(w['spotFirstDelaySec']*60);charge=max(1,round(round(w['chargeTimeSec']*100*(1-b['buff']))*3/5));click=max(1,round(b['control']['reclickMinSec']*60))
  first=aim+max(1,charge-int(aim>0));interval=click+first
  # Frame arrays are indexed from one. Aiming's last frame overlaps the first charging frame.
  expected=list(range(first,2401,interval));actual=[i+1 for i,e in enumerate(b['skill']) if e['fired']]
  check('independent arithmetic '+label,expected==actual,dict(first=first,interval=interval,actual=actual[:5]))
  if label=='manual-buff-99':check('reported 2F collapse now 14F',all(y-x==2 for x,y in zip([i+1 for i,e in enumerate(a['skill']) if e['fired']],[i+1 for i,e in enumerate(a['skill']) if e['fired']][1:])) and interval==14)
 else:
  check('unchanged all 2400 frame states '+label,a['legacy']==b['legacy'] and a['skill']==b['skill'])
  if label.startswith('auto-'):
   w=b['weapon'];charge=max(1,round(w['chargeTimeSec']*60));interval=round((w['spotLastDelaySec']+w['spotFirstDelaySec'])*60)+max(1,charge-1)
   fired=[(i+1,e) for i,e in enumerate(b['skill']) if e['fired']];gaps=[y[0]-x[0] for x,y in zip(fired,fired[1:]) if x[1]['currentAmmo']>0]
   check('independent automatic last plus first '+label,gaps and all(g==interval for g in gaps),dict(interval=interval,gaps=gaps[:5]))
summary=[]
suffix=sys.argv[1] if len(sys.argv)>1 else ''
if (OUT/('team-new'+suffix+'.json')).exists() and (OUT/('team-old'+suffix+'.json')).exists():
 a=read('team-old'+suffix+'.json');b=read('team-new'+suffix+'.json')
 def normalized(x):
  if isinstance(x,list):return [normalized(i) for i in x]
  if isinstance(x,dict):return {k:normalized(v) for k,v in x.items() if k not in ['rulesVersion','shotIntervalFrames']}
  return x
 for style in ['full_charge','tap','auto']:
  aa=[r for r in a['runs'] if r['style']==style];bb=[r for r in b['runs'] if r['style']==style]
  av=lambda rows,id,field:statistics.mean(next(m for m in r['members'] if m['characterId']==id)[field] for r in rows)
  teamold=statistics.mean(r['totalDamage'] for r in aa);teamnew=statistics.mean(r['totalDamage'] for r in bb)
  row=dict(style=style,teamOld=teamold,teamNew=teamnew,teamChangePct=(teamnew/teamold-1)*100,members=[])
  for id in ['5011','5008','5004','5009','5044']:
   d0,d1=av(aa,id,'damage'),av(bb,id,'damage');s0,s1=av(aa,id,'shots'),av(bb,id,'shots')
   row['members'].append(dict(id=id,damageOld=d0,damageNew=d1,damageChangePct=(d1/d0-1)*100,shotsOld=s0,shotsNew=s1,shotsChangePct=(s1/s0-1)*100))
  summary.append(row)
  for x,y in zip(aa,bb):
   seed=x['seed'];events=y.get('events') or [];last={};bad=[]
   for e in events:
    expected=None
    if e['kind']=='shot':
     if e['source'] in last:expected=e['frame']-last[e['source']]
     last[e['source']]=e['frame']
    if e.get('shotIntervalFrames')!=expected:bad.append(e)
   if events:check('trace actual gap '+style+str(seed),not bad,dict(count=len(events),bad=bad[:1]))
   if style!='full_charge':check('180s exact unchanged '+style+str(seed),normalized(x)==normalized(y))
   else:
    check('180s manual shots reduced seed '+str(seed),next(m['shots'] for m in y['members'] if m['characterId']=='5004')<next(m['shots'] for m in x['members'] if m['characterId']=='5004'))
    charges=list({e['shotId']:e for e in y['charge']}.values());samples=[];bad=[]
    for prev,now in zip(charges,charges[1:]):
     if prev['ammo'] is None or prev['ammo']<=0:continue
     expected=12+max(1,now['actualChargeFrames']-1);gap=now['frame']-prev['frame']
     samples.append(dict(gap=gap,base=expected,ownBurst=now['ownBurstEffectActive']))
     if gap-expected not in [1,2]:bad.append(dict(previous=prev,current=now,gap=gap,base=expected))
    check('every loaded manual gap = aim + reclick + actual charge seed '+str(seed),samples and not bad and {x['ownBurst'] for x in samples}=={True,False},dict(samples=len(samples),bad=bad[:3]))
  if style=='full_charge':
   for label,rows in [('old',aa),('new',bb)]:
    r=rows[0];frames=[s['frame'] for s in r['shots'] if s['source']=='5004'];gaps=[y-x for x,y in zip(frames,frames[1:])];row[label+'Seed1']=dict(min=min(gaps),median=statistics.median(gaps),gaps={str(n):gaps.count(n) for n in sorted(set(gaps))},fullBursts=len(r['teamBurst']['fullBursts']),firstFullBurst=r['teamBurst']['fullBursts'][0]['startFrame'])
 for x,y in zip(a['isolated']['members'],b['isolated']['members']):
  if x['characterId']!='5004':check('fixed casts constant RNG other member exact '+x['characterId'],x==y,dict(old=x,new=y))
 check('all four rule/implementation versions changed',all(a[k]!=b[k] for k in ['version','teamVersion','summaryVersion','weaponVersion']))
 (OUT/('comparison'+suffix+'.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/('probe-audit'+suffix+'.json')).write_text(json.dumps(dict(checks=checks,passed=sum(x['passed'] for x in checks),failed=[x for x in checks if not x['passed']],comparison=summary),ensure_ascii=False,indent=2),encoding='utf-8')
raise SystemExit(any(not x['passed'] for x in checks))

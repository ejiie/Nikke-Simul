"""Index fresh U-FIX-6 evidence, exclusions, row correspondence, and identifiers.
This is observation postprocessing, never an extra product test run.
"""
import json,sys
from pathlib import Path
from check_f2_sources import CASES
ROOT=Path(__file__).resolve().parents[2]/'artifacts/single-deck-qa'
OUT=ROOT/'f2-ufix6-preparation'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(name,v):(OUT/(name+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
paths={
 'F2':'f2-ufix6-1b52c394dc9f/summary.json',
 'F32':'f32-b2-403af01ae4cd/summary.json',
 'sources':'f2-ufix6-e5ba7219da11/summary.json',
 'minimal345':'f2-ufix6-48fa627d53f6/summary.json',
 'diagnostics':'f2-ufix6-9e8168b39ec4/summary.json',
 'minimal6':'f2-ufix6-1213fc48923f/summary.json',
 'engine':'f2-ufix6-preparation/engine-audit.json',
}
reports={scope:read(ROOT/p) for scope,p in paths.items()}
entries=[dict(scope=k,path=paths[k],status=r['status'],checks=len(r['checks']),passed=sum(c['passed'] for c in r['checks']),failed=[c['name'] for c in r['checks'] if not c['passed']],port=r.get('port'),ownedPids=r.get('ownedPids',[r['ownedPid']] if r.get('ownedPid') else []),ownApiStopped=r.get('ownApiStopped')) for k,r in reports.items()]
save('evidence-index',dict(product='59fe22d',merge='dc612bd',previousQA='02b63fb',verdict='F2-Q-3/4/5 accepted; overall blocked by F2-Q-6 visible audit wire text',freshRuns=entries,total=sum(e['checks'] for e in entries),passed=sum(e['passed'] for e in entries),failed=sum(len(e['failed']) for e in entries),excludedAttempts=[dict(path='f2-ufix6-d2fe788e28c0',reason='QA tried unavailable GPU select option; aborted, replaced by actual outgoing GPU refusal'),dict(path='f2-ufix6-858994941469',reason='QA phrase expected 사용 할 수 없음 instead of actual GPU 사용 불가; replaced by fresh final run'),dict(path='f32-b2-9c287367e48b',reason='QA waited for obsolete warmup text; aborted, fresh final desktop run')],responseMocks=False,loadBenchmark=False))
# Historical /legacy checks are explicitly outside the newest user scope. Derive
# their exact names from the old ordered web block; never silently drop missing checks.
old=read(ROOT/'f32-b2-68d26cb9dbb5/summary.json')['checks'];legacy=set()
for c in old:
 if c['name']=='desktop policy default and history options':break
 legacy.add(c['name'])
current={c['name']:(scope,c) for scope,r in reports.items() for c in r['checks']}
coverage={}
for label,group in read(ROOT/'f2-ufix5-preparation/regression-coverage.json').items():
 items=[]
 for c in group['obligations']:
  name=c['name']
  if name in current:
   scope,actual=current[name];items.append(dict(name=name,status='passed' if actual['passed'] else 'failed',source=paths[scope]))
  elif c['scope']=='F32' and name in legacy:items.append(dict(name=name,status='excluded',reason='User explicitly excluded desktop-unlinked /legacy'))
  else:items.append(dict(name=name,status='missing'))
 coverage[label]=dict(total=len(items),passed=sum(c['status']=='passed' for c in items),excluded=sum(c['status']=='excluded' for c in items),failed=[c for c in items if c['status']=='failed'],missing=[c for c in items if c['status']=='missing'],obligations=items)
save('regression-coverage',coverage)
assert all(not x['failed'] and not x['missing'] for x in coverage.values()),coverage
# Actual API order, not another row's label, determines correspondence.
rowchecks=[];source=ROOT/Path(paths['sources']).parent
for policy in ['client_f32','legacy_term_floor','final_round_even','nested_floor']:
 data=read(source/('source-families-'+policy+'.json'))['response']
 hit=next(e['hit'] for e in data['result']['damageLog']['entries'] if set(k for k,_ in CASES).issubset({b['source'] for b in e['hit'].get('runtimeAttackBuffs',[])}))
 rows=read(source/('source-panel-'+policy+'.json'))['rows'];offset=len(hit.get('attackBuffs',[]));keys=[b['source'] for b in hit['runtimeAttackBuffs']]
 for key,words in CASES:
  row=rows[offset+keys.index(key)];rowchecks.append(dict(policy=policy,source=key,visibleRow=row,passed=all(w in row for w in words) and key not in row))
save('source-row-audit',dict(origin='postprocess real API and captured DOM; no new product execution',checks=rowchecks))
assert all(c['passed'] for c in rowchecks)
save('identifier-inventory',[dict(scope=k,observations=r.get('identifierInventory',[])) for k,r in reports.items()])
save('visible-text-inventory',[dict(scope=k,scans=r.get('visibleTextScans',[])) for k,r in reports.items()])
print(json.dumps(dict(total=sum(e['checks'] for e in entries),passed=sum(e['passed'] for e in entries),coverage={k:dict(total=v['total'],passed=v['passed'],excluded=v['excluded']) for k,v in coverage.items()},sourceRows=len(rowchecks))))

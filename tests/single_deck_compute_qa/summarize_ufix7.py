"""Index this run's independent evidence, old obligations and owned process IDs."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'artifacts/single-deck-qa';OUT=BASE/'ufix7-preparation'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(n,v):(OUT/(n+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
paths={}
for name in ['f2','f32','sources','diagnostics','archive34','audit','surfaces','missing']:
    raw=(OUT/(name+'.log')).read_bytes();text=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig')
    folder=text.split('EVIDENCE ')[-1].strip().splitlines()[0]
    paths[name]=Path(folder)/'summary.json'
paths['engine']=OUT/'engine-audit.json'
reports={k:read(p) for k,p in paths.items()}
rows=[dict(scope=k,path=str(paths[k].relative_to(BASE)),status=r['status'],checks=len(r['checks']),passed=sum(c['passed'] for c in r['checks']),failed=[c for c in r['checks'] if not c['passed']],port=r.get('port'),ownedPids=r.get('ownedPids',[r['ownedPid']] if r.get('ownedPid') else []),ownApiStopped=r.get('ownApiStopped')) for k,r in reports.items()]
save('evidence-index',dict(product='b401421',previousQA='180f23b',merge='git merge --no-edit b401421; fast-forward',freshRuns=rows,total=sum(x['checks'] for x in rows),passed=sum(x['passed'] for x in rows),failed=sum(len(x['failed']) for x in rows),note='Older QA runner metadata may still say 59fe22d/U-FIX-6; this index records actual checked-out b401421 and new run paths. No old PASS result was reused.'))
current={c['name']:(k,c) for k,r in reports.items() for c in r['checks']}
prior=read(BASE/'f2-ufix6-preparation/regression-coverage.json');coverage={}
for label,group in prior.items():
    items=[]
    for c in group['obligations']:
        if c['status']=='excluded':items.append(c);continue
        scope,actual=current.get(c['name'],(None,None))
        items.append(dict(name=c['name'],status=('passed' if actual['passed'] else 'failed') if actual else 'missing',source=str(paths[scope].relative_to(BASE)) if scope else None))
    coverage[label]=dict(total=len(items),passed=sum(x['status']=='passed' for x in items),excluded=sum(x['status']=='excluded' for x in items),missing=[x for x in items if x['status']=='missing'],failed=[x for x in items if x['status']=='failed'],obligations=items)
save('regression-coverage',coverage)
save('identifier-inventory',[dict(scope=k,observations=r.get('identifierInventory',[])) for k,r in reports.items()])
save('visible-text-inventory',[dict(scope=k,scans=r.get('visibleTextScans',[])) for k,r in reports.items()])
started=OUT.stat().st_ctime
final_paths={p.resolve() for p in paths.values()}
attempts=[]
for p in BASE.glob('*/summary.json'):
    if p.parent.stat().st_ctime<started:continue
    r=read(p)
    attempts.append(dict(path=str(p.relative_to(BASE)),included=p.resolve() in final_paths,status=r.get('status'),error=r.get('error'),ownedPids=r.get('ownedPids',[r['ownedPid']] if r.get('ownedPid') else []),ownApiStopped=r.get('ownApiStopped'),note=None if p.resolve() in final_paths else 'Superseded QA attempt, excluded from final totals. See report for environment/assertion/instrumentation corrections.'))
save('attempt-index',attempts)
print(json.dumps(dict(total=sum(x['checks'] for x in rows),passed=sum(x['passed'] for x in rows),runs=[dict(scope=x['scope'],checks=x['checks'],passed=x['passed'],path=x['path']) for x in rows],coverage={k:dict(passed=v['passed'],excluded=v['excluded'],missing=len(v['missing'])) for k,v in coverage.items()}),ensure_ascii=False,indent=2))

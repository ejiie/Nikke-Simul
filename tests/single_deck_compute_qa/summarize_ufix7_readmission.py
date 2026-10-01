"""Index fresh QA readmission runs; retain old obligations and policy adaptations."""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser();parser.add_argument('--allowlist',action='store_true');args=parser.parse_args()
BASE=ROOT/'artifacts/single-deck-qa';OUT=BASE/('ufix7-allowlist' if args.allowlist else 'ufix7-readmission')

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(n,v):(OUT/(n+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')

paths={}
for name in ['audit','surfaces','missing','families','f2','f32','sources','diagnostics','archive34']+(['allowlist'] if args.allowlist else []):
    raw=(OUT/(name+'.log')).read_bytes();log=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig')
    matches=re.findall(r'^EVIDENCE (.+)$',log,re.M);assert len(matches)==1,(name,matches)
    paths[name]=Path(matches[0].strip())/'summary.json'
paths['engine']=OUT/'engine-audit.json'
reports={k:read(p) for k,p in paths.items()}
assert all(r['status'] in ['passed','failed'] for r in reports.values())
rows=[dict(scope=k,path=str(paths[k].relative_to(BASE)),status=r['status'],checks=len(r['checks']),passed=sum(c['passed'] for c in r['checks']),failed=[c for c in r['checks'] if not c['passed']],port=r.get('port'),ownedPids=r.get('ownedPids',[r['ownedPid']] if r.get('ownedPid') else []),ownApiStopped=r.get('ownApiStopped')) for k,r in reports.items()]
assert all(x['port'] not in [5180,5181] for x in rows)
save('evidence-index',dict(product='5243062' if args.allowlist else '8da098f',previousQA='f5a8057' if args.allowlist else '706d7fd',merge='e01ec8fca306772799fc750c60bc435171966cff' if args.allowlist else '89e903e3d20cb3112916781c4573650f76b4cbc6',freshRuns=rows,total=sum(x['checks'] for x in rows),passed=sum(x['passed'] for x in rows),failed=sum(len(x['failed']) for x in rows),note='Older QA runner metadata retains b401421/59fe22d/U-FIX-6 labels. All indexed runs are fresh on the product and merge recorded above. No old PASS results or owner test answers reused.'))
current={c['name']:(k,c) for k,r in reports.items() for c in r['checks']}
prior=read(BASE/'ufix7-preparation/regression-coverage.json');coverage={}
for label,group in prior.items():
    items=[]
    for c in group['obligations']:
        if c['status']=='excluded':items.append(c);continue
        scope,actual=current.get(c['name'],(None,None))
        items.append(dict(name=c['name'],status=('passed' if actual['passed'] else 'failed') if actual else 'missing',source=str(paths[scope].relative_to(BASE)) if scope else None))
    coverage[label]=dict(total=len(items),passed=sum(x['status']=='passed' for x in items),excluded=sum(x['status']=='excluded' for x in items),missing=[x for x in items if x['status']=='missing'],failed=[x for x in items if x['status']=='failed'],obligations=items)
save('regression-coverage',coverage)
old=read(BASE/('ufix7-readmission' if args.allowlist else 'ufix7-preparation')/'evidence-index.json');oldgroups=[]
def stable_checks(checks):
    result={};occurrences={}
    for c in checks:
        name=re.sub(r'^real GET [0-9a-f]{32}$','real GET <fresh replay ID>',c['name'])
        if args.allowlist:name=name.replace('ordinary Korean preserved ','unregistered QA Korean generic ')
        occurrences[name]=occurrences.get(name,0)+1
        result[(name,occurrences[name])]=c
    return result
for row in old['freshRuns']:
    previous=read(BASE/row['path']);latest=stable_checks(reports[row['scope']]['checks'])
    checks=[dict(name=c['name'],currentName=latest.get(key,{}).get('name'),previousPassed=c['passed'],currentPassed=latest.get(key,{}).get('passed'),wasBlocker=not c['passed'],mapping='name and occurrence; fresh GET UUID normalized; allowlist policy intentionally changes four unregistered QA sentences and two image status fallbacks' if args.allowlist else 'name and occurrence; fresh GET UUID normalized') for key,c in stable_checks(previous['checks']).items()]
    oldgroups.append(dict(scope=row['scope'],checks=checks,passed=sum(c['currentPassed'] is True for c in checks),missing=[c for c in checks if c['currentPassed'] is None]))
save('previous-qa-coverage',oldgroups)
save('identifier-inventory',[dict(scope=k,observations=r.get('identifierInventory',[])) for k,r in reports.items()])
save('visible-text-inventory',[dict(scope=k,scans=r.get('visibleTextScans',[])) for k,r in reports.items()])
started=OUT.stat().st_ctime;final_paths={p.resolve() for p in paths.values()};attempts=[]
for p in BASE.glob('*/summary.json'):
    if p.parent.stat().st_ctime<started:continue
    r=read(p)
    attempts.append(dict(path=str(p.relative_to(BASE)),included=p.resolve() in final_paths,status=r.get('status'),error=r.get('error'),ownedPids=r.get('ownedPids',[r['ownedPid']] if r.get('ownedPid') else []),ownApiStopped=r.get('ownApiStopped'),note=None if p.resolve() in final_paths else ('Superseded attempt: positive control source path and unitless distance assertions corrected. Excluded from final counts.' if args.allowlist else 'Superseded attempt: zero-state expected text corrected; one display wait timeout retained separately. Excluded from final counts.')))
save('attempt-index',attempts)
print(json.dumps(dict(total=sum(x['checks'] for x in rows),passed=sum(x['passed'] for x in rows),runs=[dict(scope=x['scope'],checks=x['checks'],passed=x['passed'],path=x['path']) for x in rows],coverage={k:dict(passed=v['passed'],excluded=v['excluded'],missing=len(v['missing'])) for k,v in coverage.items()},previousQA=dict(total=sum(len(x['checks']) for x in oldgroups),passed=sum(x['passed'] for x in oldgroups))),ensure_ascii=False,indent=2))

"""Index only finished E-BUG-1 runs and match every prior accepted QA obligation."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'artifacts/single-deck-qa';OUT=BASE/'ebug1';REG=BASE/'ebug1-regression'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(n,v):(OUT/(n+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths={}
for name in ['audit','surfaces','missing','families','f2','f32','sources','diagnostics','archive34','allowlist','modules']:
 raw=(REG/(name+'.log')).read_bytes();log=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig');matches=re.findall(r'^EVIDENCE (.+)$',log,re.M);assert len(matches)==1,(name,matches)
 paths[name]=Path(matches[0].strip())/'summary.json'
paths['engine']=REG/'engine-audit.json';reports={k:read(p) for k,p in paths.items()}
prior=read(BASE/'ufix7-readmission4/evidence-index.json');coverage=[]
def stable(checks):
 occurrences={};result={}
 for c in checks:
  name=re.sub(r'^real GET [0-9a-f]{32}$','real GET <replay ID>',c['name']);occurrences[name]=occurrences.get(name,0)+1;result[(name,occurrences[name])]=c
 return result
for row in prior['freshRuns']:
 old=read(BASE/row['path']);current=stable(reports[row['scope']]['checks'])
 for key,c in stable(old['checks']).items():coverage.append(dict(scope=row['scope'],name=c['name'],passed=current.get(key,{}).get('passed'),previousPassed=c['passed']))
save('previous-qa-coverage',coverage)
for name in ['api','browser']:paths[name]=Path((OUT/(name+'-evidence.txt')).read_text(encoding='utf-8'))/'summary.json';reports[name]=read(paths[name])
paths['charge-probe']=OUT/'probe-audit-rotation2.json';reports['charge-probe']=read(paths['charge-probe'])
rows=[dict(scope=k,path=str(paths[k].relative_to(BASE)),checks=len(r['checks']),passed=sum(c['passed'] for c in r['checks']),failed=[c for c in r['checks'] if not c['passed']],port=r.get('port'),pids=r.get('ownedPids',[r['ownedPid']] if r.get('ownedPid') else []),ownApiStopped=r.get('ownApiStopped')) for k,r in reports.items()]
before=read(OUT/'public-hashes-before.json');original=Path('C:/Users/user/Documents/GitHub/Nikke-Simul/data/local');after={k:digest(original/k) for k in before}
save('public-hashes-final',dict(before=before,after=after,equal=before==after))
assert before==after
assert subprocess.run(['git','diff','--quiet','d932716','--','src','apps','tools'],cwd=ROOT).returncode==0
assert digest(ROOT/'package-lock.json')=='2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767'
cache=read(paths['api'].parent/'cache-separation.json')
cacheok=len(cache['new'])==len(cache['old'])+1 and cache['newExecution']['tuning']['cacheSource']=='miss' and all(cache['new'][k]==v for k,v in cache['old'].items())
index=dict(product='d93271610603e227b50665815881449d8bcadc9c',baseline='2487bbd',previousQA='8705d17',runs=rows,total=sum(r['checks'] for r in rows),passed=sum(r['passed'] for r in rows),previousAccepted=len(coverage),previousAcceptedPassing=sum(c['passed'] is True for c in coverage),cacheSeparated=cacheok,publicHashesPreserved=before==after,originalPrivateFilesAccessed=False,ownerTestsOrHarnessReused=False,productModified=False,notes=['F2 initial image-read race kept in f2-image-race.log; final run waits for actual image completion.','Large trace/browser cache eviction and daemon interruption attempts excluded; actual browser final run uses UI controls without response interception.','Initial three-caster rotation retained separately; report reproduction uses explicitly recorded Alice/Modernia rotation.'])
save('evidence-index',index);print(json.dumps(index,ensure_ascii=False,indent=2))
assert cacheok and index['total']==index['passed'] and all(c['passed'] is True for c in coverage)

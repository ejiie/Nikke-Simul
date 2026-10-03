"""B-DATA followup: independent byte/ESM checks and isolated committed-tree UI checks.

Only the explicitly requested standard UI suite/generator are reused. No owner oracle.
Preparation uses the same public ZIP and injected fixed clock in both production modules.
"""
import datetime, hashlib, importlib.util, io, json, subprocess, tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/single-deck-qa/bdata1r3'
ARCHIVE=Path('C:/Users/user/Desktop/StaticData.zip')
checks=[]
def sha(data):return hashlib.sha256(data).hexdigest()
def check(name,passed,detail=None):checks.append(dict(name=name,passed=bool(passed),detail=detail))
def save(name,value):(OUT/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def snapshot(ref):
 target=OUT/('tree-'+ref);target.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','archive',ref,'src','tools/data-pipeline','apps/desktop-ui','tests/ui'],cwd=ROOT)
 with tarfile.open(fileobj=io.BytesIO(raw)) as archive:archive.extractall(target,filter='data')
 return target
class Clock(datetime.datetime):
 @classmethod
 def now(cls,tz=None):return cls(2026,10,4,0,0,0,tzinfo=datetime.timezone.utc).astimezone(tz)
def prepare(tree,label):
 file=tree/'tools/data-pipeline/prepare_solo_raid_boss_attributes.py'
 spec=importlib.util.spec_from_file_location('qa_prepare_'+label,file);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 module.datetime=Clock
 module.prepare(ARCHIVE,OUT/label)
 return (OUT/label/'solo-raid-boss-attributes.json').read_bytes()
def run(args,cwd,label):
 p=subprocess.run(args,cwd=cwd,capture_output=True,encoding='utf-8')
 (OUT/(label+'.log')).write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
 return p
def main():
 OUT.mkdir(parents=True,exist_ok=True);before=sha(ARCHIVE.read_bytes())
 old=snapshot('a050853');new=snapshot('e21b774');integrated=snapshot('020a6d2')
 a=prepare(old,'old-prepared');b=prepare(new,'new-prepared')
 check('entire prepared bytes equal with identical clock input',a==b,dict(oldSha256=sha(a),newSha256=sha(b),bytes=len(b)))
 check('nine metadata records unchanged',json.loads(a)['fields']==json.loads(b)['fields'] and len(json.loads(b)['fields'])==9)
 check('public ZIP unchanged',before==sha(ARCHIVE.read_bytes()),dict(sha256=before,bytes=ARCHIVE.stat().st_size))
 for ref,tree in [('target',new),('integrated',integrated)]:
  p=run(['node','tests/ui/tools/gen_registered_messages.mjs','--check'],tree,ref+'-generator-check')
  check(ref+' generator --check',p.returncode==0)
  testfiles=[str(f.relative_to(tree)) for f in (tree/'tests/ui').glob('*.test.mjs')]
  p=run(['node','--test',*testfiles],tree,ref+'-ui-tests');check(ref+' UI 7/7',p.returncode==0)
  registry=tree/'apps/desktop-ui/registered-messages.js';previous=registry.read_text(encoding='utf-8')
  # Generate only in the ignored archive, never the product worktree.
  run(['node','tests/ui/tools/gen_registered_messages.mjs'],tree,ref+'-generated-copy')
  parse=lambda text:json.loads(text.split('new Set(',1)[1].rsplit(');',1)[0])
  prior=parse(previous);after=parse(registry.read_text(encoding='utf-8'))
  save(ref+'-registry-delta',dict(registeredCount=len(prior),generatedCount=len(after),missing=sorted(set(after)-set(prior)),extra=sorted(set(prior)-set(after))))
 for file in (ROOT/'apps/desktop-ui').rglob('*.js'):
  p=subprocess.run(['node','--input-type=module','--check'],input=file.read_bytes(),capture_output=True)
  check('ESM '+str(file.relative_to(ROOT)),p.returncode==0,p.stderr.decode('utf-8') or None)
 save('followup-audit',checks);print(json.dumps(dict(total=len(checks),failed=sum(not c['passed'] for c in checks)),ensure_ascii=False))
 return int(any(not c['passed'] for c in checks))
if __name__=='__main__':raise SystemExit(main())

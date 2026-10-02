"""Compare B-DATA product runs with independent QA's pre-merge E-PREC evidence.

Run own PrecisionProbe arithmetic/team modes against the B-DATA binaries first.
Neither the implementation's harness nor its answers are used here.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/single-deck-qa/bdata1'
BEFORE=ROOT/'artifacts/single-deck-qa/precision1'
checks=[]
for file,count in [('team-new.jsonl',60),('math-new.jsonl',737)]:
 old=[json.loads(x) for x in (BEFORE/file).read_text(encoding='utf-8-sig').splitlines()]
 new=[json.loads(x) for x in (OUT/file).read_text(encoding='utf-8-sig').splitlines()]
 assert len(old)==len(new)==count,(file,len(old),len(new))
 for a,b in zip(old,new):
  label=a.get('id') or str((a['scenario'],a['policy'],a['seed']))
  checks.append(dict(name=file+' '+label,passed=a==b))
report=dict(checks=checks,passed=sum(c['passed'] for c in checks),failed=[c for c in checks if not c['passed']],note='Exact JSON equality including versions. Team includes all members, burst windows/timeline/gauge, event counts. Arithmetic includes expected overflow/rejection.')
(OUT/'regression-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(passed=report['passed'],failed=report['failed']),ensure_ascii=False));assert not report['failed']

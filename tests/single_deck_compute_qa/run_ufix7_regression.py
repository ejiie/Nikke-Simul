"""Run only pre-existing independent QA tools against U-FIX-7, no owner tests."""
import argparse,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2];out=root/'artifacts/single-deck-qa/ufix7-preparation'
cases=[('f32','check_f32_b2.py',['--f2-legacy-regression','--desktop-only']),
       ('sources','check_f2_sources.py',[]),('diagnostics','check_f2_ufix6.py',[]),
       ('archive34','check_f2_sources.py',['--inspect-archive',str(root/'artifacts/single-deck-qa/f2-ufix3-554048887882/data/skill-replays/b41c653c67fa48dfa35cb46547de88ab.json')])]
results=[]
for label,script,extra in cases:
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:
        done=subprocess.run([sys.executable,str(Path(__file__).parent/script),'--dotnet',a.dotnet,*extra],cwd=root,env=dict(os.environ,PYTHONIOENCODING='utf-8'),stdout=log,stderr=log)
    results.append(dict(label=label,exitCode=done.returncode));(out/'regression-exits.json').write_text(json.dumps(results),encoding='utf-8')
    print(label,done.returncode,flush=True)
raise SystemExit(any(x['exitCode'] for x in results))

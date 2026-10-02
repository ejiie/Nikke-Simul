"""Fresh rerun of QA-owned U-FIX-7 repros and accepted regressions."""
import argparse,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);p.add_argument('--allowlist',action='store_true');p.add_argument('--readmission4',action='store_true');p.add_argument('--output-name');a=p.parse_args();a.allowlist=a.allowlist or a.readmission4
root=Path(__file__).resolve().parents[2];out=root/'artifacts/single-deck-qa'/(a.output_name or ('ufix7-readmission4' if a.readmission4 else 'ufix7-allowlist' if a.allowlist else 'ufix7-readmission'));out.mkdir(exist_ok=True)
cases=[('audit','check_ufix7_audit.py',[]),('surfaces','check_ufix7_surfaces.py',['--allowlist'] if a.allowlist else []),('missing','check_ufix7_missing.py',[]),
       ('f2','check_f2_conditions.py',[]),('f32','check_f32_b2.py',['--f2-legacy-regression','--desktop-only']),
       ('sources','check_f2_sources.py',[]),('diagnostics','check_f2_ufix6.py',[]),
       ('archive34','check_f2_sources.py',['--inspect-archive',str(root/'artifacts/single-deck-qa/f2-ufix3-554048887882/data/skill-replays/b41c653c67fa48dfa35cb46547de88ab.json')])]
results=[]
for label,script,extra in cases:
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:
        done=subprocess.run([sys.executable,str(Path(__file__).parent/script),'--dotnet',a.dotnet,*extra],cwd=root,env=dict(os.environ,PYTHONIOENCODING='utf-8'),stdout=log,stderr=log)
    results.append(dict(label=label,exitCode=done.returncode));(out/'regression-exits.json').write_text(json.dumps(results),encoding='utf-8')
    print(label,done.returncode,flush=True)
raise SystemExit(any(x['exitCode'] for x in results))

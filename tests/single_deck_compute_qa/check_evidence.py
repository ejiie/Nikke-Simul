"""Validate QA-normalized evidence; never invent or invoke a Backend route.

Exit 0 means evidence predicates passed, NOT completed product acceptance.
Missing/invalid evidence returns 2; outputs are always a new own-workspace artifact.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
from oracle import batch, hardware, portable, stats
from backend_v1 import results as backend_results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--kind', choices=('batch','hardware','portable','backend-results-v1'), required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    run=root/'artifacts/single-deck-qa'/('evidence-'+uuid.uuid4().hex)
    run.mkdir(parents=True)
    report=dict(productAcceptance='not_evaluated', adapter='QA_normalized_pending_Backend_contract',
                kind=args.kind, commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip())
    try:
        raw=args.input.read_bytes()
        report['inputSha256']=hashlib.sha256(raw).hexdigest()
        document=json.loads(raw.decode('utf-8-sig'))
        if args.kind=='backend-results-v1':
            report.update(backend_results(document))
            report['adapter']='Backend_Compute.cs_48c11d8'
        elif args.kind=='batch':
            rows=batch(document)
            report['validRuns']=len(rows)
            report['statistics']=stats([r['damage'] for r in rows],document['cutoff'])
        elif args.kind=='hardware':
            hardware(document['hardware'],document['selection'])
        else:
            report['scope']=portable(document)
        report['status']='evidence_predicates_passed'
        code=0
    except (ValueError,TypeError,KeyError,OSError,UnicodeError) as error:
        report.update(status='invalid_or_unsupported_evidence',errorType=type(error).__name__)
        # Do not echo arbitrary source content, paths, account fields or exception text.
        code=2
    (run/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(report,artifact=str(run)),ensure_ascii=True))
    return code


if __name__=='__main__': raise SystemExit(main())

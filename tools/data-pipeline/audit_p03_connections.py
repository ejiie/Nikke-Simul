"""Live API connection audit. Writes reference replays only; never changes account builds."""
import json
from pathlib import Path
import audit_p03_skills
from audit_p03 import request

ROOT = Path(__file__).resolve().parents[2]


def main():
    out=ROOT/'artifacts/p03/connection-implementation/api'
    audit_p03_skills.main(out)
    catalog=request('/runtime/catalog')
    assert all(c['support']['connectionReady'] and c['support']['burstSourceAvailable']
               and not c['support']['gameVerified'] and not c['support']['automaticCycleReady']
               and c['support']['gaugeFormulaStatus']=='unverified' for c in catalog['characters'])
    replays=json.loads((out/'skill-audit-replays.json').read_text(encoding='utf-8'))
    detailed=json.loads((out/'skill-audit-trace.json').read_text(encoding='utf-8'))
    for saved in replays+[detailed]:
        result=saved['result']; connection=result['connection']
        assert result['rulesVersion']=='p03.skills.2'
        assert connection['contractVersion']=='p03.connection.1' and connection['connectionReady']
        assert not connection['gameVerified'] and not connection['timelineTruncated']
        counts=connection['eventCounts']; members=result['members']
        assert counts['Shot']==sum(m['shots'] for m in members)
        assert counts['AmmoConsumed']==sum(m['ammoConsumed'] for m in members)
        assert counts['NormalHit']==sum(m['hits'] for m in members)
        assert counts['FullBurstEntered']==len(result['conditions']['combat']['fullBurstWindows'])
        assert max(e['frame'] for e in connection['timeline'])>10000
        for member in saved['inputs']:
            assert member['skills']['burstConnection']['shotId']>0
        assert request('/runtime/skill-replays/'+saved['id'])==saved
    assert detailed['result']['connection']==replays[0]['result']['connection']
    old_path=ROOT/'artifacts/p03/connection-review/api-audit/artifacts/p03/skill-audit-replays.json'
    old_count=0
    if old_path.exists():
        for old in json.loads(old_path.read_text(encoding='utf-8')):
            reread=request('/runtime/skill-replays/'+old['id'])
            assert reread['result']['rulesVersion']=='p03.skills.1' and reread['result']['connection'] is None
            assert reread['result']['members']==old['result']['members']
            old_count+=1
    summary={'newSavedRoundTrips':4,'oldSavedRoundTrips':old_count,'completeCycleSummary':True,
             'traceSummaryParity':True,'runtimeDataId':catalog['runtimeDataId'],'gameVerified':False}
    (out/'connection-api-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary))


if __name__=='__main__':
    main()

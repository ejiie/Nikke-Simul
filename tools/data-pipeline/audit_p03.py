"""Local P03 weapon-reference audit. No login, resync, or account mutations.

POSTs intentionally save versioned weapon-reference replays, never measured damage.
"""
import json
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = 'http://127.0.0.1:5180/api'


def request(path, payload=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token: headers['X-Nikke-Token'] = token
    req = urllib.request.Request(BASE+path, data=None if payload is None else json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


def main():
    boot = request('/bootstrap'); token = boot['token']
    catalog = request('/runtime/catalog')
    assert catalog['skillExecutionStatus']=='not_connected' and not catalog['missing']
    account = next(c['accountId'] for c in boot['connections'] if c.get('accountId'))
    snapshot = request('/accounts/'+account+'/snapshot')
    ids = [c['characterId'] for c in catalog['characters']]
    reports = []
    for policy in ('per_trigger','per_pellet'):
        body = {'snapshotId':snapshot['id'],'characterIds':ids,'scenarioLevel':400,
                'conditions': {'durationFrames':10800,'pelletCoefficientPolicy':policy,'critMode':'off','trace':False,
                               'targetLabel':'synthetic fixed target, defense 0',
                               'notes':'Weapon reference audit, not measured game damage.'}}
        result = request('/runtime/weapon-replays',body,token)
        assert request('/runtime/weapon-replays/'+result['id'])==result
        r=result['result']
        assert r['status']=='weapon_reference_only' and r['skillExecutionStatus']=='not_connected'
        assert len(r['members'])==5 and not r['events']
        for member in r['members']:
            assert member['shots']>0
            for rounding,damage in member['damage'].items():
                assert damage==sum(effect[rounding] for effect in member['effects'].values())
        for rounding,damage in r['totalDamage'].items():
            assert damage==sum(member['damage'][rounding] for member in r['members'])
        reports.append(result)
    # Same firing timeline for both coefficient hypotheses; never silently choose an SG answer.
    for a,b in zip(reports[0]['result']['members'], reports[1]['result']['members']):
        assert a['shots']==b['shots'] and a['hits']==b['hits']
        if next(c['weapon'] for c in catalog['characters'] if c['characterId']==a['characterId'])!='SG':
            assert a['damage']==b['damage']
    alice=next(c['characterId'] for c in catalog['characters'] if c['name']=='앨리스')
    condition = {'durationFrames':600,'critMode':'on','core':True,'trace':True,'traceLimit':2000,
                 'fullBurstWindows':[{'startFrame':101,'endFrame':401}],
                 'attackBuffWindows':[{'characterId':alice,'startFrame':101,'endFrame':301,
                                       'buff':{'source':'audit:manual_attack','rate':.5,'stacks':1}}]}
    record=request('/runtime/weapon-replays',{'snapshotId':snapshot['id'],'characterIds':[alice],
                                             'scenarioLevel':400,'conditions':condition},token)
    assert any(e['kind']=='hit' and e['fullBurst'] for e in record['result']['events'])
    reports.append(record)
    # Detail sink does not change auto/control-off execution or damage.
    condition['trace']=False
    plain=request('/runtime/weapon-replays',{'snapshotId':snapshot['id'],'characterIds':[alice],
                                             'scenarioLevel':400,'conditions':condition},token)
    assert plain['result']['totalDamage']==record['result']['totalDamage']
    assert plain['result']['eventCount']==record['result']['eventCount']
    try:
        request('/runtime/weapon-replays',{'snapshotId':snapshot['id'],'characterIds':ids,
                                          'scenarioLevel':400,'conditions':{'durationFrames':60}},token)
        raise AssertionError('SG policy was not required')
    except urllib.error.HTTPError as error:
        assert error.code==400
    output=ROOT/'artifacts/p03'; output.mkdir(parents=True,exist_ok=True)
    (output/'weapon-replays.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
    summary={'characters':len(ids),'officialFunctions':catalog['functions'],'nestedCharacterSkills':catalog['characterSkills'],
             'missingGraphEdges':catalog['missing'],'durationFrames':10800,'pelletPoliciesCompared':2,
             'savedReplaysChecked':4,'traceSummaryParity':True,'implicitSgPolicyRejected':True,
             'skillExecutionStatus':'not_connected','gameObservation':'none',
             'members':[{k:m[k] for k in ('characterId','shots','hits','fullChargeShots','reloadCompletions')}
                        for m in reports[0]['result']['members']]}
    (output/'audit-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary))


if __name__=='__main__': main()

"""Exercise official five-character skills against a saved account, without resyncing.

Creates local synthetic-condition replay artifacts. None are game observations.
"""
import copy
import json
import urllib.error
from pathlib import Path
from audit_p03 import request

ROOT = Path(__file__).resolve().parents[2]


def main():
    boot = request('/bootstrap')
    token = boot['token']
    catalog = request('/runtime/catalog')
    assert catalog['skillReplayAvailable']
    assert all(c['support']['allLevelsExecutable'] for c in catalog['characters'])
    account = next(c['accountId'] for c in boot['connections'] if c.get('accountId'))
    snapshot = request('/accounts/'+account+'/snapshot')
    by_name = {c['name']: c['characterId'] for c in catalog['characters']}
    names = ['리타', '블랑', '누아르', '앨리스', '모더니아']
    ids = [by_name[n] for n in names]
    casts, windows = [], []
    for index, start in enumerate(range(601, 10202, 1200)):
        burst3 = '모더니아' if index == 3 else ('앨리스' if index % 2 == 0 else '누아르')
        casts.extend({'frame':start+offset, 'characterId':by_name[name]} for offset,name in enumerate(['리타','블랑',burst3]))
        windows.append({'startFrame':start+3, 'endFrame':min(10801,start+3+(900 if burst3=='모더니아' else 600))})
    conditions = {'roundingPolicy':'legacy_term_floor', 'casts':casts,
                  'combat': {'durationFrames':10800, 'enemyDefense':30925, 'pelletCoefficientPolicy':'per_trigger',
                             'critMode':'off', 'trace':False, 'traceLimit':20000, 'fullBurstWindows':windows,
                             'targetLabel':'Solo Raid challenge measurement reference; fixed pre-2B defense',
                             'notes':'Synthetic prescribed casts/HP; no measured game damage; no automatic defense transition.'}}
    body = {'snapshotId':snapshot['id'], 'characterIds':ids, 'scenarioLevel':400, 'conditions':conditions}
    reports = []
    for policy in ('legacy_term_floor','final_round_even','nested_floor'):
        body['conditions']['roundingPolicy'] = policy
        saved = request('/runtime/skill-replays',body,token)
        assert request('/runtime/skill-replays/'+saved['id']) == saved
        result = saved['result']
        assert result['skillExecutionStatus']=='selected_five_effects_connected'
        assert result['totalDamage']==sum(m['damage'] for m in result['members'])
        assert all(m['damage']==sum(m['effects'].values()) for m in result['members'])
        assert all(m['shots']>0 and m['hp']>0 for m in result['members'])
        modernia = next(m for m in result['members'] if m['characterId']==by_name['모더니아'])
        assert any(k.startswith('function:') for k in modernia['effects'])
        assert any(k.endswith(':weapon') for k in modernia['effects'])
        assert modernia['ammoConsumed'] < modernia['shots']
        noir = next(m for m in result['members'] if m['characterId']==by_name['누아르'])
        assert any(k.startswith('skill:') for k in noir['effects'])
        for member in saved['inputs']:
            build = next(c for c in snapshot['characters'] if c['characterId']==member['weapon']['characterId'])
            assert member['skills']['levels']=={slot:build['skills'][key] for slot,key in (('skill1','1'),('skill2','2'),('burst','3'))}
        reports.append(saved)
    detail = copy.deepcopy(body)
    detail['conditions']['roundingPolicy']='legacy_term_floor'
    detail['conditions']['combat']['trace']=True
    detailed = request('/runtime/skill-replays',detail,token)
    assert detailed['result']['totalDamage']==reports[0]['result']['totalDamage']
    assert detailed['result']['members']==reports[0]['result']['members']
    assert detailed['result']['eventCount']==reports[0]['result']['eventCount']
    assert detailed['result']['traceTruncated']
    assert any(e['kind']=='shared_shield' for e in detailed['result']['events'])
    assert any(e['kind']=='heal' for e in detailed['result']['events'])
    assert any(e['kind']=='cooldown_change' for e in detailed['result']['events'])
    for invalid in ({'roundingPolicy':''}, {'casts':[{'frame':1,'characterId':ids[0]},{'frame':2,'characterId':ids[0]}]}):
        bad=copy.deepcopy(body)
        bad['conditions'].update(invalid)
        try:
            request('/runtime/skill-replays',bad,token)
            raise AssertionError('Invalid skill replay was accepted')
        except urllib.error.HTTPError as e:
            assert e.code==400
    out=ROOT/'artifacts/p03'; out.mkdir(parents=True,exist_ok=True)
    summary={'gameObservation':'none', 'runtimeDataId':catalog['runtimeDataId'], 'characters':5,
             'skillLevelsAudited':10, 'slotLevelDefinitions':150, 'roundingPoliciesCompared':3,
             'durationFrames':10800, 'savedReplaysChecked':3, 'traceSummaryParity':True,
             'missingSupport':[], 'invalidRoundingAndCooldownRejected':True,
             'members':[{k:m[k] for k in ('characterId','shots','hits','ammoConsumed','maxAmmo','effects')}
                        for m in reports[0]['result']['members']]}
    (out/'skill-audit-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'skill-audit-replays.json').write_text(json.dumps(reports,ensure_ascii=False),encoding='utf-8')
    (out/'skill-audit-trace.json').write_text(json.dumps(detailed,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='members'}))


if __name__ == '__main__':
    main()

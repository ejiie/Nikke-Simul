"""P04 API audit: saved specs are read only; generated runs are synthetic comparisons."""
import argparse, copy, json, math, urllib.request, urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=5188);args=parser.parse_args()
    base=f'http://127.0.0.1:{args.port}/api'
    def request(path,body=None,token=None):
        req=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json',**({'X-Nikke-Token':token} if token else {})})
        with urllib.request.urlopen(req,timeout=180) as response:return json.load(response)
    boot=request('/bootstrap');token=boot['token'];catalog=request('/runtime/catalog')
    assert all(c['support']['automaticCycleReady'] and not c['support']['gameVerified'] for c in catalog['characters'])
    account=next(c['accountId'] for c in boot['connections'] if c['status']=='ready')
    snapshot=request('/accounts/'+account+'/snapshot')
    body={'snapshotId':snapshot['id'],'characterIds':['5011','5008','5009','5004','5044'],'scenarioLevel':400,
          'conditions':{'roundingPolicy':'legacy_term_floor','autoBurst':{'stageDelayMinFrames':1,'stageDelayMaxFrames':1,'fullBurstEntryDelayFrames':28,'burst3Rotation':['5004','5044']},
                        'combat':{'durationFrames':10800,'enemyDefense':30925,'critMode':'off','pelletCoefficientPolicy':'per_trigger','trace':False,'traceLimit':20000}}}
    out=ROOT/'artifacts/p04/charge-verification';out.mkdir(parents=True,exist_ok=True)
    reports=[]
    for policy in ['legacy_term_floor','final_round_even','nested_floor']:
        body['conditions']['roundingPolicy']=policy
        saved=request('/runtime/skill-replays',body,token);r=saved['result'];team=r['teamBurst']
        assert saved['kind']=='team_burst_replay' and r['rulesVersion']=='p04.team.2'
        assert not team['gameVerified'] and team['gaugeFormulaStatus']=='reference_candidate'
        assert len(team['fullBursts'])>=4
        alice_gauge=[e for e in team['timeline'] if e['kind']=='gauge' and e['characterId']=='5004']
        assert alice_gauge and all(e['requestedRaw']==196000 for e in alice_gauge)
        assert math.isclose(r['totalDamage'],sum(m['damage'] for m in r['members']))
        assert all(math.isclose(m['damage'],sum(m['effects'].values())) for m in r['members'])
        casts=[e for e in team['timeline'] if e['kind']=='burst_cast']
        assert [e['step'] for e in casts]==[1,2,3]*(len(casts)//3)+[1,2,3][:len(casts)%3]
        assert any(w['caster']=='5044' for w in team['fullBursts'])
        for w in team['fullBursts']:
            assert w['plannedEndFrame']-w['startFrame']==(900 if w['caster']=='5044' else 600)
            assert w['startFrame']-max(e['frame'] for e in casts if e['step']==3 and e['frame']<w['startFrame'])==28
            assert not any(e['kind']=='gauge' and w['startFrame']<=e['frame']<(w['endFrame'] or w['plannedEndFrame']) for e in team['timeline'])
        assert request('/runtime/skill-replays/'+saved['id'])==saved
        reports.append(saved)
    detail=copy.deepcopy(body);detail['conditions']['roundingPolicy']='legacy_term_floor';detail['conditions']['combat']['trace']=True
    detailed=request('/runtime/skill-replays',detail,token)
    assert detailed['result']['teamBurst']==reports[0]['result']['teamBurst']
    assert detailed['result']['totalDamage']==reports[0]['result']['totalDamage']
    assert detailed['result']['traceTruncated']
    for invalid in [{'casts':[{'frame':1,'characterId':'5011'}]}, {'autoBurst':{'burst3Rotation':['5011']}}]:
        bad=copy.deepcopy(body);bad['conditions'].update(invalid)
        try: request('/runtime/skill-replays',bad,token)
        except urllib.error.HTTPError as exc: assert exc.code==400
        else: raise AssertionError('Invalid automatic input accepted')
    # Defaults use genuine random stage delays, not a seeded production RNG.
    default=copy.deepcopy(body);default['conditions']['autoBurst']={'burst3Rotation':['5044','5004']};default['conditions']['combat']['critMode']='sample'
    sampled=request('/runtime/skill-replays',default,token);assert len(sampled['result']['teamBurst']['fullBursts'])>=4
    summary={'durationFrames':10800,'roundingPolicies':3,'savedRoundTrips':3,'traceParity':True,'invalidInputsRejected':2,
             'randomCycleRun':True,'cycles':len(reports[0]['result']['teamBurst']['fullBursts']),
             'fullBurstFrames':reports[0]['result']['teamBurst']['fullBurstFrames'],'gameVerified':False}
    (out/'api-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (out/'replays.json').write_text(json.dumps(reports+[sampled]),encoding='utf-8')
    print(json.dumps(summary))
if __name__=='__main__':main()

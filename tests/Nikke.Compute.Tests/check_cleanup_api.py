"""F2-B HTTP checks used with the public-fixture/synthetic-account harness."""
import copy
import hashlib
import json
import sqlite3
import time


def verify_cleanup(call, base, report, data):
    evidence=report['cleanup']={}
    catalog=call('presentation/solo-raid-bosses')
    evidence['bossCatalog']=catalog
    assert catalog['bosses'][0]['id']=='dummy'
    assert len(catalog['bosses'])>1
    assert not catalog['complete'] and catalog['diagnostics']
    assert all('sourceName' not in row and 'sourceId' not in row for row in catalog['bosses'])
    assert all(row['displayable'] is False and row['code']=='korean_name_unavailable' for row in catalog['diagnostics'])
    boss=next(b for b in catalog['bosses'] if b['season']==41)
    assert boss['name']=='리버렐리오 바디'
    manifest=json.loads((data/'presentation/solo-raid-bosses.manifest.json').read_text(encoding='utf-8'))
    hashes={row['id']:row['sha256'] for row in manifest['bosses'] if row['displayable']}
    for row in catalog['bosses'][1:]:
        path=data/'presentation/assets/bosses'/row['imageUrl'].rsplit('/',1)[1]
        assert hashlib.sha256(path.read_bytes()).hexdigest()==hashes[row['id']]
        assert hashes[row['id']] not in json.dumps(catalog)
        assert call(row['imageUrl'],binary=True)==path.read_bytes()
    call('/editor/assets/solo-raid-bosses.manifest.json',expected=404)
    auto=copy.deepcopy(base)
    auto.pop('conditionProfile')
    auto['bossId']=boss['id']
    c=auto['conditions']['combat']
    for key in ('properDistance','elementAdvantage','durationFrames','pelletCoefficientPolicy','critMode'):
        c.pop(key,None)
    c.update(bossDistance=35,bossWeakElement='Fire')
    default=call('runtime/skill-replays',auto)
    evidence['defaultReplay']=default
    actual=default['result']['conditions']['combat']
    assert (actual['durationFrames'],actual['pelletCoefficientPolicy'],actual['critMode'],actual['defenseMode'])==(10800,'per_trigger','sample','team_damage_threshold')
    assert default['boss']==boss
    assert default['battleConditions']['defenseMode']=='team_damage_threshold'
    assert call('runtime/skill-replays/'+default['id']+'/battle-conditions')==default['battleConditions']
    c.update(critMode='off',trace=True,traceLimit=20000,attackBuffWindows=[
        {'characterId':cid,'buff':{'source':'synthetic_f2_threshold','rate':100,'stacks':1},'startFrame':1,'endFrame':10801}
        for cid in base['characterIds']])
    replay=call('runtime/skill-replays',auto)
    evidence['switchReplay']=replay
    defense=replay['result']['defense']; switch=defense['switchAfterHit']
    assert switch and switch['cumulativeDamage']>2_000_000_000 and defense['finalDefense']==31784
    hit_events=[e for e in replay['result']['events'] if e.get('hit')]
    crossing=next(e for e in hit_events if e['id']==switch['hitTraceId'])
    assert crossing['hit']['defense']==30925
    later=next(e for e in hit_events if e['id']>switch['hitTraceId'])
    assert later['hit']['defense']==31784
    assert call('runtime/skill-replays/'+replay['id'])==replay
    def batch(boss_id,legacy=False):
        conditions=copy.deepcopy(auto['conditions'])
        if legacy:
            conditions['combat'].update(durationFrames=10800,pelletCoefficientPolicy='per_trigger',defenseMode='fixed')
        request={'snapshotId':base['snapshotId'],'characterIds':base['characterIds'],'conditions':conditions,
                 'runs':1,'useSavedTactic':False,'execution':{'requested':'cpu','maxWorkers':1},'bossId':boss_id}
        if legacy: request['conditionProfile']='legacy'
        created=call('compute/experiments',request,202)
        for _ in range(1200):
            state=call('compute/experiments/'+created['id'])
            if state['state'] in ('completed','failed','cancelled'):break
            time.sleep(.05)
        assert state['state']=='completed',state
        rows=call('compute/experiments/'+state['id']+'/results')['runs']
        assert len(rows)==1 and rows[0]['defense']
        assert call('compute/experiments/'+state['id']+'/battle-conditions')==state['input']['battleConditions']
        return {'status':state,'run':rows[0]}
    first=batch('dummy'); second=batch(boss['id']); fixed=batch('dummy',True)
    evidence['batches']={'dummy':first,'selected':second,'fixed':fixed}
    assert first['status']['input']['fingerprint']==second['status']['input']['fingerprint']
    assert first['status']['execution']['fingerprint']==second['status']['execution']['fingerprint']
    assert first['status']['input']['boss']['id']=='dummy' and second['status']['input']['boss']==boss
    assert first['run']['teamDamage']==second['run']['teamDamage']==replay['result']['totalDamage']
    assert first['run']['defense']==second['run']['defense']==defense
    assert fixed['status']['input']['fingerprint']!=first['status']['input']['fingerprint']
    assert fixed['status']['execution']['fingerprint']!=first['status']['execution']['fingerprint']
    assert fixed['status']['input']['defPolicy']=='fixed:30925'
    assert first['status']['input']['defPolicy']=='team_damage_threshold:30925:2000000000:31784'
    assert fixed['run']['defense']['mode']=='fixed' and fixed['run']['defense']['switchAfterHit'] is None
    legacy=report['legacyReplay']
    assert call('runtime/skill-replays/'+legacy['id']+'/battle-conditions')['durationFrames']==120
    def storage():
        files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (data/'skill-replays').glob('*.json')}
        with sqlite3.connect(data/'compute/batches.db') as db:
            counts=[db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('experiments','batch_runs')]
        return files,counts
    before=storage(); evidence['errors']=[]
    for fields in ({'durationFrames':120},{'durationFrames':None},{'durationFrames':'10800'},
                   {'pelletCoefficientPolicy':'per_pellet'},{'defenseMode':'fixed'},{'defenseMode':'unknown'}):
        bad=copy.deepcopy(auto); bad['conditions']['combat'].update(fields)
        evidence['errors'].append(call('runtime/skill-replays',bad,400))
        evidence['errors'].append(call('compute/experiments',dict(bad,runs=1,useSavedTactic=False),400))
    for boss_id in ('unknown',catalog['diagnostics'][0]['id']):
        bad=dict(auto,bossId=boss_id)
        evidence['errors'].append(call('runtime/skill-replays',bad,400))
        evidence['errors'].append(call('compute/experiments',dict(bad,runs=1,useSavedTactic=False),400))
    weapon=dict(base,conditions=dict(auto['conditions']['combat'],defenseMode='team_damage_threshold'))
    evidence['errors'].append(call('runtime/weapon-replays',weapon,400))
    assert before==storage(), 'invalid request wrote replay/compute data'
    # Raw historical record without the new fields remains byte-identical on GET/export.
    historical=copy.deepcopy(legacy)
    for key in ('boss','battleConditions'): historical.pop(key,None)
    historical['result'].pop('defense',None)
    historical['result']['conditions']['combat'].pop('defenseMode',None)
    historical['id']='f2'*16
    file=data/'skill-replays'/(historical['id']+'.json')
    raw=json.dumps(historical,ensure_ascii=False).encode()
    file.write_bytes(raw)
    assert call('runtime/skill-replays/'+historical['id'])==historical
    assert call('/api/runtime/skill-replays/'+historical['id']+'/export.json',binary=True)==raw
    assert call('runtime/skill-replays/'+historical['id']+'/battle-conditions')['defenseMode']=='fixed'
    assert file.read_bytes()==raw
    evidence['status']='passed'

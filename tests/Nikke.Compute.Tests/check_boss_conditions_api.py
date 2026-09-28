"""F-COND-B isolated catalog/API evidence. Public allowlist + newly authored account.
--catalog-only captures pre-engine legacy reference without any new engine behavior.
"""
import argparse
import copy
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from check_compute_api import ROOT, digest, read
sys.path.insert(0, str(ROOT / 'tools/data-pipeline'))
from prepare_combat_conditions import load_profiles, enrich_runtime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-data', type=Path, required=True)
    parser.add_argument('--source-roster', type=Path, required=True)
    parser.add_argument('--dotnet', required=True)
    parser.add_argument('--catalog-only', action='store_true')
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    run = ROOT / 'artifacts/boss-conditions/api' / uuid.uuid4().hex
    data = run / 'data'
    data.mkdir(parents=True)
    source = args.source_data.resolve()
    hashes, checks = {}, []
    report = {'status': 'failed', 'kind': 'synthetic_account_public_catalog', 'checks': checks}
    process = log = None
    def public_copy(relative):
        src, dst = source / relative, data / relative
        hashes[str(src)] = digest(src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    try:
        public_copy(Path('game-catalog.json'))
        for folder in ('calculation', 'runtime'):
            public_copy(Path(folder) / 'current.json')
            manifest = read(data / folder / 'current.json')
            version = manifest['id']
            assert len(version) == 64 and all(c in '0123456789abcdef' for c in version)
            for name in (manifest['fileHashes'] if folder == 'calculation' else ['catalog.json']):
                assert Path(name).name == name
                public_copy(Path(folder) / version / name)
        hashes[str(args.source_roster.resolve())] = digest(args.source_roster)
        profiles = load_profiles(args.source_roster)
        runtime_id = enrich_runtime(data / 'runtime', profiles)
        report['runtimeDataId'] = runtime_id
        ids = ['5011', '5008', '5004', '5009', '5044']
        game = read(data / 'game-catalog.json')
        snapshot = {'id': 'synthetic-boss', 'accountId': 'synthetic-account', 'gameSnapshotId': game['id'], 'synchroLevel': 400,
            'savedAt': '2026-09-28T00:00:00+00:00', 'observedAt': '2026-09-28T00:00:00+00:00',
            'consoles': {k: 0 for k in ('1001', '1101', '1102', '1103', '1201', '1202', '1203', '1204', '1205')},
            'characters': [{'characterId': id, 'name': game['names'][id], 'level': 400, 'nativeLevel': 400,
                'limitBreak': 0, 'core': 0, 'bond': 0, 'skills': {'1': 10, '2': 10, '3': 10}, 'cubeId': '0', 'cubeLevel': 0,
                'collectionId': '0', 'collectionGrade': 'none', 'collectionLevel': 0,
                'equipment': [{'slot': slot, 'tier': 0, 'level': 0, 'manufacturer': 0,
                    'lines': [{'lineIndex': i, 'presence': 'absent'} for i in range(1, 4)]} for slot in ('head', 'torso', 'arm', 'leg')]} for id in ids]}
        # This is a NEW account database, never copied from source.
        with sqlite3.connect(data / 'accounts.db') as db:
            db.execute('CREATE TABLE snapshots(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL)')
            db.execute('CREATE TABLE accounts(id TEXT PRIMARY KEY,current_id TEXT NOT NULL REFERENCES snapshots(id))')
            db.execute('INSERT INTO snapshots VALUES(?,?,?,?)', (snapshot['id'], snapshot['accountId'], 1, json.dumps(snapshot)))
            db.execute('INSERT INTO accounts VALUES(?,?)', (snapshot['accountId'], snapshot['id']))
            ol_snapshot=copy.deepcopy(snapshot)
            ol_snapshot.update(id='synthetic-boss-ol',accountId='synthetic-ol-account')
            for member in ol_snapshot['characters']:
                head=member['equipment'][0]
                head['tier']=10
                head['lines'][0]={'lineIndex':1,'presence':'present','optionType':'StatAtk',
                                 'normalizedValue':game['optionSteps']['atk_pct'][0],'unit':'ratio'}
            db.execute('INSERT INTO snapshots VALUES(?,?,?,?)', (ol_snapshot['id'], ol_snapshot['accountId'], 1, json.dumps(ol_snapshot)))
            db.execute('INSERT INTO accounts VALUES(?,?)', (ol_snapshot['accountId'], ol_snapshot['id']))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        assert port not in (5180, 5181)
        report['port'] = port
        env = dict(os.environ, NIKKE_DATA_ROOT=str(data), NIKKE_PROJECT_ROOT=str(ROOT), NIKKE_PORT=str(port), NIKKE_TEST_FIXTURE='1')
        env.pop('NIKKE_GAME_CATALOG', None)
        token = ''
        def call(path, payload=None, expected=200):
            request = urllib.request.Request(f'http://127.0.0.1:{port}/api/' + path,
                data=None if payload is None else json.dumps(payload).encode(),
                headers={'Content-Type': 'application/json', 'X-Nikke-Token': token})
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    status, body = response.status, json.load(response)
            except urllib.error.HTTPError as error:
                status, raw_body = error.code, error.read()
                try:
                    body=json.loads(raw_body)
                except ValueError:
                    body={'raw':raw_body.decode(errors='replace')}
            assert status == expected, (path, status, body)
            return body
        log = (run / 'api.log').open('w', encoding='utf-8')
        process = subprocess.Popen([args.dotnet, str(ROOT / 'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],
            cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        for _ in range(200):
            try:
                token = call('bootstrap')['token']
                break
            except (OSError, urllib.error.URLError):
                time.sleep(.1)
        assert token, 'API startup failed'
        initial = call('snapshots/' + snapshot['id'])
        catalog = call('runtime/combat-conditions')
        report['catalog'] = catalog
        assert catalog['source']['sha256'] == hashes[str(args.source_roster.resolve())]
        assert sum(g['characterCount'] for g in catalog['weaponRanges']) == 192
        ranges = {g['weaponType']: g for g in catalog['weaponRanges']}
        assert ranges['SR']['exceptions'][0]['characterId'] == '5042'
        assert [(r['min'], r['max'], r['count']) for r in ranges['SR']['ranges']] == [(45, 100, 35), (25, 45, 1)]
        assert ranges['RL']['ranges'][0]['min'] == ranges['RL']['ranges'][0]['max'] == 0
        deck = call('snapshots/' + snapshot['id'] + '/combat-conditions?characterIds=' + ','.join(ids))
        report['deck'] = deck
        assert [m['characterId'] for m in deck['members']] == ids
        assert deck['members'][0]['bonusRangeMin'] == 15 and deck['members'][2]['element'] == 'Fire'
        call('snapshots/' + snapshot['id'] + '/combat-conditions?characterIds=missing', expected=400)
        checks.append('source hash, 192-row dynamic aggregation, SR exception/RL data, ordered owned deck profiles')
        base = {'snapshotId': snapshot['id'], 'characterIds': ids, 'scenarioLevel': 400,
            'conditions': {'roundingPolicy': 'client_f32', 'combat': {'durationFrames': 120, 'enemyDefense': 30925,
                'critMode': 'off', 'pelletCoefficientPolicy': 'per_trigger', 'properDistance': True, 'elementAdvantage': True}}}
        legacy = call('runtime/skill-replays', base)
        report['legacyReplay'] = legacy
        assert call('runtime/skill-replays/' + legacy['id']) == legacy
        if args.baseline:
            before = read(args.baseline)['legacyReplay']['result']
            assert legacy['result']['members'] == before['members']
            assert legacy['result']['totalDamage'] == before['totalDamage']
            checks.append('pre-engine legacy bool replay results exactly reproduced')
        checks.append('legacy bool replay saved/read without changing conditions')
        if not args.catalog_only:
            verify_integrated(call, base, report)
        assert call('snapshots/' + snapshot['id']) == initial
        report['status'] = 'passed'
    finally:
        if process is not None:
            process.terminate()
            process.wait(timeout=30)
        if log:
            log.close()
        report['sourceChanges'] = [name for name, value in hashes.items() if digest(Path(name)) != value]
        (run / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        (run / 'source-hashes.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
        print(run)
        assert not report['sourceChanges']


def verify_integrated(call, base, report):
    legacy=report['legacyReplay']
    assert legacy['conditionCompatibility']['mode']=='legacy_global'
    assert '전원 적용' in call('runtime/skill-replays/'+legacy['id']+'/condition-compatibility')['label']
    modern=copy.deepcopy(base)
    combat=modern['conditions']['combat']
    del combat['properDistance'],combat['elementAdvantage']
    combat.update(bossDistance=35,bossWeakElement='Fire',trace=True)
    mixed=call('runtime/skill-replays',modern)
    report['mixedReplay']=mixed
    assert mixed['conditionCompatibility']['mode']=='per_member'
    assert mixed['result']['totalDamage']==sum(m['damage'] for m in mixed['result']['members'])
    assert 'properDistance' not in mixed['result']['conditions']['combat']
    expected={'5011':(True,False),'5008':(True,False),'5004':(False,True),'5009':(False,False),'5044':(True,True)}
    hit_events=[e for e in mixed['result']['events'] if e.get('hit')]
    assert set(e['source'] for e in hit_events)==set(expected)
    for event in hit_events:
        hit=event['hit']
        distance,element=expected[event['source']]
        assert hit['properDistance']==(distance and hit['damageType']=='normal'),event
        assert hit['elementAdvantage']==element,event
    for member in mixed['inputs']:
        assert member['weapon']['bonusRangeMin'] is not None and member['weapon']['element']
    assert call('runtime/skill-replays/'+mixed['id'])==mixed
    unset=copy.deepcopy(modern)
    unset['conditions']['combat'].update(bossDistance=None,bossWeakElement=None)
    none=call('runtime/skill-replays',unset)
    assert none['conditionCompatibility']['mode']=='per_member'
    assert call('runtime/skill-replays/'+none['id']+'/condition-compatibility')['mode']=='per_member'
    assert all(not e['hit']['properDistance'] and not e['hit']['elementAdvantage'] for e in none['result']['events'] if e.get('hit'))
    report['unsetReplay']=none
    invalid=[{'bossDistance':-1},{'bossDistance':101},{'bossDistance':35.5},{'bossWeakElement':'Electric'},
             {'bossWeakElement':'fire'},{'bossDistance':None,'properDistance':False},{'bossWeakElement':None,'elementAdvantage':True}]
    report['errors']=[]
    for fields in invalid:
        bad=copy.deepcopy(modern)
        bad['conditions']['combat'].update(fields)
        report['errors'].append(call('runtime/skill-replays',bad,400))
    report['checks'].append('new mixed-deck member hit flags, null mode preserved, saved profiles, 7 invalid/mixed wire errors')
    def batch(conditions):
        request={'snapshotId':'synthetic-boss-ol','characterIds':base['characterIds'],'conditions':conditions,
                 'runs':1,'phase':'final','useSavedTactic':False,'execution':{'requested':'cpu','maxWorkers':1}}
        created=call('compute/experiments',request,202)
        for _ in range(1200):
            end=call('compute/experiments/'+created['id'])
            if end['state'] in ('completed','cancelled','failed'):
                break
            time.sleep(.05)
        assert end['state']=='completed',end
        rows=call('compute/experiments/'+end['id']+'/results')['runs']
        stats=call('compute/experiments/'+end['id']+'/statistics')
        mode=call('compute/experiments/'+end['id']+'/condition-compatibility')
        catalog=call('compute/experiments/'+end['id']+'/ol-candidates')
        assert len(rows)==1 and stats['team']['n']==1
        assert end['input']['conditionCompatibility']==mode
        return {'status':end,'runs':rows,'statistics':stats,'mode':mode,'olCatalog':catalog}
    a=batch(modern['conditions'])
    unset_conditions=copy.deepcopy(unset['conditions'])
    unset_conditions['Combat']=unset_conditions.pop('combat') # accepted envelope casing must not lose saved mode/OL filtering
    b=batch(unset_conditions)
    c=batch(base['conditions'])
    report['batches']={'perMember':a,'unset':b,'legacy':c}
    assert len({x['status']['input']['fingerprint'] for x in (a,b,c)})==3
    assert len({x['status']['execution']['fingerprint'] for x in (a,b,c)})==3
    fire_candidates={x['after']['characterId'] for x in a['olCatalog']['candidates'] if x['after']['optionId']=='IncElementDmg'}
    all_candidates={x['after']['characterId'] for x in c['olCatalog']['candidates'] if x['after']['optionId']=='IncElementDmg'}
    assert fire_candidates=={'5004','5044'}
    assert all_candidates==set(base['characterIds'])
    assert not any(x['after']['optionId']=='IncElementDmg' for x in b['olCatalog']['candidates'])
    assert b['mode']['mode']=='per_member' and b['mode']['bossDistance'] is None
    bad_conditions=copy.deepcopy(modern['conditions'])
    bad_conditions['combat']['properDistance']=False
    report['errors'].append(call('compute/experiments',{'snapshotId':'synthetic-boss-ol','characterIds':base['characterIds'],
                           'conditions':bad_conditions,'runs':1,'useSavedTactic':False},400))
    report['checks'].append('three 1-run compute batches: mode/fingerprints/cache separated; elemental OL only matching members; legacy all/unset none')


if __name__ == '__main__':
    main()

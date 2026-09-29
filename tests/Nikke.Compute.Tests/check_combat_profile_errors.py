"""B-FIX-2: hash-valid malformed public catalogs, NEW synthetic accounts, isolated HTTP.

Never copies accounts, sessions, or caches. --source-data may use a previous isolated
public fixture. --before-fix records the three missing-field defects with the old DLL.
"""
import argparse
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from check_compute_api import ROOT, digest, read


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-data', type=Path, required=True)
    parser.add_argument('--dotnet', required=True)
    parser.add_argument('--before-fix', action='store_true')
    args = parser.parse_args()
    run = ROOT / 'artifacts/boss-conditions/errors' / uuid.uuid4().hex
    run.mkdir(parents=True)
    source = args.source_data.resolve()
    hashes, cases = {}, []
    report = {'status': 'failed', 'beforeFix': args.before_fix, 'cases': cases}
    mutations = [('missing', None), ('null', None), ('wrong_type', '0'),
                 ('wrong_type', False), ('wrong_type', {}), ('wrong_type', []), ('wrong_type', 0.5)]
    if args.before_fix:
        mutations = mutations[:1]
    try:
        for field in ('bonusRangeMin', 'bonusRangeMax', 'element'):
            for index, (reason, value) in enumerate(mutations):
                case = {'field': field, 'reason': reason, 'value': value, 'responses': []}
                cases.append(case)
                folder = run / f'{field}-{index}'
                data = folder / 'data'
                data.mkdir(parents=True)
                def public_copy(relative):
                    src, dst = source / relative, data / relative
                    hashes[str(src)] = digest(src)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
                public_copy(Path('game-catalog.json'))
                public_copy(Path('calculation/current.json'))
                manifest = read(data / 'calculation/current.json')
                assert len(manifest['id']) == 64 and all(c in '0123456789abcdef' for c in manifest['id'])
                for name in manifest['fileHashes']:
                    assert Path(name).name == name
                    public_copy(Path('calculation') / manifest['id'] / name)
                runtime_manifest = source / 'runtime/current.json'
                hashes[str(runtime_manifest)] = digest(runtime_manifest)
                runtime_id = read(runtime_manifest)['id']
                assert len(runtime_id) == 64 and all(c in '0123456789abcdef' for c in runtime_id)
                runtime_file = source / 'runtime' / runtime_id / 'catalog.json'
                hashes[str(runtime_file)] = digest(runtime_file)
                catalog = read(runtime_file)
                member = catalog['combatProfiles']['characters']['5004']
                # A string is valid for element, so use a number for its string-type case.
                if field == 'element' and index == 2:
                    value = case['value'] = 0
                if reason == 'missing':
                    del member[field]
                else:
                    member[field] = value
                raw = json.dumps(catalog, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                malformed_id = hashlib.sha256(raw).hexdigest()
                target = data / 'runtime' / malformed_id
                target.mkdir(parents=True)
                (target / 'catalog.json').write_bytes(raw)
                (data / 'runtime/current.json').write_text(json.dumps({'id': malformed_id}), encoding='utf-8')
                case['runtimeDataId'] = malformed_id
                game = read(data / 'game-catalog.json')
                ids = ['5011', '5008', '5004', '5009', '5044']
                snapshot = {'id': 'synthetic-errors', 'accountId': 'synthetic-errors-account',
                    'gameSnapshotId': game['id'], 'synchroLevel': 400,
                    'savedAt': '2026-09-28T00:00:00+00:00', 'observedAt': '2026-09-28T00:00:00+00:00',
                    'consoles': {k: 0 for k in ('1001', '1101', '1102', '1103', '1201', '1202', '1203', '1204', '1205')},
                    'characters': [{'characterId': cid, 'name': game['names'][cid], 'level': 400, 'nativeLevel': 400,
                        'limitBreak': 0, 'core': 0, 'bond': 0, 'skills': {'1': 10, '2': 10, '3': 10},
                        'cubeId': '0', 'cubeLevel': 0, 'collectionId': '0', 'collectionGrade': 'none', 'collectionLevel': 0,
                        'equipment': [{'slot': slot, 'tier': 0, 'level': 0, 'manufacturer': 0,
                            'lines': [{'lineIndex': i, 'presence': 'absent'} for i in range(1, 4)]}
                            for slot in ('head', 'torso', 'arm', 'leg')]} for cid in ids]}
                with sqlite3.connect(data / 'accounts.db') as db:
                    db.execute('CREATE TABLE snapshots(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL)')
                    db.execute('CREATE TABLE accounts(id TEXT PRIMARY KEY,current_id TEXT NOT NULL REFERENCES snapshots(id))')
                    db.execute('INSERT INTO snapshots VALUES(?,?,?,?)', (snapshot['id'], snapshot['accountId'], 1, json.dumps(snapshot)))
                    db.execute('INSERT INTO accounts VALUES(?,?)', (snapshot['accountId'], snapshot['id']))
                with socket.socket() as sock:
                    sock.bind(('127.0.0.1', 0))
                    port = sock.getsockname()[1]
                assert port not in (5180, 5181)
                case['port'] = port
                env = dict(os.environ, NIKKE_DATA_ROOT=str(data), NIKKE_PROJECT_ROOT=str(ROOT),
                           NIKKE_PORT=str(port), NIKKE_TEST_FIXTURE='1')
                env.pop('NIKKE_GAME_CATALOG', None)
                token = ''
                def call(path, payload=None):
                    request = urllib.request.Request(f'http://127.0.0.1:{port}/api/' + path,
                        data=None if payload is None else json.dumps(payload).encode(),
                        headers={'Content-Type': 'application/json', 'X-Nikke-Token': token})
                    try:
                        with urllib.request.urlopen(request, timeout=60) as response:
                            return response.status, json.load(response)
                    except urllib.error.HTTPError as error:
                        raw_body = error.read()
                        try:
                            body = json.loads(raw_body)
                        except ValueError:
                            body = {'raw': raw_body.decode(errors='replace')}
                        return error.code, body
                with (folder / 'api.log').open('w', encoding='utf-8') as log:
                    process = subprocess.Popen([args.dotnet, str(ROOT / 'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],
                        cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                    try:
                        for _ in range(200):
                            try:
                                token = call('bootstrap')[1]['token']
                                break
                            except (OSError, urllib.error.URLError):
                                time.sleep(.1)
                        assert token, 'API startup failed'
                        initial = call('snapshots/' + snapshot['id'])
                        def persisted_files():
                            return {str(p.relative_to(data)): digest(p) for name in ('weapon-replays', 'skill-replays', 'compute')
                                    for p in (data / name).rglob('*') if p.is_file()}
                        initial_files = persisted_files()
                        combat = {'durationFrames': 120 if args.before_fix else 10800, 'enemyDefense': 30925, 'critMode': 'off',
                                  'pelletCoefficientPolicy': 'per_trigger', 'bossDistance': 35, 'bossWeakElement': 'Fire'}
                        replay = {'snapshotId': snapshot['id'], 'characterIds': ids, 'scenarioLevel': 400,
                                  'conditions': {'roundingPolicy': 'client_f32', 'combat': combat}}
                        requests = [('runtime/combat-conditions', None),
                            ('snapshots/' + snapshot['id'] + '/combat-conditions?characterIds=5004', None),
                            ('runtime/skill-replays', replay),
                            ('runtime/weapon-replays', dict(replay, conditions=combat))]
                        # Before-fix compute could start a real job; only reproduce the QA GET/replay bug.
                        if not args.before_fix:
                            requests.append(('compute/experiments', dict(replay, runs=1, useSavedTactic=False,
                                execution={'requested': 'cpu', 'maxWorkers': 1})))
                        for path, payload in requests:
                            status, body = call(path, payload)
                            case['responses'].append({'path': path, 'status': status, 'body': body})
                            if args.before_fix:
                                assert status == (200 if field == 'bonusRangeMin' else 500), (field, status, body)
                            else:
                                assert status == 409, (path, status, body)
                                assert body['code'] == 'combat_profile_invalid', body
                                assert body['characterId'] == '5004', body
                                assert body['field'] == 'combatProfiles.characters.5004.' + field, body
                                assert body['reason'] == reason, body
                        assert call('snapshots/' + snapshot['id']) == initial
                        persisted = persisted_files()
                        case['persistedFiles'] = persisted
                        if not args.before_fix:
                            assert persisted == initial_files, (initial_files, persisted)
                            with sqlite3.connect(data / 'compute/batches.db') as db:
                                case['experimentCount'] = db.execute('SELECT COUNT(*) FROM experiments').fetchone()[0]
                                case['runCount'] = db.execute('SELECT COUNT(*) FROM batch_runs').fetchone()[0]
                            assert case['experimentCount'] == case['runCount'] == 0
                    finally:
                        process.terminate()
                        process.wait(timeout=30)
                print(field, index, 'passed', flush=True)
        report['status'] = 'passed'
    finally:
        report['sourceChanges'] = [name for name, value in hashes.items() if digest(Path(name)) != value]
        (run / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        (run / 'source-hashes.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
        print(run)
        assert not report['sourceChanges']


if __name__ == '__main__':
    main()

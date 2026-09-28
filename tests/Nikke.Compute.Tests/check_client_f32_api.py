"""I-BE integration acceptance: public tables, NEW synthetic DB, isolated API/port.

Copies only the public catalog allowlist. Never reads source accounts/session/cache.
No UI, independent engine oracle, game observation, deployment or load benchmark.
"""
import argparse
import copy
import csv
import io
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
from decimal import Decimal
from pathlib import Path
from check_compute_api import ROOT, digest, read


def audit_tables(data):
    folder = data / 'calculation' / read(data / 'calculation/current.json')['id']
    output = {}
    for name in ('cube_base_table.json', 'equip_stat_table.json', 'collection.json'):
        obj = json.loads((folder / name).read_text(encoding='utf-8-sig'), parse_float=Decimal)
        if name == 'collection.json':
            obj = obj['_stat_table']
        counts = {s: 0 for s in ('hp', 'atk', 'def')}
        examples = []
        def visit(node, path=''):
            if isinstance(node, dict):
                for key, val in node.items():
                    current = path + '/' + key
                    if key.lower() in counts and isinstance(val, (int, Decimal)) and val != int(val):
                        counts[key.lower()] += 1
                        if len(examples) < 12:
                            examples.append({'path': current, 'value': str(val)})
                    visit(val, current)
            elif isinstance(node, list):
                for i, val in enumerate(node):
                    visit(val, path + '/' + str(i))
        visit(obj)
        output[name] = {'fractionalCounts': counts, 'examples': examples}
    # The pinned legacy CSV is CP949, unlike the UTF-8 task and report documents.
    raw = (folder / 'stat_table.csv').read_bytes()
    rows = list(csv.reader(io.StringIO(raw.decode('cp949'))))
    fractional = []
    for rownum, row in enumerate(rows, 1):
        for col, text in enumerate(row, 1):
            try:
                number = Decimal(text.replace(',', ''))
                if number.is_finite() and number != int(number):
                    fractional.append({'row': rownum, 'column': col, 'value': str(number)})
            except (ArithmeticError, ValueError):
                pass
    output['stat_table.csv'] = {'encoding': 'cp949', 'fractionalCellCount': len(fractional),
                                'examples': fractional[:20], 'headerRows': rows[:8]}
    # Match the existing StatTable section boundaries: notes/percentages elsewhere
    # in this worksheet are not native stats. Columns in evidence are one-based.
    loaded = {}
    for section, keycol, columns in (('level', 0, range(1, 25)), ('bond', 26, range(28, 37))):
        start = next(i for i, row in enumerate(rows) if len(row) > max(columns) and row[keycol].strip() == '1')
        count, cells, fractions = 0, 0, []
        for i in range(start, len(rows)):
            row = rows[i]
            if len(row) <= max(columns) or not row[keycol].strip().isdigit() or int(row[keycol]) <= 0:
                break
            count += 1
            for col in columns:
                value = Decimal(row[col].replace(',', '').strip() or '0')
                cells += 1
                if value != int(value):
                    fractions.append({'level': int(row[keycol]), 'row': i+1, 'column': col+1, 'value': str(value)})
        loaded[section] = {'rows': count, 'cells': cells, 'fractionalCount': len(fractions), 'examples': fractions[:20]}
    output['stat_table.csv']['consumedStats'] = loaded
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-data', type=Path, required=True)
    parser.add_argument('--dotnet', required=True)
    args = parser.parse_args()
    source = args.source_data.resolve()
    run = ROOT / 'artifacts/client-f32-integration/api' / uuid.uuid4().hex
    data = run / 'data'
    data.mkdir(parents=True)
    report = {'kind': 'backend_integration_public_tables_synthetic_account', 'status': 'failed', 'checks': []}
    hashes = {}
    process = log = None
    def public_copy(relative):
        src = source / relative
        hashes[str(relative)] = digest(src)
        target = data / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
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
        report['publicTableAudit'] = audit_tables(data)
        game = read(data / 'game-catalog.json')
        ids = ['5011', '5008', '5004', '5009', '5044']
        snapshot = {'id': 'synthetic-f32', 'accountId': 'synthetic-account', 'gameSnapshotId': game['id'],
                    'synchroLevel': 400, 'savedAt': '2026-09-28T00:00:00+00:00', 'observedAt': '2026-09-28T00:00:00+00:00',
                    'consoles': {k: 0 for k in ('1001', '1101', '1102', '1103', '1201', '1202', '1203', '1204', '1205')},
                    'characters': []}
        for id in ids:
            snapshot['characters'].append({'characterId': id, 'name': game['names'][id], 'level': 400, 'nativeLevel': 400,
                'limitBreak': 0, 'core': 0, 'bond': 0, 'skills': {'1': 10, '2': 10, '3': 10}, 'cubeId': '0', 'cubeLevel': 0,
                'collectionId': '0', 'collectionGrade': 'none', 'collectionLevel': 0,
                'equipment': [{'slot': slot, 'tier': 0, 'level': 0, 'manufacturer': 0,
                    'lines': [{'lineIndex': i, 'presence': 'absent'} for i in range(1, 4)]} for slot in ('head', 'torso', 'arm', 'leg')]})
        # One catalog OL value with BOTH original raw numerator and normalized ratio.
        head = snapshot['characters'][2]['equipment'][0]
        head['tier'] = 10
        rate = game['optionSteps']['atk_pct'][0]
        raw = int(Decimal(str(rate)) * 10000)
        head['lines'][0] = {'lineIndex': 1, 'presence': 'present', 'optionType': 'StatAtk', 'normalizedValue': rate,
                            'unit': 'ratio', 'rawValue': raw, 'rawUnit': 'Percent'}
        with sqlite3.connect(data / 'accounts.db') as db:
            db.execute('CREATE TABLE snapshots(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL)')
            db.execute('CREATE TABLE accounts(id TEXT PRIMARY KEY,current_id TEXT NOT NULL REFERENCES snapshots(id))')
            db.execute('INSERT INTO snapshots VALUES(?,?,?,?)', (snapshot['id'], snapshot['accountId'], 1, json.dumps(snapshot)))
            db.execute('INSERT INTO accounts VALUES(?,?)', (snapshot['accountId'], snapshot['id']))
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
                status, body = error.code, json.loads(error.read())
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
        report['hits'] = {}
        v3 = call('calculations/hit', {'inputSchemaVersion': 3, 'input': {'statAttack': 100, 'statDamageRatio': 2, 'defenceRatioRate': .25}})
        assert v3['selectedPolicy'] == 'client_f32' and v3['selectedCandidate']['exactDamage'] == '150'
        assert [c['policy'] for c in v3['candidates']] == ['client_f32', 'legacy_term_floor', 'final_round_even', 'nested_floor']
        assert len(v3['selectedCandidate']['terms']) > 0 and not v3['conversion']['converted']
        assert call('calculations/hit/' + v3['id']) == v3
        report['hits']['v3'] = v3
        old_input = {'statAttack': 100, 'runtimeAttackBuffs': [{'source': 'fixture', 'rate': .145}]}
        v2 = call('calculations/hit', {'inputSchemaVersion': 2, 'input': old_input})
        assert v2['conversion']['originalSchemaVersion'] == 2 and v2['conversion']['converted']
        assert v2['originalInput'] == old_input and v2['exactEffectiveAttack'] == '115'
        assert v2['input']['statDamageRatio'] == 1 and v2['input']['defenceRatioRate'] == 0
        report['hits']['v2'] = v2
        artifact = {'kind': 'single_hit_calibration', 'inputSchemaVersion': 2, 'comparison': {'input': old_input, 'observedDamage': 114}}
        imported = call('calculations/hit/import', artifact)
        assert imported['sourceArtifact'] == artifact and call('calculations/hit/' + imported['id']) == imported
        report['hits']['imported'] = imported
        for policy in ('legacy_term_floor', 'final_round_even', 'nested_floor'):
            selected = call('calculations/hit', {'inputSchemaVersion': 3, 'input': {'statAttack': 100}, 'roundingPolicy': policy})
            assert selected['selectedCandidate']['policy'] == policy and selected['selectedCandidate']['terms']
        exact = call('calculations/hit', {'inputSchemaVersion': 3, 'input': {'statAttack': 0,
            'attackFlatBuffs': [{'source': 'exact', 'exactAmount': '9007199254740993'}]}})
        assert exact['exactEffectiveAttack'] == '9007199254740993'
        assert exact['input']['attackFlatBuffs'][0]['exactAmount'] == '9007199254740993'
        assert all(c['status'] == 'unavailable' for c in exact['candidates'][1:])
        report['hits']['largeExact'] = exact
        invalid = [{'statAttack': 100.5}, {'statAttack': 100, 'defense': 1.5},
            {'statAttack': 100, 'attackFlatBuffs': [{'source': 'bad', 'amount': .5}]},
            {'statAttack': 100, 'runtimeAttackBuffs': [{'source': 'bad', 'rate': .01401}]},
            {'statAttack': 0, 'attackFlatBuffs': [{'source': 'bad', 'exactAmount': 9007199254740993}]},
            {'statAttack': 100, 'coefficient': 1e12, 'statDamageRatio': 1e12}]
        report['errors'] = [call('calculations/hit', {'inputSchemaVersion': 3, 'input': val}, 400) for val in invalid]
        report['checks'].append('v3/v2 explicit migration/import/persist/read, four policies/audit, long string and errors')
        initial = call('snapshots/' + snapshot['id'])
        stats = [call(f'snapshots/{snapshot["id"]}/characters/{id}/stats?scenarioLevel=400') for id in ids]
        report['nativeStats'] = [{'id': x['characterId'], 'native': x['nativeStats'], 'deferred': x['deferredEffects']} for x in stats]
        assert stats[2]['basicHit']['attackBuffs'][0]['rawRate10000'] == str(raw)
        report['checks'].append('snapshot raw OL numerator preserved by stats API')
        base = {'snapshotId': snapshot['id'], 'characterIds': ids, 'runs': 1, 'phase': 'final', 'useSavedTactic': False,
                'conditions': {'combat': {'durationFrames': 600, 'enemyDefense': 30925, 'critMode': 'off', 'core': True,
                    'pelletCoefficientPolicy': 'per_trigger', 'manualCharacterId': ids[2]}}, 'execution': {'requested': 'cpu', 'maxWorkers': 1}}
        def batch(request):
            created = call('compute/experiments', request, 202)
            for _ in range(1200):
                end = call('compute/experiments/' + created['id'])
                if end['state'] in ('completed', 'failed', 'cancelled'):
                    break
                time.sleep(.05)
            assert end['state'] == 'completed', end
            rows = call('compute/experiments/' + end['id'] + '/results')['runs']
            stat = call('compute/experiments/' + end['id'] + '/statistics')
            assert len(rows) == 1 and stat['team']['n'] == 1 and rows[0]['teamDamage'] > 0
            assert rows[0]['teamDamage'] == sum(m['damage'] for m in rows[0]['members'])
            return {'status': end, 'runs': rows, 'statistics': stat}
        a = batch(base)
        assert a['status']['input']['roundingPolicy'] == 'client_f32' and a['status']['input']['inputSchemaVersion'] == 3
        legacy = copy.deepcopy(base)
        legacy['conditions']['roundingPolicy'] = 'legacy_term_floor'
        b = batch(legacy)
        changed = copy.deepcopy(base)
        changed['hitOverrides'] = {ids[2]: {'statDamageRatio': 2, 'defenceRatioRate': .25,
            'runtimeAttackBuffs': [{'source': 'experiment', 'rawRate10000': '1450'}],
            'attackFlatBuffs': [{'source': 'experiment', 'exactAmount': '100'}]}}
        c = batch(changed)
        assert c['runs'][0]['teamDamage'] != a['runs'][0]['teamDamage']
        assert len({x['status']['input']['fingerprint'] for x in (a, b, c)}) == 3
        assert len({x['status']['execution']['fingerprint'] for x in (a, b, c)}) == 3
        assert all(x['status']['execution']['tuning']['cacheSource'] == 'miss' for x in (a, b, c))
        report['batches'] = {'defaultClient': a, 'explicitLegacy': b, 'experimentalRatesRawExact': c}
        report['errors'].append(call('compute/experiments', dict(changed, baselineExperimentId=a['status']['id']), 400))
        assert call('compute/experiments/' + b['status']['id'] + '/results')['runs'] == b['runs']
        assert call('compute/experiments/' + a['status']['id'] + '/statistics')['team']['n'] == 1
        assert call('snapshots/' + snapshot['id']) == initial
        report['checks'].append('three isolated 1-run/600-frame batches: client default, explicit legacy, changed rates/raw/exact; separate fingerprints/cache/stats')
        report['status'] = 'passed'
    finally:
        if process is not None:
            process.terminate()
            process.wait(timeout=30)
        if log:
            log.close()
        report['sourceFilesChecked'] = len(hashes)
        report['sourceChanges'] = [name for name, value in hashes.items() if digest(source / name) != value]
        (run / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        (run / 'source-hashes.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
        print(run)
        assert not report['sourceChanges'], 'public source changed'


if __name__ == '__main__':
    main()

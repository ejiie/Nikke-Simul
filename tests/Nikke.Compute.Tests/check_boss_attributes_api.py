"""B-DATA-1: boss static attributes GET API only, using a new Backend artifact dataRoot (no accounts, no original data)."""
import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--source-game', type=Path, required=True)
    parser.add_argument('--dotnet', required=True)
    args = parser.parse_args()
    data, source = args.data_root.resolve(), args.source_game.resolve()
    assert data.is_relative_to(ROOT / 'artifacts') and source.is_relative_to(ROOT / 'artifacts')
    assert not (data / 'accounts.db').exists(), 'requires a new synthetic dataRoot'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    source_hash = sha(source)
    shutil.copyfile(source, data / 'game-catalog.json')
    prepared = data / 'presentation' / 'solo-raid-boss-attributes.json'
    expected = json.loads(prepared.read_text(encoding='utf-8'))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    assert port not in (5180, 5181)
    env = dict(os.environ, NIKKE_DATA_ROOT=str(data), NIKKE_PROJECT_ROOT=str(ROOT), NIKKE_PORT=str(port), NIKKE_TEST_FIXTURE='1')
    env.pop('NIKKE_GAME_CATALOG', None)
    report = {'status': 'failed', 'port': port, 'sourceChanges': []}
    process = None

    def get(path, status=200):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}' + path, timeout=10) as response:
                actual, raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            actual, raw = error.code, error.read()
        assert actual == status, (path, actual)
        return raw

    try:
        with (data.parent / 'api.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen([args.dotnet, str(ROOT / 'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],
                cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            for _ in range(200):
                try:
                    get('/api/bootstrap')
                    break
                except OSError:
                    if process.poll() is not None:
                        raise AssertionError('API exited during startup')
                    time.sleep(.1)
            catalog = json.loads(get('/api/presentation/solo-raid-bosses/attributes'))
            assert [b['id'] for b in catalog['bosses']] == [b['id'] for b in expected['bosses']]
            assert len(catalog['bosses']) == 42 and catalog['complete'] is False
            assert [d['season'] for d in catalog['diagnostics']] == [41, 42]
            by_season = {b['season']: b for b in catalog['bosses']}
            assert by_season[41]['status'] == by_season[42]['status'] == 'unavailable'
            assert by_season[41].get('challenge') is None and by_season[41].get('element') is None
            for season in range(1, 41):
                boss = by_season[season]
                assert boss['status'] == 'available' and boss['challenge']['level'] == 390 and boss['challenge']['characterLevel'] == 400
                assert boss['challenge']['stats']['defence'] == 30925 and boss['defenceRatioRate'] == 0 and boss['defenceRatio'] == 10000
                steps = boss['challenge']['levelChange']['steps']
                assert [s['stats']['defence'] for s in steps] == [30925] * 6 + [31784] * 3
                assert boss['element']['key'] in ('Fire', 'Water', 'Wind', 'Iron', 'Electronic') and boss['element']['weakKey']
            # wire matches the prepared file field-for-field (camelCase names are the file's names)
            assert catalog['bosses'][39] == expected['bosses'][39]
            # the existing boss list API is untouched (no catalog prepared in this root -> explicit diagnostic)
            old = json.loads(get('/api/presentation/solo-raid-bosses'))
            assert old['bosses'][0]['id'] == 'dummy' and old['complete'] is False
            # BD1-Q-1/Q-2 injections into the isolated file: every one must be 409 boss_attributes_invalid; declared nulls stay 200.
            original = prepared.read_text(encoding='utf-8')
            accepted, rejected = [], []

            def inject(path, value, declare=None, remove=False):
                doc = json.loads(original)
                node = doc
                tokens = path.split('/')
                for token in tokens[:-1]:
                    node = node[int(token)] if token.isdigit() else node[token]
                last = tokens[-1]
                if remove:
                    del node[last]
                elif last.isdigit():
                    node[int(last)] = value
                else:
                    node[last] = value
                if declare:
                    doc['bosses'][0]['unconfirmed'].append(declare)
                prepared.write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8')
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/presentation/solo-raid-bosses/attributes', timeout=10) as response:
                        return response.status, response.read()
                except urllib.error.HTTPError as error:
                    return error.code, error.read()

            undeclared = ['bosses/0/element', 'bosses/0/element/weakKey', 'bosses/0', 'bosses/0/challenge/levelChange/steps/0',
                          'bosses/0/parts/0', 'bosses/0/ladder/0', 'diagnostics/0', 'fields/0', 'bosses/0/challenge/stats',
                          'bosses/0/challenge/levelChange', 'bosses/0/challenge/levelChange/steps/0/stats', 'bosses/0/modelPrefab',
                          'bosses/0/core/evidence', 'bosses/0/parts/0/coreMarkers/0']
            expected_doc = json.loads(original)
            for path in undeclared:
                node = expected_doc
                for token in path.split('/'):
                    if token.isdigit() and not (isinstance(node, list) and int(token) < len(node)):
                        break
                    node = node[int(token)] if token.isdigit() else node[token]
                else:
                    status, body = inject(path, None)
                    assert status == 409 and b'boss_attributes_invalid' in body, (path, status, body[:200])
                    rejected.append(path)
            declared = [('bosses/0/element', 'element'), ('bosses/0/element/weakKey', 'weak_element'),
                        ('bosses/0/challenge/stats', 'challenge_level_stats'), ('bosses/0/challenge/levelChange', 'level_change_rows'),
                        ('bosses/0/challenge/levelChange/steps/0/stats', 'level_change_step_1_stats')]
            for path, code in declared:
                status, body = inject(path, None, declare=code)
                assert status == 200, (path, status, body[:200])
                accepted.append(path)
            prepared.write_text(original, encoding='utf-8')
            assert json.loads(get('/api/presentation/solo-raid-bosses/attributes')) == catalog
            report.update(status='passed', bosses=len(catalog['bosses']), available=40, unavailable=[41, 42],
                          injectionsRejected=rejected, declaredNullsAccepted=accepted)
    finally:
        if process is not None:
            process.terminate()
            process.wait(timeout=30)
        report['sourceChanges'] = [] if sha(source) == source_hash else [str(source)]
        (data.parent / 'api-summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    assert not report['sourceChanges']
    print(json.dumps({k: report[k] for k in ('status', 'port', 'bosses', 'available', 'unavailable')} | {'injectionsRejected': len(report['injectionsRejected']), 'declaredNullsAccepted': len(report['declaredNullsAccepted'])}))


if __name__ == '__main__':
    main()

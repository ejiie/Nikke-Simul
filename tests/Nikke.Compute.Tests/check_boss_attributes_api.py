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
            report.update(status='passed', bosses=len(catalog['bosses']), available=40, unavailable=[41, 42])
    finally:
        if process is not None:
            process.terminate()
            process.wait(timeout=30)
        report['sourceChanges'] = [] if sha(source) == source_hash else [str(source)]
        (data.parent / 'api-summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    assert not report['sourceChanges']
    print(json.dumps({k: report[k] for k in ('status', 'port', 'bosses', 'available', 'unavailable')}))


if __name__ == '__main__':
    main()

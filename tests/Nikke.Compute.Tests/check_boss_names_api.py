"""B-FIX-3: only the boss GET API and images, using a new Backend artifact dataRoot."""
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
    presentation = data / 'presentation'
    manifest = json.loads((presentation / 'solo-raid-bosses.manifest.json').read_text(encoding='utf-8'))
    expected = {r['season']: r['name'] for r in manifest['koreanSources']['records']}
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    assert port not in (5180, 5181)
    env = dict(os.environ, NIKKE_DATA_ROOT=str(data), NIKKE_PROJECT_ROOT=str(ROOT),
               NIKKE_PORT=str(port), NIKKE_TEST_FIXTURE='1')
    env.pop('NIKKE_GAME_CATALOG', None)
    report = {'status': 'failed', 'port': port, 'checks': [], 'sourceChanges': []}
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
            raw = get('/api/presentation/solo-raid-bosses')
            catalog = json.loads(raw)
            assert catalog == json.loads((presentation / 'solo-raid-bosses.json').read_text(encoding='utf-8'))
            assert catalog['complete'] is True and catalog['diagnostics'] == []
            assert {b['season']: b['name'] for b in catalog['bosses'][1:]} == expected
            assert len(catalog['bosses']) == 43 and expected[37] == '울트라' and expected[42] == '앨트루이아'
            assert all(set(b) == {'id', 'name', 'imageUrl', 'season'} for b in catalog['bosses'])
            assert 'https://' not in raw.decode('utf-8') and 'verifiedAt' not in raw.decode('utf-8')
            by_season = {r['season']: r for r in manifest['bosses']}
            for boss in catalog['bosses'][1:]:
                image = get(boss['imageUrl'])
                internal = by_season[boss['season']]
                assert hashlib.sha256(image).hexdigest() == internal['sha256']
                assert image == (presentation / 'assets/bosses' / internal['localFile']).read_bytes()
            for path in ('/editor/solo-raid-bosses.manifest.json', '/editor/assets/solo-raid-bosses.manifest.json',
                         '/editor/assets/bosses/solo-raid-korean-names.manifest.json',
                         '/tools/data-pipeline/manifests/solo-raid-korean-names.manifest.json'):
                get(path, 404)
            report.update(status='passed', displayed=len(catalog['bosses']), excluded=0, imagesChecked=42,
                          names=expected, checks=['42 reviewed season names + dummy; no fallback',
                          'season37 exact name; season42 user-confirmed name', '42 HTTP images match internal hashes',
                          'public field allowlist; internal source manifest paths return404'])
    finally:
        if process is not None:
            process.terminate()
            process.wait(timeout=30)
        report['sourceChanges'] = [] if sha(source) == source_hash else [str(source)]
        (data.parent / 'api-summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    assert not report['sourceChanges']
    print(json.dumps({k: report[k] for k in ('status', 'port', 'displayed', 'excluded', 'imagesChecked')}))


if __name__ == '__main__':
    main()

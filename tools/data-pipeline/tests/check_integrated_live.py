"""Director integration check: real local API/engine/UI, isolated account copy, no game claims."""
import argparse
import asyncio
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[3]
IDS = ['5011', '5008', '5009', '5004', '5044']


def source_digest(source):
    with closing(sqlite3.connect((source / 'accounts.db').as_uri() + '?mode=ro', uri=True)) as db:
        rows = []
        for table in ('connections', 'snapshots', 'accounts', 'solo_formations'):
            rows.append((table, db.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()))
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode()).hexdigest()


def prepare(source, output):
    with closing(sqlite3.connect((source / 'accounts.db').as_uri() + '?mode=ro', uri=True)) as db:
        candidates = db.execute('SELECT s.payload FROM snapshots s JOIN accounts a ON a.current_id=s.id').fetchall()
    snapshots = [json.loads(row[0]) for row in candidates]
    snapshot = next((s for s in snapshots if set(IDS) <= {c['characterId'] for c in s['characters']}), None)
    if snapshot is None:
        raise RuntimeError('No current account snapshot contains all five supported characters')
    request = {'snapshotId': snapshot['id'], 'characterIds': IDS, 'scenarioLevel': 400,
               'conditions': {'roundingPolicy': 'legacy_term_floor', 'damageLog': {'characterId': '5004'},
                  'autoBurst': {'stageDelayMinFrames': 1, 'stageDelayMaxFrames': 1, 'tactic': {
                      'schemaVersion': 1, 'allowedCharacterIds': IDS,
                      'stage1Priority': ['5011'], 'stage2Priority': ['5008'],
                      'stage3Priority': ['5004', '5044', '5009'], 'burst3Rotation': ['5004', '5044'],
                      'firstBurst3CharacterId': '5004', 'unavailablePolicy': 'next_ready'}},
                  'combat': {'durationFrames': 10800, 'enemyDefense': 30925, 'critMode': 'off',
                      'core': True, 'properDistance': True, 'elementAdvantage': False,
                      'pelletCoefficientPolicy': 'per_pellet', 'manualCharacterId': '',
                      'manualStyle': 'full_charge', 'fullBurstWindows': [], 'trace': False,
                      'targetLabel': 'solo_raid_challenge'}}}
    path = output / 'request.json'
    path.write_text(json.dumps(request, indent=2), encoding='utf-8')
    return path, snapshot['accountId'], snapshot.get('rawManifestId')


async def browser_check(base, output):
    from playwright.async_api import async_playwright
    errors, posts = [], []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel='msedge', headless=True)
        try:
            page = await browser.new_page(viewport={'width': 1500, 'height': 1000})
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: posts.append(request.post_data_json)
                    if request.method == 'POST' and request.url.endswith('/api/runtime/skill-replays') else None)
            # This test never talks to the source live server or external services.
            await page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base + '/') else route.abort())
            await page.goto(base + '/editor/')
            await page.wait_for_function("document.body.dataset.ready==='true'", timeout=60000)
            await page.locator('[data-tab="raid"]').click()
            await page.locator('[name="level"]').fill('400')
            await page.locator('[name="crit"]').select_option('off')
            await page.locator('[name="seconds"]').fill('180')
            await page.screenshot(path=str(output / 'ui-before.png'))
            async with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/runtime/skill-replays'), timeout=120000) as pending:
                await page.locator('#run-replay').click()
            response = await pending.value
            body = await response.json()
            (output / 'ui-response.json').write_text(json.dumps(body), encoding='utf-8')
            (output / 'ui-request.json').write_text(json.dumps(posts[-1]), encoding='utf-8')
            assert response.status == 200, f'UI replay HTTP {response.status}: {str(body)[:300]}'
            assert posts[-1]['conditions']['damageLog']['characterId'] == '5004', 'UI did not request Alice log'
            actual = body['result']['damageLog']
            assert actual['characterId'] == '5004' and actual['eventCount'] > 0 and not actual['truncated']
            await page.wait_for_function("document.querySelector('#damage-log-container')?.textContent.includes('발사')", timeout=30000)
            text = await page.locator('#damage-log-container').inner_text()
            assert '아직 수집하지' not in text and '연동 대기' not in text, 'Actual log treated as uncollected'
            await page.screenshot(path=str(output / 'ui-result.png'), full_page=True)
            for width in [1500, 850, 500]:
                await page.set_viewport_size({'width': width, 'height': 1000})
                assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), f'overflow {width}'
            assert not errors, errors
            return {'status': 'passed', 'hits': actual['eventCount'], 'damage': actual['totalDamage'], 'pageErrors': errors}
        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dotnet', required=True)
    parser.add_argument('--source-data', type=Path, required=True)
    parser.add_argument('--browser-data', type=Path, help='Reuse an isolated B2 integration data copy for browser check only')
    parser.add_argument('--api-only', action='store_true', help='Run API checks while UI fixes are pending')
    args = parser.parse_args()
    source = args.source_data.resolve()
    output = ROOT / 'artifacts/director' / ('live-' + uuid.uuid4().hex)
    output.mkdir(parents=True)
    before = source_digest(source)
    report = {'kind': 'real_api_engine_account_copy_not_game_measurement', 'status': 'failed',
              'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
    try:
        request, account, raw_manifest = prepare(source, output)
        if not args.browser_data:
            run = subprocess.run([sys.executable, str(ROOT / 'tests/Nikke.Sync.Tests/check_damage_log_integration.py'),
                                  '--dotnet', args.dotnet, '--source-data', str(source), '--request', str(request),
                                  '--expected-commit', report['commit']], cwd=ROOT, capture_output=True, text=True)
            (output / 'api-runner.log').write_text(run.stdout + run.stderr, encoding='utf-8')
            assert run.returncode == 0, f'API runner failed; see {output / "api-runner.log"}'
            api_output = Path(run.stdout.strip().splitlines()[-1])
            report['apiEvidence'] = str(api_output)
            report['api'] = json.loads((api_output / 'summary.json').read_text())
            data = api_output / 'data'
        else:
            data = args.browser_data.resolve()
            assert data.is_relative_to(ROOT / 'artifacts'), 'Browser data must be a Director-owned isolated copy'
        if args.api_only:
            report['status'] = 'passed'
            report['browser'] = {'status': 'not_run'}
            return
        # The normal UI reads combat powers from this snapshot's raw envelope.
        # Copy only that envelope and its integrity manifest, never session/login files.
        if raw_manifest:
            for filename in ('envelope.json', 'manifest.json'):
                raw_source = (source / 'raw' / raw_manifest / filename).resolve()
                assert raw_source.is_relative_to(source / 'raw'), 'Invalid raw manifest path'
                raw_target = data / 'raw' / raw_manifest / filename
                if not raw_target.exists():
                    raw_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(raw_source, raw_target)
        # Add a synthetic local connection pointer only in the isolated database.
        connection = {'id': 'director-validation', 'accountId': account, 'status': 'ready',
                      'nickname': 'Integration validation', 'area': 1,
                      'choices': [{'area': 1, 'label': 'Isolated copy'}]}
        with closing(sqlite3.connect(data / 'accounts.db')) as db:
            db.execute('DELETE FROM connections')
            db.execute('INSERT INTO connections VALUES(?,?)', (connection['id'], json.dumps(connection)))
            db.execute('DELETE FROM solo_burst_tactics')
            # The API runner's final stale test clears formation. Restore through the API below.
            db.commit()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        env = dict(os.environ, NIKKE_PROJECT_ROOT=str(ROOT), NIKKE_DATA_ROOT=str(data),
                   NIKKE_GAME_CATALOG=str(data / 'game-catalog.json'), NIKKE_TEST_FIXTURE='1', NIKKE_PORT=str(port))
        with (output / 'server.log').open('w') as log:
            process = subprocess.Popen([args.dotnet, str(ROOT / 'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],
                                       cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                for _ in range(100):
                    try:
                        with urllib.request.urlopen(base + '/api/bootstrap') as response:
                            token = json.load(response)['token']
                        break
                    except OSError:
                        if process.poll() is not None:
                            raise RuntimeError('Isolated API exited; see server.log')
                        time.sleep(.2)
                else:
                    raise RuntimeError('API startup timed out')
                req = urllib.request.Request(base + f'/api/accounts/{account}/formation', method='PUT',
                      data=json.dumps({'slots': IDS}).encode(), headers={'Content-Type': 'application/json', 'X-Nikke-Token': token})
                with urllib.request.urlopen(req) as response:
                    assert response.status == 200
                report['browser'] = asyncio.run(browser_check(base, output))
            finally:
                process.terminate()
                process.wait(timeout=10)
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        report['sourceLogicalDigestBefore'] = before
        report['sourceLogicalDigestAfter'] = source_digest(source)
        report['sourceUnchanged'] = report['sourceLogicalDigestBefore'] == report['sourceLogicalDigestAfter']
        (output / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(output, flush=True)


if __name__ == '__main__':
    main()

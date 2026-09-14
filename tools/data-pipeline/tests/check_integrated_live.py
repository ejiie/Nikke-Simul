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
            async def save_action(action):
                async with page.expect_response(lambda r: r.request.method == 'PUT' and r.url.endswith('/burst-tactic')) as pending:
                    await action()
                response = await pending.value
                assert response.status == 200
                await page.wait_for_function("!document.querySelector('#burst-tactics-container').textContent.includes('서버 저장 중')")
                return (await response.json())['saved']['tactic']

            formation_tactic = await save_action(lambda: page.locator('#preset-formation').click())
            assert formation_tactic['burst3Rotation'] == ['5009', '5004', '5044']
            assert formation_tactic['firstBurst3CharacterId'] == '5009'
            await save_action(lambda: page.locator('#preset-alice-only').click())
            expanded = await save_action(lambda: page.locator('[data-tactic-allow="5009"]').check())
            assert expanded['burst3Rotation'] == ['5004', '5009']
            reordered = await save_action(lambda: page.locator('[data-move-id="5009"][data-move-dir="-1"]').click())
            assert reordered['burst3Rotation'] == ['5009', '5004']
            assert reordered['firstBurst3CharacterId'] == '5009'
            disabled = await save_action(lambda: page.locator('[data-tactic-allow="5009"]').uncheck())
            assert disabled['burst3Rotation'] == ['5004']
            assert disabled['firstBurst3CharacterId'] == '5004'
            assert '첫 시전자' not in await page.locator('.tactic-nikke-row').filter(has=page.locator('[data-tactic-allow="5009"]')).inner_text()
            async with page.expect_response(lambda r: r.request.method == 'PUT' and r.url.endswith('/burst-tactic')) as pending_save:
                await page.locator('#preset-alice-only').click()
            saved_response = await pending_save.value
            assert saved_response.status == 200
            saved_tactic = (await saved_response.json())['saved']['tactic']
            (output / 'ui-saved-tactic.json').write_text(json.dumps(saved_tactic, indent=2), encoding='utf-8')
            assert saved_tactic['burst3Rotation'] == ['5004']
            assert saved_tactic['unavailablePolicy'] == 'next_ready'
            # Require restoration from the real server, not just the browser cache.
            await page.evaluate("Object.keys(localStorage).filter(k => k.startsWith('nikke-burst-tactics-')).forEach(k => localStorage.removeItem(k))")
            await page.reload()
            await page.wait_for_function("document.body.dataset.ready==='true'", timeout=60000)
            await page.locator('[data-tab="raid"]').click()
            removed = '#tactic-fallback-policy, #tactic-first-caster, #tactic-stage3-mode, [name="burst"], [name="burstAt"], [name="burstRotation"], [name="burstUnavailable"]'
            assert await page.locator(removed).count() == 0
            assert '첫 시전자' in await page.locator('.tactic-nikke-row').filter(has=page.locator('[data-tactic-allow="5004"]')).inner_text()
            assert await page.locator('[name="manualCharacter"], [name="manualStyle"]').count() == 2
            restore_state = await page.evaluate("""() => ({
                allow: [...document.querySelectorAll('[data-tactic-allow]')].map(e => ({id:e.dataset.tacticAllow, checked:e.checked})),
                local: Object.fromEntries(Object.entries(localStorage).filter(([k]) => k.startsWith('nikke-burst-tactics-')))
            })""")
            (output / 'ui-restored-state.json').write_text(json.dumps(restore_state, indent=2), encoding='utf-8')
            expected_allow = {id: id in saved_tactic['allowedCharacterIds'] for id in IDS}
            assert {item['id']: item['checked'] for item in restore_state['allow']} == expected_allow, 'Allowlist not restored at ready=true'
            assert not await page.locator('[data-tactic-allow="5044"]').is_checked(), 'Alice-only exclusion lost after reload'
            assert await page.locator('#replay-form [name="level"]').count() == 0
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
            assert posts[-1]['scenarioLevel'] == 400, 'Solo raid challenge must use level 400'
            assert set(body['appliedLevels'].values()) == {400}, 'Replay stats must use level 400 for every member'
            assert posts[-1]['conditions']['damageLog']['characterId'] == '5004', 'UI did not request Alice log'
            assert posts[-1]['conditions']['autoBurst']['tactic'] == saved_tactic
            actual = body['result']['damageLog']
            assert actual['characterId'] == '5004' and actual['eventCount'] > 0 and not actual['truncated']
            assert body['result']['teamBurst']['fullBursts']
            assert all(b['caster'] == '5004' for b in body['result']['teamBurst']['fullBursts'])
            await page.wait_for_function("document.querySelector('#damage-log-container')?.textContent.includes('발사')", timeout=30000)
            text = await page.locator('#damage-log-container').inner_text()
            assert '아직 수집하지' not in text and '연동 대기' not in text, 'Actual log treated as uncollected'
            assert await page.locator('.graph-hit-dot').count() == actual['eventCount']
            await page.locator('[data-view-audit]').first.click()
            export_checks = []
            for extension in ('json', 'csv'):
                async with page.expect_download() as pending_download:
                    await page.locator('#btn-export-' + extension).click()
                download = await pending_download.value
                target = output / ('ui-download.' + extension)
                await download.save_as(target)
                expected = await page.request.get(base + '/api/runtime/skill-replays/' + body['id'] + '/damage-log/export.' + extension)
                assert expected.status == 200
                expected_bytes = await expected.body()
                (output / ('server-export.' + extension)).write_bytes(expected_bytes)
                export_checks.append({'format': extension, 'exactBytes': target.read_bytes() == expected_bytes})
            (output / 'ui-export-checks.json').write_text(json.dumps(export_checks, indent=2), encoding='utf-8')
            await page.screenshot(path=str(output / 'ui-result.png'), full_page=True)
            for width in [1500, 850, 500]:
                await page.set_viewport_size({'width': width, 'height': 1000})
                assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), f'overflow {width}'
            assert not errors, errors
            assert all(c['exactBytes'] for c in export_checks), f'Exports differ from server bytes: {export_checks}'
            # Separate, explicitly synthetic fault test after all real-API checks.
            # A server failure must be shown instead of exporting a local success.
            unexpected_downloads = []
            page.on('download', lambda download: unexpected_downloads.append(download.suggested_filename))
            for extension in ('json', 'csv'):
                fault_url = base + '/api/runtime/skill-replays/' + body['id'] + '/damage-log/export.' + extension
                await page.route(fault_url, lambda route: route.fulfill(status=503, body='Director injected export fault'))
                await page.locator('#btn-export-' + extension).click()
                await page.wait_for_function("document.querySelector('#status')?.textContent.includes('503')")
                assert not unexpected_downloads, 'Server failure disguised as successful local download'
                await page.unroute(fault_url)
                await page.evaluate("document.querySelector('#status').textContent=''")
            assert not errors, errors
            return {'status': 'passed', 'hits': actual['eventCount'], 'damage': actual['totalDamage'],
                    'initialRestoreState': restore_state['allow'],
                    'serverOnlyRestoreReady': True,
                    'syntheticExport503NoFallback': True,
                    'serverSaveReloadExecution': True, 'aliceOnlyNextReady': True,
                    'compactControlsAndOrder': True,
                    'jsonCsvExactDownloads': True, 'widths': [1500, 850, 500], 'pageErrors': errors}
        except Exception:
            await page.screenshot(path=str(output / 'ui-failure.png'), full_page=True)
            (output / 'ui-page-errors.json').write_text(json.dumps(errors), encoding='utf-8')
            raise
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

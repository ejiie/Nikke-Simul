"""Regression for the solo raid challenge scenario level (apps/desktop-ui/app.js).

Drives the real renderRaid submit path in a browser with synthetic HTTP routes and inspects the
captured POST /api/runtime/skill-replays payload. Source-string checks alone are not accepted here.

Checks:
1. The 검산 레벨 input is gone from the form (no [name="level"], no hidden level field).
2. The request always sends scenarioLevel 400, even when the account snapshot carries other levels
   and when a rogue level field is injected into the form.
3. The remaining conditions (time, defense, crit, rounding, pellet, flags, manual control, tactic,
   damage log target) keep the values the user selected.

Output: artifacts/ui/solo-raid-level/run-<id>/ (git-ignored). Exit code 1 means NOT accepted.
"""
import asyncio
import http.server
import json
from pathlib import Path
import socket
import socketserver
import subprocess
import threading
import uuid

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
IDS = ['5011', '5008', '5009', '5004', '5044']
NAMES = ['리타', '블랑', '누아르', '앨리스', '모더니아']
EXPECTED_LEVEL = 400
ACCOUNT_LEVEL = 137  # deliberately different from 400
ROGUE_LEVEL = '777'


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def serve(directory):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def end_headers(self):
            self.send_header('Cache-Control', 'no-store')
            super().end_headers()

        def translate_path(self, path):
            return super().translate_path(path[len('/editor'):] if path.startswith('/editor/') else path)

        def log_message(self, *args):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', free_port()), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f'http://127.0.0.1:{httpd.server_address[1]}'


async def route_api(page, posts):
    async def fulfil(route, body):
        await route.fulfill(json=body)

    async def skill_replays(route):
        posts.append(route.request.post_data_json)
        await route.fulfill(json={'id': f'replay-{len(posts)}', 'createdAt': '2026-09-14T00:00:00Z',
                                  'inputs': [{'weapon': {'characterId': i}, 'skills': {'slots': {}}} for i in IDS],
                                  'conditions': {'roundingPolicy': 'legacy_term_floor'},
                                  'result': {'totalDamage': 1, 'members': [{'characterId': i, 'damage': 1, 'effects': {'normal_attack': 1}} for i in IDS],
                                             'teamBurst': {'fullBursts': [], 'timeline': [], 'fullBurstFrames': 0,
                                                           'acceptedGaugeByMember': {i: 0 for i in IDS}, 'sourceConstants': {'capacityRaw': 1000000}},
                                             'damageLog': {'schemaVersion': 1, 'characterId': '5004', 'status': 'complete',
                                                           'truncated': False, 'eventCount': 0, 'totalDamage': 0, 'entries': []}}})

    await page.route('**/api/bootstrap', lambda r: fulfil(r, {'token': 'solo-raid-token', 'testMode': True, 'jobs': [],
        'connections': [{'id': 'c1', 'accountId': 'acc-level', 'nickname': '검증용', 'status': 'ready',
                         'choices': [{'area': 1, 'label': 'synthetic'}]}]}))
    await page.route('**/api/accounts/*/snapshot', lambda r: fulfil(r, {'id': 'snap-level', 'accountId': 'acc-level',
        'synchroLevel': ACCOUNT_LEVEL, 'observedAt': '2026-09-14T00:00:00Z',
        'characters': [{'characterId': i, 'name': n, 'level': ACCOUNT_LEVEL, 'limitBreak': 3, 'core': 0} for i, n in zip(IDS, NAMES)]}))
    await page.route('**/api/presentation', lambda r: fulfil(r, {'characters': [
        {'characterUid': i, 'displayName': n, 'burstStep': s} for i, n, s in zip(IDS, NAMES, [1, 2, 3, 3, 3])]}))
    await page.route('**/api/presentation/status', lambda r: fulfil(r, {'status': 'idle', 'revision': 1, 'message': 'ready'}))
    await page.route('**/api/accounts/*/formation', lambda r: fulfil(r, {'accountId': 'acc-level', 'slots': IDS}))
    await page.route('**/api/accounts/*/burst-tactic', lambda r: fulfil(r, {'saved': None, 'stale': False, 'executionStatus': 'legacy'}))
    await page.route('**/api/snapshots/*/combat-powers', lambda r: fulfil(r, {i: 1 for i in IDS}))
    await page.route('**/api/runtime/skill-replays/*/damage-log**', lambda r: fulfil(r, {'exportSchemaVersion': 1,
        'collectionStatus': 'not_collected', 'replay': {'id': 'replay-1', 'result': {}}}))
    await page.route('**/api/runtime/skill-replays', skill_replays)


def check_conditions(payload):
    """The user's other selections must survive the level removal."""
    problems = []
    conditions = payload.get('conditions', {})
    combat = conditions.get('combat', {})
    expected = {'durationFrames': 7200, 'enemyDefense': 31784, 'critMode': 'on', 'core': True, 'properDistance': True,
                'elementAdvantage': True, 'pelletCoefficientPolicy': 'per_pellet', 'manualCharacterId': '5004',
                'manualStyle': 'tap'}
    for key, value in expected.items():
        if combat.get(key) != value:
            problems.append(f'combat.{key}={combat.get(key)!r} expected {value!r}')
    if conditions.get('roundingPolicy') != 'nested_floor':
        problems.append(f"roundingPolicy={conditions.get('roundingPolicy')!r}")
    if payload.get('characterIds') != IDS:
        problems.append(f"characterIds={payload.get('characterIds')!r}")
    if payload.get('snapshotId') != 'snap-level':
        problems.append(f"snapshotId={payload.get('snapshotId')!r}")
    if conditions.get('damageLog', {}).get('characterId') != '5004':
        problems.append(f"damageLog={conditions.get('damageLog')!r}")
    if not conditions.get('autoBurst', {}).get('tactic'):
        problems.append('autoBurst.tactic missing')
    return problems


async def fill_and_submit(page, posts):
    await page.locator('[name="seconds"]').fill('120')
    await page.locator('[name="defense"]').select_option('31784')
    await page.locator('[name="crit"]').select_option('on')
    await page.locator('[name="rounding"]').select_option('nested_floor')
    await page.locator('[name="pellet"]').select_option('per_pellet')
    for flag in ('core', 'distance', 'element'):
        await page.locator(f'[name="{flag}"]').check()
    await page.locator('[name="manualCharacter"]').select_option('5004')
    await page.locator('[name="manualStyle"]').select_option('tap')
    before = len(posts)
    await page.locator('#run-replay').click()
    for _ in range(100):
        if len(posts) > before:
            return posts[-1]
        await page.wait_for_timeout(100)
    raise RuntimeError('No replay request captured')


async def run():
    output = ROOT / 'artifacts/ui/solo-raid-level' / f'run-{uuid.uuid4().hex[:12]}'
    output.mkdir(parents=True)
    server, base = serve(ROOT / 'apps/desktop-ui')
    summary = {'kind': 'solo_raid_scenario_level_regression',
               'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain', 'apps/desktop-ui', 'tests/ui'], cwd=ROOT, text=True).strip()),
               'accountLevel': ACCOUNT_LEVEL, 'expectedScenarioLevel': EXPECTED_LEVEL}
    problems, errors, asset_warnings, posts = [], [], [], []
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(channel='msedge', headless=True)
            try:
                page = await browser.new_page(viewport={'width': 1500, 'height': 1000})
                page.on('pageerror', lambda e: errors.append(str(e)))
                # Portrait/decoration assets are absent in this isolated server; only code errors fail the run.
                page.on('console', lambda m: (asset_warnings if 'Failed to load resource' in m.text else errors)
                        .append('console: ' + m.text) if m.type == 'error' and 'favicon' not in m.text else None)
                await route_api(page, posts)
                await page.goto(base + '/editor/')
                await page.wait_for_function("document.body.dataset.ready==='true'", timeout=60000)
                await page.locator('[data-tab="raid"]').click()

                fields = await page.evaluate("""() => {
                    const form = document.querySelector('#replay-form');
                    return { level: form.querySelectorAll('[name="level"]').length,
                             hidden: form.querySelectorAll('input[type="hidden"]').length,
                             names: [...form.elements].map(e => e.name).filter(Boolean),
                             text: form.innerText };
                }""")
                summary['formFields'] = fields['names']
                if fields['level'] or 'level' in fields['names']:
                    problems.append('level field still present')
                if fields['hidden']:
                    problems.append(f"hidden inputs present: {fields['hidden']}")
                if '검산 레벨' in fields['text']:
                    problems.append('검산 레벨 label still shown')
                if '싱크로 레벨 400' not in fields['text']:
                    problems.append('fixed level notice missing')

                first = await fill_and_submit(page, posts)
                summary['firstRequest'] = {'scenarioLevel': first.get('scenarioLevel'), 'conditions': first.get('conditions')}
                if first.get('scenarioLevel') != EXPECTED_LEVEL:
                    problems.append(f"scenarioLevel={first.get('scenarioLevel')!r} (account level {ACCOUNT_LEVEL})")
                problems += check_conditions(first)
                # The saved result must render; the transient status line is later replaced by the log viewer.
                body_text = await page.locator('body').inner_text()
                summary['resultLines'] = [line for line in body_text.splitlines() if '검산 결과' in line or '총 대미지' in line][:3]
                if 'Cannot convert' in body_text or not await page.locator('#replay-result').inner_text():
                    problems.append('submit path did not render a saved result')
                await page.screenshot(path=str(output / 'raid-form.png'), full_page=False)

                # A rogue level field must not reach the request: the value is fixed in code, not read from the form.
                await page.evaluate(f"""() => {{
                    const input = document.createElement('input');
                    input.name = 'level'; input.value = '{ROGUE_LEVEL}';
                    document.querySelector('#replay-form').appendChild(input);
                }}""")
                second = await fill_and_submit(page, posts)
                summary['rogueFieldRequest'] = {'injected': ROGUE_LEVEL, 'scenarioLevel': second.get('scenarioLevel')}
                if second.get('scenarioLevel') != EXPECTED_LEVEL:
                    problems.append(f"rogue level field changed the request: {second.get('scenarioLevel')!r}")
                problems += check_conditions(second)
                await page.close()
            finally:
                await browser.close()
    finally:
        server.shutdown()
    summary['requests'] = posts
    summary['errors'] = errors
    summary['assetWarnings'] = asset_warnings
    summary['problems'] = problems + [f'JS {e}' for e in errors]
    summary['passed'] = not summary['problems']
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output)
    print(json.dumps({'passed': summary['passed'], 'problems': summary['problems'],
                      'scenarioLevels': [p.get('scenarioLevel') for p in posts]}, ensure_ascii=False, indent=2))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(run()))

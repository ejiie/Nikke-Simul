"""Browser check for the per-hit damage audit panel (apps/desktop-ui).

Scenarios are labelled by evidence type and never mixed:
- synthetic_http_real_saved_replay: Playwright routes return a real saved replay JSON (read only).
- synthetic_http_boundary: explicit synthetic entries whose terms come from the real HitCalculator
  (tests/ui/fixtures/hit-calculator-cases.json) plus synthetic buff snapshots.
- real_local_api (--live): the Release Nikke.Api built from this worktree, on a private copy of an
  isolated data directory. The source copy and the user's running server are not touched.
A "before" capture serves apps/desktop-ui from --before-ref for comparison.
Outputs go to artifacts/ui/damage-audit/<run>/ (git-ignored).
"""
import argparse
import asyncio
import copy
import hashlib
import http.server
import io
import json
import os
import re
from pathlib import Path
import shutil
import socket
import socketserver
import sqlite3
import subprocess
import tarfile
import threading
import time
import urllib.request
import uuid

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'tests/ui/fixtures/hit-calculator-cases.json'
IDS = ['5011', '5008', '5009', '5004', '5044']
WIDTHS = [1500, 850, 500]

PANEL_PROBE = """() => {
  const p = document.querySelector('.damage-audit-panel');
  if (!p) return null;
  const cards = Object.fromEntries([...p.querySelectorAll('.audit-stat-card')].map(c =>
    [c.querySelector('.audit-label')?.textContent.trim(), c.querySelector('.audit-val')?.textContent.trim()]));
  const steps = [...p.querySelectorAll('tr[data-term]')].map(r => ({ name: r.dataset.term, cells: [...r.cells].map(c => c.textContent.trim()) }));
  const groups = Object.fromEntries([...p.querySelectorAll('[data-audit-group]')].map(g =>
    [g.dataset.auditGroup, [...g.querySelectorAll('li')].map(li => li.textContent.replace(/\\s+/g, ' ').trim())]));
  const shells = [...p.querySelectorAll('.table-scroll')];
  const outside = [...p.querySelectorAll('*')].filter(e => !shells.some(s => s.contains(e)))
    .filter(e => e.getBoundingClientRect().right > p.getBoundingClientRect().right + 1).length;
  return { text: p.innerText, cards, steps, groups, row: document.querySelector('tr.selected-row')?.innerText ?? null,
    overflow: { document: document.documentElement.scrollWidth - window.innerWidth, panel: p.scrollWidth - p.clientWidth, outsideElements: outside } };
}"""


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def serve(ui_dir):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ui_dir), **kwargs)

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


def extract_before(ref, target):
    data = subprocess.check_output(['git', 'archive', ref, 'apps/desktop-ui'], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(target, filter='data')
    return target / 'apps/desktop-ui'


def synthetic_buffs(frame):
    def buff(source, fid, type_, value, basis, target='5004', stacks=1, expires=None):
        return {'effect': {'source': source, 'target': target, 'functionId': fid, 'groupId': fid // 100, 'type': type_,
                           'value': value, 'stacks': stacks, 'expiresAt': expires, 'basis': basis},
                'appliedAtFrame': frame - 30, 'eventId': fid % 1000, 'burstCastId': None}
    return [
        buff('5009', 227110701, 1, 17191, 'native_caster_flat_at_application'),
        buff('5011', 108231001, 1, 0.66, 'native_recipient', expires=frame + 191),
        buff('5008', 127031001, 2, 165770.72639999999, 'caster_final_max_hp_at_application', expires=frame + 380),
        buff('5009', 227120701, 14, 4, 'native_recipient', expires=frame + 531),
        buff('5004', 119111002, 61, 12, 'caster_charge_centiseconds', expires=frame + 531),
        buff('5008', 127031004, 42, 0.3926, 'native_recipient', target='boss', expires=frame + 500),
        buff('5011', 208211008, 51, 0.1246, 'native_recipient', stacks=2, expires=frame + 191),
        buff('5044', 226020701, 8, -0.0749, 'native_recipient', expires=frame + 831),
        buff('5004', 119111003, 11, 0.07, 'native_caster', expires=frame + 531),
        buff('5044', 1, 999, 7, 'synthetic_unknown_basis'),
    ]


def synthetic_replay(template):
    fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
    replay = copy.deepcopy(template)
    entries, total = [], 0
    plan = [('crit_core_fullburst_distance', 'legacy_term_floor'), ('non_full_charge_core', 'nested_floor'),
            ('minimum_damage', 'final_round_even')]
    for index, (name, policy) in enumerate(plan):
        case = fixture['cases'][name]
        calculation = next(c for c in case['candidates'] if c['policy'] == policy)
        total += calculation['damage']
        frame = 600 + index * 60
        entries.append({'hitId': 9000 + index, 'parentId': 8000 + index, 'shotId': 8000 + index, 'pelletIndex': 0,
                        'frame': frame, 'seconds': frame / 60, 'source': '5004', 'target': 'boss', 'effect': 'normal_attack',
                        'kind': 2, 'skillId': None, 'functionId': None, 'damage': calculation['damage'], 'cumulativeDamage': total,
                        'weaponShotId': 1019101, 'chargeRatioRaw': 10000 if case['hit']['fullCharge'] else 5000,
                        'fullCharge': case['hit']['fullCharge'], 'effectiveChargeFrames': 83, 'actualChargeFrames': 83 if case['hit']['fullCharge'] else 40,
                        'shot': None, 'ownBurstEffectActive': False, 'ownBurstCastId': None,
                        'hit': case['hit'], 'calculation': calculation, 'buffs': synthetic_buffs(frame)})
    replay['id'] = 'synthetic-audit-boundary'
    replay['result']['damageLog'] = {'schemaVersion': 1, 'characterId': '5004', 'status': 'complete', 'truncated': False,
                                     'truncationReason': None, 'eventCount': len(entries), 'totalDamage': total, 'entries': entries}
    return replay


def missing_flags_replay(template):
    """Synthetic: stored terms kept while hit flags are removed, null or explicitly false."""
    fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))

    def case(name):
        c = fixture['cases'][name]
        return c['hit'], next(x for x in c['candidates'] if x['policy'] == 'legacy_term_floor')

    crit_hit, crit_calc = case('crit_core_fullburst_distance')
    false_hit, false_calc = case('all_flags_false')
    partial = dict(crit_hit, crit=None, pierce=None)
    for key in ('fullCharge', 'properDistance', 'damageTaken', 'runtimeAttackBuffs'):
        partial.pop(key, None)

    def buffs(frame):
        def buff(source, fid, type_, value, basis, target='5004'):
            return {'effect': {'source': source, 'target': target, 'functionId': fid, 'groupId': fid // 100, 'type': type_,
                               'value': value, 'stacks': 1, 'expiresAt': frame + 300, 'basis': basis},
                    'appliedAtFrame': frame - 30, 'eventId': fid % 1000, 'burstCastId': None}
        return [buff('5011', 208211008, 51, 0.1246, 'native_recipient'), buff('5004', 119111003, 11, 0.07, 'native_caster'),
                buff('5004', 219120701, 54, 10, 'native_caster'), buff('5008', 127031004, 42, 0.3926, 'native_recipient', target='boss'),
                buff('5009', 227120701, 14, 1, 'native_recipient'), buff('5011', 208211006, 14, 0.4517, 'native_recipient'),
                buff('5011', 108231001, 1, 0.66, 'native_recipient')]

    variants = [('empty_hit', {}, crit_calc, None), ('partial_null_hit', partial, crit_calc, None),
                ('no_hit', None, crit_calc, None), ('explicit_false', false_hit, false_calc, False)]
    entries, total = [], 0
    for index, (variant, hit, calculation, flag) in enumerate(variants):
        total += calculation['damage']
        frame = 900 + index * 60
        entry = {'hitId': 9100 + index, 'parentId': 8100 + index, 'shotId': 8100 + index, 'pelletIndex': 0, 'frame': frame,
                 'seconds': frame / 60, 'source': '5004', 'target': 'boss', 'effect': 'normal_attack', 'kind': 2, 'skillId': None,
                 'functionId': None, 'damage': calculation['damage'], 'cumulativeDamage': total, 'weaponShotId': 1019101,
                 'chargeRatioRaw': None, 'fullCharge': flag, 'effectiveChargeFrames': None, 'actualChargeFrames': None, 'shot': None,
                 'ownBurstEffectActive': flag, 'ownBurstCastId': None, 'calculation': calculation, 'buffs': buffs(frame),
                 'syntheticVariant': variant}
        if hit is not None:
            entry['hit'] = hit
        entries.append(entry)
    replay = copy.deepcopy(template)
    replay['id'] = 'synthetic-audit-missing-flags'
    replay['result']['damageLog'] = {'schemaVersion': 1, 'characterId': '5004', 'status': 'complete', 'truncated': False,
                                     'truncationReason': None, 'eventCount': len(entries), 'totalDamage': total, 'entries': entries}
    return replay


def expect_flags(probe, entry):
    """Missing/null flags must stay unknown; explicit false may be stated; type14 integer never gets a unit."""
    problems = []
    text, cards, groups, row = probe['text'], probe['cards'], probe['groups'], probe.get('row') or ''
    if '단위 미확인 · 원값 1' not in text or '+45.17%' not in text or '+1발' in text or '+100%' in text:
        problems.append('type14 unit claim')
    bonus = cards.get('가산 보너스 묶음 (1 + 합)')
    if entry['syntheticVariant'] == 'explicit_false':
        excluded = ' '.join(groups.get('excluded', []))
        if bonus != '1' or '풀차지 아님 → 1' not in text:
            problems.append(f'explicit false not stated: {bonus!r}')
        if '크리티컬 아님' not in excluded or '풀차지 타격 아님' not in excluded:
            problems.append('explicit false exclusions missing')
        if '일반' not in row or '비풀차지' not in row:
            problems.append('explicit false row: ' + row)
    else:
        if bonus != '미확인' or '풀차지 여부 미기록' not in text:
            problems.append(f'unknown flags shown as known: {bonus!r}')
        if groups.get('applied') or groups.get('excluded'):
            problems.append(f"unprovable claim: {groups.get('applied')} {groups.get('excluded')}")
        if any(word in text for word in ('크리티컬 아님', '풀차지 아님', '미적용')):
            problems.append('missing flag rendered as false')
        if '판정 미기록' not in row or '차지 기록 없음' not in row or '버스트 기록 없음' not in row:
            problems.append('row flags: ' + row)
    return problems


def pick_hit(replay):
    entries = replay['result']['damageLog']['entries']
    def score(e):
        types = {b['effect']['type'] for b in e['buffs']}
        return (e['hit'].get('crit', False), e['hit'].get('fullBurst', False), 2 in types, len(e['buffs']))
    return max(entries, key=score)


def number(text):
    cleaned = text.replace(',', '').replace('×', '').replace('%', '').strip()
    return float(cleaned)


def close(a, b, tolerance=1e-9):
    return abs(a - b) <= tolerance * max(1.0, abs(b))


def compare_panel(probe, entry):
    """Displayed values against the stored entry; returns a list of problems."""
    problems = []
    terms = {t['name']: t for t in entry['calculation']['terms']}
    cards = probe['cards']
    expectations = [('버프 적용 공격력 (최종 공격력)', terms['effectiveAttack']['after']),
                    ('공방차 (ATK − DEF)', terms['P']['before']), ('기본 피해 P (정수화 전)', terms['P']['after']),
                    ('최종 피해', entry['damage']), ('적 방어력 (Target DEF)', terms['effectiveDefense']['after'])]
    for label, expected in expectations:
        try:
            if not close(number(cards[label]), expected):
                problems.append(f'{label}: shown {cards[label]} expected {expected}')
        except (KeyError, ValueError):
            problems.append(f'{label}: missing or non-numeric {cards.get(label)!r}')
    if cards.get('정수화 정책') != entry['calculation']['policy']:
        problems.append(f"policy {cards.get('정수화 정책')!r}")
    if [s['name'] for s in probe['steps']] != [t['name'] for t in entry['calculation']['terms']]:
        problems.append('term rows differ from stored terms')
    for step in probe['steps']:
        if not close(number(step['cells'][2]), terms[step['name']]['after']):
            problems.append(f"term {step['name']} shown {step['cells'][2]}")
    items = [li for key, rows in probe['groups'].items() if key != 'attack' for li in rows]
    if len(items) != len(entry['buffs']):
        problems.append(f'effect rows {len(items)} != buffs {len(entry["buffs"])}')
    for li in items:
        if '+-' in li or 'NaN' in li or 'undefined' in li:
            problems.append('bad effect text: ' + li)
        if 'HP 지속 회복' in li and ('%' in li.split('·')[1] or '초당 HP' not in li):
            problems.append('heal shown as percent: ' + li)
        if re.search(r'최대 장탄 수 (스택당 )?[+-]?[\d,.]+발', li):
            problems.append('ammo count claimed without value-type metadata: ' + li)
    if '크리배율 × 코어배율 × 풀버스트배율' in probe['text']:
        problems.append('old multiplicative formula still shown')
    return problems


async def open_panel(page, base, hit_id, errors):
    await page.goto(base + '/editor/')
    await page.wait_for_function("document.body.dataset.ready==='true'", timeout=60000)
    await page.locator('[data-tab="raid"]').click()
    await page.locator('#run-replay').click()
    await page.wait_for_function("document.querySelector('#damage-log-container')?.textContent.includes('발사')", timeout=60000)
    await page.evaluate("id => document.querySelector(`.graph-hit-dot[data-hit-id=\"${id}\"]`).dispatchEvent(new MouseEvent('click'))", hit_id)
    await page.wait_for_selector('.damage-audit-panel', timeout=10000)


async def route_synthetic(page, replay_holder):
    async def fulfil(route, body):
        await route.fulfill(json=body)
    await page.route('**/api/bootstrap', lambda r: fulfil(r, {'token': 'audit-token', 'testMode': True, 'jobs': [],
        'connections': [{'id': 'c1', 'accountId': 'acc-audit', 'nickname': '검증용', 'status': 'ready', 'choices': [{'area': 1, 'label': 'synthetic'}]}]}))
    await page.route('**/api/accounts/*/snapshot', lambda r: fulfil(r, {'id': 'snap-audit', 'accountId': 'acc-audit', 'synchroLevel': 400,
        'observedAt': '2026-09-11T10:00:00Z', 'characters': [{'characterId': i, 'name': n, 'level': 400, 'limitBreak': 3, 'core': 0}
        for i, n in zip(IDS, ['리타', '블랑', '누아르', '앨리스', '모더니아'])]}))
    await page.route('**/api/presentation', lambda r: fulfil(r, {'characters': [{'characterUid': i, 'displayName': n, 'burstStep': s}
        for i, n, s in zip(IDS, ['리타', '블랑', '누아르', '앨리스', '모더니아'], [1, 2, 3, 3, 3])]}))
    await page.route('**/api/presentation/status', lambda r: fulfil(r, {'status': 'idle', 'revision': 1, 'message': 'ready'}))
    await page.route('**/api/accounts/*/formation', lambda r: fulfil(r, {'accountId': 'acc-audit', 'slots': IDS}))
    await page.route('**/api/accounts/*/burst-tactic', lambda r: fulfil(r, {'saved': None, 'stale': False, 'executionStatus': 'legacy'}))
    await page.route('**/api/snapshots/*/combat-powers', lambda r: fulfil(r, {i: 1 for i in IDS}))
    await page.route('**/api/runtime/skill-replays/*/damage-log**', lambda r: fulfil(r, {'exportSchemaVersion': 1,
        'collectionStatus': 'complete', 'replay': replay_holder['replay']}))
    await page.route('**/api/runtime/skill-replays', lambda r: fulfil(r, replay_holder['replay']))


async def capture(browser, label, base, replay, entry, output, widths, synthetic=True):
    errors = []
    page = await browser.new_page(viewport={'width': widths[0], 'height': 1000})
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' and 'favicon' not in m.text and '404' not in m.text else None)
    if synthetic:
        await route_synthetic(page, {'replay': replay})
    await open_panel(page, base, entry['hitId'], errors)
    shots = {}
    for width in widths:
        await page.set_viewport_size({'width': width, 'height': 1000})
        await page.wait_for_timeout(150)
        probe = await page.evaluate(PANEL_PROBE)
        path = output / f'{label}-{width}.png'
        await page.locator('.damage-audit-panel').screenshot(path=str(path))
        shots[width] = {'screenshot': str(path.relative_to(ROOT)), 'overflow': probe['overflow'], 'probe': probe}
    await page.close()
    return shots, errors


def copy_isolated_data(source, target):
    # Byte copies only: opening the source database (even read only) could touch its WAL index.
    target.mkdir(parents=True)
    for name in ('accounts.db', 'accounts.db-wal', 'accounts.db-shm'):
        if (source / name).exists():
            shutil.copyfile(source / name, target / name)
    for name in ('calculation', 'presentation', 'raw', 'runtime'):
        if (source / name).exists():
            shutil.copytree(source / name, target / name)
    shutil.copyfile(source / 'game-catalog.json', target / 'game-catalog.json')


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


async def live_check(browser, dotnet, source, output):
    data = output / 'live-data'
    digests = {name: file_digest(source / name) for name in ('accounts.db', 'accounts.db-wal')}
    copy_isolated_data(source, data)
    with sqlite3.connect(data / 'accounts.db') as db:
        connection = json.loads(db.execute('SELECT * FROM connections').fetchone()[1])
        db.execute('DELETE FROM solo_burst_tactics')
    port = free_port()
    base = f'http://127.0.0.1:{port}'
    env = dict(os.environ, NIKKE_PROJECT_ROOT=str(ROOT), NIKKE_DATA_ROOT=str(data), NIKKE_GAME_CATALOG=str(data / 'game-catalog.json'),
               NIKKE_TEST_FIXTURE='1', NIKKE_PORT=str(port))
    result = {'kind': 'real_local_api_private_data_copy', 'base': base}
    with (output / 'live-server.log').open('w') as log:
        process = subprocess.Popen([dotnet, str(ROOT / 'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')], cwd=ROOT, env=env,
                                   stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            for _ in range(150):
                try:
                    with urllib.request.urlopen(base + '/api/bootstrap') as response:
                        token = json.load(response)['token']
                    break
                except OSError:
                    if process.poll() is not None:
                        raise RuntimeError('API exited; see live-server.log')
                    time.sleep(.2)
            else:
                raise RuntimeError('API startup timed out')
            request = urllib.request.Request(base + f"/api/accounts/{connection['accountId']}/formation", method='PUT',
                                             data=json.dumps({'slots': IDS}).encode(), headers={'Content-Type': 'application/json', 'X-Nikke-Token': token})
            with urllib.request.urlopen(request) as response:
                assert response.status == 200
            errors = []
            page = await browser.new_page(viewport={'width': 1500, 'height': 1000})
            page.on('pageerror', lambda e: errors.append(str(e)))
            await page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base + '/') else route.abort())
            await page.goto(base + '/editor/')
            await page.wait_for_function("document.body.dataset.ready==='true'", timeout=60000)
            await page.locator('[data-tab="raid"]').click()
            await page.locator('[name="crit"]').select_option('on')
            await page.locator('[name="seconds"]').fill('180')
            async with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/runtime/skill-replays'), timeout=180000) as pending:
                await page.locator('#run-replay').click()
            response = await pending.value
            body = await response.json()
            (output / 'live-response.json').write_text(json.dumps(body), encoding='utf-8')
            assert response.status == 200, f'HTTP {response.status}: {str(body)[:300]}'
            await page.wait_for_function("document.querySelector('#damage-log-container')?.textContent.includes('발사')", timeout=60000)
            entry = pick_hit(body)
            await page.evaluate("id => document.querySelector(`.graph-hit-dot[data-hit-id=\"${id}\"]`).dispatchEvent(new MouseEvent('click'))", entry['hitId'])
            await page.wait_for_selector('.damage-audit-panel', timeout=10000)
            shots = {}
            for width in WIDTHS:
                await page.set_viewport_size({'width': width, 'height': 1000})
                await page.wait_for_timeout(150)
                probe = await page.evaluate(PANEL_PROBE)
                path = output / f'live-after-{width}.png'
                await page.locator('.damage-audit-panel').screenshot(path=str(path))
                shots[width] = {'screenshot': str(path.relative_to(ROOT)), 'overflow': probe['overflow'], 'probe': probe}
            await page.close()
            result.update({'hitId': entry['hitId'], 'crit': entry['hit']['crit'], 'fullBurst': entry['hit']['fullBurst'],
                           'policy': entry['calculation']['policy'], 'damage': entry['damage'], 'entries': len(body['result']['damageLog']['entries']),
                           'problems': compare_panel(shots[1500]['probe'], entry), 'errors': errors, 'shots': shots})
        finally:
            process.terminate()
            process.wait(timeout=10)
    result['sourceUnchanged'] = digests == {name: file_digest(source / name) for name in digests}
    return result


async def run(args):
    output = ROOT / 'artifacts/ui/damage-audit' / f'run-{uuid.uuid4().hex[:12]}'
    output.mkdir(parents=True)
    real = json.loads(Path(args.real_replay).read_text(encoding='utf-8'))
    real = real.get('replay', real)
    boundary = synthetic_replay(real)
    before_ui = extract_before(args.before_ref, output / 'before-src')
    after_server, after_base = serve(ROOT / 'apps/desktop-ui')
    before_server, before_base = serve(before_ui)
    summary = {'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain', 'apps/desktop-ui', 'tests/ui'], cwd=ROOT, text=True).strip()),
               'beforeRef': args.before_ref, 'realReplay': str(args.real_replay), 'scenarios': {}}
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(channel='msedge', headless=True)
            try:
                scenarios = [('synthetic_http_real_saved_replay', real), ('synthetic_http_boundary', boundary),
                             ('synthetic_http_missing_flags', missing_flags_replay(real))]
                for label, replay in scenarios:
                    entries = replay['result']['damageLog']['entries']
                    targets = [pick_hit(replay)] if label == 'synthetic_http_real_saved_replay' else entries
                    for entry in targets:
                        key = f"{label}-hit{entry['hitId']}"
                        after, after_errors = await capture(browser, key + '-after', after_base, replay, entry, output, WIDTHS)
                        problems = compare_panel(after[1500]['probe'], entry)
                        if label == 'synthetic_http_missing_flags':
                            problems += expect_flags(after[1500]['probe'], entry)
                        hit = entry.get('hit') or {}
                        scenario = {'hitId': entry['hitId'], 'variant': entry.get('syntheticVariant'),
                                    'policy': entry['calculation']['policy'], 'damage': entry['damage'],
                                    'crit': hit.get('crit'), 'core': hit.get('core'), 'fullBurst': hit.get('fullBurst'),
                                    'row': after[1500]['probe'].get('row'), 'problems': problems, 'errors': after_errors,
                                    'overflow': {w: s['overflow'] for w, s in after.items()},
                                    'screenshots': [s['screenshot'] for s in after.values()],
                                    'effects': after[1500]['probe']['groups'], 'cards': after[1500]['probe']['cards']}
                        if entry is targets[0]:
                            before, before_errors = await capture(browser, key + '-before', before_base, replay, entry, output, [1500])
                            scenario['before'] = {'screenshot': before[1500]['screenshot'], 'errors': before_errors,
                                                  'text': before[1500]['probe']['text']}
                        summary['scenarios'][key] = scenario
                if args.live:
                    summary['scenarios']['real_local_api'] = await live_check(browser, args.dotnet, Path(args.live_source), output)
            finally:
                await browser.close()
    finally:
        after_server.shutdown()
        before_server.shutdown()
    failures = []
    for key, scenario in summary['scenarios'].items():
        failures += [f'{key}: {p}' for p in scenario.get('problems', [])]
        failures += [f'{key}: JS {e}' for e in scenario.get('errors', [])]
        overflow = scenario.get('overflow') or {w: s['overflow'] for w, s in scenario.get('shots', {}).items()}
        for width, value in overflow.items():
            if value['document'] > 0 or value['panel'] > 0 or value['outsideElements'] > 0:
                failures.append(f'{key}: overflow at {width}px {value}')
        if key == 'real_local_api' and not scenario.get('sourceUnchanged'):
            failures.append('live source data changed')
    summary['failures'] = failures
    summary['passed'] = not failures
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output)
    print(json.dumps({'passed': summary['passed'], 'failures': failures}, ensure_ascii=False, indent=2))
    return 0 if summary['passed'] else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--real-replay', required=True, help='Saved replay JSON (read only)')
    parser.add_argument('--before-ref', default='77b3ccecd352a592ddc9f8e0bbf09bf03a730085')
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--dotnet')
    parser.add_argument('--live-source', help='Isolated data directory to copy (never modified)')
    args = parser.parse_args()
    if args.live and not (args.dotnet and args.live_source):
        parser.error('--live needs --dotnet and --live-source')
    raise SystemExit(asyncio.run(run(args)))


if __name__ == '__main__':
    main()

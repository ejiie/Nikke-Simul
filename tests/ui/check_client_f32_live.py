"""I-UI stage B: client_f32 schema 3 UI against a REAL isolated local API (Release Nikke.Api from this worktree).

Evidence type: real_local_api_synthetic_account.
- Data root: a NEW directory under artifacts/ui/client-f32-live/run-*/data. Only the public catalog allowlist
  (game-catalog.json, calculation/<id>/*, runtime/<id>/catalog.json) is copied from --source-data, which is read
  only and hash-checked before/after. The account DB is NEW and synthetic (same shape as the Backend I-BE check).
  No original account DB/session/cache is opened. Port is random and never 5180/5181.
- Browser: Chromium drives the real web single-hit screen (/legacy/) and desktop UI (/editor/). Synthetic HTTP
  is limited to two presentation routes: /api/bootstrap gets a synthetic ready connection appended (no game login),
  and /api/snapshots/*/combat-powers answers {} (synthetic snapshot has no raw manifest; badge only).
  Snapshot, stats, hit, formation, replay and compute calls all go to the real API.
U-FIX-1 (Q-F32 B2-STAT-1/2): the n=1 statistics screen must show the API's mean/median/P5/P95 and mark only
SD/mean CI unsupported; n=2 shows the CI; a 400 baseline_required comparison keeps the API "connected" with a
"비교 기준 없음" state, while aborted compute routes (synthetic transport failure) still show "compute API 미연결".
Output: artifacts/ui/client-f32-live/run-<id>/ (git-ignored). Exit code 1 means NOT accepted.
Usage: python tests/ui/check_client_f32_live.py --dotnet <dotnet.exe> --source-data <public data dir>
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from decimal import Decimal

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
IDS = ['5011', '5008', '5004', '5009', '5044']
WIDTHS = [1500, 850, 500]
CONNECTION = {'id': 'synthetic-connection', 'status': 'ready', 'area': 1, 'accountId': 'synthetic-account', 'message': None,
              'choices': [{'area': 1, 'label': '합성 계정(검증용)', 'characterCount': 5}]}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def free_port():
    while True:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        if port not in (5180, 5181):
            return port


def prepare_data(source, data):
    hashes = {}

    def copy(relative):
        src = source / relative
        hashes[relative.as_posix()] = digest(src)
        target = data / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
    copy(Path('game-catalog.json'))
    for folder in ('calculation', 'runtime'):
        copy(Path(folder) / 'current.json')
        manifest = read(data / folder / 'current.json')
        version = manifest['id']
        for name in (manifest['fileHashes'] if folder == 'calculation' else ['catalog.json']):
            copy(Path(folder) / version / name)
    game = read(data / 'game-catalog.json')
    snapshot = {'id': 'synthetic-f32-ui', 'accountId': CONNECTION['accountId'], 'gameSnapshotId': game['id'],
                'synchroLevel': 400, 'savedAt': '2026-09-28T00:00:00+00:00', 'observedAt': '2026-09-28T00:00:00+00:00',
                'consoles': {k: 0 for k in ('1001', '1101', '1102', '1103', '1201', '1202', '1203', '1204', '1205')},
                'characters': []}
    for cid in IDS:
        snapshot['characters'].append({'characterId': cid, 'name': game['names'][cid], 'level': 400, 'nativeLevel': 400,
            'limitBreak': 0, 'core': 0, 'bond': 0, 'skills': {'1': 10, '2': 10, '3': 10}, 'cubeId': '0', 'cubeLevel': 0,
            'collectionId': '0', 'collectionGrade': 'none', 'collectionLevel': 0,
            'equipment': [{'slot': slot, 'tier': 0, 'level': 0, 'manufacturer': 0,
                'lines': [{'lineIndex': i, 'presence': 'absent'} for i in range(1, 4)]} for slot in ('head', 'torso', 'arm', 'leg')]})
    # One catalog OL attack line with raw numerator + normalized ratio on 5004 (앨리스).
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
    return hashes, snapshot, str(raw)


class Api:
    def __init__(self, base):
        self.base, self.token = base, ''

    def call(self, path, payload=None, method=None):
        request = urllib.request.Request(self.base + '/api/' + path, method=method,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json', 'X-Nikke-Token': self.token})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            text = error.read().decode('utf-8', 'replace')
            try:
                return error.code, json.loads(text)
            except ValueError:
                return error.code, {'raw': text}


async def patch_bootstrap(page, base):
    async def handle(route):
        response = await route.fetch()
        body = await response.json()
        body['connections'] = [c for c in body.get('connections', []) if c.get('id') != CONNECTION['id']] + [CONNECTION]
        await route.fulfill(response=response, json=body)
    # Nothing outside the isolated API is reachable. Playwright tries the LAST registered route first,
    # so the bootstrap patch is registered after the catch-all.
    await page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base + '/') else route.abort())
    await page.route(base + '/api/bootstrap', handle)
    # The synthetic snapshot has no raw collector manifest, so the combat-power badge endpoint answers 400
    # "Invalid manifest ID". The badge is presentation only (not a damage input); it is answered with {}.
    await page.route(base + '/api/snapshots/*/combat-powers', lambda route: route.fulfill(json={}))


async def web_checks(browser, base, api, out, problems):
    result = {}
    page = await browser.new_page(viewport={'width': 1500, 'height': 1100})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    await patch_bootstrap(page, base)
    await page.goto(base + '/legacy/')
    await page.wait_for_selector('[data-character="5004"]', timeout=60000)
    await page.locator('[data-character="5004"]').click()
    await page.locator('#load-stats').click()
    await page.wait_for_selector('.hit-workbench', timeout=60000)
    await page.locator('.hit-workbench > summary').click()
    select = page.locator('.hit-form [name="roundingPolicy"]')
    options = await select.evaluate("s => [...s.options].map(o => ({value: o.value, text: o.text, selected: o.selected}))")
    result['policyOptions'] = options
    if [o['value'] for o in options] != ['client_f32', 'legacy_term_floor', 'final_round_even', 'nested_floor'] or not options[0]['selected']:
        problems.append(f'web: policy options {options}')
    fields = await page.evaluate("() => ['statDamageRatio','defenceRatioRate'].map(n => { const i = document.querySelector(`.hit-form [name=${n}]`); return {name: n, value: i.value, disabled: i.matches(':disabled')}; })")
    result['experimentalDefaults'] = fields
    if [f['value'] for f in fields] != ['1', '0'] or any(f['disabled'] for f in fields):
        problems.append(f'web: experimental defaults {fields}')

    async def submit(label):
        async with page.expect_response(lambda r: r.url.endswith('/api/calculations/hit') and r.request.method == 'POST', timeout=60000) as pending:
            await page.locator('.hit-form button[type="submit"]').click()
        response = await pending.value
        body = await response.json()
        request = json.loads(response.request.post_data)
        await page.wait_for_function("() => { const r = document.querySelector('.hit-result'); return r && !r.textContent.includes('다시 비교') && r.textContent.trim().length > 0; }")
        dom = await page.evaluate("""() => { const r = document.querySelector('.hit-result');
          return { text: r.innerText, rows: [...r.querySelectorAll('tr[data-policy]')].map(t => ({policy: t.dataset.policy, status: t.dataset.status, text: t.innerText.replace(/\\s+/g,' ').trim()})),
            terms: [...r.querySelectorAll('tr[data-term]')].map(t => t.dataset.term), attack: r.querySelector('.effective-attack')?.textContent,
            overflow: document.documentElement.scrollWidth - window.innerWidth }; }""")
        (out / f'web-{label}-response.json').write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding='utf-8')
        return response.status, request, body, dom

    # 1) client_f32 default with experimental rates and an exact manual attack buff.
    await page.locator('.hit-form [name="attack-buffs"]').fill('14.5')
    await page.locator('.hit-form [name="statDamageRatio"]').fill('2')
    await page.locator('.hit-form [name="defenceRatioRate"]').fill('0.25')
    status, request, body, dom = await submit('client')
    result['client'] = {'status': status, 'request': {k: request[k] for k in ('inputSchemaVersion', 'roundingPolicy')},
                        'requestRates': {k: request['input'].get(k) for k in ('statDamageRatio', 'defenceRatioRate')},
                        'runtimeAttackBuffs': request['input'].get('runtimeAttackBuffs'), 'rows': dom['rows'], 'terms': dom['terms'],
                        'exactEffectiveAttack': body.get('exactEffectiveAttack'), 'attackText': dom['attack']}
    if status != 200 or request['inputSchemaVersion'] != 3 or request['roundingPolicy'] != 'client_f32':
        problems.append(f'web client: status/request {status} {request.get("inputSchemaVersion")} {request.get("roundingPolicy")}')
    if request['input'].get('statDamageRatio') != 2 or request['input'].get('defenceRatioRate') != 0.25:
        problems.append('web client: experimental rates not sent')
    if (request['input'].get('runtimeAttackBuffs') or [{}])[0].get('rawRate10000') != '1450':
        problems.append(f'web client: manual buff raw {request["input"].get("runtimeAttackBuffs")}')
    if status == 200:
        if [r['policy'] for r in dom['rows']] != [c['policy'] for c in body['candidates']] or dom['rows'][0]['policy'] != 'client_f32':
            problems.append(f'web client: row order {dom["rows"]}')
        if dom['terms'] != [t['name'] for t in body['selectedCandidate']['terms']]:
            problems.append(f'web client: audit terms {dom["terms"]}')
        exact = int(body['selectedCandidate']['exactDamage'])
        if f'{exact:,}' not in dom['rows'][0]['text'] or '선택' not in dom['rows'][0]['text']:
            problems.append(f'web client: exact damage {exact} not shown {dom["rows"][0]}')
        if dom['attack'] != f"{int(body['exactEffectiveAttack']):,}":
            problems.append(f'web client: effective attack {dom["attack"]} vs {body["exactEffectiveAttack"]}')
        if sum('비교 후보' in r['text'] for r in dom['rows']) != 3:
            problems.append('web client: comparison tags')
        if '새 두 비율을 적용하지 않음' not in dom['text'] or 'schema 2' in dom['text']:
            problems.append('web client: limitations/conversion text')
        stored_status, stored = api.call('calculations/hit/' + body['id'])
        if stored_status != 200 or stored != body:
            problems.append('web client: stored record differs from response')
    for width in WIDTHS:
        await page.set_viewport_size({'width': width, 'height': 1100})
        await page.wait_for_timeout(150)
        overflow = await page.evaluate('document.documentElement.scrollWidth - window.innerWidth')
        if overflow > 0:
            problems.append(f'web client @{width}: horizontal overflow {overflow}')
        await page.locator('.hit-result').screenshot(path=str(out / f'web-client-{width}.png'))
    await page.set_viewport_size({'width': 1500, 'height': 1100})

    # 2) Comparison candidate selected: its own audit terms are shown.
    await select.select_option('nested_floor')
    status, request, body, dom = await submit('nested')
    result['nested'] = {'status': status, 'terms': dom['terms'], 'rows': dom['rows']}
    if status != 200 or request['roundingPolicy'] != 'nested_floor' or body['selectedPolicy'] != 'nested_floor':
        problems.append(f'web nested: {status} {request.get("roundingPolicy")}')
    elif dom['terms'] != [t['name'] for t in body['selectedCandidate']['terms']] or 'B2' not in dom['terms']:
        problems.append(f'web nested: audit terms {dom["terms"]}')
    elif '선택' not in next(r['text'] for r in dom['rows'] if r['policy'] == 'nested_floor'):
        problems.append('web nested: selected tag')
    await select.select_option('client_f32')

    # 3) Finer-than-1/10000 manual buff: rejected in the browser, no request.
    await page.locator('.hit-form [name="attack-buffs"]').fill('1.234')
    sent = []
    page.on('request', lambda r: sent.append(r.url) if r.url.endswith('/api/calculations/hit') else None)
    await page.locator('.hit-form button[type="submit"]').click()
    await page.wait_for_timeout(400)
    text = await page.locator('.hit-result').inner_text()
    result['finerBuff'] = {'text': text, 'requests': len(sent)}
    if sent or '1/10000' not in text:
        problems.append(f'web finer buff: {text!r} requests={len(sent)}')
    await page.locator('.hit-form [name="attack-buffs"]').fill('')

    # 4) Server constraint: fractional native attack is a 400, shown with the server code (not truncated).
    await page.locator('.hit-form [name="statAttack"]').fill('100000.5')
    status, request, body, dom = await submit('fractional')
    result['fractional'] = {'status': status, 'message': body.get('message'), 'text': dom['text']}
    if status != 400 or 'must_be_integer_never_truncated' not in (body.get('message') or '') or '정수만 허용' not in dom['text']:
        problems.append(f'web fractional: {status} {body} {dom["text"]!r}')
    await page.locator('.hit-result').screenshot(path=str(out / 'web-error-1500.png'))
    result['pageErrors'] = errors
    if errors:
        problems.append(f'web page errors {errors}')
    await page.close()
    return result


def pick_entry(replay):
    entries = replay['result']['damageLog']['entries']
    return max(entries, key=lambda e: (bool((e.get('hit') or {}).get('fullBurst')), bool((e.get('hit') or {}).get('core')), e['damage']))


async def desktop_checks(browser, base, api, out, problems):
    result = {}
    page = await browser.new_page(viewport={'width': 1500, 'height': 1100})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    await patch_bootstrap(page, base)
    await page.goto(base + '/editor/')
    await page.wait_for_function("document.body.dataset.ready==='true'", timeout=90000)
    await page.locator('[data-tab="raid"]').click()
    options = await page.locator('[name="rounding"]').evaluate("s => [...s.options].map(o => ({value: o.value, text: o.text, selected: o.selected}))")
    result['raidPolicyOptions'] = options
    if [o['value'] for o in options] != ['client_f32', 'legacy_term_floor', 'final_round_even', 'nested_floor'] or not options[0]['selected']:
        problems.append(f'desktop: raid policy options {options}')
    # F-COND-2 R3: battle time is fixed at 180 s (no input).
    await page.locator('[name="core"]').check()
    async with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/runtime/skill-replays'), timeout=240000) as pending:
        await page.locator('#run-replay').click()
    response = await pending.value
    body = await response.json()
    request = json.loads(response.request.post_data)
    (out / 'desktop-replay-response.json').write_text(json.dumps(body, ensure_ascii=False), encoding='utf-8')
    result['replayRequest'] = {'roundingPolicy': request.get('conditions', {}).get('roundingPolicy'), 'status': response.status}
    if response.status != 200 or request.get('conditions', {}).get('roundingPolicy') != 'client_f32':
        problems.append(f'desktop replay: {response.status} {request.get("conditions", {}).get("roundingPolicy")} {str(body)[:300]}')
        await page.close()
        return result
    await page.wait_for_function("document.querySelector('#damage-log-container')?.textContent.includes('발사')", timeout=90000)
    entry = pick_entry(body)
    policies = {e['calculation']['policy'] for e in body['result']['damageLog']['entries']}
    result['logPolicies'] = sorted(policies)
    if policies != {'client_f32'}:
        problems.append(f'desktop: damage log policies {policies}')
    await page.evaluate("id => document.querySelector(`.graph-hit-dot[data-hit-id=\"${id}\"]`).dispatchEvent(new MouseEvent('click'))", entry['hitId'])
    await page.wait_for_selector('.damage-audit-panel', timeout=15000)
    probe = await page.evaluate("""() => { const p = document.querySelector('.damage-audit-panel');
      return { text: p.innerText, cards: Object.fromEntries([...p.querySelectorAll('.audit-stat-card')].map(c => [c.querySelector('.audit-label')?.textContent.trim(), c.querySelector('.audit-val')?.textContent.trim()])),
        steps: [...p.querySelectorAll('tr[data-term]')].map(r => ({ name: r.dataset.term, after: r.cells[2].textContent.trim() })) }; }""")
    terms = entry['calculation']['terms']
    result['auditHit'] = {'hitId': entry['hitId'], 'damage': entry['damage'], 'steps': [s['name'] for s in probe['steps']],
                          'cards': probe['cards']}
    if [s['name'] for s in probe['steps']] != [t['name'] for t in terms]:
        problems.append(f'desktop audit: steps {probe["steps"]}')
    if 'B3 × B4 × B5' in probe['cards'] or 'statDamageRatio' not in probe['cards'] or '1 − defenceRatioRate' not in probe['cards']:
        problems.append(f'desktop audit: client cards {list(probe["cards"])}')
    if probe['cards'].get('최종 피해') != f"{int(entry['damage']):,}":
        problems.append(f'desktop audit: final {probe["cards"].get("최종 피해")} vs {entry["damage"]}')
    if probe['cards'].get('정수화 정책') != 'client_f32' or '저장된 발당 피해와 일치' not in probe['text']:
        problems.append('desktop audit: policy/final match text')
    for width in WIDTHS:
        await page.set_viewport_size({'width': width, 'height': 1100})
        await page.wait_for_timeout(150)
        overflow = await page.evaluate('document.documentElement.scrollWidth - window.innerWidth')
        if overflow > 0:
            problems.append(f'desktop audit @{width}: horizontal overflow {overflow}')
        await page.locator('.damage-audit-panel').screenshot(path=str(out / f'desktop-audit-{width}.png'))
    await page.set_viewport_size({'width': 1500, 'height': 1100})

    # Statistics screen: one tiny batch with the client default, then its recorded policy metadata.
    comparison_answers = []

    async def on_response(response):
        if response.url.split('?')[0].endswith('/comparison'):
            comparison_answers.append({'status': response.status, 'body': (await response.text())[:300]})
    page.on('response', on_response)
    await page.locator('[data-tab="stats"]').click()
    await page.wait_for_selector('#compute-start', timeout=30000)
    await page.locator('#compute-runs').fill('1')
    async with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/compute/experiments'), timeout=240000) as pending:
        await page.locator('#compute-start').click()
    response = await pending.value
    created = await response.json()
    request = json.loads(response.request.post_data)
    result['computeRequest'] = {'status': response.status, 'roundingPolicy': request['conditions'].get('roundingPolicy'),
                                'durationFrames': request['conditions'].get('combat', {}).get('durationFrames')}
    if response.status != 202 or request['conditions'].get('roundingPolicy') != 'client_f32':
        problems.append(f'desktop stats: create {response.status} {request["conditions"].get("roundingPolicy")} {str(created)[:300]}')
    else:
        final = None
        for _ in range(600):
            _, final = api.call('compute/experiments/' + created['id'])
            if final['state'] in ('completed', 'failed', 'cancelled'):
                break
            time.sleep(.2)
        result['batch'] = {'state': final['state'], 'input': {k: final['input'].get(k) for k in ('inputSchemaVersion', 'roundingPolicy', 'summaryVersion', 'engineVersion')}}
        if final['state'] != 'completed' or final['input'].get('roundingPolicy') != 'client_f32' or final['input'].get('inputSchemaVersion') != 3                 or not str(final['input'].get('summaryVersion', '')).startswith('cpu-summary.'):
            problems.append(f'desktop stats: batch {result["batch"]}')
        # The summary version follows the Backend (cpu-summary.2-client-f32, later cpu-summary.3-boss-conditions).
        await page.wait_for_function("v => document.querySelector('#stats-content')?.innerText.includes(v)", arg=final['input'].get('summaryVersion') or '<none>', timeout=120000)
        try:
            await page.wait_for_function("document.querySelector('#stats-content')?.innerText.includes('표본 수 n')", timeout=60000)
        except Exception:
            problems.append('desktop stats: statistics section not rendered')
        text = await page.locator('#stats-content').inner_text()
        (out / 'desktop-stats-text.txt').write_text(text, encoding='utf-8')
        _, stat = api.call('compute/experiments/' + created['id'] + '/statistics')
        result['statisticsN'] = (stat.get('team') or {}).get('n')
        result['statsHasPolicyCard'] = 'client_f32' in text and 'schema 3' in text
        if not result['statsHasPolicyCard']:
            problems.append('desktop stats: policy card missing')
        for width in WIDTHS:
            await page.set_viewport_size({'width': width, 'height': 1100})
            await page.wait_for_timeout(150)
            overflow = await page.evaluate('document.documentElement.scrollWidth - window.innerWidth')
            if overflow > 0:
                problems.append(f'desktop stats @{width}: horizontal overflow {overflow}')
            await page.locator('#stats-content').screenshot(path=str(out / f'desktop-stats-{width}.png'))
        await page.set_viewport_size({'width': 1500, 'height': 1100})
        await stats_fix_checks(page, base, api, out, problems, result, created['id'], comparison_answers)
    result['pageErrors'] = errors
    if errors:
        problems.append(f'desktop page errors {errors}')
    await page.close()
    return result


STATS_PROBE = """() => { const root = document.querySelector('#stats-content');
  const cards = Object.fromEntries([...root.querySelectorAll('.metric-card')].map(c => [c.querySelector('span')?.textContent.trim(), c.querySelector('strong')?.textContent.trim()]));
  const members = [...root.querySelectorAll('.compute-member-table tbody tr')].map(r => [...r.cells].map(c => c.textContent.trim()));
  return { text: root.innerText, cards, members,
    pill: document.querySelector('#stats-content .section-heading .status-pill')?.textContent.trim() ?? null,
    noBaseline: Boolean(root.querySelector('[data-comparison-state="no_baseline"]')),
    errors: [...root.querySelectorAll('.compute-errors li')].map(li => li.textContent.trim()) }; }"""


def fmt_int(value):
    return f'{int(value):,}' if value is not None and float(value).is_integer() else None


async def stats_fix_checks(page, base, api, out, problems, result, experiment_id, comparison_answers):
    """U-FIX-1: B2-STAT-1 (n=1 point estimates shown, n>=2 CI) and B2-STAT-2 (no baseline is not an outage)."""
    fix = result.setdefault('uFix1', {})
    _, stat = api.call(f'compute/experiments/{experiment_id}/statistics')
    probe = await page.evaluate(STATS_PROBE)
    (out / 'desktop-stats-n1-probe.json').write_text(json.dumps({'api': stat, 'dom': probe}, ensure_ascii=False, indent=2), encoding='utf-8')
    team = stat['team']
    fix['n1'] = {'api': {k: team.get(k) for k in ('n', 'mean', 'median', 'p5', 'p95', 'sampleSd', 'meanCi', 'unsupportedReason')},
                 'cards': {k: probe['cards'].get(k) for k in ('표본 수 n', '평균 팀 피해', '중앙값', 'P5', 'P95', '표본 표준편차', '평균 CI')},
                 'pill': probe['pill'], 'noBaseline': probe['noBaseline'], 'errors': probe['errors'],
                 'comparisonAnswers': comparison_answers}
    if team['n'] != 1 or team['unsupportedReason'] != 'mean_ci_requires_n_at_least_2':
        problems.append(f'U-FIX-1 n1: unexpected API shape {fix["n1"]["api"]}')
    for label, key in (('평균 팀 피해', 'mean'), ('중앙값', 'median'), ('P5', 'p5'), ('P95', 'p95')):
        if team[key] is None or probe['cards'].get(label) != fmt_int(team[key]):
            problems.append(f'U-FIX-1 n1: {label} shows {probe["cards"].get(label)!r}, API {team[key]}')
    for label in ('표본 표준편차', '평균 CI'):
        if probe['cards'].get(label) != '미지원':
            problems.append(f'U-FIX-1 n1: {label} shows {probe["cards"].get(label)!r} for a null API value')
    if '표본 2건 이상 필요' not in probe['text'] or 'mean_ci_requires_n_at_least_2' in probe['text']:
        problems.append('U-FIX-1/U-FIX-6 n1: scoped reason not shown in Korean only')
    _, batch = api.call('compute/experiments/' + experiment_id)
    order = batch['input']['characterIds']
    if len(probe['members']) != len(order):
        problems.append(f'U-FIX-1 n1: member rows {len(probe["members"])} vs {len(order)}')
    for cid, row in zip(order, probe['members']):
        metrics = stat['members'][cid]
        values = [fmt_int(metrics[k]) for k in ('mean', 'median', 'p5', 'p95')]
        if [row[2], row[4], row[5], row[6]] != values or row[3] != '미지원':
            problems.append(f'U-FIX-1 n1: member {cid} row {row} vs API {values}')
    # B2-STAT-2
    if [a['status'] for a in comparison_answers] != [400] * len(comparison_answers) or not comparison_answers \
            or any('baseline_required' not in a['body'] for a in comparison_answers):
        problems.append(f'U-FIX-1 no-baseline: comparison answers {comparison_answers}')
    if probe['pill'] != '실제 API 응답' or '미연결' in probe['text'] or not probe['noBaseline'] or probe['errors']:
        problems.append(f'U-FIX-1 no-baseline: pill={probe["pill"]!r} noBaseline={probe["noBaseline"]} errors={probe["errors"]}')
    await page.locator('#stats-content').screenshot(path=str(out / 'desktop-stats-n1-fixed.png'))

    # n>=2: the interval is supplied and shown.
    await page.locator('#compute-runs').fill('2')
    async with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/compute/experiments'), timeout=240000) as pending:
        await page.locator('#compute-start').click()
    created = await (await pending.value).json()
    for _ in range(900):
        _, status = api.call('compute/experiments/' + created['id'])
        if status['state'] in ('completed', 'failed', 'cancelled'):
            break
        time.sleep(.2)
    _, stat2 = api.call(f'compute/experiments/{created["id"]}/statistics')
    try:
        await page.wait_for_function("() => [...document.querySelectorAll('#stats-content .metric-card')].some(c => c.querySelector('span')?.textContent.trim() === '표본 수 n' && c.querySelector('strong')?.textContent.trim() === '2')", timeout=90000)
    except Exception:
        problems.append('U-FIX-1 n2: statistics with n=2 not rendered')
    probe2 = await page.evaluate(STATS_PROBE)
    fix['n2'] = {'state': status['state'], 'api': {k: stat2['team'].get(k) for k in ('n', 'meanCi', 'sampleSd', 'unsupportedReason')},
                 'cards': {k: probe2['cards'].get(k) for k in ('표본 수 n', '평균 CI', '표본 표준편차')}}
    if stat2['team']['n'] != 2 or stat2['team']['meanCi'] is None or stat2['team'].get('unsupportedReason'):
        problems.append(f'U-FIX-1 n2: API {fix["n2"]["api"]}')
    elif probe2['cards'].get('평균 CI') in (None, '미지원', '미확인') or probe2['cards'].get('표본 표준편차') in (None, '미지원', '미확인'):
        problems.append(f'U-FIX-1 n2: CI/SD not shown {fix["n2"]["cards"]}')
    await page.locator('#stats-content').screenshot(path=str(out / 'desktop-stats-n2.png'))

    # Transport failure is still an outage: compute routes are aborted (synthetic network failure), then reload.
    await page.route(base + '/api/compute/**', lambda route: route.abort())
    await page.reload()
    await page.wait_for_function("document.body.dataset.ready==='true'", timeout=90000)
    await page.locator('[data-tab="stats"]').click()
    try:
        await page.wait_for_function("document.querySelector('#stats-content')?.innerText.includes('compute API 미연결')", timeout=30000)
        fix['transportOutage'] = 'compute API 미연결'
    except Exception:
        fix['transportOutage'] = None
        problems.append('U-FIX-1 transport: aborted compute routes not shown as 미연결')
    await page.locator('#stats-content').screenshot(path=str(out / 'desktop-stats-transport-outage.png'))
    await page.unroute(base + '/api/compute/**')


def api_checks(api, problems):
    """Direct API calls documenting the confirmed wire the UI consumes (no browser)."""
    out = {}
    status, v2 = api.call('calculations/hit', {'inputSchemaVersion': 2, 'input': {'statAttack': 100, 'runtimeAttackBuffs': [{'source': 'fixture', 'rate': .145}]}})
    out['v2'] = {'status': status, 'conversion': v2.get('conversion'), 'exactEffectiveAttack': v2.get('exactEffectiveAttack')}
    if status != 200 or not v2['conversion']['converted']:
        problems.append(f'api v2: {status} {v2}')
    status, big = api.call('calculations/hit', {'inputSchemaVersion': 3, 'input': {'statAttack': 0,
        'attackFlatBuffs': [{'source': 'exact', 'exactAmount': '9007199254740993'}]}})
    out['largeExact'] = {'status': status, 'candidates': [(c['policy'], c['status'], c.get('exactDamage'), c.get('errorCode')) for c in big.get('candidates', [])]}
    if status != 200 or big['exactEffectiveAttack'] != '9007199254740993':
        problems.append(f'api large exact: {status}')
    return out, big


async def run(args):
    out = ROOT / 'artifacts/ui/client-f32-live' / f'run-{uuid.uuid4().hex[:12]}'
    data = out / 'data'
    data.mkdir(parents=True)
    source = Path(args.source_data).resolve()
    problems = []
    hashes, snapshot, raw = prepare_data(source, data)
    port = free_port()
    base = f'http://127.0.0.1:{port}'
    env = dict(os.environ, NIKKE_DATA_ROOT=str(data), NIKKE_PROJECT_ROOT=str(ROOT), NIKKE_PORT=str(port), NIKKE_TEST_FIXTURE='1')
    env.pop('NIKKE_GAME_CATALOG', None)
    summary = {'kind': 'real_local_api_synthetic_account', 'port': port, 'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain', 'apps', 'tests/ui'], cwd=ROOT, text=True).strip()),
               'syntheticHttp': ['/api/bootstrap connection list', '/api/snapshots/*/combat-powers -> {}'], 'source': str(source)}
    api = Api(base)
    log = (out / 'api.log').open('w', encoding='utf-8')
    process = subprocess.Popen([args.dotnet, str(ROOT / 'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')], cwd=ROOT, env=env,
                               stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        for _ in range(300):
            try:
                status, boot = api.call('bootstrap')
                api.token = boot['token']
                break
            except (OSError, urllib.error.URLError):
                if process.poll() is not None:
                    raise RuntimeError('API exited; see api.log')
                time.sleep(.2)
        else:
            raise RuntimeError('API startup timed out')
        status, health = api.call('health')
        summary['health'] = {'projectRoot': health.get('projectRoot')}
        if Path(health.get('projectRoot', '')).resolve() != ROOT:
            problems.append(f'api projectRoot {health.get("projectRoot")}')
        status, _ = api.call(f"accounts/{snapshot['accountId']}/formation", {'slots': IDS}, method='PUT')
        if status != 200:
            problems.append(f'formation PUT {status}')
        summary['api'], _ = api_checks(api, problems)
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            try:
                summary['web'] = await web_checks(browser, base, api, out, problems)
                summary['desktop'] = await desktop_checks(browser, base, api, out, problems)
            finally:
                await browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()
    changed = [name for name, value in hashes.items() if digest(source / name) != value]
    summary['sourceUnchanged'] = not changed
    if changed:
        problems.append(f'source data changed {changed}')
    summary['accepted'] = not problems
    summary['problems'] = problems
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(out), 'accepted': not problems, 'problems': problems}, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dotnet', required=True)
    parser.add_argument('--source-data', required=True, help='Public catalog data directory (read only, hash-checked)')
    raise SystemExit(asyncio.run(run(parser.parse_args())))

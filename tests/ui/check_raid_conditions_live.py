"""F2-U stage 2: R4 (DEF switch) and R8 (boss selection) against a REAL isolated API. Evidence: real_local_api.

Isolation as in check_combat_conditions_live.py: Release Nikke.Api from this worktree, random port (never
5180/5181), NEW dataRoot under artifacts/ui/raid-conditions-live/run-*/data with only the public catalog allowlist
(--source-data), the presentation catalog and icons (--assets, isolated copy), a NEW synthetic account, the runtime
prepared with prepare_combat_conditions.py, and the boss list/images prepared by
tools/data-pipeline/prepare_solo_raid_bosses.py into an isolated cache (--boss-presentation, copied here).
All sources are hash-checked before/after. Original data/local is never used.
Synthetic HTTP: /api/bootstrap connection and /api/snapshots/*/combat-powers {} (presentation only). One scenario
rewrites the OUTGOING replay request to add synthetic 100x attack buff windows (the Backend's own threshold
fixture) so the real engine crosses 2,000,000,000; another sends an explicit conditionProfile "legacy" request the
UI never sends (an older-style record). Responses are always real.
Output: artifacts/ui/raid-conditions-live/run-<id>/ (git-ignored). Exit 1 = NOT accepted.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.error
import uuid

from playwright.async_api import async_playwright

from check_client_f32_live import IDS, Api, digest, free_port, patch_bootstrap, prepare_data

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = [1500, 850, 500]
sys.path.insert(0, str(ROOT / 'tests/ui'))


def fmt(v):
    return f'{int(v):,}'


async def run_replay(page, rewrite=None):
    if rewrite:
        async def handler(route):
            body = route.request.post_data_json
            rewrite(body)
            await route.continue_(post_data=json.dumps(body))
        await page.route('**/api/runtime/skill-replays', handler)
    async with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/runtime/skill-replays'), timeout=300000) as pending:
        await page.locator('#run-replay').click()
    response = await pending.value
    body = await response.json()
    request = json.loads(response.request.post_data)
    if rewrite:
        await page.unroute('**/api/runtime/skill-replays')
    await page.wait_for_selector('#replay-result [data-saved-combat]', timeout=60000)
    await page.wait_for_timeout(300)
    lines = await page.evaluate("""() => ({ saved: document.querySelector('#replay-result [data-saved-combat]')?.textContent.trim() ?? null,
      defense: document.querySelector('#replay-result [data-defense-result]')?.textContent.trim() ?? null })""")
    return response.status, request, body, lines


def expected_defense(defense, names):
    hit = defense.get('switchAfterHit')
    if defense.get('mode') == 'fixed':
        return f"방어력 {fmt(defense['initialDefense'])} 고정"
    if not hit:
        return f"방어력 전환 없음 · 끝까지 {fmt(defense['finalDefense'])} (누적 피해 20억 이하)"
    seconds = round(hit['frame'] / 60 * 100) / 100
    sec = f'{seconds:,.2f}'.rstrip('0').rstrip('.')
    return (f"방어력 {fmt(hit['previousDefense'])} → {fmt(hit['newDefense'])} · {sec}초({fmt(hit['frame'])}프레임) "
            f"{names.get(str(hit['characterId']), '니케')} 타격 후 전환 · 누적 {fmt(hit['cumulativeDamage'])}")


async def run(args):
    out = ROOT / 'artifacts/ui/raid-conditions-live' / f'run-{uuid.uuid4().hex[:12]}'
    data = out / 'data'
    data.mkdir(parents=True)
    source, roster, assets, bosses_src = (Path(args.source_data).resolve(), Path(args.source_roster).resolve(),
                                          Path(args.assets).resolve(), Path(args.boss_presentation).resolve())
    problems = []
    summary = {'kind': 'real_local_api_synthetic_account', 'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain', 'apps', 'tests/ui'], cwd=ROOT, text=True).strip()),
               'syntheticHttp': ['/api/bootstrap connection list', '/api/snapshots/*/combat-powers -> {}',
                                 'switch scenario: outgoing request + synthetic attackBuffWindows (100x)', 'legacy scenario: outgoing request conditionProfile legacy']}
    hashes, snapshot, _ = prepare_data(source, data)
    extra = {str(roster): digest(roster)}
    (data / 'presentation/assets/ui').mkdir(parents=True)
    presentation_src = assets.parent.parent / 'presentation.json'
    extra[str(presentation_src)] = digest(presentation_src)
    shutil.copyfile(presentation_src, data / 'presentation/presentation.json')
    names = {str(c['characterUid']): c['displayName'] for c in json.loads(presentation_src.read_text(encoding='utf-8-sig'))['characters']}
    for icon in sorted(list(assets.glob('code-*.png')) + list(assets.glob('weapon-*.png'))):
        extra[str(icon)] = digest(icon)
        shutil.copyfile(icon, data / 'presentation/assets/ui' / icon.name)
    for item in bosses_src.rglob('*'):
        if item.is_file():
            extra[str(item)] = digest(item)
            target = data / 'presentation' / item.relative_to(bosses_src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, target)
    prep = subprocess.run([sys.executable, str(ROOT / 'tools/data-pipeline/prepare_combat_conditions.py'), '--runtime-root', str(data / 'runtime'),
                           '--source-roster', str(roster)], cwd=ROOT, capture_output=True, text=True)
    if prep.returncode:
        raise RuntimeError(prep.stderr)
    port = free_port()
    base = f'http://127.0.0.1:{port}'
    summary['port'] = port
    env = dict(os.environ, NIKKE_DATA_ROOT=str(data), NIKKE_PROJECT_ROOT=str(ROOT), NIKKE_PORT=str(port), NIKKE_TEST_FIXTURE='1')
    env.pop('NIKKE_GAME_CATALOG', None)
    api = Api(base)
    log = (out / 'api.log').open('w', encoding='utf-8')
    process = subprocess.Popen([args.dotnet, str(ROOT / 'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')], cwd=ROOT, env=env,
                               stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        for _ in range(300):
            try:
                _, boot = api.call('bootstrap'); api.token = boot['token']; break
            except (OSError, urllib.error.URLError):
                if process.poll() is not None:
                    raise RuntimeError('API exited; see api.log')
                time.sleep(.2)
        api.call(f"accounts/{snapshot['accountId']}/formation", {'slots': IDS}, method='PUT')
        _, catalog = api.call('presentation/solo-raid-bosses')
        (out / 'api-bosses.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
        summary['bossCatalog'] = {'defaultBossId': catalog['defaultBossId'], 'bosses': [[b['id'], b['name'], b['season'], bool(b['imageUrl'])] for b in catalog['bosses']],
                                  'diagnostics': len(catalog['diagnostics']), 'complete': catalog['complete']}
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page(viewport={'width': 1500, 'height': 1000})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            await patch_bootstrap(page, base)
            await page.goto(base + '/editor/')
            await page.wait_for_function("document.body.dataset.ready==='true'", timeout=90000)
            await page.locator('[data-tab="raid"]').click()
            await page.wait_for_function("document.querySelector('#raid-boss [data-boss-open]')?.innerText.length > 0")
            await page.wait_for_timeout(500)
            form = await page.evaluate("""() => { const f = document.querySelector('#replay-form');
              return { names: [...f.elements].map(e => e.name).filter(Boolean), note: f.querySelector('[data-conditions-note]')?.textContent,
                boss: f.querySelector('[data-boss-open]')?.innerText.replace(/\\s+/g, ' ').trim(),
                notice: f.querySelector('[data-boss-notice]')?.textContent.trim() ?? null, text: f.innerText }; }""")
            summary['form'] = {k: form[k] for k in ('names', 'note', 'boss', 'notice')}
            default = next(b for b in catalog['bosses'] if b['id'] == catalog['defaultBossId'])
            if any(n in form['names'] for n in ('seconds', 'pellet', 'defense')) or default['name'] not in (form['boss'] or ''):
                problems.append(f'form {summary["form"]}')
            if '자동 전환됩니다' not in (form['note'] or ''):
                problems.append('R4 note')
            # The readiness notice appears only when the API reports excluded bosses (diagnostics).
            want_notice = '일부 보스 이름 준비 중' if catalog['diagnostics'] else None
            if form['notice'] != want_notice:
                problems.append(f'boss notice {form["notice"]!r} (diagnostics {len(catalog["diagnostics"])})')
            if args.expect_bosses and (len(catalog['bosses']) != args.expect_bosses or catalog['diagnostics'] or not catalog['complete']):
                problems.append(f'boss catalog {len(catalog["bosses"])} bosses, {len(catalog["diagnostics"])} excluded, complete={catalog["complete"]}')
            if '한국어 이름 원천' in form['text']:
                problems.append('raw diagnostic text shown')

            # Boss dialog = API list (Korean names), real images, nothing from diagnostics.
            await page.locator('[data-boss-open]').click()
            await page.wait_for_selector('dialog.boss-dialog[open] [data-boss-id]')
            await page.wait_for_timeout(800)
            cards = await page.evaluate("""() => [...document.querySelectorAll('dialog.boss-dialog [data-boss-id]')].map(b => ({ id: b.dataset.bossId,
              name: b.querySelector('strong')?.textContent.trim(), img: b.querySelector('.boss-pick-image') ? b.querySelector('.boss-pick-image').naturalWidth : null }))""")
            summary['bossCards'] = cards
            if sorted(c['id'] for c in cards) != sorted(b['id'] for b in catalog['bosses']) or cards[0]['id'] != catalog['defaultBossId']:
                problems.append('boss cards differ from API list')
            for c in cards:
                api_row = next(b for b in catalog['bosses'] if b['id'] == c['id'])
                if c['name'] != api_row['name'] or (api_row['imageUrl'] and not c['img']):
                    problems.append(f'boss card {c} vs API {api_row["name"]}')
            for width in WIDTHS:
                await page.set_viewport_size({'width': width, 'height': 900})
                await page.wait_for_timeout(200)
                await page.screenshot(path=str(out / f'boss-dialog-{width}.png'))
                if await page.evaluate("document.documentElement.scrollWidth - innerWidth") > 0:
                    problems.append(f'boss dialog overflow @{width}')
            await page.set_viewport_size({'width': 1500, 'height': 1000})
            chosen = next(b for b in catalog['bosses'] if b['id'] != catalog['defaultBossId'] and b['imageUrl'])
            await page.locator(f'dialog.boss-dialog [data-boss-id="{chosen["id"]}"]').click()

            # 1) Plain new replay: defaults (no DEF/profile fields), bossId, real battleConditions/boss/defense shown.
            status, request, body, lines = await run_replay(page)
            combat = request['conditions']['combat']
            summary['replayDefault'] = {'status': status, 'bossId': request.get('bossId'), 'conditionProfile': request.get('conditionProfile', '<absent>'),
                                        'combat': {k: combat.get(k, '<absent>') for k in ('durationFrames', 'pelletCoefficientPolicy', 'critMode', 'enemyDefense', 'defenseMode')},
                                        'battleConditions': body.get('battleConditions'), 'boss': body.get('boss'), 'defense': body.get('result', {}).get('defense'), 'lines': lines}
            if status != 200 or request.get('bossId') != chosen['id'] or 'conditionProfile' in request or any(k in combat for k in ('enemyDefense', 'defenseMode')):
                problems.append(f'default replay request {summary["replayDefault"]}')
            else:
                bc = body['battleConditions']
                if body.get('boss', {}).get('name') != chosen['name'] or bc.get('defenseMode') != 'team_damage_threshold':
                    problems.append('default replay saved boss/battleConditions')
                if not lines['saved'] or not lines['saved'].startswith(f"180초 · {bc['label']} ({fmt(bc['initialDefense'])} → {fmt(bc['switchedDefense'])})") \
                        or f"보스 {chosen['name']}" not in lines['saved']:
                    problems.append(f'saved line {lines["saved"]!r}')
                if lines['defense'] != expected_defense(body['result']['defense'], names):
                    problems.append(f'defense line {lines["defense"]!r} vs {expected_defense(body["result"]["defense"], names)!r}')
            await page.locator('#replay-result').screenshot(path=str(out / 'result-default.png'))

            # U-FIX-4 (F2-Q-2): the audit panel names the attack sources; the saved record is not recalculated or rewritten.
            import hashlib, re
            _, stored_before = api.call('runtime/skill-replays/' + body['id'])
            entry = next((e for e in body['result']['damageLog']['entries']
                          if any(str(b.get('source', '')).startswith('overload:') for b in (e.get('hit') or {}).get('attackBuffs', []))), None)
            if entry is None:
                problems.append('no hit with an overload attack source in the synthetic replay')
            else:
                await page.wait_for_selector(f".graph-hit-dot[data-hit-id=\"{entry['hitId']}\"]", state='attached', timeout=60000)
                await page.evaluate("id => document.querySelector(`.graph-hit-dot[data-hit-id=\"${id}\"]`).dispatchEvent(new MouseEvent('click'))", entry['hitId'])
                await page.wait_for_selector('.damage-audit-panel', timeout=15000)
                panel = await page.locator('.damage-audit-panel').inner_text()
                lines = await page.evaluate("() => [...document.querySelectorAll('.damage-audit-panel [data-audit-group=\"attack\"] li')].map(li => li.textContent.replace(/\\s+/g, ' ').trim())")
                raw = re.findall(r'overload:|cube:|collection:|skill:\d|function:|StatAtk|native_|basis |\b50\d\d\b', panel)
                src = next(b['source'] for b in entry['hit']['attackBuffs'] if b['source'].startswith('overload:'))
                parts = src.split(':')
                want = f"{names.get(parts[1], '이름 미확인')} · {({'head': '머리', 'torso': '몸통', 'arm': '팔', 'leg': '다리'})[parts[2]]} {parts[3]}번 줄 · {'공격력' if parts[4] == 'StatAtk' else parts[4]}"
                summary['auditSources'] = {'hitId': entry['hitId'], 'source': src, 'lines': lines, 'raw': raw}
                if not any(want in line for line in lines) or raw:
                    problems.append(f'audit sources {lines} raw {raw[:5]} expected {want!r}')
                for width in WIDTHS:
                    await page.set_viewport_size({'width': width, 'height': 1000})
                    await page.wait_for_timeout(150)
                    if await page.evaluate("document.documentElement.scrollWidth - innerWidth") > 0:
                        problems.append(f'audit panel overflow @{width}')
                    await page.locator('.damage-audit-panel').screenshot(path=str(out / f'audit-sources-{width}.png'))
                await page.set_viewport_size({'width': 1500, 'height': 1000})
            _, stored_after = api.call('runtime/skill-replays/' + body['id'])
            digest_of = lambda v: hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            summary['storedReplayUnchanged'] = digest_of(stored_before) == digest_of(stored_after) and stored_after['result']['totalDamage'] == body['result']['totalDamage']
            if not summary['storedReplayUnchanged']:
                problems.append('stored replay changed after viewing the audit panel')

            # 2) Real switch: synthetic 100x attack windows added to the outgoing request (Backend threshold fixture).
            def boost(body):
                body['conditions']['combat']['attackBuffWindows'] = [{'characterId': cid, 'buff': {'source': 'synthetic_f2u_threshold', 'rate': 100, 'stacks': 1},
                                                                      'startFrame': 1, 'endFrame': 10801} for cid in body['characterIds']]
            status, request, body, lines = await run_replay(page, boost)
            defense = body.get('result', {}).get('defense') or {}
            summary['replaySwitch'] = {'status': status, 'defense': defense, 'lines': lines}
            if status != 200 or not defense.get('switchAfterHit') or defense.get('finalDefense') != 31784:
                problems.append(f'switch replay {status} {defense}')
            elif lines['defense'] != expected_defense(defense, names):
                problems.append(f'switch line {lines["defense"]!r} vs {expected_defense(defense, names)!r}')
            for width in WIDTHS:
                await page.set_viewport_size({'width': width, 'height': 900})
                await page.wait_for_timeout(150)
                if await page.evaluate("document.documentElement.scrollWidth - innerWidth") > 0:
                    problems.append(f'result overflow @{width}')
                await page.locator('#replay-result').screenshot(path=str(out / f'result-switch-{width}.png'))
            await page.set_viewport_size({'width': 1500, 'height': 1000})

            # 3) Older-style record (explicit legacy profile, fixed DEF 31784, 120 s, per_pellet): shown as stored.
            def legacy(body):
                body['conditionProfile'] = 'legacy'
                body['conditions']['combat'].update({'durationFrames': 7200, 'pelletCoefficientPolicy': 'per_pellet', 'enemyDefense': 31784, 'defenseMode': 'fixed'})
            status, request, body, lines = await run_replay(page, legacy)
            summary['replayLegacy'] = {'status': status, 'battleConditions': body.get('battleConditions'), 'defense': body.get('result', {}).get('defense'), 'lines': lines}
            if status != 200 or (body.get('battleConditions') or {}).get('profile') != 'legacy' \
                    or not (lines['saved'] or '').startswith(f"120초 · {body['battleConditions']['label']} · 방어력 31,784") \
                    or lines['defense'] != '방어력 31,784 고정':
                problems.append(f'legacy display {summary["replayLegacy"]}')
            _, endpoint = api.call(f"runtime/skill-replays/{body['id']}/battle-conditions")
            summary['replayLegacy']['endpoint'] = endpoint

            # 4) Statistics: bossId stored, battle conditions card.
            await page.locator('[data-tab="stats"]').click()
            await page.wait_for_selector('#compute-start')
            await page.locator('#compute-runs').fill('1')
            async with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/compute/experiments'), timeout=300000) as pending:
                await page.locator('#compute-start').click()
            response = await pending.value
            created = await response.json()
            exp_request = json.loads(response.request.post_data)
            final = None
            for _ in range(1500):
                _, final = api.call('compute/experiments/' + created['id'])
                if final['state'] in ('completed', 'failed', 'cancelled'):
                    break
                time.sleep(.2)
            try:
                await page.wait_for_function("[...document.querySelectorAll('#stats-content .metric-card')].some(c => c.querySelector('span')?.textContent.trim() === '전투 조건')", timeout=60000)
            except Exception:
                pass
            card = await page.evaluate("() => { const c = [...document.querySelectorAll('#stats-content .metric-card')].find(c => c.querySelector('span')?.textContent.trim() === '전투 조건'); return c ? c.querySelector('strong').textContent.trim() : null; }")
            summary['statistics'] = {'status': response.status, 'bossId': exp_request.get('bossId'), 'state': final['state'], 'inputBoss': final['input'].get('boss'),
                                     'battleConditions': final['input'].get('battleConditions'), 'defPolicy': final['input'].get('defPolicy'), 'card': card}
            if response.status != 202 or exp_request.get('bossId') != chosen['id'] or final['state'] != 'completed' \
                    or (final['input'].get('boss') or {}).get('name') != chosen['name'] or not card or f"보스 {chosen['name']}" not in card \
                    or final['input']['battleConditions']['label'] not in card:
                problems.append(f'statistics {summary["statistics"]}')
            for width in WIDTHS:
                await page.set_viewport_size({'width': width, 'height': 1000})
                await page.wait_for_timeout(150)
                if await page.evaluate("document.documentElement.scrollWidth - innerWidth") > 0:
                    problems.append(f'stats overflow @{width}')
            await page.locator('#stats-content').screenshot(path=str(out / 'stats.png'))
            # 5) U-FIX-3 / F2-Q-1: DEF policy card for no switch (above), a real switch and an old fixed-DEF experiment.
            async def stats_card():
                return await page.evaluate("""() => { const c = [...document.querySelectorAll('#stats-content .metric-card')].find(c => c.querySelector('span')?.textContent.trim() === 'DEF 정책');
                  return c ? [c.querySelector('strong').textContent.trim(), c.querySelector('small')?.textContent.trim() ?? ''] : null; }""")

            async def run_experiment(rewrite, label):
                if rewrite:
                    async def handler(route):
                        body = route.request.post_data_json
                        rewrite(body)
                        await route.continue_(post_data=json.dumps(body))
                    await page.route('**/api/compute/experiments', handler)
                async with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/compute/experiments'), timeout=300000) as pending:
                    await page.locator('#compute-start').click()
                created = await (await pending.value).json()
                if rewrite:
                    await page.unroute('**/api/compute/experiments')
                for _ in range(1500):
                    _, done = api.call('compute/experiments/' + created['id'])
                    if done['state'] in ('completed', 'failed', 'cancelled'):
                        break
                    time.sleep(.2)
                _, results = api.call(f"compute/experiments/{created['id']}/results?offset=0&limit=1000")
                defense = [r.get('defense') for r in results.get('runs', [])]
                try:
                    await page.wait_for_function("id => document.querySelector('#stats-content')?.innerText.includes(id)", arg=created['id'], timeout=60000)
                except Exception:
                    pass
                await page.wait_for_timeout(1500)
                card = await stats_card()
                await page.locator('#stats-content').screenshot(path=str(out / f'stats-def-{label}.png'))
                return done, defense, card

            no_switch_card = await stats_card()
            _, results0 = api.call(f"compute/experiments/{created['id']}/results?offset=0&limit=1000")
            defense0 = [r.get('defense') for r in results0.get('runs', [])]
            want0 = ('자동 전환 (30,925 → 31,784)', '전환 없음 · 1회 모두 누적 20억 이하') if defense0 and not defense0[0].get('switchAfterHit') else None
            summary['defCardNoSwitch'] = {'card': no_switch_card, 'defense': defense0}
            if not want0 or tuple(no_switch_card or ()) != want0:
                problems.append(f'DEF card (no switch) {no_switch_card} expected {want0}')

            def boost(body):
                body['conditions']['combat']['attackBuffWindows'] = [{'characterId': cid, 'buff': {'source': 'synthetic_f2u_threshold', 'rate': 100, 'stacks': 1},
                                                                      'startFrame': 1, 'endFrame': 10801} for cid in body['characterIds']]
            done, defense1, card1 = await run_experiment(boost, 'switch')
            summary['defCardSwitch'] = {'state': done['state'], 'card': card1, 'defense': defense1}
            hit = (defense1[0] or {}).get('switchAfterHit') if defense1 else None
            if done['state'] != 'completed' or not hit:
                problems.append(f'switch experiment {done["state"]} {defense1}')
            else:
                sec = f"{round(hit['frame'] / 60 * 100) / 100:,.2f}".rstrip('0').rstrip('.')
                want1 = ('자동 전환 (30,925 → 31,784)', f"방어력 30,925 → 31,784 · {sec}초({hit['frame']:,}프레임) {names.get(str(hit['characterId']), '니케')} 타격 후 전환 · 누적 {hit['cumulativeDamage']:,}")
                if tuple(card1 or ()) != want1:
                    problems.append(f'DEF card (switch) {card1} expected {want1}')

            def legacy_exp(body):
                body['conditionProfile'] = 'legacy'
                body['conditions']['combat'].update({'enemyDefense': 31784, 'defenseMode': 'fixed'})
            done, defense2, card2 = await run_experiment(legacy_exp, 'legacy')
            summary['defCardLegacy'] = {'state': done['state'], 'defPolicy': done['input'].get('defPolicy'), 'card': card2, 'defense': defense2}
            if done['state'] != 'completed' or tuple(card2 or ()) != ('이전 방식 · 방어력 31,784 고정', f"{done['input']['battleConditions']['label']} · 누적 대미지에 따른 전환 없음(당시 조건)"):
                problems.append(f'DEF card (legacy) {card2}')
            for card in (no_switch_card, card1, card2):
                if card and '자동 20억 전환 없음' in ' '.join(card) and card is not card2:
                    problems.append('old fixed DEF wording on an automatic experiment')

            # U-FIX-3: no character codes in visible text of the raid and statistics screens.
            import re
            code = re.compile(r'#\s?50\d\d|\b50\d\d\b')
            stats_text = await page.locator('#stats-content').inner_text()
            await page.locator('[data-tab="raid"]').click()
            raid_text = await page.locator('#raid-content').inner_text()
            leaks = [m for m in code.findall(stats_text + '\n' + raid_text)]
            summary['codeLeaks'] = leaks
            if leaks:
                problems.append(f'character codes visible: {leaks[:5]}')
            summary['pageErrors'] = errors
            if errors:
                problems.append(f'page errors {errors}')
            await browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()
    changed = [n for n, v in hashes.items() if digest(source / n) != v] + [n for n, v in extra.items() if digest(Path(n)) != v]
    summary['sourceUnchanged'] = not changed
    if changed:
        problems.append(f'source changed {changed}')
    summary['problems'] = problems
    summary['accepted'] = not problems
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(out), 'accepted': not problems, 'problems': problems}, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dotnet', required=True)
    parser.add_argument('--source-data', required=True)
    parser.add_argument('--source-roster', required=True)
    parser.add_argument('--assets', required=True)
    parser.add_argument('--boss-presentation', required=True, help='presentation root prepared by prepare_solo_raid_bosses.py in an isolated place')
    parser.add_argument('--expect-bosses', type=int, default=0, help='expected list size incl. the dummy (e.g. 43 = dummy + seasons 1-42)')
    raise SystemExit(asyncio.run(run(parser.parse_args())))

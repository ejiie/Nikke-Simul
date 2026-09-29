"""F-COND-U stage B: boss distance / weak element UI against a REAL isolated local API. Evidence: real_local_api.

Isolation (same as check_client_f32_live.py): Release Nikke.Api from this worktree, random port (never 5180/5181),
a NEW dataRoot under artifacts/ui/combat-conditions-live/run-*/data holding only the public catalog allowlist
copied from --source-data and a NEW synthetic account. The runtime is extended with combat profiles by
tools/data-pipeline/prepare_combat_conditions.py (--source-roster, public roster, hash-pinned) inside that dataRoot
only. Element icons are copied from --assets (isolated copy). All sources are hash-checked before/after.
Synthetic HTTP is limited to presentation: /api/bootstrap gets a synthetic ready connection and
/api/snapshots/*/combat-powers answers {} (no raw manifest in the synthetic snapshot). Scenario 5 rewrites the
OUTGOING replay request to the old deck-wide bools (the response stays real) because the UI no longer sends them.
Output: artifacts/ui/combat-conditions-live/run-<id>/ (git-ignored). Exit 1 means NOT accepted.
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
ELEMENT_CODE = {'Fire': 'fire', 'Water': 'water', 'Wind': 'wind', 'Iron': 'iron', 'Electronic': 'electric'}
DIALOG = """() => { const d = document.querySelector('dialog.cond-dialog');
  if (!d || !d.open) return { open: false };
  const r = d.getBoundingClientRect();
  return { open: true, text: d.innerText, rect: { left: r.left, right: r.right }, viewport: innerWidth,
    members: [...d.querySelectorAll('[data-member]')].map(li => [li.dataset.member, li.dataset.distanceKind, li.querySelector('em').textContent]),
    weapons: [...d.querySelectorAll('[data-weapon]')].map(tr => [tr.dataset.weapon, ...[...tr.cells].slice(1).map(c => c.textContent.trim())]),
    elements: [...d.querySelectorAll('[data-cond-element]')].map(b => ({ code: b.dataset.condElement, img: b.querySelector('img')?.naturalWidth ?? null,
      members: b.querySelector('.cond-element-members')?.textContent.trim() })),
    overflow: document.documentElement.scrollWidth - innerWidth }; }"""
SUMMARY = "() => [...document.querySelectorAll('[data-cond-value]')].map(e => e.textContent.trim())"


def expected_kind(profile, distance):
    if profile['rangeBonusAvailable'] is False or (profile['bonusRangeMin'] == 0 and profile['bonusRangeMax'] == 0):
        return 'no_bonus'
    if distance is None:
        return 'unset'
    return 'in' if profile['bonusRangeMin'] <= distance <= profile['bonusRangeMax'] else 'out'


def typical_text(row):
    typical = next((r for r in row['ranges'] if r['isTypical']), None)
    if row['rangeBonusAvailable'] is False or (typical and typical['min'] == 0 and typical['max'] == 0):
        return '0–0 · 보너스 없음'
    return f"{typical['min']}–{typical['max']}" if typical else '미확인'


async def open_dialog(page, kind):
    await page.locator(f'[data-cond-open="{kind}"]').click()
    selector = '[data-weapon]' if kind == 'distance' else '[data-cond-element] img'
    await page.wait_for_function(f"document.querySelector('dialog.cond-dialog')?.open && document.querySelectorAll('{selector}').length >= 5")
    await page.wait_for_timeout(200)


async def run_replay(page, rewrite_legacy=False):
    if rewrite_legacy:
        async def legacy(route):
            body = route.request.post_data_json
            combat = body['conditions']['combat']
            combat.pop('bossDistance', None); combat.pop('bossWeakElement', None)
            combat.update({'properDistance': True, 'elementAdvantage': False})
            await route.continue_(post_data=json.dumps(body))
        await page.route('**/api/runtime/skill-replays', legacy)
    async with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/runtime/skill-replays'), timeout=240000) as pending:
        await page.locator('#run-replay').click()
    response = await pending.value
    body = await response.json()
    request = json.loads(response.request.post_data)
    if rewrite_legacy:
        await page.unroute('**/api/runtime/skill-replays')
    await page.wait_for_selector('#replay-result [data-cond-mode]', timeout=60000)
    line = await page.locator('#replay-result [data-cond-mode]').evaluate('e => ({ mode: e.dataset.condMode, text: e.textContent.trim() })')
    return response.status, request, body, line


async def run(args):
    out = ROOT / 'artifacts/ui/combat-conditions-live' / f'run-{uuid.uuid4().hex[:12]}'
    data = out / 'data'
    data.mkdir(parents=True)
    source, roster, assets = Path(args.source_data).resolve(), Path(args.source_roster).resolve(), Path(args.assets).resolve()
    problems, summary = [], {'kind': 'real_local_api_synthetic_account', 'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain', 'apps', 'tests/ui'], cwd=ROOT, text=True).strip()),
        'syntheticHttp': ['/api/bootstrap connection list', '/api/snapshots/*/combat-powers -> {}', 'scenario legacy: outgoing request rewritten to old bools']}
    hashes, snapshot, _ = prepare_data(source, data)
    extra_sources = {str(roster): digest(roster)}
    (data / 'presentation/assets/ui').mkdir(parents=True)
    # Presentation catalog (Korean names, weapon icons) from the same isolated copy as the icons, read only.
    presentation_src = assets.parent.parent / 'presentation.json'
    extra_sources[str(presentation_src)] = digest(presentation_src)
    shutil.copyfile(presentation_src, data / 'presentation/presentation.json')
    korean_names = {str(c['characterUid']): c['displayName'] for c in json.loads(presentation_src.read_text(encoding='utf-8-sig'))['characters']}
    for icon in sorted(list(assets.glob('code-*.png')) + list(assets.glob('weapon-*.png'))):
        extra_sources[str(icon)] = digest(icon)
        shutil.copyfile(icon, data / 'presentation/assets/ui' / icon.name)
    prep = subprocess.run([sys.executable, str(ROOT / 'tools/data-pipeline/prepare_combat_conditions.py'), '--runtime-root', str(data / 'runtime'),
                           '--source-roster', str(roster)], cwd=ROOT, capture_output=True, text=True)
    (out / 'prepare.log').write_text(prep.stdout + prep.stderr, encoding='utf-8')
    if prep.returncode:
        raise RuntimeError('prepare_combat_conditions failed; see prepare.log')
    summary['runtimeId'] = json.loads((data / 'runtime/current.json').read_text(encoding='utf-8-sig'))['id']
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
        _, health = api.call('health')
        summary['projectRoot'] = health.get('projectRoot')
        if Path(health.get('projectRoot', '')).resolve() != ROOT:
            problems.append(f'projectRoot {health.get("projectRoot")}')
        api.call(f"accounts/{snapshot['accountId']}/formation", {'slots': IDS}, method='PUT')
        status, catalog = api.call('runtime/combat-conditions')
        status_m, members = api.call(f"snapshots/{snapshot['id']}/combat-conditions?characterIds={','.join(IDS)}")
        (out / 'api-catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
        (out / 'api-members.json').write_text(json.dumps(members, ensure_ascii=False, indent=2), encoding='utf-8')
        if status != 200 or status_m != 200:
            raise RuntimeError(f'combat-conditions API {status}/{status_m}: {catalog} {members}')
        profiles = {m['characterId']: m for m in members['members']}
        summary['profiles'] = {k: [v['weaponType'], v['bonusRangeMin'], v['bonusRangeMax'], v['element']] for k, v in profiles.items()}
        # Contract refusal the UI never sends: mixed new + old fields.
        mixed_status, mixed = api.call('runtime/skill-replays', {'snapshotId': snapshot['id'], 'characterIds': IDS, 'scenarioLevel': 400,
            'conditions': {'combat': {'durationFrames': 60, 'enemyDefense': 30925, 'bossDistance': 35, 'bossWeakElement': None, 'properDistance': False}}})
        summary['mixedRequest'] = {'status': mixed_status, 'message': mixed.get('message')}
        if mixed_status != 400 or 'boss_conditions_mixed_with_legacy' not in (mixed.get('message') or ''):
            problems.append(f'mixed request not refused {summary["mixedRequest"]}')

        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page(viewport={'width': 1500, 'height': 1000})
            errors, traffic = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('response', lambda r: traffic.append([r.status, r.request.method, r.url.split(base)[-1]]) if '/combat-conditions' in r.url or 'condition-compatibility' in r.url else None)
            await patch_bootstrap(page, base)
            await page.goto(base + '/editor/')
            await page.wait_for_function("document.body.dataset.ready==='true'", timeout=90000)
            await page.locator('[data-tab="raid"]').click()
            names = await page.evaluate("() => [...document.querySelector('#replay-form').elements].map(e => e.name).filter(Boolean)")
            if 'distance' in names or 'element' in names:
                problems.append('old checkboxes still in the form')

            distance = 35
            await open_dialog(page, 'distance')
            await page.locator('dialog [name="distance"]').fill(str(distance))
            d = await page.evaluate(DIALOG)
            summary['distanceDialog'] = {'members': d['members'], 'weapons': d['weapons']}
            want_members = [[cid, expected_kind(profiles[cid], distance)] for cid in IDS]
            if [m[:2] for m in d['members']] != want_members:
                problems.append(f'member preview {d["members"]} vs API {want_members}')
            want_weapons = {row['weaponType']: [typical_text(row), str(row['characterCount'])] for row in catalog['weaponRanges']}
            for row in d['weapons']:
                if want_weapons.get(row[0]) != row[1:3]:
                    problems.append(f'weapon row {row} vs API {want_weapons.get(row[0])}')
            if len(d['weapons']) != len(catalog['weaponRanges']):
                problems.append('weapon row count')
            exceptions = [x for row in catalog['weaponRanges'] for x in row['exceptions']]
            # R2: exception characters by Korean display name (presentation catalog), never by code.
            for x in exceptions:
                korean = korean_names.get(x['characterId'])
                if not korean or f"{korean}: {x['bonusRangeMin']}–{x['bonusRangeMax']}" not in d['text'] or f"#{x['characterId']}" in d['text']:
                    problems.append(f'exception {x["characterId"]} not shown by Korean name ({korean})')
            summary['exceptions'] = [[x['characterId'], x['name'], x['bonusRangeMin'], x['bonusRangeMax']] for x in exceptions]
            for width in WIDTHS:
                await page.set_viewport_size({'width': width, 'height': 900})
                await page.wait_for_timeout(150)
                probe = await page.evaluate(DIALOG)
                await page.screenshot(path=str(out / f'distance-dialog-{width}.png'))
                if probe['overflow'] > 0 or probe['rect']['left'] < 0 or probe['rect']['right'] > probe['viewport'] + .5:
                    problems.append(f'distance dialog @{width} outside viewport')
            await page.set_viewport_size({'width': 1500, 'height': 1000})
            await page.locator('dialog button[value="apply"]').click()

            weak = profiles['5004']['element']
            await open_dialog(page, 'element')
            e = await page.evaluate(DIALOG)
            summary['elementDialog'] = e['elements']
            if any(x['code'] and not x['img'] for x in e['elements']):
                problems.append(f'element icons not loaded {e["elements"]}')
            for code, wire in ((v, k) for k, v in ELEMENT_CODE.items()):
                owners = [cid for cid in IDS if profiles[cid]['element'] == wire]
                shown = next(x['members'] for x in e['elements'] if x['code'] == code)
                if bool(owners) == ('덱에 없음' in shown):
                    problems.append(f'element {code} members {shown} vs API owners {owners}')
            for width in WIDTHS:
                await page.set_viewport_size({'width': width, 'height': 900})
                await page.wait_for_timeout(150)
                await page.screenshot(path=str(out / f'element-dialog-{width}.png'))
                probe = await page.evaluate(DIALOG)
                if probe['overflow'] > 0 or probe['rect']['right'] > probe['viewport'] + .5:
                    problems.append(f'element dialog @{width} outside viewport')
            await page.set_viewport_size({'width': 1500, 'height': 1000})
            await page.locator(f'[data-cond-element="{ELEMENT_CODE[weak]}"]').click()
            summary['controls'] = await page.evaluate(SUMMARY)

            # 1) New mode with values: request fields, real saved compatibility, per-member engine flags (target 5004).
            status, request, body, line = await run_replay(page)
            combat = request['conditions']['combat']
            summary['replayNew'] = {'status': status, 'combat': {k: combat.get(k, '<absent>') for k in ('bossDistance', 'bossWeakElement', 'properDistance', 'elementAdvantage')},
                                    'compatibility': body.get('conditionCompatibility'), 'line': line}
            if status != 200 or combat.get('bossDistance') != distance or combat.get('bossWeakElement') != weak or 'properDistance' in combat or 'elementAdvantage' in combat:
                problems.append(f'new replay request/status {summary["replayNew"]}')
            elif (body.get('conditionCompatibility') or {}).get('mode') != 'per_member' or line['mode'] != 'per_member' \
                    or not line['text'].startswith(body['conditionCompatibility']['label']):
                problems.append(f'new replay mode display {line} vs {body.get("conditionCompatibility")}')
            else:
                target = body['result']['damageLog']['characterId']
                normals = [x for x in body['result']['damageLog']['entries'] if x.get('kind') == 2 and x.get('hit')]
                p = profiles[target]
                want = (expected_kind(p, distance) == 'in', p['element'] == weak)
                got = sorted({(x['hit'].get('properDistance'), x['hit'].get('elementAdvantage')) for x in normals})
                summary['replayNew']['engineFlags'] = {'target': target, 'normalHits': len(normals), 'flags': got, 'expected': want}
                if not normals or got != [want]:
                    problems.append(f'engine per-member flags for {target}: {got} expected {want}')
            await page.locator('#replay-result').screenshot(path=str(out / 'result-per-member.png'))

            # 2) All unset: explicit nulls, still the new mode.
            await open_dialog(page, 'distance')
            await page.locator('dialog [data-cond-unset]').click()
            await page.locator('dialog button[value="apply"]').click()
            await open_dialog(page, 'element')
            await page.locator('[data-cond-element=""]').click()
            status, request, body, line = await run_replay(page)
            combat = request['conditions']['combat']
            summary['replayUnset'] = {'status': status, 'combat': {k: combat.get(k, '<absent>') for k in ('bossDistance', 'bossWeakElement', 'properDistance')},
                                      'compatibility': body.get('conditionCompatibility'), 'line': line}
            if status != 200 or 'bossDistance' not in combat or combat['bossDistance'] is not None or combat.get('bossWeakElement', '<absent>') is not None \
                    or 'properDistance' in combat or (body.get('conditionCompatibility') or {}).get('mode') != 'per_member' or line['mode'] != 'per_member':
                problems.append(f'unset replay {summary["replayUnset"]}')

            # 3) Old deck-wide record (outgoing request rewritten; real response): shown as the Backend label, not reinterpreted.
            status, request, body, line = await run_replay(page, rewrite_legacy=True)
            summary['replayLegacy'] = {'status': status, 'compatibility': body.get('conditionCompatibility'), 'line': line}
            if status != 200 or (body.get('conditionCompatibility') or {}).get('mode') != 'legacy_global' or line['mode'] != 'legacy' \
                    or line['text'] != f"{body['conditionCompatibility']['label']} · 적정 거리 적용 · 우월 코드 미적용":
                problems.append(f'legacy display {summary["replayLegacy"]}')
            _, compat = api.call(f"runtime/skill-replays/{body['id']}/condition-compatibility")
            summary['replayLegacy']['endpoint'] = compat
            await page.locator('#replay-result').screenshot(path=str(out / 'result-legacy.png'))

            # 4) Statistics: conditions from the form, stored compatibility shown.
            await open_dialog(page, 'distance')
            await page.locator('dialog [name="distance"]').fill(str(distance))
            await page.locator('dialog button[value="apply"]').click()
            await open_dialog(page, 'element')
            await page.locator(f'[data-cond-element="{ELEMENT_CODE[weak]}"]').click()
            await page.locator('[data-tab="stats"]').click()
            await page.wait_for_selector('#compute-start')
            await page.locator('#compute-runs').fill('1')
            async with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/compute/experiments'), timeout=240000) as pending:
                await page.locator('#compute-start').click()
            response = await pending.value
            created = await response.json()
            request = json.loads(response.request.post_data)
            final = None
            for _ in range(900):
                _, final = api.call('compute/experiments/' + created['id'])
                if final['state'] in ('completed', 'failed', 'cancelled'):
                    break
                time.sleep(.2)
            compat = final['input'].get('conditionCompatibility')
            try:
                await page.wait_for_function("[...document.querySelectorAll('#stats-content .metric-card')].some(c => c.querySelector('span')?.textContent.trim() === '보스 거리·약점' && c.querySelector('small')?.textContent.includes('저장된 실험 조건'))", timeout=60000)
            except Exception:
                pass
            card = await page.evaluate("() => { const c = [...document.querySelectorAll('#stats-content .metric-card')].find(c => c.querySelector('span')?.textContent.trim() === '보스 거리·약점'); return c ? [c.querySelector('strong').textContent.trim(), c.querySelector('small')?.textContent.trim()] : null; }")
            c_combat = request['conditions']['combat']
            summary['statistics'] = {'status': response.status, 'combat': {k: c_combat.get(k, '<absent>') for k in ('bossDistance', 'bossWeakElement', 'properDistance')},
                                     'state': final['state'], 'compatibility': compat, 'card': card, 'summaryVersion': final['input'].get('summaryVersion')}
            if response.status != 202 or c_combat.get('bossDistance') != distance or c_combat.get('bossWeakElement') != weak or 'properDistance' in c_combat:
                problems.append(f'statistics request {summary["statistics"]}')
            elif final['state'] != 'completed' or (compat or {}).get('mode') != 'per_member' or not card or not card[0].startswith(compat['label']) \
                    or '저장된 실험 조건' not in (card[1] or ''):
                problems.append(f'statistics compatibility display {summary["statistics"]}')
            for width in WIDTHS:
                await page.set_viewport_size({'width': width, 'height': 1000})
                await page.wait_for_timeout(150)
                if await page.evaluate('document.documentElement.scrollWidth - innerWidth') > 0:
                    problems.append(f'stats @{width} overflow')
            await page.locator('#stats-content').screenshot(path=str(out / 'stats.png'))
            summary['traffic'] = traffic
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
    changed = [n for n, v in hashes.items() if digest(source / n) != v] + [n for n, v in extra_sources.items() if digest(Path(n)) != v]
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
    parser.add_argument('--source-data', required=True, help='Public catalog data dir (read only)')
    parser.add_argument('--source-roster', required=True, help='Public roster blabla_roledata.json (read only, hash-pinned)')
    parser.add_argument('--assets', required=True, help='Isolated copy of presentation/assets/ui (read only)')
    raise SystemExit(asyncio.run(run(parser.parse_args())))

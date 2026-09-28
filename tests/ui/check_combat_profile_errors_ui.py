"""U-FIX-2: combat profile error diagnostics in the desktop UI against a REAL isolated API. Evidence: real_local_api.

Each case gets its own NEW dataRoot under artifacts/ui/combat-profile-errors/run-*/<case>/data (public catalog
allowlist copied read-only from --source-data, NEW synthetic account). The runtime is prepared with
prepare_combat_conditions.py inside that dataRoot and then deliberately damaged there only, written back as a
hash-valid runtime (write_runtime) so the API reaches the B-FIX-2 semantic checks:
- member_min_missing: combatProfiles.characters.5004.bonusRangeMin removed -> 409 combat_profile_invalid (missing)
- element_null: combatProfiles.characters.5011.element = null -> 409 combat_profile_invalid (null)
- catalog_missing: runtime NOT prepared (no combatProfiles) -> 409 combat_profile_catalog_missing
Synthetic HTTP: /api/bootstrap connection and /api/snapshots/*/combat-powers {} only (as in check_combat_conditions_live.py).
Checks: both dialogs, solo raid result, statistics start error; Korean diagnostic with character/field/reason and the
data-preparation hint; the API stays "connected" (not an outage); 1500/850/500px; no JS errors; sources unchanged.
Output: artifacts/ui/combat-profile-errors/run-<id>/ (git-ignored). Exit 1 means NOT accepted.
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
sys.path.insert(0, str(ROOT / 'tools/data-pipeline'))
from prepare_combat_conditions import write_runtime  # noqa: E402

WIDTHS = [1500, 850, 500]
CASES = {
    'member_min_missing': {'mutate': lambda c: c['combatProfiles']['characters']['5004'].pop('bonusRangeMin'),
                           'code': 'combat_profile_invalid', 'expect': ['앨리스(#5004)', '최소 사거리(bonusRangeMin)', '값 없음(키 누락)']},
    'element_null': {'mutate': lambda c: c['combatProfiles']['characters']['5011'].__setitem__('element', None),
                     'code': 'combat_profile_invalid', 'expect': ['리타(#5011)', '속성(element)', '값이 null']},
    'catalog_missing': {'mutate': None, 'code': 'combat_profile_catalog_missing', 'expect': ['준비되지 않았습니다']},
}
HINT = 'prepare_combat_conditions.py'


async def run_case(browser, name, spec, args, out, sources):
    case_out = out / name
    data = case_out / 'data'
    data.mkdir(parents=True)
    hashes, snapshot, _ = prepare_data(Path(args.source_data).resolve(), data)
    sources.update({f'{name}:{k}': (Path(args.source_data).resolve() / k, v) for k, v in hashes.items()})
    (data / 'presentation/assets/ui').mkdir(parents=True)
    for icon in Path(args.assets).glob('code-*.png'):
        shutil.copyfile(icon, data / 'presentation/assets/ui' / icon.name)
    result = {'case': name}
    if spec['mutate']:
        prep = subprocess.run([sys.executable, str(ROOT / 'tools/data-pipeline/prepare_combat_conditions.py'), '--runtime-root', str(data / 'runtime'),
                               '--source-roster', args.source_roster], cwd=ROOT, capture_output=True, text=True)
        if prep.returncode:
            raise RuntimeError(prep.stderr)
        runtime = data / 'runtime'
        current = json.loads((runtime / 'current.json').read_text(encoding='utf-8-sig'))['id']
        catalog = json.loads((runtime / current / 'catalog.json').read_text(encoding='utf-8'))
        spec['mutate'](catalog)
        result['runtimeId'] = write_runtime(runtime, catalog)  # isolated dataRoot only; hash-valid damaged catalog
    port = free_port()
    base = f'http://127.0.0.1:{port}'
    env = dict(os.environ, NIKKE_DATA_ROOT=str(data), NIKKE_PROJECT_ROOT=str(ROOT), NIKKE_PORT=str(port), NIKKE_TEST_FIXTURE='1')
    env.pop('NIKKE_GAME_CATALOG', None)
    api = Api(base)
    log = (case_out / 'api.log').open('w', encoding='utf-8')
    process = subprocess.Popen([args.dotnet, str(ROOT / 'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')], cwd=ROOT, env=env,
                               stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    problems = []
    try:
        for _ in range(300):
            try:
                _, boot = api.call('bootstrap'); api.token = boot['token']; break
            except (OSError, urllib.error.URLError):
                if process.poll() is not None:
                    raise RuntimeError('API exited; see api.log')
                time.sleep(.2)
        api.call(f"accounts/{snapshot['accountId']}/formation", {'slots': IDS}, method='PUT')
        status, body = api.call('runtime/combat-conditions')
        result['apiCatalog'] = {'status': status, 'body': body}
        if status != 409 or (body.get('code') or body.get('message', '').split(':')[0]) != spec['code']:
            problems.append(f'{name}: API catalog answer {status} {body}')
        page = await browser.new_page(viewport={'width': 1500, 'height': 1000})
        errors, answers = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('response', lambda r: answers.append([r.status, r.request.method, r.url.split(base)[-1].split('?')[0]])
                if any(k in r.url for k in ('/combat-conditions', '/skill-replays', '/compute/experiments')) else None)
        await patch_bootstrap(page, base)
        await page.goto(base + '/editor/')
        await page.wait_for_function("document.body.dataset.ready==='true'", timeout=90000)
        await page.locator('[data-tab="raid"]').click()
        await page.locator('[name="seconds"]').fill('5')

        def has_expected(textv):
            return all(x in textv for x in spec['expect']) and HINT in textv

        # Distance dialog: catalog and member errors.
        await page.locator('[data-cond-open="distance"]').click()
        await page.wait_for_selector('dialog [data-cond-error]', timeout=30000)
        await page.wait_for_timeout(300)
        texts = await page.locator('dialog [data-cond-error]').all_inner_texts()
        result['distanceDialog'] = texts
        if not texts or not all(has_expected(t) for t in texts):
            problems.append(f'{name}: distance dialog errors {texts}')
        for width in WIDTHS:
            await page.set_viewport_size({'width': width, 'height': 900})
            await page.wait_for_timeout(150)
            await page.screenshot(path=str(case_out / f'distance-dialog-{width}.png'))
            if await page.evaluate('document.documentElement.scrollWidth - innerWidth') > 0:
                problems.append(f'{name}: distance dialog overflow @{width}')
            right = await page.evaluate("document.querySelector('dialog.cond-dialog').getBoundingClientRect().right - innerWidth")
            if right > .5:
                problems.append(f'{name}: dialog outside viewport @{width}')
        await page.set_viewport_size({'width': 1500, 'height': 1000})
        await page.locator('dialog [name="distance"]').fill('35')
        await page.locator('dialog button[value="apply"]').click()
        await page.locator('[data-cond-open="element"]').click()
        await page.wait_for_selector('dialog [data-cond-error]', timeout=30000)
        element_text = await page.locator('dialog [data-cond-error]').inner_text()
        result['elementDialog'] = element_text
        if not has_expected(element_text):
            problems.append(f'{name}: element dialog error {element_text!r}')
        await page.locator('[data-cond-element="fire"]').click()

        # Solo raid run: the real 409 becomes a Korean diagnostic in the result area.
        async with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/runtime/skill-replays'), timeout=120000) as pending:
            await page.locator('#run-replay').click()
        response = await pending.value
        replay_body = await response.json()
        await page.wait_for_selector('#replay-result [data-profile-error]', timeout=30000)
        replay_text = await page.locator('#replay-result').inner_text()
        result['replay'] = {'status': response.status, 'body': replay_body, 'text': replay_text}
        if response.status != 409 or not has_expected(replay_text):
            problems.append(f'{name}: replay diagnostic {response.status} {replay_text!r}')
        for width in WIDTHS:
            await page.set_viewport_size({'width': width, 'height': 900})
            await page.wait_for_timeout(150)
            if await page.evaluate('document.documentElement.scrollWidth - innerWidth') > 0:
                problems.append(f'{name}: raid result overflow @{width}')
            await page.locator('#replay-result').screenshot(path=str(case_out / f'replay-error-{width}.png'))
        await page.set_viewport_size({'width': 1500, 'height': 1000})

        # Statistics: experiment creation 409 is listed as a data diagnostic and the API stays connected.
        await page.locator('[data-tab="stats"]').click()
        await page.wait_for_selector('#compute-start')
        await page.locator('#compute-runs').fill('1')
        async with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/compute/experiments'), timeout=120000) as pending:
            await page.locator('#compute-start').click()
        response = await pending.value
        await page.wait_for_selector('#stats-content .compute-errors li', timeout=30000)
        stats = await page.evaluate("""() => ({ errors: [...document.querySelectorAll('#stats-content .compute-errors li')].map(li => li.textContent.trim()),
          pill: document.querySelector('#stats-content .section-heading .status-pill')?.textContent.trim() ?? null,
          text: document.querySelector('#stats-content').innerText })""")
        result['statistics'] = {'status': response.status, **{k: stats[k] for k in ('errors', 'pill')}}
        if response.status != 409 or not any(has_expected(e) for e in stats['errors']):
            problems.append(f'{name}: statistics diagnostic {response.status} {stats["errors"]}')
        if stats['pill'] != '실제 API 응답' or '미연결' in stats['text']:
            problems.append(f'{name}: statistics classified as outage (pill {stats["pill"]!r})')
        await page.locator('#stats-content').screenshot(path=str(case_out / 'stats-error.png'))
        result['answers'] = answers
        result['pageErrors'] = errors
        if errors:
            problems.append(f'{name}: page errors {errors}')
        await page.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()
    result['problems'] = problems
    return result


async def run(args):
    out = ROOT / 'artifacts/ui/combat-profile-errors' / f'run-{uuid.uuid4().hex[:12]}'
    out.mkdir(parents=True)
    extra = {args.source_roster: digest(Path(args.source_roster))}
    extra.update({str(p): digest(p) for p in Path(args.assets).glob('code-*.png')})
    sources = {}
    summary = {'kind': 'real_local_api_damaged_isolated_runtime', 'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain', 'apps', 'tests/ui'], cwd=ROOT, text=True).strip()),
               'syntheticHttp': ['/api/bootstrap connection list', '/api/snapshots/*/combat-powers -> {}'], 'cases': []}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for name, spec in CASES.items():
            summary['cases'].append(await run_case(browser, name, spec, args, out, sources))
        await browser.close()
    changed = [k for k, (path, value) in sources.items() if digest(path) != value] + [k for k, v in extra.items() if digest(Path(k)) != v]
    summary['sourceUnchanged'] = not changed
    problems = [p for case in summary['cases'] for p in case['problems']] + ([f'sources changed {changed}'] if changed else [])
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
    raise SystemExit(asyncio.run(run(parser.parse_args())))

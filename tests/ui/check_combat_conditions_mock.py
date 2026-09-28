"""F-COND-U browser check of the boss distance / weak element controls. Evidence type: MOCK ONLY.

The real desktop app (apps/desktop-ui) is served statically; every /api route is synthetic HTTP (the same style as
check_solo_raid_level.py) in the confirmed F-COND-B shape (tests/ui/fixtures/combat-conditions-mock.json).
Replay responses carry conditionCompatibility (per_member, then legacy_global); a third response omits it to exercise
the read-only condition-compatibility endpoint. Element icons are read from an isolated copy passed with --assets
(read only). No API server, no account data, no 5180/5181. Real API: check_combat_conditions_live.py.
Output: artifacts/ui/combat-conditions-mock/run-<id>/ (git-ignored). Exit 1 means NOT accepted.
"""
import argparse
import asyncio
import json
from pathlib import Path
import subprocess
import uuid

from playwright.async_api import async_playwright

from check_solo_raid_level import IDS, NAMES, serve

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = [1500, 850, 500]
ELEMENTS = {'5011': 'fire', '5008': 'water', '5009': 'fire', '5004': 'electric', '5044': 'wind'}
WEAPONS = {'5011': 'submachine_gun', '5008': 'machine_gun', '5009': 'rocket_launcher', '5004': 'sniper_rifle', '5044': 'sniper_rifle'}
MOCK = json.loads((ROOT / 'tests/ui/fixtures/combat-conditions-mock.json').read_text(encoding='utf-8'))
LEGACY_COMPAT = {'mode': 'legacy_global', 'label': '이전 방식(전원 적용)', 'legacyProperDistance': True,
                 'legacyElementAdvantage': False, 'bossDistance': None, 'bossWeakElement': None}


async def route_api(page, captured, assets):
    async def fulfil(route, body, status=200):
        await route.fulfill(status=status, json=body)

    async def skill_replays(route):
        body = route.request.post_data_json
        captured['replays'].append(body)
        n = len(captured['replays'])
        combat = body['conditions']['combat']
        # 1: new record (per_member); 2: old deck-wide record (legacy_global); 3: record without the field.
        compat = ({'mode': 'per_member', 'label': '보스 거리·약점(멤버별)', 'legacyProperDistance': False, 'legacyElementAdvantage': False,
                   'bossDistance': combat.get('bossDistance'), 'bossWeakElement': combat.get('bossWeakElement')} if n == 1
                  else LEGACY_COMPAT if n == 2 else None)
        extra = {'conditionCompatibility': compat} if compat else {}
        await route.fulfill(json={'id': f"replay-{n}", 'createdAt': '2026-09-28T00:00:00Z', **extra,
            'inputs': [{'weapon': {'characterId': i}, 'skills': {'slots': {}}} for i in IDS], 'conditions': body['conditions'],
            'result': {'totalDamage': 1, 'members': [{'characterId': i, 'damage': 1, 'effects': {'normal_attack': 1}} for i in IDS],
                       'teamBurst': {'fullBursts': [], 'timeline': [], 'fullBurstFrames': 0,
                                     'acceptedGaugeByMember': {i: 0 for i in IDS}, 'sourceConstants': {'capacityRaw': 1000000}},
                       'damageLog': {'schemaVersion': 1, 'characterId': '5004', 'status': 'complete', 'truncated': False,
                                     'eventCount': 0, 'totalDamage': 0, 'entries': []}}})

    async def experiments(route):
        if route.request.method == 'POST':
            captured['experiments'].append(route.request.post_data_json)
            await route.fulfill(status=409, json={'message': 'gpu_unavailable'})
        else:
            await route.fulfill(status=404, json={'message': 'not found'})

    async def catalog(route):
        captured['rangeCalls'].append(route.request.url)
        await route.fulfill(json=MOCK['catalog'])

    async def members(route):
        captured['rangeCalls'].append(route.request.url)
        await route.fulfill(json=MOCK['members'])

    async def compatibility(route):
        captured['compatibilityCalls'].append(route.request.url)
        await route.fulfill(json=LEGACY_COMPAT)

    async def asset(route):
        name = route.request.url.rsplit('/', 1)[-1]
        path = assets / name if assets else None
        if path and path.is_file():
            await route.fulfill(path=str(path))
        else:
            captured['missingAssets'].append(name)
            await route.fulfill(status=404, body='')

    await page.route('**/editor/assets/ui/*', asset)
    await page.route('**/api/bootstrap', lambda r: fulfil(r, {'token': 't', 'testMode': True, 'jobs': [],
        'connections': [{'id': 'c1', 'accountId': 'acc', 'nickname': '검증용', 'status': 'ready', 'choices': [{'area': 1, 'label': 'synthetic'}]}]}))
    await page.route('**/api/accounts/*/snapshot', lambda r: fulfil(r, {'id': 'snap-cond', 'accountId': 'acc', 'synchroLevel': 400,
        'observedAt': '2026-09-28T00:00:00Z', 'characters': [{'characterId': i, 'name': n, 'level': 400, 'limitBreak': 3, 'core': 0} for i, n in zip(IDS, NAMES)]}))
    await page.route('**/api/presentation', lambda r: fulfil(r, {'characters': [
        {'characterUid': i, 'displayName': n, 'burstStep': s, 'weaponCode': WEAPONS[i], 'elementCode': ELEMENTS[i]}
        for i, n, s in zip(IDS, NAMES, [1, 2, 3, 3, 3])]}))
    await page.route('**/api/presentation/status', lambda r: fulfil(r, {'status': 'idle', 'revision': 1, 'message': 'ready'}))
    await page.route('**/api/accounts/*/formation', lambda r: fulfil(r, {'accountId': 'acc', 'slots': IDS}))
    await page.route('**/api/accounts/*/burst-tactic', lambda r: fulfil(r, {'saved': None, 'stale': False, 'executionStatus': 'legacy'}))
    await page.route('**/api/snapshots/*/combat-powers', lambda r: fulfil(r, {i: 1 for i in IDS}))
    await page.route('**/api/runtime/combat-conditions', catalog)
    await page.route('**/api/snapshots/*/combat-conditions**', members)
    await page.route('**/api/runtime/skill-replays/*/damage-log**', lambda r: fulfil(r, {'exportSchemaVersion': 1,
        'collectionStatus': 'not_collected', 'replay': {'id': 'replay-1', 'result': {}}}))
    await page.route('**/api/runtime/skill-replays', skill_replays)
    await page.route('**/api/runtime/skill-replays/*/condition-compatibility', compatibility)
    await page.route('**/api/compute/hardware', lambda r: fulfil(r, {'present': True, 'gpus': []}))
    await page.route('**/api/compute/experiments', experiments)


DIALOG_PROBE = """() => { const d = document.querySelector('dialog.cond-dialog');
  if (!d || !d.open) return { open: false };
  const r = d.getBoundingClientRect();
  return { open: true, text: d.innerText, labelledBy: d.getAttribute('aria-labelledby'), active: document.activeElement?.outerHTML.slice(0, 120),
    rect: { left: r.left, right: r.right, top: r.top, bottom: r.bottom }, viewport: { w: innerWidth, h: innerHeight },
    members: [...d.querySelectorAll('[data-member]')].map(li => [li.dataset.member, li.dataset.distanceKind, li.querySelector('em').textContent]),
    weapons: [...d.querySelectorAll('[data-weapon]')].map(tr => tr.innerText.replace(/\\s+/g, ' ').trim()),
    elements: [...d.querySelectorAll('[data-cond-element]')].map(b => ({ code: b.dataset.condElement, pressed: b.getAttribute('aria-pressed'),
      img: b.querySelector('img')?.naturalWidth ?? null, text: b.innerText.replace(/\\s+/g, ' ').trim() })),
    overflow: document.documentElement.scrollWidth - innerWidth }; }"""
SUMMARY = "() => [...document.querySelectorAll('[data-cond-value]')].map(e => e.textContent.trim())"


async def run(args):
    out = ROOT / 'artifacts/ui/combat-conditions-mock' / f'run-{uuid.uuid4().hex[:12]}'
    out.mkdir(parents=True)
    server, base = serve(ROOT / 'apps/desktop-ui')
    captured = {'replays': [], 'experiments': [], 'rangeCalls': [], 'compatibilityCalls': [], 'missingAssets': []}
    problems, errors, report = [], [], {}
    assets = Path(args.assets) if args.assets else None
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page(viewport={'width': 1500, 'height': 1000})
            page.on('pageerror', lambda e: errors.append(str(e)))
            await route_api(page, captured, assets)
            await page.goto(base + '/editor/')
            await page.wait_for_function("document.body.dataset.ready==='true'", timeout=60000)
            await page.locator('[data-tab="raid"]').click()
            form = await page.evaluate("""() => { const f = document.querySelector('#replay-form');
              return { names: [...f.elements].map(e => e.name).filter(Boolean), hidden: f.querySelectorAll('input[type=hidden]').length,
                buttons: [...f.querySelectorAll('.cond-icon-btn')].map(b => { const r = b.getBoundingClientRect(); return [b.getAttribute('aria-label'), Math.round(r.width), Math.round(r.height)]; }) }; }""")
            report['form'] = form
            if 'distance' in form['names'] or 'element' in form['names'] or form['hidden']:
                problems.append(f'form still has old checkboxes/hidden inputs {form}')
            if len(form['buttons']) != 2 or any(w != h for _, w, h in form['buttons']):
                problems.append(f'icon buttons not two squares {form["buttons"]}')
            if await page.evaluate(SUMMARY) != ['적정 거리 · 미설정', '약점 · 없음']:
                problems.append(f'initial summary {await page.evaluate(SUMMARY)}')

            # Distance dialog: keyboard open, range table, per-member preview, strict input, ESC discards.
            await page.locator('[data-cond-open="distance"]').focus()
            await page.keyboard.press('Enter')
            await page.wait_for_function("document.querySelector('dialog.cond-dialog')?.open && document.querySelectorAll('[data-weapon]').length === 6")
            await page.locator('dialog [name="distance"]').fill('35')
            d = await page.evaluate(DIALOG_PROBE)
            report['distanceDialog'] = d
            if d['labelledBy'] != 'cond-distance-title' or len(d['weapons']) != 6 or not any('0–0 · 보너스 없음(확인 필요)' in w for w in d['weapons']):
                problems.append(f'distance dialog content {d.get("weapons")}')
            if [m[1] for m in d['members']] != ['in', 'in', 'no_bonus', 'out', 'in']:
                problems.append(f'distance preview {d["members"]}')
            await page.locator('dialog [name="distance"]').fill('101')
            if not await page.locator('dialog .cond-error').is_visible():
                problems.append('101 accepted without error')
            await page.locator('dialog button[value="apply"]').click()
            if not (await page.evaluate(DIALOG_PROBE))['open']:
                problems.append('invalid distance closed the dialog')
            await page.locator('dialog [name="distanceRange"]').fill('35')
            await page.locator('dialog button[value="apply"]').click()
            summary = await page.evaluate(SUMMARY)
            focused = await page.evaluate("document.activeElement?.dataset?.condOpen ?? null")
            report['afterDistance'] = {'summary': summary, 'focus': focused}
            if summary[0] != '적정 거리 · 35' or focused != 'distance':
                problems.append(f'distance apply/focus {summary} {focused}')
            await page.keyboard.press('Enter')
            await page.locator('dialog [name="distance"]').fill('50')
            await page.keyboard.press('Escape')
            if (await page.evaluate(DIALOG_PROBE))['open'] or (await page.evaluate(SUMMARY))[0] != '적정 거리 · 35':
                problems.append('ESC did not close without applying')

            # Weak element dialog.
            await page.locator('[data-cond-open="element"]').click()
            await page.wait_for_function("document.querySelector('dialog.cond-dialog')?.open && document.querySelectorAll('[data-cond-element]').length === 6")
            e = await page.evaluate(DIALOG_PROBE)
            report['elementDialog'] = e
            if '보스의 약점 속성 — 이 속성 니케가 우월 코드 보너스를 받습니다' not in e['text'] or e['labelledBy'] != 'cond-element-title':
                problems.append('weak element wording missing')
            fire = next(x for x in e['elements'] if x['code'] == 'fire')
            if '덱: 리타, 누아르' not in fire['text']:
                problems.append(f'fire members {fire}')
            if assets and any(x['code'] and not x['img'] for x in e['elements']):
                problems.append(f'element images not loaded {e["elements"]}')
            await page.keyboard.press('Escape')
            await page.locator('[data-cond-open="element"]').click()
            await page.locator('[data-cond-element="fire"]').focus()
            await page.keyboard.press('Enter')
            summary = await page.evaluate(SUMMARY)
            report['afterElement'] = summary
            if summary != ['적정 거리 · 35', '약점 · 작열(Fire)']:
                problems.append(f'element apply {summary}')

            for width in WIDTHS:
                await page.set_viewport_size({'width': width, 'height': 900})
                await page.wait_for_timeout(150)
                await page.locator('#replay-form').screenshot(path=str(out / f'form-{width}.png'))
                for kind in ('distance', 'element'):
                    await page.locator(f'[data-cond-open="{kind}"]').click()
                    await page.wait_for_function("document.querySelector('dialog.cond-dialog')?.open")
                    await page.wait_for_timeout(100)
                    probe = await page.evaluate(DIALOG_PROBE)
                    await page.screenshot(path=str(out / f'{kind}-dialog-{width}.png'))
                    if probe['overflow'] > 0 or probe['rect']['left'] < 0 or probe['rect']['right'] > probe['viewport']['w'] + 0.5:
                        problems.append(f'{kind} dialog @{width} outside viewport {probe["rect"]} overflow {probe["overflow"]}')
                    await page.keyboard.press('Escape')
                overflow = await page.evaluate('document.documentElement.scrollWidth - innerWidth')
                if overflow > 0:
                    problems.append(f'form @{width} overflow {overflow}')
            await page.set_viewport_size({'width': 1500, 'height': 1000})

            # Requests carry the new fields and never the old bools; the result names the mode.
            await page.locator('#run-replay').click()
            await page.wait_for_selector('[data-cond-mode]')
            combat = captured['replays'][-1]['conditions']['combat']
            mode1 = await page.locator('[data-cond-mode]').get_attribute('data-cond-mode')
            await page.locator('#run-replay').click()
            await page.wait_for_function("document.querySelector('[data-cond-mode]')?.dataset.condMode === 'legacy'")
            legacy_text = await page.locator('[data-cond-mode]').inner_text()
            # A record saved without conditionCompatibility is described through the read-only endpoint.
            await page.locator('#run-replay').click()
            for _ in range(50):
                if captured['compatibilityCalls']:
                    break
                await page.wait_for_timeout(100)
            await page.wait_for_function("document.querySelector('[data-cond-mode]')?.dataset.condMode === 'legacy'")
            report['replay'] = {'combat': {k: combat.get(k, '<absent>') for k in ('bossDistance', 'bossWeakElement', 'properDistance', 'elementAdvantage')},
                                'firstMode': mode1, 'legacyText': legacy_text, 'compatibilityCalls': captured['compatibilityCalls']}
            if len(captured['compatibilityCalls']) != 1 or not captured['compatibilityCalls'][0].endswith('/replay-3/condition-compatibility'):
                problems.append(f"compatibility endpoint calls {captured['compatibilityCalls']}")
            if combat.get('bossDistance') != 35 or combat.get('bossWeakElement') != 'Fire' or 'properDistance' in combat or 'elementAdvantage' in combat:
                problems.append(f'replay combat fields {report["replay"]["combat"]}')
            if mode1 != 'per_member' or legacy_text != '이전 방식(전원 적용) · 적정 거리 적용 · 우월 코드 미적용':
                problems.append(f'result mode {mode1} / {legacy_text!r}')
            await page.locator('#replay-result').screenshot(path=str(out / 'result-legacy.png'))

            await page.locator('[data-tab="stats"]').click()
            await page.wait_for_selector('#compute-start')
            card = await page.evaluate("() => [...document.querySelectorAll('#stats-content .metric-card')].find(c => c.querySelector('span')?.textContent.trim() === '보스 거리·약점')?.querySelector('strong')?.textContent.trim() ?? null")
            report['statisticsCard'] = card
            if card != '보스 거리 35 · 약점 작열(Fire) (멤버별 판정)':
                problems.append(f'statistics condition card {card!r}')
            await page.locator('#compute-start').click()
            for _ in range(50):
                if captured['experiments']:
                    break
                await page.wait_for_timeout(100)
            stat_combat = captured['experiments'][-1]['conditions']['combat'] if captured['experiments'] else {}
            report['statistics'] = {k: stat_combat.get(k, '<absent>') for k in ('bossDistance', 'bossWeakElement', 'properDistance', 'elementAdvantage')}
            if stat_combat.get('bossDistance') != 35 or stat_combat.get('bossWeakElement') != 'Fire' or 'properDistance' in stat_combat:
                problems.append(f'statistics combat fields {report["statistics"]}')
            await browser.close()
    finally:
        server.shutdown()
    report.update({'evidence': 'mock_only_not_api', 'rangeCalls': len(captured['rangeCalls']), 'missingAssets': sorted(set(captured['missingAssets'])),
                   'errors': errors, 'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain', 'apps', 'tests/ui'], cwd=ROOT, text=True).strip())})
    if errors:
        problems.append(f'JS errors {errors}')
    report['problems'] = problems
    report['accepted'] = not problems
    (out / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(out), 'accepted': not problems, 'problems': problems, 'missingAssets': report['missingAssets']}, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--assets', help='Directory with code-*.png (isolated copy, read only)')
    raise SystemExit(asyncio.run(run(parser.parse_args())))

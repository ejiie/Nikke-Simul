"""F2-U (F-COND-2 R1-R8) browser check. Evidence type: MOCK ONLY.

The real desktop app is served statically with the synthetic /api routes of check_combat_conditions_mock.py
(confirmed F-COND-B shapes) plus:
- raid-conditions.js served with DEF_WIRE/BOSS_WIRE confirmed=true for this run only (files on disk stay false);
- the boss list from tests/ui/fixtures/solo-raid-bosses-mock.json, boss images routed to local stand-in icons;
- presentation with a Korean name for the SR exception character (5042);
- the 2nd replay response imitates an older record (120 s, fixed DEF 30925, per_pellet) to check the saved line.
A second page keeps the on-disk flags (live form before the wire): the fixed-DEF select must still be there.
No API server, no account data, no 5180/5181. Output: artifacts/ui/raid-conditions-mock/run-<id>/. Exit 1 = NOT accepted.
"""
import argparse
import asyncio
import json
from pathlib import Path
import uuid

from playwright.async_api import async_playwright

from check_combat_conditions_mock import IDS, NAMES, ELEMENTS, WEAPONS, route_api as route_condition_api
from check_solo_raid_level import serve

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = [1500, 850, 500]
BOSSES = json.loads((ROOT / 'tests/ui/fixtures/solo-raid-bosses-mock.json').read_text(encoding='utf-8'))


async def route_extra(page, captured, assets, confirmed):
    async def module(route):
        source = (ROOT / 'apps/desktop-ui/raid-conditions.js').read_text(encoding='utf-8')
        assert source.count('confirmed: false,') == 2
        await route.fulfill(body=source.replace('confirmed: false,', 'confirmed: true,'), content_type='text/javascript')

    async def presentation(route):
        chars = [{'characterUid': i, 'displayName': n, 'burstStep': s, 'weaponCode': WEAPONS[i], 'elementCode': ELEMENTS[i]}
                 for i, n, s in zip(IDS, NAMES, [1, 2, 3, 3, 3])]
        chars.append({'characterUid': '5042', 'displayName': '하란', 'burstStep': 3, 'weaponCode': 'sniper_rifle', 'elementCode': 'electric'})
        await route.fulfill(json={'characters': chars})

    async def boss_image(route):
        name = {'a.png': 'code-fire.png', 'b.png': 'code-electric.png'}[route.request.url.rsplit('/', 1)[-1]]
        await route.fulfill(path=str(assets / name))

    async def replays(route):
        body = route.request.post_data_json
        captured['replays'].append(body)
        n = len(captured['replays'])
        conditions = body['conditions']
        if n == 2:  # an older saved record: its own time, fixed DEF and shotgun setting
            combat = {k: v for k, v in conditions['combat'].items() if k != 'enemyDefenseMode'}
            combat.update({'durationFrames': 7200, 'enemyDefense': 30925, 'pelletCoefficientPolicy': 'per_pellet', 'critMode': 'off'})
            conditions = {k: v for k, v in conditions.items() if k != 'boss'} | {'combat': combat}
        await route.fulfill(json={'id': f'replay-{n}', 'createdAt': '2026-09-29T00:00:00Z', 'conditions': conditions,
            'conditionCompatibility': {'mode': 'per_member', 'label': '보스 거리·약점(멤버별)', 'bossDistance': None, 'bossWeakElement': None},
            'inputs': [{'weapon': {'characterId': i}, 'skills': {'slots': {}}} for i in IDS],
            'result': {'totalDamage': 1, 'members': [{'characterId': i, 'damage': 1, 'effects': {'normal_attack': 1}} for i in IDS],
                       'teamBurst': {'fullBursts': [], 'timeline': [], 'fullBurstFrames': 0, 'acceptedGaugeByMember': {i: 0 for i in IDS},
                                     'sourceConstants': {'capacityRaw': 1000000}},
                       'damageLog': {'schemaVersion': 1, 'characterId': '5004', 'status': 'complete', 'truncated': False,
                                     'eventCount': 0, 'totalDamage': 0, 'entries': []}}})

    if confirmed:
        await page.route('**/editor/raid-conditions.js', module)
    await page.route('**/api/presentation', presentation)
    await page.route('**/mock-boss/*', boss_image)
    await page.route('**/api/runtime/solo-raid-bosses', lambda r: r.fulfill(json=BOSSES))
    await page.route('**/api/runtime/skill-replays', replays)


FORM = """() => { const f = document.querySelector('#replay-form');
  const grid = f.querySelector('.form-grid'); const boss = f.querySelector('#raid-boss');
  return { names: [...f.elements].map(e => e.name).filter(Boolean),
    crit: f.querySelector('[name=crit]')?.value, critOptions: [...f.querySelectorAll('[name=crit] option')].map(o => o.textContent),
    rounding: Boolean(f.querySelector('[name=rounding]')),
    bossBelowGrid: Boolean(boss && grid && (grid.compareDocumentPosition(boss) & Node.DOCUMENT_POSITION_FOLLOWING)),
    note: f.querySelector('[data-conditions-note]')?.textContent ?? null,
    boss: f.querySelector('[data-boss-open]')?.innerText.replace(/\\s+/g, ' ').trim() ?? null,
    overflow: document.documentElement.scrollWidth - innerWidth }; }"""


async def run(args):
    out = ROOT / 'artifacts/ui/raid-conditions-mock' / f'run-{uuid.uuid4().hex[:12]}'
    out.mkdir(parents=True)
    assets = Path(args.assets)
    server, base = serve(ROOT / 'apps/desktop-ui')
    problems, report = [], {'evidence': 'mock_only_not_api'}
    captured_c = {'replays': [], 'experiments': [], 'rangeCalls': [], 'compatibilityCalls': [], 'missingAssets': []}
    captured = {'replays': []}
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            # Live form with on-disk flags (before the DEF/boss wire): fixed-DEF select kept, no boss selector.
            page = await browser.new_page(viewport={'width': 1500, 'height': 1000})
            await route_condition_api(page, dict(captured_c), assets)
            await route_extra(page, {'replays': []}, assets, confirmed=False)
            await page.goto(base + '/editor/')
            await page.wait_for_function("document.body.dataset.ready==='true'", timeout=60000)
            await page.locator('[data-tab="raid"]').click()
            live = await page.evaluate(FORM)
            report['liveForm'] = live
            if 'defense' not in live['names'] or 'seconds' in live['names'] or 'pellet' in live['names'] or live['boss'] is not None:
                problems.append(f'live form (unconfirmed wires) {live["names"]} boss={live["boss"]}')
            if live['crit'] != 'sample' or '자동 전환은 아직 적용하지 않습니다' not in (live['note'] or ''):
                problems.append(f'live form crit/note {live["crit"]} {live["note"]}')
            await page.close()

            errors = []
            page = await browser.new_page(viewport={'width': 1500, 'height': 1000})
            page.on('pageerror', lambda e: errors.append(str(e)))
            await route_condition_api(page, captured_c, assets)
            await route_extra(page, captured, assets, confirmed=True)
            await page.goto(base + '/editor/')
            await page.wait_for_function("document.body.dataset.ready==='true'", timeout=60000)
            await page.locator('[data-tab="raid"]').click()
            await page.wait_for_selector('[data-boss-open]')
            form = await page.evaluate(FORM)
            report['form'] = form
            for gone in ('seconds', 'pellet', 'defense'):
                if gone in form['names']:
                    problems.append(f'R3/R4/R7: {gone} still in form')
            if form['crit'] != 'sample' or form['critOptions'][0] != '확률 적용':
                problems.append(f'R5 crit default {form["crit"]}')
            if not form['rounding']:
                problems.append('R6 rounding policy removed')
            if not form['bossBelowGrid'] or '더미 보스' not in (form['boss'] or ''):
                problems.append(f'R8 boss selector position/default {form}')
            if '자동 전환됩니다' not in (form['note'] or '') or '180초' not in form['note']:
                problems.append(f'R4 note {form["note"]}')

            # R8 dialog: dummy first, images, keyboard select, ESC.
            await page.locator('[data-boss-open]').focus()
            await page.keyboard.press('Enter')
            await page.wait_for_selector('dialog.boss-dialog[open] [data-boss-id]')
            cards = await page.evaluate("""() => [...document.querySelectorAll('dialog.boss-dialog [data-boss-id]')].map(b => ({ id: b.dataset.bossId,
              pressed: b.getAttribute('aria-pressed'), text: b.innerText.replace(/\\s+/g, ' ').trim(), img: b.querySelector('.boss-pick-image')?.naturalWidth ?? null }))""")
            report['bossCards'] = cards
            if [c['id'] for c in cards] != ['dummy', 'mock-a', 'mock-b', 'mock-c'] or cards[0]['pressed'] != 'true':
                problems.append(f'boss cards {cards}')
            await page.wait_for_timeout(300)
            if not (await page.evaluate("() => [...document.querySelectorAll('dialog.boss-dialog .boss-pick-image')].every(i => i.naturalWidth > 0)")):
                problems.append('boss images not loaded')
            for width in WIDTHS:
                await page.set_viewport_size({'width': width, 'height': 900})
                await page.wait_for_timeout(150)
                await page.screenshot(path=str(out / f'boss-dialog-{width}.png'))
                if await page.evaluate("document.documentElement.scrollWidth - innerWidth") > 0:
                    problems.append(f'boss dialog overflow @{width}')
            await page.set_viewport_size({'width': 1500, 'height': 1000})
            await page.keyboard.press('Escape')
            await page.locator('[data-boss-open]').click()
            await page.locator('dialog.boss-dialog [data-boss-id="mock-a"]').focus()
            await page.keyboard.press('Enter')
            boss = await page.evaluate("document.querySelector('[data-boss-open]')?.innerText.replace(/\\s+/g,' ').trim()")
            focus = await page.evaluate("document.activeElement?.dataset?.bossOpen ?? null")
            report['bossAfter'] = [boss, focus]
            if '모의 보스 A' not in (boss or '') or focus != '1':
                problems.append(f'boss select/focus {boss} {focus}')

            # R1/R2 in the condition dialogs.
            await page.locator('[data-cond-open="distance"]').click()
            await page.wait_for_function("document.querySelectorAll('dialog.cond-dialog[open] [data-weapon]').length === 6")
            d = await page.evaluate("""() => { const d = document.querySelector('dialog.cond-dialog');
              return { text: d.innerText, icons: [...d.querySelectorAll('.cond-weapon img')].map(i => i.naturalWidth) }; }""")
            report['distanceDialogText'] = d['text']
            for need in ('하란: 25–45', '적정 사거리', '0–0 · 보너스 없음'):
                if need not in d['text']:
                    problems.append(f'R2 missing {need}')
            for gone in ('#5042', 'Harran', '(다수)', '확인 필요', '잠정', '양끝 포함', '실게임', '무기군 표는 참고용', 'sha256'):
                if gone in d['text']:
                    problems.append(f'R2 still shows {gone}')
            if len(d['icons']) != 6 or not all(d['icons']):
                problems.append(f'R2 weapon icons {d["icons"]}')
            for width in WIDTHS:
                await page.set_viewport_size({'width': width, 'height': 900})
                await page.wait_for_timeout(150)
                await page.screenshot(path=str(out / f'distance-dialog-{width}.png'))
            await page.set_viewport_size({'width': 1500, 'height': 1000})
            await page.keyboard.press('Escape')
            await page.locator('[data-cond-open="element"]').click()
            await page.wait_for_selector('dialog.cond-dialog[open] [data-cond-element]')
            el = await page.locator('dialog.cond-dialog').inner_text()
            report['elementDialogText'] = el
            if '보스의 약점 속성 — 이 속성 니케가 우월 코드 보너스를 받습니다' not in el or '니케 자신의 속성' in el \
                    or any(x in el for x in ('Fire', 'Water', 'Wind', 'Iron', 'Electr')):
                problems.append('R1 element dialog wording')
            await page.locator('[data-cond-element="fire"]').click()
            summary = await page.evaluate("[...document.querySelectorAll('[data-cond-value]')].map(e => e.textContent.trim())")
            if summary[1] != '약점 · 작열':
                problems.append(f'R1 summary {summary}')

            for width in WIDTHS:
                await page.set_viewport_size({'width': width, 'height': 900})
                await page.wait_for_timeout(150)
                await page.locator('#replay-form').screenshot(path=str(out / f'form-{width}.png'))
                if await page.evaluate("document.documentElement.scrollWidth - innerWidth") > 0:
                    problems.append(f'form overflow @{width}')
            await page.set_viewport_size({'width': 1500, 'height': 1000})

            # Requests and saved-condition lines.
            await page.locator('#run-replay').click()
            await page.wait_for_selector('#replay-result [data-saved-combat]')
            first = await page.locator('#replay-result [data-saved-combat]').inner_text()
            combat = captured['replays'][0]['conditions']['combat']
            boss_field = captured['replays'][0]['conditions'].get('boss')
            await page.locator('#run-replay').click()
            await page.wait_for_function("document.querySelector('#replay-result [data-saved-combat]')?.textContent.includes('120초')")
            second = await page.locator('#replay-result [data-saved-combat]').inner_text()
            report['replay'] = {'combat': {k: combat.get(k, '<absent>') for k in ('durationFrames', 'enemyDefense', 'enemyDefenseMode', 'pelletCoefficientPolicy', 'critMode')},
                                'boss': boss_field, 'savedLine': first, 'olderSavedLine': second}
            if combat.get('durationFrames') != 10800 or combat.get('pelletCoefficientPolicy') != 'per_trigger' or 'enemyDefense' in combat \
                    or combat.get('enemyDefenseMode') != 'cumulative_switch' or combat.get('critMode') != 'sample' or boss_field != {'id': 'mock-a'}:
                problems.append(f'replay request {report["replay"]}')
            if first != '180초 · 방어력 자동 전환 (30,925 → 31,784) · 크리티컬 확률 적용 · 샷건 계수 발사 1회':
                problems.append(f'saved line {first!r}')
            if second != '120초 · 방어력 30,925 고정 · 크리티컬 끔 · 샷건 계수 펠릿마다':
                problems.append(f'older saved line {second!r}')

            await page.locator('[data-tab="stats"]').click()
            await page.wait_for_selector('#compute-start')
            await page.locator('#compute-start').click()
            for _ in range(50):
                if captured_c['experiments']:
                    break
                await page.wait_for_timeout(100)
            exp = captured_c['experiments'][-1]['conditions'] if captured_c['experiments'] else {}
            report['statistics'] = {'combat': {k: exp.get('combat', {}).get(k, '<absent>') for k in ('durationFrames', 'enemyDefense', 'enemyDefenseMode', 'pelletCoefficientPolicy', 'critMode')},
                                    'boss': exp.get('boss')}
            sc = exp.get('combat', {})
            if sc.get('durationFrames') != 10800 or sc.get('pelletCoefficientPolicy') != 'per_trigger' or 'enemyDefense' in sc \
                    or sc.get('enemyDefenseMode') != 'cumulative_switch' or exp.get('boss') != {'id': 'mock-a'}:
                problems.append(f'statistics request {report["statistics"]}')
            report['errors'] = errors
            if errors:
                problems.append(f'JS errors {errors}')
            await browser.close()
    finally:
        server.shutdown()
    report['problems'] = problems
    report['accepted'] = not problems
    (out / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(out), 'accepted': not problems, 'problems': problems}, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--assets', required=True, help='Isolated copy of presentation/assets/ui (read only)')
    raise SystemExit(asyncio.run(run(parser.parse_args())))

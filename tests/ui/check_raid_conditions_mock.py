"""F2-U (F-COND-2 R1-R8) browser check. Evidence type: MOCK ONLY.

The real desktop app is served statically with the synthetic /api routes of check_combat_conditions_mock.py
(confirmed F-COND-B shapes) plus the confirmed F2-B shapes:
- the boss list from tests/ui/fixtures/solo-raid-bosses-mock.json (one boss excluded for lack of a Korean name),
  boss images routed to local stand-in icons;
- presentation with a Korean name for the SR exception character (5042);
- replay 1 answers with battleConditions, boss and result.defense (a switch); replay 2 imitates an older record
  (120 s, fixed DEF, per_pellet, no battleConditions/boss/defense), described through /battle-conditions.
Real API: check_raid_conditions_live.py.
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
BATTLE_SOLO = {'profile': 'solo_raid', 'label': '덱 누적 피해에 따라 방어력 자동 전환', 'defenseMode': 'team_damage_threshold',
               'initialDefense': 30925, 'switchedDefense': 31784, 'damageThreshold': 2000000000, 'durationFrames': 10800,
               'pelletCoefficientPolicy': 'per_trigger'}
BATTLE_LEGACY = {'profile': 'legacy', 'label': '이전 방식(고정 방어력)', 'defenseMode': 'fixed', 'initialDefense': 30925,
                 'switchedDefense': None, 'damageThreshold': None, 'durationFrames': 7200, 'pelletCoefficientPolicy': 'per_pellet'}
DEFENSE_SWITCH = {'mode': 'team_damage_threshold', 'initialDefense': 30925, 'finalDefense': 31784, 'damageThreshold': 2000000000,
                  'switchAfterHit': {'frame': 1133, 'hitTraceId': 3804, 'hitOrdinal': 2011, 'characterId': '5009', 'effect': 'normal_attack',
                                     'cumulativeDamage': 2001052869, 'previousDefense': 30925, 'newDefense': 31784}}


async def route_extra(page, captured, assets):
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
        extra = {}
        if n == 1:
            boss = next(b for b in BOSSES['bosses'] if b['id'] == body.get('bossId', 'dummy'))
            extra = {'battleConditions': BATTLE_SOLO, 'boss': boss}
        else:  # an older saved record: its own time, fixed DEF and shotgun setting, no new fields
            combat = dict(conditions['combat'])
            combat.update({'durationFrames': 7200, 'enemyDefense': 30925, 'pelletCoefficientPolicy': 'per_pellet', 'critMode': 'off'})
            conditions = conditions | {'combat': combat}
        defense = DEFENSE_SWITCH if n == 1 else None
        await route.fulfill(json={'id': f'replay-{n}', 'createdAt': '2026-09-29T00:00:00Z', 'conditions': conditions, **extra,
            'conditionCompatibility': {'mode': 'per_member', 'label': '보스 거리·약점(멤버별)', 'bossDistance': None, 'bossWeakElement': None},
            'inputs': [{'weapon': {'characterId': i}, 'skills': {'slots': {}}} for i in IDS],
            'result': {'totalDamage': 1, 'members': [{'characterId': i, 'damage': 1, 'effects': {'normal_attack': 1}} for i in IDS],
                       **({'defense': defense} if defense else {}),
                       'teamBurst': {'fullBursts': [], 'timeline': [], 'fullBurstFrames': 0, 'acceptedGaugeByMember': {i: 0 for i in IDS},
                                     'sourceConstants': {'capacityRaw': 1000000}},
                       'damageLog': {'schemaVersion': 1, 'characterId': '5004', 'status': 'complete', 'truncated': False,
                                     'eventCount': 0, 'totalDamage': 0, 'entries': []}}})

    async def battle_conditions(route):
        captured.setdefault('battleConditionCalls', []).append(route.request.url)
        await route.fulfill(json=BATTLE_LEGACY)

    await page.route('**/api/presentation', presentation)
    await page.route('**/mock-boss/*', boss_image)
    await page.route('**/api/presentation/solo-raid-bosses', lambda r: r.fulfill(json=BOSSES))
    await page.route('**/api/runtime/skill-replays', replays)
    await page.route('**/api/runtime/skill-replays/*/battle-conditions', battle_conditions)


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
            errors = []
            page = await browser.new_page(viewport={'width': 1500, 'height': 1000})
            page.on('pageerror', lambda e: errors.append(str(e)))
            await route_condition_api(page, captured_c, assets)
            await route_extra(page, captured, assets)
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
            notice = await page.evaluate("document.querySelector('#raid-boss [data-boss-notice]')?.textContent.trim() ?? null")
            form_text = await page.locator('#replay-form').inner_text()
            report['bossNotice'] = notice
            if notice != '일부 보스 이름 준비 중' or '한국어 이름 원천' in form_text:
                problems.append(f'R8 excluded-boss notice {notice!r}')

            # R8 dialog: dummy first, images, keyboard select, ESC.
            await page.locator('[data-boss-open]').focus()
            await page.keyboard.press('Enter')
            await page.wait_for_selector('dialog.boss-dialog[open] [data-boss-id]')
            cards = await page.evaluate("""() => [...document.querySelectorAll('dialog.boss-dialog [data-boss-id]')].map(b => ({ id: b.dataset.bossId,
              pressed: b.getAttribute('aria-pressed'), text: b.innerText.replace(/\\s+/g, ' ').trim(), img: b.querySelector('.boss-pick-image')?.naturalWidth ?? null }))""")
            report['bossCards'] = cards
            if [c['id'] for c in cards] != ['dummy', 'solo-raid-41', 'solo-raid-40', 'solo-raid-39'] or cards[0]['pressed'] != 'true':
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
            await page.locator('dialog.boss-dialog [data-boss-id="solo-raid-41"]').focus()
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
            defense_line = await page.locator('#replay-result [data-defense-result]').inner_text()
            request = captured['replays'][0]
            combat = request['conditions']['combat']
            await page.locator('#run-replay').click()
            await page.wait_for_function("document.querySelector('#replay-result [data-saved-combat]')?.textContent.includes('이전 방식')")
            second = await page.locator('#replay-result [data-saved-combat]').inner_text()
            no_defense = await page.evaluate("document.querySelector('#replay-result [data-defense-result]') === null")
            report['replay'] = {'combat': {k: combat.get(k, '<absent>') for k in ('durationFrames', 'enemyDefense', 'defenseMode', 'enemyDefenseMode', 'pelletCoefficientPolicy', 'critMode')},
                                'bossId': request.get('bossId'), 'conditionProfile': request.get('conditionProfile', '<absent>'), 'conditionsBoss': request['conditions'].get('boss', '<absent>'),
                                'savedLine': first, 'defenseLine': defense_line, 'olderSavedLine': second, 'battleConditionCalls': captured.get('battleConditionCalls')}
            if combat.get('durationFrames') != 10800 or combat.get('pelletCoefficientPolicy') != 'per_trigger' or any(k in combat for k in ('enemyDefense', 'defenseMode', 'enemyDefenseMode')) \
                    or combat.get('critMode') != 'sample' or request.get('bossId') != 'solo-raid-41' or 'conditionProfile' in request or 'boss' in request['conditions']:
                problems.append(f'replay request {report["replay"]}')
            if first != '180초 · 덱 누적 피해에 따라 방어력 자동 전환 (30,925 → 31,784) · 크리티컬 확률 적용 · 샷건 계수 발사 1회 · 보스 모의 보스 A':
                problems.append(f'saved line {first!r}')
            if defense_line != '방어력 30,925 → 31,784 · 18.88초(1,133프레임) 누아르 타격 후 전환 · 누적 2,001,052,869':
                problems.append(f'defense line {defense_line!r}')
            if second != '120초 · 이전 방식(고정 방어력) · 방어력 30,925 · 크리티컬 끔 · 샷건 계수 펠릿마다' or not no_defense \
                    or len(captured.get('battleConditionCalls') or []) != 1:
                problems.append(f'older saved line {second!r} (defense line absent: {no_defense})')

            await page.locator('[data-tab="stats"]').click()
            await page.wait_for_selector('#compute-start')
            await page.locator('#compute-start').click()
            for _ in range(50):
                if captured_c['experiments']:
                    break
                await page.wait_for_timeout(100)
            exp = captured_c['experiments'][-1]['conditions'] if captured_c['experiments'] else {}
            body = captured_c['experiments'][-1] if captured_c['experiments'] else {}
            report['statistics'] = {'combat': {k: exp.get('combat', {}).get(k, '<absent>') for k in ('durationFrames', 'enemyDefense', 'defenseMode', 'pelletCoefficientPolicy', 'critMode')},
                                    'bossId': body.get('bossId'), 'conditionsBoss': exp.get('boss', '<absent>')}
            sc = exp.get('combat', {})
            if sc.get('durationFrames') != 10800 or sc.get('pelletCoefficientPolicy') != 'per_trigger' or 'enemyDefense' in sc \
                    or body.get('bossId') != 'solo-raid-41' or 'boss' in exp:
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

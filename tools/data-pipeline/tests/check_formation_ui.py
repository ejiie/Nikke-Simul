"""Formation E2E against a disposable SQLite backup. Never edits the source account.

Requires the published artifacts/desktop/backend-formation backend and local cached data.
"""
import asyncio
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import urllib.request
import uuid

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / 'artifacts/desktop/formation-ui'
BASE = 'http://127.0.0.1:5187'


def prepare():
    source = ROOT / 'data/local'
    target = OUTPUT / ('data-' + uuid.uuid4().hex)
    target.mkdir(parents=True)
    with sqlite3.connect(source.joinpath('accounts.db').as_uri() + '?mode=ro', uri=True) as src, sqlite3.connect(target / 'accounts.db') as db:
        src.backup(db)
        db.execute('DROP TABLE IF EXISTS solo_formations')
        db.execute('DELETE FROM jobs')
    for name in ['raw', 'presentation']:
        shutil.copytree(source / name, target / name)
    return target


def start(target):
    env = dict(os.environ, NIKKE_PROJECT_ROOT=str(ROOT), NIKKE_DATA_ROOT=str(target),
               NIKKE_PORT='5187', NIKKE_PYTHON=os.sys.executable, NIKKE_TEST_FIXTURE='formation-ui')
    log = open(target / 'server.log', 'a', encoding='utf-8')
    process = subprocess.Popen([str(ROOT / 'artifacts/desktop/backend-formation/Nikke.Api.exe')],
                               cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
    log.close()
    for _ in range(80):
        try:
            with urllib.request.urlopen(BASE + '/api/health', timeout=1):
                return process
        except OSError:
            if process.poll() is not None:
                raise RuntimeError('Test backend failed: ' + str(target / 'server.log'))
            time.sleep(.25)
    process.terminate()
    raise RuntimeError('Test backend startup timeout')


async def check(target, process):
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='msedge', headless=True)
        page = await browser.new_page(viewport={'width':1500, 'height':1100})
        page.on('pageerror', lambda e: errors.append(str(e)))
        async def ready():
            await page.goto(BASE + '/editor/')
            await page.wait_for_function("document.body.dataset.ready==='true'")
        async def raid():
            await page.locator('[data-tab="raid"]').click()
        async def slots(where='formation-team'):
            return await page.locator(f'#{where} .formation-slot').evaluate_all('(items)=>items.map(i=>i.dataset.characterUid)')
        async def choose(cid):
            await page.locator('#nikke-search').fill('')
            await page.locator(f'.nikke-card[data-character-uid="{cid}"]').click()
        await ready()
        await raid()
        assert await slots('raid-team') == [''] * 5
        await page.locator('#raid-team').screenshot(path=str(OUTPUT / 'empty.png'))
        # Any slot starts selection; picks always fill from the left.
        await page.locator('#raid-team .formation-slot').nth(4).click()
        assert await page.locator('#formation-editor').is_visible()
        order = await page.locator('.nikke-card').evaluate_all('(items)=>items.map(i=>i.dataset.characterUid)')
        # Percentage image sizes must resolve against the hexagon, not a shrunken auto grid track.
        for step in ['1', '2', '3']:
            badge = page.locator(f'.nikke-icon-rail .burst:has(img[src$="burst-{step}.png"])').first
            geometry = await badge.evaluate('''e=>{
                const i=e.querySelector('img'),a=e.getBoundingClientRect(),b=i.getBoundingClientRect();
                return {ratio:b.width/a.width,dx:b.x+b.width/2-a.x-a.width/2,
                    dy:b.y+b.height/2-a.y-a.height/2,objectPosition:getComputedStyle(i).objectPosition};
            }''')
            assert .55 < geometry['ratio'] < .65 and abs(geometry['dx']) < .5 and abs(geometry['dy']) < .5, geometry
            assert geometry['objectPosition'] == '50% 50%', geometry
        await choose('5011'); await choose('5008')
        assert await slots() == ['5011', '5008', '', '', '']
        await choose('5011')
        assert await slots() == ['5011', '5008', '', '', '']
        # A hold opens details and does not select on release; filters and draft survive back.
        await page.locator('#nikke-search').fill('앨리스')
        alice = page.locator('.nikke-card[data-character-uid="5004"]')
        await alice.click(delay=1100)
        await page.wait_for_selector('#character-save-bar')
        assert await page.locator('#nikke-detail-back').inner_text() == '‹ 편성'
        await page.locator('#nikke-detail-back').click()
        assert await page.locator('#nikke-search').input_value() == '앨리스'
        assert await slots() == ['5011', '5008', '', '', '']
        # Scroll/drag and cancelled pointer gestures must not become a selection or a hold.
        box = await alice.bounding_box()
        x,y = box['x']+box['width']/2, box['y']+40
        await page.mouse.move(x,y); await page.mouse.down(); await page.mouse.move(x+25,y+25)
        await page.wait_for_timeout(1100); await page.mouse.up()
        assert await page.locator('#formation-editor').is_visible()
        assert await slots() == ['5011', '5008', '', '', '']
        await alice.dispatch_event('pointerdown', {'pointerId':1,'isPrimary':True,'button':0,'clientX':x,'clientY':y})
        await alice.dispatch_event('pointercancel', {'pointerId':1})
        await page.wait_for_timeout(1100)
        assert await page.locator('#formation-editor').is_visible()
        await choose('5004'); await choose('5009'); await choose('5044')
        expected = ['5011','5008','5004','5009','5044']
        assert await slots() == expected
        extra = next(cid for cid in order if cid not in expected)
        await choose(extra); assert await slots() == expected
        # Remove from the middle; next pick fills that hole.
        await page.locator('#formation-team .formation-slot').nth(1).click()
        await choose('5008'); assert await slots() == expected
        await page.locator('.nikke-card[data-owned="false"]').first.click()
        assert await slots() == expected
        await page.evaluate('scrollTo(0,0)')
        await page.screenshot(path=str(OUTPUT / 'selection.png'))
        await page.locator('#formation-save').click()
        await page.wait_for_selector('#raid-team')
        assert await slots('raid-team') == expected
        # Unsaved changes do not overwrite the saved team, including after a reload.
        await page.locator('#raid-team .formation-slot').first.click()
        await page.locator('#formation-team .formation-slot').first.click()
        await page.locator('#formation-cancel').click()
        assert await slots('raid-team') == expected
        await ready(); await raid(); assert await slots('raid-team') == expected
        # Switching accounts must not expose or overwrite the other account's formation.
        original_connection = await page.evaluate("localStorage.getItem('nikke-sync-connection')")
        boot = await (await page.request.get(BASE + '/api/bootstrap')).json()
        other = next((c for c in boot['connections'] if c['id'] != original_connection and c['status'] == 'ready'), None)
        if other:
            await page.locator('[data-tab="home"]').click()
            await page.locator(f'[data-connection="{other["id"]}"]').click()
            await page.wait_for_function("[...document.querySelectorAll('#raid-team .formation-slot')].every(e=>!e.dataset.characterUid&&!e.disabled)")
            await raid(); assert await slots('raid-team') == [''] * 5
            await page.locator('[data-tab="home"]').click()
            await page.locator(f'[data-connection="{original_connection}"]').click()
            await page.wait_for_function("document.querySelector('#raid-team .formation-slot')?.dataset.characterUid==='5011'")
            await raid(); assert await slots('raid-team') == expected
        # Failed save leaves the draft editable and the saved team intact.
        await page.locator('#raid-team .formation-slot').first.click()
        await page.locator('#formation-team .formation-slot').first.click()
        async def reject_save(route):
            if route.request.method == 'PUT': await route.fulfill(status=503,json={'message':'테스트 저장 실패'})
            else: await route.continue_()
        await page.route('**/api/accounts/*/formation', reject_save)
        await page.locator('#formation-save').click()
        await page.wait_for_function("document.querySelector('#status').textContent==='테스트 저장 실패'")
        assert await page.locator('#formation-editor').is_visible()
        assert await slots() == ['', *expected[1:]]
        await page.unroute('**/api/accounts/*/formation', reject_save)
        await page.locator('#formation-cancel').click()
        assert await slots('raid-team') == expected
        # Browser storage is not the source of truth; a restarted backend serves the saved team.
        process.terminate(); process.wait(timeout=15)
        process = start(target)
        await page.evaluate('localStorage.clear()')
        await ready(); await raid(); assert await slots('raid-team') == expected
        for width in [1500,850,500]:
            await page.set_viewport_size({'width':width,'height':1100})
            await page.locator('#raid-team').screenshot(path=str(OUTPUT / f'team-{width}.png'))
            assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert await page.locator('#raid-team img').evaluate_all('(items)=>items.every(i=>i.complete&&i.naturalWidth>0)')
        # Normal catalogue click keeps its original details behavior and ordering.
        await page.set_viewport_size({'width':1500,'height':1100})
        await page.locator('[data-tab="nikkes"]').click()
        assert await page.locator('.nikke-card').evaluate_all('(items)=>items.map(i=>i.dataset.characterUid)') == order
        await choose('5004'); await page.wait_for_selector('#character-save-bar')
        assert await page.locator('#nikke-detail-back').inner_text() == '‹ 니케 도감'
        await page.locator('#nikke-detail-back').click()
        assert await page.locator('#nikke-browser').is_visible()
        assert not await page.locator('#formation-editor').is_visible()
        # Replay request uses saved team order. Intercept execution, not formation storage.
        sent = []
        async def replay(route):
            sent.append(route.request.post_data_json)
            await route.fulfill(status=409, json={'message':'검산 요청 검증 완료'})
        await page.route('**/api/runtime/skill-replays', replay)
        await raid(); await page.locator('#run-replay').click()
        await page.wait_for_function("document.querySelector('#replay-result').textContent==='검산 요청 검증 완료'")
        assert sent[0]['characterIds'] == expected
        # Empty formation can be explicitly saved and restored too.
        await page.locator('#raid-team .formation-slot').first.click()
        for index in range(5): await page.locator('#formation-team .formation-slot').nth(index).click()
        await page.locator('#formation-save').click()
        await page.wait_for_selector('#raid-team')
        await ready(); await raid(); assert await slots('raid-team') == [''] * 5
        assert not errors, errors
        await browser.close()
        print(json.dumps({'formationUi':'passed','storage':'isolated SQLite + backend restart','widths':[1500,850,500],'pageErrors':errors}))
    return process


if __name__ == '__main__':
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data = prepare()
    server = start(data)
    try:
        server = asyncio.run(check(data, server))
    finally:
        # Also stop a backend restarted by the test if an assertion failed afterwards.
        try:
            with urllib.request.urlopen(BASE + '/api/bootstrap') as response: boot = json.load(response)
            urllib.request.urlopen(urllib.request.Request(BASE + '/api/desktop/shutdown', data=b'', headers={'X-Nikke-Token':boot['token']})).close()
        except OSError: pass
        if server.poll() is None: server.terminate()

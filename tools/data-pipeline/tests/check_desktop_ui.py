"""Read-only saved account checks + one explicitly labelled P03 simulation saved locally.

Run against dev:sync or the desktop's localhost server. No real account edits/logins.
"""
import asyncio
import json
from pathlib import Path
import sys
import urllib.request
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[3]
OUTPUT=ROOT/'artifacts/desktop/ui'
BASE='http://127.0.0.1:5180'

def get(path):
    with urllib.request.urlopen(BASE+'/api'+path) as r:return json.load(r)

async def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    boot=get('/bootstrap');connection=next(c for c in boot['connections'] if c['status']=='ready')
    snapshot=get('/accounts/'+connection['accountId']+'/snapshot')
    results={};errors=[];failed=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='msedge',headless=True)
        page=await browser.new_page(viewport={'width':1500,'height':940},device_scale_factor=1)
        # Keep this smoke's fixed P03 inputs without overwriting the user's saved formation.
        async def fixture_formation(route):
            if route.request.method == 'GET':
                await route.fulfill(json={'accountId':snapshot['accountId'],'slots':['5011','5008','5009','5004','5044']})
            else: await route.continue_()
        await page.route('**/api/accounts/*/formation',fixture_formation)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda r:failed.append((r.status,r.url)) if r.status>=400 else None)
        await page.goto(BASE+'/editor/')
        await page.wait_for_function("document.body.dataset.ready==='true'")
        await page.locator('[data-tab="nikkes"]').click()
        count=await page.locator('.nikke-card').count();assert count>=len(snapshot['characters'])
        results['cards']=count;results['owned']=await page.locator('.nikke-card[data-owned="true"]').count()
        assert results['owned']==len(snapshot['characters'])
        await page.screenshot(path=str(OUTPUT/'cards.png'))
        checked=[]
        for cid in ['5011','5008','5009','5004','5044']:
            await page.locator(f'.nikke-card[data-character-uid="{cid}"]').click()
            await page.wait_for_function("Array.from(document.querySelectorAll('.equipment-stat-rows')).some(el=>!el.textContent.includes('미확인'))")
            assert await page.locator('.overload-row > select').count()==12
            assert await page.locator('.overload-row > label > select').count()==12
            assert await page.locator('[data-lock-slot],.calculation,.simul-option-row').count()==0
            checked.append(cid)
            if cid=='5004':
                await page.screenshot(path=str(OUTPUT/'alice-detail.png'),full_page=True)
                await page.locator('[data-detail-tab="skill"]').click()
                expected=next(c for c in snapshot['characters'] if c['characterId']==cid)['skills']
                assert [int(v) for v in await page.locator('#skill-editor input').evaluate_all('(items)=>items.map(i=>i.value)')]==list(expected.values())
                await page.locator('[data-detail-tab="equipment"]').click()
            await page.locator('#nikke-detail-back').click()
        results['localLabDetailsChecked']=checked
        await page.locator('#nikke-search').fill('레드 후드')
        for step in ['1','2','3']:
            await page.locator(f'[data-filter-select="nikke-filter-burst"][data-filter-value="{step}"]').click()
            assert await page.locator('.nikke-card[data-character-uid="5101"]').count()==1
        await page.locator('#nikke-search').fill('')
        await page.locator('[data-filter-select="nikke-filter-burst"][data-filter-value="all"]').click()
        await page.set_viewport_size({'width':738,'height':850})
        for tab in ['home','account','nikkes','raid','import','advanced']:
            label=page.locator(f'[data-tab="{tab}"] span').last
            assert await label.is_visible(),tab
        results['smallScreenNavigation']=True
        await page.set_viewport_size({'width':1500,'height':940})
        await page.locator('[data-tab="raid"]').click()
        await page.locator('#replay-form [name="seconds"]').fill('30')
        await page.locator('#replay-form [name="burst"]').select_option('5004')
        await page.locator('#run-replay').click()
        await page.locator('#replay-result h2').wait_for(timeout=45000)
        totalText=await page.locator('#replay-result h2').inner_text()
        assert float(totalText.removeprefix('총 대미지 ').replace(',',''))>0
        results['replay']=totalText
        await page.screenshot(path=str(OUTPUT/'replay.png'))
        # Account/collection diagnostics are displayed; this acceptance does not save personal edits.
        await page.locator('[data-tab="import"]').click()
        assert await page.locator('#sync').is_enabled()
        assert await page.locator('#refresh-images').is_enabled()
        await page.locator('[data-tab="account"]').click()
        assert await page.locator('#account-form [name="synchro"]').input_value()==str(snapshot['synchroLevel'])
        results['brokenImages']=await page.evaluate("[...document.images].filter(x=>x.offsetParent!==null&&x.complete&&!x.naturalWidth).map(x=>x.src)")
        results['pageErrors']=errors;results['httpFailures']=failed
        assert not results['brokenImages'] and not errors and not failed,results
        await browser.close()
    (OUTPUT/'acceptance.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False))

if __name__=='__main__':asyncio.run(main())

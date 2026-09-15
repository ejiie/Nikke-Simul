"""Read-only live UI with simulation requests routed to the isolated P04 backend."""
import asyncio,json,urllib.request
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[3]; OUT=ROOT/'artifacts/p04/verification'
async def main():
    base='http://127.0.0.1:5180'; isolated='http://127.0.0.1:5188'
    boot=json.load(urllib.request.urlopen(isolated+'/api/bootstrap'))
    errors=[];summary={}
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='msedge',headless=True)
        page=await browser.new_page(viewport={'width':1500,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        async def formation(route):
            assert route.request.method=='GET'
            await route.fulfill(json={'accountId':'ui-readonly-fixture','slots':['5011','5008','5009','5004','5044']})
        async def replay(route):
            data=route.request.post_data_json
            assert data['scenarioLevel']==400, 'Solo raid challenge must use level 400'
            response=await page.request.post(isolated+'/api/runtime/skill-replays',data=data,headers={'X-Nikke-Token':boot['token']})
            await route.fulfill(response=response)
        await page.route('**/api/accounts/*/formation',formation)
        await page.route('**/api/runtime/skill-replays',replay)
        await page.goto(base+'/editor/');await page.wait_for_function("document.body.dataset.ready==='true'")
        await page.locator('[data-tab="raid"]').click()
        assert await page.locator('[name="burst"]').input_value()=='auto'
        assert await page.locator('[data-prescribed-burst]').is_hidden()
        await page.locator('[name="burstRotation"]').select_option('5004,5044')
        assert await page.locator('#replay-form [name="level"]').count()==0
        await page.locator('#run-replay').click()
        await page.wait_for_function("document.querySelector('#replay-result').textContent.includes('자동 버스트 사이클')",timeout=90000)
        assert await page.locator('#replay-result .simul-result-grid > article').count()==5
        rows=await page.locator('#replay-result .table-scroll').first.locator('tbody tr').count();assert rows>=4
        summary['fullBurstRows']=rows
        await page.locator('#replay-result').scroll_into_view_if_needed()
        await page.screenshot(path=str(OUT/'ui-result.png'))
        for width in [500,850,1500]:
            await page.set_viewport_size({'width':width,'height':1000})
            assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),width
        await page.locator('[name="burst"]').select_option('5004')
        assert await page.locator('#automatic-burst-options').is_hidden()
        assert await page.locator('[data-prescribed-burst]').is_visible()
        await page.locator('[name="burst"]').select_option('none')
        assert await page.locator('[data-prescribed-burst]').is_hidden()
        await page.locator('[name="burst"]').select_option('auto')
        await page.locator('[name="burstRotation"]').select_option('5044,5004')
        await page.locator('[name="manualCharacter"]').select_option('5004')
        await page.locator('[name="manualStyle"]').select_option('tap')
        await page.locator('#run-replay').click()
        await page.wait_for_function("document.querySelector('#replay-result').textContent.includes('자동 버스트 사이클')",timeout=90000)
        assert not errors,errors
        await browser.close()
    summary.update({'modes':3,'widths':[500,850,1500],'manualTap':True,'pageErrors':0,'accountEdits':0})
    (OUT/'ui-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary))
if __name__=='__main__':asyncio.run(main())

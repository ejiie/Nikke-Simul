"""Real saved data, read-only browser checks. Save request is intercepted, never sent."""
import asyncio,json,urllib.request,os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[3]
BASE=os.environ.get('NIKKE_UI_TEST_URL','http://127.0.0.1:5180')
def get(path):
    with urllib.request.urlopen(BASE+'/api'+path) as response:return json.load(response)

async def main():
    output=ROOT/'artifacts/desktop/account-ui';output.mkdir(parents=True,exist_ok=True)
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='msedge',headless=True)
        page=await browser.new_page(viewport={'width':1500,'height':1000})
        errors=[];failed=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda r:failed.append(r.url) if r.status>=400 else None)
        await page.goto(BASE+'/editor/');await page.wait_for_function("document.body.dataset.ready==='true'")
        await page.locator('[data-tab="account"]').click()
        assert await page.locator('.console-card').count()==9
        assert await page.locator('.console-card .console-image').count()==9
        assert await page.locator('#general-console-experience').count()==0
        assert await page.locator('.cube-card').count()==16
        await page.locator('.cube-card[data-cube-uid="1000303"]').click()
        await page.locator('#account-cube-level').select_option('8')
        assert await page.locator('.cube-card[data-cube-uid="1000303"] .cube-level').inner_text()=='Lv. 8'
        await page.evaluate('window.scrollTo(0,0)')
        await page.screenshot(path=str(output/'account.png'),full_page=True)
        captured=[]
        async def intercept(route):
            captured.append(route.request.post_data_json)
            await route.fulfill(status=200,content_type='application/json',body='{}')
        await page.route('**/api/accounts/*/overrides',intercept)
        await page.locator('#account-form button[type="submit"]').click()
        await page.wait_for_function("document.querySelector('#status').textContent.includes('저장했습니다')")
        assert captured[0]['cubeLevels']=={'1000303':8},captured
        await page.locator('[data-tab="nikkes"]').click()
        await page.locator('.nikke-card[data-character-uid="5004"]').click()
        await page.wait_for_function("document.querySelectorAll('.equipment-stat-rows strong').length>0")
        growth=await page.evaluate("""async()=>{
            const {renderLocalLabDetail}=await import('/editor/local-lab-adapter.js');
            const boot=await (await fetch('/api/bootstrap')).json();
            const conn=boot.connections.find(c=>c.id===localStorage.getItem('nikke-sync-connection'));
            const snap=await (await fetch(`/api/accounts/${conn.accountId}/snapshot`)).json();
            const data=await (await fetch('/api/presentation')).json();
            const original=snap.characters.find(c=>c.characterId==='5004');
            const item=data.characters.find(c=>c.characterUid==='5004');
            const results=[];
            for(const core of [0,1,7]){
                renderLocalLabDetail({...original,core,limitBreak:3},item,null,null,data);
                const stars=document.querySelector('.growth-joined .growth-stars').getBoundingClientRect();
                const badge=document.querySelector('.growth-joined .detail-core-evolve');
                results.push({core,count:document.querySelectorAll('.growth-stars img[src*="star-filled"]').length,
                  visible:!!badge,sameRow:!badge||Math.abs((badge.getBoundingClientRect().top+badge.getBoundingClientRect().height/2)-(stars.top+stars.height/2))<1,
                  right:!badge||Math.abs(badge.getBoundingClientRect().left-stars.right)<1});
            }
            return results;
        }""")
        assert all(r['count']==3 and r['sameRow'] and r['right'] and r['visible']==(r['core']>=1) for r in growth),growth
        await page.locator('#nikke-core-panel').screenshot(path=str(output/'growth.png'))
        for width in [850,500]:
            await page.set_viewport_size({'width':width,'height':1000})
            boxes=await page.locator('.growth-joined > *').evaluate_all('(els)=>els.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y+r.height/2,right:r.right}})')
            assert abs(boxes[0]['y']-boxes[1]['y'])<1 and abs(boxes[1]['x']-boxes[0]['right'])<1,boxes
        broken=await page.locator('img').evaluate_all('(imgs)=>imgs.filter(i=>i.complete&&!i.naturalWidth).map(i=>i.src)')
        assert not errors and not failed and not broken,(errors,failed,broken)
        result={'consoleCards':9,'cubeCards':16,'savePayloadVerified':True,'growthCases':growth,'errors':errors,'brokenImages':broken}
        (output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result))
        await browser.close()

if __name__=='__main__':asyncio.run(main())

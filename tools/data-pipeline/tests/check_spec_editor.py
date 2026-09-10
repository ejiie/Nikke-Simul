"""End-to-end edit/save checks against the isolated spec-edit-test data root, never live data."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[3]
BASE='http://127.0.0.1:5186'

async def main():
    output=ROOT/'artifacts/desktop/spec-editor-ui';output.mkdir(parents=True,exist_ok=True)
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='msedge',headless=True)
        page=await browser.new_page(viewport={'width':1500,'height':1100})
        errors=[];failed=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda r:failed.append((r.status,r.url)) if r.status>=400 else None)
        await page.goto(BASE+'/editor/')
        await page.wait_for_function("document.body.dataset.ready==='true'")
        await page.locator('[data-tab="nikkes"]').click()
        await page.locator('.nikke-card[data-character-uid="5004"]').click()
        await page.wait_for_selector('#character-save-bar')
        await page.wait_for_function("document.querySelectorAll('.equipment-image').length===4 && Array.from(document.querySelectorAll('.equipment-image')).every(i=>i.complete&&i.naturalWidth>0)")
        before=await page.evaluate("async()=>{const m=await import('/editor/local-lab-adapter.js');return m.detailDraft()}")
        before_report=await page.locator('#detail-final-stats').inner_text()
        # +/- crosses MLB -> core 1 and back, then reaches both bounds.
        down=page.get_by_role('button',name='돌파·코어 강화 하락',exact=True)
        up=page.get_by_role('button',name='돌파·코어 강화 상승',exact=True)
        while await down.is_enabled():await down.click()
        assert await page.locator('.growth-joined .detail-core-evolve').count()==0
        for _ in range(3):await up.click()
        assert await page.locator('.growth-stars button[aria-pressed="true"]').count()==3
        assert await page.locator('.growth-joined .detail-core-evolve').count()==0
        await up.click();assert await page.locator('.growth-joined .detail-core-evolve').inner_text()=='1'
        await down.click();assert await page.locator('.growth-joined .detail-core-evolve').count()==0
        for _ in range(7):await up.click()
        assert not await up.is_enabled()
        assert await page.locator('.growth-joined .detail-core-evolve').inner_text()=='MAX'
        # A visually invalid numeric field must not save the previous valid draft instead.
        await down.click()
        await page.locator('#nikke-core-panel input').nth(0).fill('10001')
        await page.locator('#nikke-core-panel input').nth(0).press('Tab')
        await page.locator('#character-save-bar').get_by_role('button',name='Save',exact=True).click()
        assert '범위를 확인' in await page.locator('#character-save-bar').inner_text()
        await page.get_by_role('button',name='변경 취소',exact=True).click()
        while await up.is_enabled():await up.click()
        await page.locator('#nikke-core-panel').screenshot(path=str(output/'growth-max.png'))
        cancel=page.get_by_role('button',name='변경 취소',exact=True)
        if await cancel.is_enabled():await cancel.click()
        # Equipment type selection uses the original Local Lab picker.
        head=page.locator('.equipment-card').nth(0)
        await head.locator('.equipment-icon').click()
        await head.locator('.equipment-picker-choice').filter(has_text='9티어').click()
        assert await head.locator('.overload-row select:enabled').count()==0
        await head.locator('.equipment-icon').click()
        await head.locator('.equipment-picker-choice').filter(has_text='10티어').click()
        await head.locator('select[aria-label="오버로드 옵션 1"]').select_option('StatAtk')
        await head.locator('select[aria-label="오버로드 옵션 1 수치"]').select_option('1463:4')
        assert await head.locator('select[aria-label="오버로드 옵션 1 수치"] option').count()==15
        await head.locator('select[aria-label="오버로드 옵션 2"]').select_option('StatChargeTime')
        await head.locator('select[aria-label="오버로드 옵션 2 수치"]').select_option('609:4')
        await head.locator('.equipment-enhancement input').fill('4');await head.locator('.equipment-enhancement input').press('Tab')
        await page.locator('#nikke-core-panel input').nth(0).fill('400');await page.locator('#nikke-core-panel input').nth(0).press('Tab')
        await page.locator('#nikke-core-panel input').nth(1).fill('20');await page.locator('#nikke-core-panel input').nth(1).press('Tab')
        await page.locator('[data-detail-tab="skill"]').click()
        await page.locator('#skill-editor input').nth(0).fill('8');await page.locator('#skill-editor input').nth(0).press('Tab')
        await page.locator('[data-detail-tab="collection"]').click()
        # SR doll matches Alice's weapon; do not grant an unrelated favorite.
        await page.locator('#collection-editor select').select_option('100602')
        await page.locator('#collection-editor input').fill('10');await page.locator('#collection-editor input').press('Tab')
        await page.get_by_label('장착 큐브',exact=True).select_option('1000303')
        await page.get_by_label('장착 큐브 레벨',exact=True).select_option('8')
        await page.wait_for_function("document.querySelector('#detail-final-stats').textContent.startsWith('체력')")
        after=await page.evaluate("async()=>{const m=await import('/editor/local-lab-adapter.js');return m.detailDraft()}")
        assert after['equipment'][0]['lines'][1]['normalizedValue']==-.0609
        assert after['level']==400 and after['bond']==20 and after['skills']['1']==8
        assert after['collectionGrade']=='SR' and after['collectionLevel']==10
        # Navigating to another character and back retains the unsaved draft.
        await page.locator('#nikke-detail-back').click()
        await page.locator('.nikke-card[data-character-uid="5011"]').click();await page.wait_for_function("document.querySelector('#nikke-selected-name').textContent.includes('리타')")
        await page.locator('#nikke-detail-back').click()
        await page.locator('.nikke-card[data-character-uid="5004"]').click()
        await page.wait_for_function("document.querySelector('#nikke-core-panel input')?.value==='400'")
        async with page.expect_response('**/api/accounts/*/characters/5004/edit') as saving:
            await page.locator('#character-save-bar').get_by_role('button',name='Save',exact=True).click()
        response=await saving.value
        assert response.status==200,await response.text()
        saved=await response.json();assert saved['characters'][next(i for i,c in enumerate(saved['characters']) if c['characterId']=='5004')]['buildSource']=='manual'
        prior=(await (await page.request.get(BASE+'/api/snapshots/'+saved['previousId'])).json())
        assert next(c for c in prior['characters'] if c['characterId']=='5004')==before
        await page.reload();await page.wait_for_function("document.body.dataset.ready==='true'")
        await page.locator('[data-tab="nikkes"]').click();await page.locator('.nikke-card[data-character-uid="5004"]').click()
        await page.wait_for_function("document.querySelector('#nikke-core-panel input')?.value==='400'")
        loaded=await page.evaluate("async()=>{const m=await import('/editor/local-lab-adapter.js');return m.detailDraft()}")
        assert loaded['equipment'][0]['lines'][0]['normalizedValue']==.1463 and loaded['cubeLevel']==8 and loaded['skills']['1']==8
        await page.locator('[data-detail-tab="equipment"]').click()
        await page.screenshot(path=str(output/'equipment.png'),full_page=True)
        for width in [1500,850,500]:
            await page.set_viewport_size({'width':width,'height':1100})
            boxes=await page.locator('.growth-joined').evaluate('(e)=>({width:e.getBoundingClientRect().width,scroll:document.documentElement.scrollWidth,viewport:innerWidth})')
            assert boxes['scroll']<=boxes['viewport'],boxes
        broken=await page.locator('img').evaluate_all('(imgs)=>imgs.filter(i=>i.complete&&!i.naturalWidth).map(i=>i.src)')
        assert not errors and not failed and not broken,(errors,failed,broken)
        result=dict(saved=True,priorSnapshotPreserved=True,images=4,options=9,optionLevels=15,growthBoundaries=True,draftNavigation=True,widths=[1500,850,500],errors=errors)
        (output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result))
        await browser.close()

if __name__=='__main__':asyncio.run(main())

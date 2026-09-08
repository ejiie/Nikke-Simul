"""Read-only live snapshot UI audit; only downloads local calibration artifacts."""
import json
from pathlib import Path
import re
import math
from collections import Counter
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / 'artifacts/p02-buff-fix'

def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge',headless=True)
        context = browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
        page=context.new_page(); errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:5180/')
        page.get_by_role('searchbox',name='니케 검색').fill('앨리스')
        page.get_by_role('button',name=re.compile(r'^앨 앨리스 Lv')).click()
        page.get_by_label('검산용 적용 레벨').fill('400')
        page.get_by_role('button',name='스탯 계산',exact=True).click()
        page.locator('.final-stats').wait_for()
        assert page.locator('.final-stats dd').count()==3
        assert page.locator('.calc-output .calc-table').count()==0
        assert not page.locator('.hit-form').is_visible()
        checks.append('only_three_final_stats_visible')
        page.locator('.calculation').scroll_into_view_if_needed()
        page.screenshot(path=str(OUTPUT/'ui-desktop.png'))
        page.set_viewport_size({'width':390,'height':844})
        page.locator('.calculation').scroll_into_view_if_needed()
        page.screenshot(path=str(OUTPUT/'ui-mobile.png'))
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.set_viewport_size({'width':1440,'height':1000})
        page.get_by_text('단일 히트 검산',exact=True).click()
        page.get_by_label('풀차지',exact=True).check()
        page.get_by_label('추가 공격력 버프 (%)',exact=True).fill('50, 30')
        with page.expect_response('**/api/calculations/hit') as response:
            page.get_by_role('button',name='정수화 후보 비교').click()
        result=response.value.json()
        page.get_by_role('button',name='검산 기록 저장 (JSON)').wait_for()
        assert result['input']['fullCharge'] is True
        assert len(result['candidates'])==3; checks.append('three_rounding_candidates')
        hit=result['input']; native=hit['statAttack']; rates=Counter()
        for buff in hit['attackBuffs']+hit['runtimeAttackBuffs']: rates[buff['rate']]+=buff['stacks']
        expected_attack=native+sum(math.floor(native*(rate*count)+.5) for rate,count in rates.items())
        assert result['effectiveAttack']==expected_attack
        assert float(page.locator('[data-stat="atk"]').inner_text().replace(',',''))==native
        checks.append('OL_and_manual_buffs_share_native_attack')
        expected=result['candidates'][0]['damage']
        page.get_by_label('실측 대미지 (선택)').fill(str(int(expected)))
        assert '다시 비교' in page.locator('.hit-result').inner_text(); checks.append('edited_input_invalidates_old_result')
        with page.expect_response('**/api/calculations/hit') as response:
            page.get_by_role('button',name='정수화 후보 비교').click()
        assert response.value.json()['candidates'][0]['residual']==0; checks.append('observed_residual')
        with page.expect_download() as download:
            page.get_by_role('button',name='검산 기록 저장 (JSON)').click()
        target=OUTPUT/'ui-export.json'; download.value.save_as(target)
        exported=json.loads(target.read_text(encoding='utf-8'))
        assert exported['stats']['accountSnapshotId']
        assert exported['stats']['calculationDataId']
        assert exported['comparison']['observedDamage']==expected
        assert exported['schemaVersion']==2
        assert exported['stats']['nativeStats']['atk']==native
        assert exported['stats']['permanentBuffs']['attack']==hit['attackBuffs']
        assert 'runtimeAttackBuffs' in exported['editedFields']
        assert 'fullCharge' in exported['editedFields']; checks.append('export_contains_inputs_versions_and_observation')
        # The entered value above is synthetic UI validation, never presented as a real observation.
        page.locator('.calculation').scroll_into_view_if_needed()
        page.screenshot(path=str(OUTPUT/'ui-hit.png'))
        page.get_by_label('크리 명중',exact=True).check(); page.get_by_label('크리 허용',exact=True).uncheck()
        page.get_by_role('button',name='정수화 후보 비교').click()
        page.get_by_text('이 타격에서 허용하지 않은 크리·코어·차지 조건입니다.',exact=True).wait_for()
        checks.append('invalid_hit_condition_rejected')
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'); checks.append('mobile_no_horizontal_overflow')
        page.locator('.calculation').scroll_into_view_if_needed()
        assert not errors,errors; checks.append('no_browser_runtime_errors')
        browser.close()
    report={'passed':len(checks),'checks':checks,'observationInUiTest':'synthetic value equal to one candidate; not game evidence'}
    (OUTPUT/'ui-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report))

if __name__=='__main__': main()

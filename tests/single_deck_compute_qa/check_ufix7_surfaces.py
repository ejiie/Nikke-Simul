"""QA-authored screen-path fault injection on a real isolated API/browser.

Normal responses come from API. Explicit fault cases replace individual fields or
abort transport; these are NOT claimed as naturally occurring server failures.
No owner fixtures, expected values, or test helpers are imported.
"""
import argparse,json,re,sqlite3,time
from copy import deepcopy
from playwright.sync_api import sync_playwright
from check_f2_conditions import Session

MARK='qa_private_wire_value'

def run(s,ctx):
    s.snapshot['issues']=[dict(code=MARK,path='characters.5004.equipment.head',message='검사 필요: effectiveAttack'),
                          dict(code=MARK,path='characters.5004.equipment.torso',message='검사 필요: calculation.terms')]
    with sqlite3.connect(s.data/'accounts.db') as db:db.execute('UPDATE snapshots SET payload=?',(json.dumps(s.snapshot),))
    s.start(ctx.request);assert s.call('accounts/synthetic-account/formation',dict(slots=s.ids),'PUT')[0].ok
    def page_for(routes=(),init=None):
        p=ctx.new_page();p.on('pageerror',lambda e:s.report['errors'].append(dict(message=str(e),stack=e.stack)))
        for pattern,handler in routes:p.route(pattern,handler)
        if init:p.add_init_script(init)
        p.goto(s.base+'/editor/');p.wait_for_selector('body[data-ready="true"]');return p
    def snap(p,label,selector='body',words=(),forbidden=(MARK,)):
        text=p.locator(selector).inner_text();s.save(label,dict(text=text,selector=selector))
        s.check(label,all(w in text for w in words) and all(w not in text for w in forbidden),dict(required=words,forbidden=forbidden,text=text))
        p.screenshot(path=str(s.run/(label+'.png')),full_page=True);return text
    def mutate(fn):
        def handle(route):
            response=route.fetch();body=response.json();fn(body);route.fulfill(response=response,json=body)
        return handle
    def err(code=MARK,status=409,message=MARK):
        return lambda route:route.fulfill(status=status,json=dict(code=code,message=message))
    abort=lambda route:route.abort('failed')
    # Real persisted diagnostics, not a mocked API response.
    p=page_for();p.locator('[data-tab="advanced"]').click()
    snap(p,'persisted-mixed-Korean-internal-path','#advanced-content',forbidden=('effectiveAttack','calculation.terms'))
    s.check('diagnostic hidden path preserved',p.locator('[data-issue-path]').first.get_attribute('data-issue-path')=='characters.5004.equipment.head')
    p.close()
    # Each bootstrap branch is independently reached using this QA's fault fields.
    for mode,expected in [('awaiting_login','열린 브라우저에서 로그인하세요.'),('reauth_required','다시 로그인해야 합니다.'),('job','수집이 중단되었습니다. 다시 시도하세요.'),('failure','계정 연결에 실패했습니다.')]:
        def alter(b,mode=mode):
            c=b['connections'][0];c['message']=MARK
            if mode in ['awaiting_login','reauth_required']:c['status']=mode
            if mode=='job':b['jobs']=[dict(id='qa-job',connectionId=c['id'],status='failed',message=MARK)]
            if mode=='failure':b['connectionFailure']=dict(message=MARK)
            other=deepcopy(c);other.update(id='qa-inactive',accountId=None,status='ready');b['connections'].append(other)
        p=page_for([('**/api/bootstrap',mutate(alter))]);p.locator('[data-tab="import"]').click();snap(p,'bootstrap-'+mode,'body',words=(expected,))
        p.locator('[data-tab="home"]').click();snap(p,'connection-card-'+mode,'#account-list',words=('저장된 스펙 열기',));p.close()
    p=page_for([('**/api/presentation/status',mutate(lambda b:b.update(status='failed',revision=731,message=MARK)))])
    snap(p,'image-update-message','#status',words=('이미지 갱신 상태가 바뀌었습니다.',));p.close()
    p=page_for([('**/api/presentation/refresh',lambda r:r.fulfill(status=200,json=dict(message=MARK)))])
    p.locator('[data-tab="import"]').click();p.locator('#refresh-images').click();p.wait_for_timeout(350)
    snap(p,'image-refresh-message','#status',words=('이미지 갱신을 요청했습니다.',));p.close()
    # Unknown weapon code in the actual fetched catalog (isolated response field fault).
    def unknown_weapon(b):b['weaponRanges'][0]['weaponType']=MARK
    p=page_for([('**/api/runtime/combat-conditions',mutate(unknown_weapon))]);p.locator('[data-tab="raid"]').click();p.locator('[data-cond-open="distance"]').click();p.wait_for_selector('tr[data-weapon="'+MARK+'"]')
    snap(p,'unknown-weapon','dialog[open]',words=('무기군 미확인',));p.close()
    for label,pattern,handler in [('profile-transport','**/api/runtime/combat-conditions',abort),('profile-unknown-reason','**/api/snapshots/*/combat-conditions?*',lambda r:r.fulfill(status=409,json=dict(code='combat_profile_invalid',message=MARK,characterId='5004',field='combatProfiles.characters.5004.bonusRangeMin',reason=MARK)))]:
        p=page_for([(pattern,handler)]);p.locator('[data-tab="raid"]').click();p.locator('[data-cond-open="distance"]').click();p.wait_for_timeout(400)
        snap(p,label,'dialog[open]',words=('사유 미확인',) if 'reason' in label else ('요청을 처리하지 못했습니다',));p.close()
    p=page_for([('**/api/presentation/solo-raid-bosses',abort)]);p.locator('[data-tab="raid"]').click();p.wait_for_timeout(200)
    snap(p,'boss-list-transport','#raid-content',words=('요청을 처리하지 못했습니다',));p.close()
    # Transport caught in app, formation, tactics, log/export, character detail.
    p=page_for([('**/api/runtime/skill-replays',abort)]);p.locator('[data-tab="raid"]').click();p.locator('#run-replay').click();p.wait_for_timeout(150)
    snap(p,'replay-transport','#replay-result',words=('요청을 처리하지 못했습니다',),forbidden=('Failed to fetch',));p.close()
    def fail_put(route):abort(route) if route.request.method=='PUT' else route.continue_()
    p=page_for([('**/api/accounts/*/formation',fail_put)]);p.locator('[data-tab="raid"]').click();p.locator('#raid-team [data-slot="0"]').click();p.locator('#formation-save').click();p.wait_for_timeout(150)
    snap(p,'formation-save-transport','#status',words=('요청을 처리하지 못했습니다',));p.close()
    p=page_for([('**/api/accounts/*/burst-tactic',fail_put)]);p.locator('[data-tab="raid"]').click();p.locator('#btn-force-save-server').click();p.wait_for_timeout(300)
    snap(p,'tactic-save-transport','#status',words=('요청을 처리하지 못했습니다',));p.close()
    p=page_for(init="window.qaStatus=[];const td=Object.getOwnPropertyDescriptor(Node.prototype,'textContent');Object.defineProperty(Node.prototype,'textContent',{...td,set(v){if(this.id==='status')window.qaStatus.push(v);return td.set.call(this,v)}});const original=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k.includes('tactic'))throw new Error('qa_private_wire_value');return original.call(this,k,v)}")
    p.locator('[data-tab="raid"]').click();p.locator('#btn-force-save-server').click();p.wait_for_timeout(250)
    history=p.evaluate('window.qaStatus');s.save('tactic-local-storage-error',dict(statusHistory=history));s.check('tactic-local-storage-error',any('로컬 저장 실패' in x for x in history) and all(MARK not in x for x in history),history);p.close()
    # Existing QA source replay generated by this same session; no imported mock result.
    req=dict(snapshotId=s.snapshot['id'],characterIds=s.ids,conditionProfile='legacy',conditions=dict(roundingPolicy='client_f32',damageLog=dict(characterId=s.ids[2]),combat=dict(durationFrames=120,enemyDefense=30925,critMode='off',pelletCoefficientPolicy='per_trigger')))
    saved=s.replay(req,'export-source')
    def redirect(route):route.continue_(url=s.base+'/api/runtime/skill-replays/'+saved['id'],method='GET',post_data='')
    p=page_for([('**/api/runtime/skill-replays',redirect)]);p.locator('[data-tab="raid"]').click();p.locator('#run-replay').click();p.wait_for_selector('#btn-export-json')
    for ext in ['json','csv']:
        pattern='**/damage-log/export.'+ext;p.route(pattern,err(status=503))
        p.locator('#btn-export-'+ext).click();p.wait_for_timeout(200);snap(p,'export-error-'+ext,'#status',words=('HTTP 503',));p.unroute(pattern)
    p.close()
    # Hardware/status/backend/attempt/error-code UI after a real tiny saved compute.
    request=dict(req,runs=1,phase='pilot',useSavedTactic=False,execution=dict(requested='cpu',maxWorkers=1));r,b=s.call('compute/experiments',request);assert r.status==202,b
    for _ in range(300):
        _,b=s.call('compute/experiments/'+b['id'])
        if b['state'] in ['completed','failed']:break
        time.sleep(.1)
    assert b['state']=='completed',b
    def hardware(h):
        h['probeFailures']=[MARK];h['gpus']=[dict(deviceId='qa-device-hash-abcdef',name='검수 장치',vendor='검수',driver='1.0',backend=MARK,runtimeStatus=MARK,selfTestStatus=MARK,correctnessStatus=MARK,benchmarkStatus=MARK,eligible=False)]
    def batch(x):x.update(state=MARK,attempt=2,errorCode=MARK);x['execution'].update(backend=MARK,requested=MARK)
    init='localStorage.setItem("nikke-single-deck-experiment",'+json.dumps(b['id'])+')'
    p=page_for([('**/api/compute/hardware',mutate(hardware)),('**/api/compute/experiments/'+b['id'],mutate(batch))],init)
    p.locator('[data-tab="stats"]').click();p.wait_for_function('document.querySelector("#compute-batch-state").innerText.includes("상태 미확인")',timeout=60000)
    snap(p,'compute-unknown-fields','#stats-content',words=('상태 미확인','기타 장치','시도 2회','드라이버','알 수 없는 오류','qa-device-hash-abcdef','장치 탐지 중 일부 항목이 실패했습니다.'))
    p.close()
    comparison=dict(baselineExperimentId=b['id'],candidateExperimentId=b['id'],changes=[],teamMeanDifference=0,differenceCi=dict(lower=-1,upper=1,confidence=.95,method='qa'),verdict=MARK,phase='pilot',methodVersion='qa-v1',gameVerified=False)
    p=page_for([('**/api/compute/experiments/'+b['id']+'/comparison',lambda r:r.fulfill(status=200,json=comparison))],init)
    p.locator('[data-tab="stats"]').click();p.wait_for_function('document.querySelector("#stats-content").innerText.includes("응답 판정")',timeout=60000)
    snap(p,'comparison-unknown-verdict','#stats-content',words=('응답 판정(미확인)','우열 미확정'));p.close()
    # Recognized refusal semantics still selected from raw code, visible labels Korean.
    for code in [MARK,'analysis_not_integrated','baseline_input_mismatch','warmup_excluded_from_statistics','baseline_required']:
        p=page_for([('**/api/compute/experiments',err(code))]);p.evaluate('localStorage.removeItem("nikke-single-deck-experiment")');p.locator('[data-tab="stats"]').click();p.wait_for_timeout(400);p.locator('#compute-runs').fill('1');p.locator('#compute-start').click();p.wait_for_timeout(200)
        snap(p,'compute-error-'+code,'#stats-content',words=('통계 모듈 미연결',) if code=='analysis_not_integrated' else (),forbidden=(MARK,'hitOverrides','baselineExperimentId'))
        p.close()
    # Browser detail read/preview/edit catch paths; abort before any edit reaches API.
    for stage in ['read','preview','edit']:
        route='**/api/snapshots/*/characters/5004/stats' if stage=='read' else '**/api/accounts/*/characters/5004/'+stage
        p=page_for([(route,abort)]);p.locator('[data-tab="nikkes"]').click();p.locator('#nikke-card-list [data-character-uid="5004"]').click();p.wait_for_selector('#nikke-core-panel input')
        if stage!='read':
            field=p.locator('#nikke-core-panel input').first;field.fill('399');field.press('Tab');p.wait_for_timeout(450)
            if stage=='edit':p.locator('#character-save-bar .primary').click()
        p.wait_for_timeout(300)
        snap(p,'detail-'+stage+'-transport','#character-save-bar' if stage=='edit' else '#status',words=('요청을 처리하지 못했습니다',),forbidden=('Failed to fetch',MARK));p.close()
    # App act and refresh catch sites use a real page and abort local requests.
    p=page_for([('**/api/accounts/*/overrides',abort)]);p.locator('[data-tab="account"]').click();p.locator('#account-form button[type="submit"]').click();p.wait_for_timeout(300)
    snap(p,'account-act-transport','#status',words=('요청을 처리하지 못했습니다',));p.close()
    p=page_for();p.route('**/api/bootstrap',abort);p.locator('#refresh-accounts').click();p.wait_for_timeout(300)
    snap(p,'refresh-transport','#status',words=('요청을 처리하지 못했습니다',));p.close()
    s.check('no browser exceptions in injected paths',not s.report['errors'],s.report['errors'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args();s=Session(a.dotnet)
    s.report.update(product='b401421',scope='U-FIX-7 QA-authored exceptional screen path injection',responseMocks='explicit QA field/error injection only; underlying server is real')
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport=dict(width=1500,height=1000));ctx.tracing.start(screenshots=True,snapshots=True,sources=True)
            run(s,ctx);ctx.tracing.stop(path=str(s.run/'trace.zip'));browser.close()
    except Exception as ex:s.report.update(status='aborted',error=repr(ex));raise
    finally:s.finish()
    return 0 if s.report['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())

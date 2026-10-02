"""Independent allow-list acceptance: persisted diagnostics and browser fault fields.

Positive messages are selected from production server call sites, not UI tests or
the generated registration list. API and browser are real; injected fields are
recorded explicitly. No registration generator or implementation fixture is used.
"""
import argparse,json,sqlite3
from copy import deepcopy
from playwright.sync_api import sync_playwright
from check_f2_conditions import Session,ROOT
from check_ufix7_families import open_page,display,put_copy,request

NORMAL=['필수 원천 필드가 없습니다.','수치 형식 또는 범위가 올바르지 않습니다.','스킬 레벨은 1~10입니다.','4부위 입력이 필요합니다.','열린 브라우저에서 로그인하세요.','로그인 세션이 만료되었습니다. 다시 로그인하세요.']
BAD=['검사 필요: terms[].name','검사 필요: terms[0].operation','검사 필요: cache/replays','검사 필요: runtime\\catalog','검사 필요: skill1Rate','검수 전용 미등록 안내입니다.',NORMAL[0]+' terms[].name',NORMAL[0]+'\n',' '+NORMAL[0]]

def mutate(fn):
    def handler(route):
        response=route.fetch();body=response.json();fn(body);route.fulfill(response=response,json=body)
    return handler

def page(s,ctx,routes=(),tab='raid'):
    p=ctx.new_page();p.on('pageerror',lambda e:s.report['errors'].append(dict(message=str(e),stack=e.stack)))
    for pattern,handler in routes:p.route(pattern,handler)
    p.goto(s.base+'/editor/');p.wait_for_selector('body[data-ready="true"]');p.locator('[data-tab="'+tab+'"]').click();return p

def observe(s,p,label,selector='body',png=False):
    text=p.locator(selector).inner_text();s.save(label,dict(text=text,selector=selector))
    if png:p.screenshot(path=str(s.run/(label+'.png')),full_page=True)
    return text

def diagnostics(s,ctx):
    # Assert our positive controls really come from production call sites.
    sources=['src/Nikke.Data/SnapshotNormalizer.cs','src/Nikke.Data/CalculationService.cs','src/Nikke.Data/CharacterEditService.cs','src/Nikke.Api/SyncCoordinator.cs','tools/data-pipeline/collector.py']
    corpus='\n'.join((ROOT/f).read_text(encoding='utf-8-sig') for f in sources)
    s.check('positive controls have server source provenance',all(x in corpus for x in NORMAL),dict(messages=NORMAL,sources=sources))
    s.snapshot['issues']=[dict(code='qa_diagnostic',path='qa.path.'+str(i),message=m) for i,m in enumerate(NORMAL+BAD)]
    changes=['계정 스탯 변경','계정 큐브 레벨 변경','스펙 변경 없음','최초 수집: 200명','앨리스: 스펙 변경','앨리스: head 장비/잠금 변경','terms[0].operation: 스펙 변경','앨리스: 미등록 변경','검사 필요: cache/replays']
    s.snapshot['changes']=changes
    with sqlite3.connect(s.data/'accounts.db') as db:db.execute('UPDATE snapshots SET payload=?',(json.dumps(s.snapshot),))
    s.start(ctx.request);assert s.call('accounts/synthetic-account/formation',dict(slots=s.ids),'PUT')[0].ok
    p=page(s,ctx,tab='advanced');rows=p.locator('[data-issue-path]').all_inner_texts();observe(s,p,'persisted-allowlist','#advanced-content',True)
    for i,m in enumerate(NORMAL):s.check('registered diagnostic '+str(i)+' preserved',rows[i]==m,dict(input=m,actual=rows[i]))
    for i,m in enumerate(BAD):s.check('unregistered diagnostic '+str(i)+' generic',rows[len(NORMAL)+i]=='수집 값을 확인해야 합니다.',dict(input=m,actual=rows[len(NORMAL)+i]))
    actual=p.locator('#advanced-content article').nth(1).locator('li').all_inner_texts()
    expected=changes[:5]+['앨리스: 머리 장비/잠금 변경','이름 미확인 니케: 스펙 변경','변경 내역 (상세 미확인)','변경 내역 (상세 미확인)']
    for i,want in enumerate(expected):s.check('change template '+str(i),actual[i]==want,dict(input=changes[i],actual=actual[i],expected=want))
    s.check('diagnostic attribute preserved',p.locator('[data-issue-path]').first.get_attribute('data-issue-path')=='qa.path.0')
    with sqlite3.connect(s.data/'accounts.db') as db:stored=json.loads(db.execute('SELECT payload FROM snapshots').fetchone()[0])
    s.check('diagnostic persisted source unchanged',stored['issues']==s.snapshot['issues'] and stored['changes']==changes);p.close()

def connections_errors(s,ctx):
    cases=[('registered',NORMAL[-1],True),('registered-number',NORMAL[2],True),('array',BAD[1],False),('unknown-korean',BAD[5],False),('suffix',BAD[6],False),('newline',BAD[7],False),('leading-space',BAD[8],False)]
    for name,raw,known in cases:
        p=page(s,ctx,[('**/api/bootstrap',mutate(lambda b:b.update(connectionFailure=dict(message=raw))))],tab='import')
        text=observe(s,p,'connection-'+name,'#import-content');expected=raw if known else '계정 연결에 실패했습니다.'
        s.check('connection '+name+' display',expected in text and (known or raw.strip() not in text),dict(raw=raw,text=text));p.close()
        # Even a server-supplied display:true cannot grant the trusted UI marker.
        p=page(s,ctx,[('**/api/runtime/skill-replays',lambda r:r.fulfill(status=400,json=dict(message=raw,display=True)))])
        p.locator('#run-replay').click();p.wait_for_function('!document.querySelector("#run-replay").disabled');text=observe(s,p,'error-'+name,'#replay-result')
        expected=raw if known else '요청을 처리하지 못했습니다 (HTTP 400).'
        s.check('error '+name+' display',text==expected,dict(raw=raw,actual=text,expected=expected));p.close()
    # A mapped error code, with private detail, preserves its useful Korean meaning.
    p=page(s,ctx,[('**/api/runtime/skill-replays',lambda r:r.fulfill(status=400,json=dict(message='solo_raid_duration_fixed_10800: qa.private.path')))])
    p.locator('#run-replay').click();p.wait_for_function('!document.querySelector("#run-replay").disabled');text=observe(s,p,'mapped-error','#replay-result')
    s.check('mapped error preserves numeric meaning','180초' in text and 'qa.private.path' not in text,text);p.close()

def hardware(s,ctx):
    for i,reason in enumerate(['gpu_unavailable','검사 필요: terms[0].operation','검수 전용 미등록 사유','constructor','toString','__proto__']+(['hasOwnProperty','valueOf','__defineGetter__','isPrototypeOf'] if s.expanded else [])):
        def change(h):
            h['probeFailures']=[NORMAL[0],BAD[0],BAD[7]]
            h['gpus']=[dict(deviceId='qa-kept-hash-9ac7',name='검수 장치',vendor='검수',driver='1.25',backend='gpu',runtimeStatus='failed',selfTestStatus='not_run',correctnessStatus='not_run',benchmarkStatus='not_run',eligible=False,reason=reason)]
        p=page(s,ctx,[('**/api/compute/hardware',mutate(change))],tab='stats');p.wait_for_function('document.querySelector("#stats-content").innerText.includes("qa-kept-hash-9ac7")',timeout=60000)
        text=observe(s,p,'hardware-'+str(i),'#stats-content',True)
        s.check('hardware reason '+str(i)+' mapped or generic',('GPU 사용 불가' if i==0 else '기타 사유') in text and all(x not in text for x in ['terms[0].operation','검수 전용 미등록 사유','[native code]','[object Object]']),dict(input=reason,text=text))
        s.check('hardware '+str(i)+' probe allowlist and hash/driver preserved',NORMAL[0] in text and '장치 탐지 중 일부 항목이 실패했습니다.' in text and BAD[0] not in text and 'qa-kept-hash-9ac7' in text and '1.25' in text,text);p.close()

def conditions(s,ctx):
    for i,weapon in enumerate(['SMG','qa_unknown_weapon','constructor','__proto__']+(['toString','hasOwnProperty','valueOf','__defineGetter__','isPrototypeOf'] if s.expanded else [])):
        def change(b):b['weaponRanges'][0]['weaponType']=weapon
        p=page(s,ctx,[('**/api/runtime/combat-conditions',mutate(change))]);p.locator('[data-cond-open="distance"]').click();p.wait_for_selector('dialog[open] tr[data-weapon="'+weapon+'"]')
        row=p.locator('dialog[open] tr[data-weapon="'+weapon+'"]').first.inner_text();text=observe(s,p,'weapon-'+str(i),'dialog[open]',True)
        s.check('weapon '+str(i)+' mapped or generic',('기관단총' if i==0 else '무기군 미확인') in row and '[native code]' not in row and '[object Object]' not in row,dict(input=weapon,row=row))
        s.check('condition popup '+str(i)+' numbers and controls',p.locator('dialog[open] input').count()>0 and '0~100 정수' in text and '45–100' in text,text)
        p.locator('dialog[open] input[name="distance"]').fill('3.5')
        s.check('condition popup '+str(i)+' local validation survives','보스 거리는 0~100 사이 정수로 입력하세요.' in p.locator('dialog[open] .cond-error').inner_text())
        p.close()
    source=s.replay(request(s),'compatibility-source')
    for i,(mode,label) in enumerate([('per_member','보스 거리·약점(멤버별)'),('per_member',BAD[1]),('legacy_global','이전 방식(전원 적용)'),('qa_unknown_mode',BAD[0])]):
        def modify(saved):saved['conditionCompatibility']=dict(mode=mode,label=label,bossDistance=35,bossWeakElement='Fire',legacyProperDistance=True,legacyElementAdvantage=False)
        saved,path=put_copy(s,source,modify);before=path.read_bytes();p=open_page(s,ctx);display(s,p,saved);text=observe(s,p,'compatibility-'+str(i),'#replay-result',True)
        s.check('compatibility '+str(i)+' no raw unregistered fields',all(x not in text for x in [BAD[0],BAD[1],'qa_unknown_mode']),dict(mode=mode,label=label,text=text))
        if i<2:s.check('compatibility '+str(i)+' distance and element retained','보스 거리 35' in text and '작열' in text,text)
        if i==2:s.check('compatibility legacy booleans retained','적정 거리 적용' in text and '우월 코드 미적용' in text,text)
        s.check('compatibility '+str(i)+' saved bytes unchanged',path.read_bytes()==before==s.call('runtime/skill-replays/'+saved['id'])[0].body());p.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dotnet',required=True);parser.add_argument('--expanded',action='store_true');a=parser.parse_args();s=Session(a.dotnet);s.expanded=a.expanded;s.report.update(product='42f4329' if a.expanded else '5243062',scope='independent allowlist screens and positive server-source controls')
    try:
        with sync_playwright() as pw:
            b=pw.chromium.launch(headless=True);ctx=b.new_context(viewport=dict(width=1500,height=1000));ctx.tracing.start(screenshots=True,snapshots=True,sources=True)
            try:
                diagnostics(s,ctx);connections_errors(s,ctx);hardware(s,ctx);conditions(s,ctx)
                s.check('allowlist paths no JS errors',not s.report['errors'],s.report['errors'])
            finally:ctx.tracing.stop(path=str(s.run/'trace.zip'));b.close()
    except Exception as ex:s.report.update(status='aborted',error=repr(ex));raise
    finally:s.finish()
    return 0 if s.report['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())

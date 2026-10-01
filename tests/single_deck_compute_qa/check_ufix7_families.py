"""Independent family expansion after QA 706d7fd: full panels, mixed paths, null logs.

Only own Session plumbing and own synthetic saved records. Real API responses except
explicit HTTP/transport/field injections below. No UI-test fixtures or expected data.
"""
import argparse,json,re,sqlite3,uuid
from copy import deepcopy
from playwright.sync_api import sync_playwright
from check_f2_conditions import Session

UNKNOWN='저장된 연산 미확인'

def open_page(s,ctx,tab='raid'):
    p=ctx.new_page();p.on('pageerror',lambda e:s.report['errors'].append(dict(message=str(e),stack=e.stack)))
    p.goto(s.base+'/editor/');p.wait_for_selector('body[data-ready="true"]');p.locator('[data-tab="'+tab+'"]').click();return p

def request(s,policy='nested_floor',logged=True):
    c=dict(roundingPolicy=policy,combat=dict(durationFrames=120,enemyDefense=30925,critMode='off',core=True,pelletCoefficientPolicy='per_trigger'))
    if logged:c['damageLog']=dict(characterId=s.ids[2])
    return dict(snapshotId=s.snapshot['id'],characterIds=s.ids,conditionProfile='legacy',conditions=c)

def put_copy(s,original,modify):
    saved=deepcopy(original);saved['id']=uuid.uuid4().hex;modify(saved)
    path=s.data/'skill-replays'/(saved['id']+'.json');path.write_text(json.dumps(saved,ensure_ascii=False),encoding='utf-8');return saved,path

def display(s,p,saved):
    def redirect(route):route.continue_(url=s.base+'/api/runtime/skill-replays/'+saved['id'],method='GET',post_data='')
    p.route('**/api/runtime/skill-replays',redirect)
    with p.expect_response(lambda r:r.url.endswith('/api/runtime/skill-replays/'+saved['id'])) as pending:p.locator('#run-replay').click()
    response=pending.value;assert response.status==200 and response.json()==saved
    p.unroute('**/api/runtime/skill-replays',redirect)
    try:p.wait_for_selector('#damage-log-container',timeout=60000)
    except Exception:
        s.save('display-timeout',dict(replayId=saved['id'],text=p.locator('body').inner_text(),errors=s.report['errors']))
        p.screenshot(path=str(s.run/'display-timeout.png'),full_page=True)
        raise

def operations(s,ctx):
    p=open_page(s,ctx)
    for policy in ['client_f32','legacy_term_floor','final_round_even','nested_floor']:
        original=s.replay(request(s,policy),'operation-source-'+policy)
        # All saved names: legal original control and foreign prefix/suffix variants.
        for mode in ['original','foreign-prefix','foreign-suffix']:
            def modify(saved):
                for t in saved['result']['damageLog']['entries'][0]['calculation']['terms']:
                    if mode=='foreign-prefix':t['operation']='qa foreign '+t['operation']
                    if mode=='foreign-suffix':t['operation']+='; qa foreign'
            saved,path=put_copy(s,original,modify);before=path.read_bytes();display(s,p,saved)
            entry=saved['result']['damageLog']['entries'][0];p.locator('[data-view-audit="'+str(entry['hitId'])+'"]').click();p.wait_for_selector('.audit-steps')
            rows=p.locator('.audit-steps tr[data-term]').evaluate_all('(rs)=>rs.map(r=>({name:r.dataset.term,description:r.cells[3].innerText}))')
            s.save(policy+'-'+mode,dict(terms=entry['calculation']['terms'],rows=rows,text=p.locator('.damage-audit-panel').inner_text()))
            s.check(policy+' '+mode+' whole operation recognition',all((r['description']!=UNKNOWN) if mode=='original' else (r['description']==UNKNOWN) for r in rows),rows)
            s.check(policy+' '+mode+' data-term preserved',[r['name'] for r in rows]==[t['name'] for t in entry['calculation']['terms']])
            s.check(policy+' '+mode+' bytes unchanged',before==path.read_bytes()==s.call('runtime/skill-replays/'+saved['id'])[0].body())
    # Same original suffix repro, now inspect every visible summary card too.
    for i,op in enumerate(['multiply 1.25; qa_unknown_transform','multiply 1.25; floor_if_qa_condition','multiply 0x10','multiply 0b11','multiply 1.25\n','multiply 1.25; floor\n']):
        def modify(saved):
            for t in saved['result']['damageLog']['entries'][0]['calculation']['terms']:
                if t['name'] in ['B3','B4','B5']:t['operation']=op
        saved,path=put_copy(s,original,modify);before=path.read_bytes();display(s,p,saved)
        entry=saved['result']['damageLog']['entries'][0];p.locator('[data-view-audit="'+str(entry['hitId'])+'"]').click();p.wait_for_selector('.audit-steps')
        rows=p.locator('.audit-steps tr[data-term]').evaluate_all('(rs)=>rs.filter(r=>["B3","B4","B5"].includes(r.dataset.term)).map(r=>({name:r.dataset.term,description:r.cells[3].innerText}))')
        card=p.locator('.audit-stat-card').filter(has=p.get_by_text('B3 × B4 × B5',exact=True));cardtext=card.inner_text();value=card.locator('strong').inner_text()
        s.save('factor-variant-'+str(i),dict(operation=op,replayId=saved['id'],rows=rows,card=cardtext,terms=entry['calculation']['terms']))
        s.check('factor variant '+str(i)+' row remains unconfirmed',all(r['description']==UNKNOWN for r in rows),dict(operation=op,rows=rows))
        s.check('factor variant '+str(i)+' card does not infer a factor',any(x in value for x in ['미확인','미제공','미기록']),dict(operation=op,card=cardtext))
        s.check('factor variant '+str(i)+' saved/API unchanged',before==path.read_bytes()==s.call('runtime/skill-replays/'+saved['id'])[0].body())
        p.locator('.damage-audit-panel').screenshot(path=str(s.run/('factor-variant-'+str(i)+'.png')))
    p.close()

def messages(s,ctx):
    bad=['effectiveDefense','calculation.terms','terms[].name','terms[0].operation','attackBuffs[0].source','cache/replays','runtime\\catalog','skill1Rate']
    good=['앨리스의 머리 장비를 확인하세요.','배율 3.5배를 확인하세요.','GPU를 사용할 수 없습니다.','LV.5 장비를 확인하세요.']
    s.stop();s.snapshot['issues']=[dict(code='qa_issue',path='qa.path.'+str(i),message='검사 필요: '+x) for i,x in enumerate(bad)]+[dict(code='qa_good',path='qa.good.'+str(i),message=x) for i,x in enumerate(good)]
    with sqlite3.connect(s.data/'accounts.db') as db:db.execute('UPDATE snapshots SET payload=?',(json.dumps(s.snapshot),))
    s.start(ctx.request);p=open_page(s,ctx,'advanced');rows=p.locator('[data-issue-path]').all_inner_texts();s.save('mixed-paths',dict(inputs=bad,good=good,rows=rows))
    for i,key in enumerate(bad):s.check('persisted internal form '+key+' hidden',key not in rows[i],dict(input=key,visible=rows[i]))
    for i,txt in enumerate(good):
        expected='수집 값을 확인해야 합니다.' if getattr(s,'allowlist',False) else txt
        s.check(('unregistered QA Korean generic ' if getattr(s,'allowlist',False) else 'ordinary Korean preserved ')+str(i),rows[len(bad)+i]==expected,rows[len(bad)+i])
    p.screenshot(path=str(s.run/'mixed-paths.png'),full_page=True);p.close()
    # One array path through three independently reached caller families.
    wire='검사 필요: terms[0].operation'
    def alter_boot(route):
        response=route.fetch();b=response.json();b['connectionFailure']=dict(message=wire);route.fulfill(response=response,json=b)
    p=ctx.new_page();p.route('**/api/bootstrap',alter_boot);p.goto(s.base+'/editor/');p.wait_for_selector('body[data-ready="true"]');p.locator('[data-tab="import"]').click()
    text=p.locator('#import-content').inner_text();s.save('mixed-connection',dict(text=text));s.check('mixed array path in connection hidden','terms[0].operation' not in text,text);p.close()
    p=open_page(s,ctx);p.route('**/api/runtime/skill-replays',lambda r:r.fulfill(status=400,json=dict(message=wire)))
    p.locator('#run-replay').click();p.wait_for_function('!document.querySelector("#run-replay").disabled');text=p.locator('#replay-result').inner_text()
    s.save('mixed-error',dict(text=text));s.check('mixed array path in caught Error hidden','terms[0].operation' not in text,text);p.close()
    def alter_hardware(route):
        response=route.fetch();h=response.json();h['probeFailures']=[wire];h['gpus']=[dict(deviceId='qa-hash-preserve',name='검수 장치',vendor='검수',driver='1.0',backend='gpu',runtimeStatus='failed',selfTestStatus='not_run',correctnessStatus='not_run',benchmarkStatus='not_run',eligible=False,reason=wire)];route.fulfill(response=response,json=h)
    p=ctx.new_page();p.route('**/api/compute/hardware',alter_hardware);p.goto(s.base+'/editor/');p.wait_for_selector('body[data-ready="true"]');p.locator('[data-tab="stats"]').click();p.wait_for_function('document.querySelector("#stats-content").innerText.includes("qa-hash-preserve")',timeout=60000)
    text=p.locator('#stats-content').inner_text();s.save('mixed-device',dict(text=text));s.check('mixed path in hardware reason and probe hidden','terms[0].operation' not in text,text);p.close()

def logs(s,ctx):
    original=s.replay(request(s,logged=False),'logless-source');logged=s.replay(request(s),'collected-source')
    for case in ['uncollected','empty-http','http400','http404','http409','http500','http503','transport','unsupported-embedded','unsupported-endpoint','zero']:
        start=len(s.report['errors']);p=open_page(s,ctx);saved=deepcopy(original);path=s.data/'skill-replays'/(saved['id']+'.json');before=path.read_bytes()
        pattern='**/damage-log?*';faults=[]
        def fault(route):
            faults.append(route.request.url)
            if case=='transport':route.abort('failed')
            elif case.startswith('http'):route.fulfill(status=int(case[4:]),json=dict(message='QA English backend failure',code='qa_unregistered_failure'))
            elif case=='empty-http':route.fulfill(status=200,json=None)
            elif case=='unsupported-endpoint':route.fulfill(status=200,json=dict(entries=[],schemaVersion=93,totalDamage=10,characterId=s.ids[2]))
            else:route.continue_()
        if case=='unsupported-embedded':
            saved,path=put_copy(s,logged,lambda x:x['result']['damageLog'].update(schemaVersion=93));before=path.read_bytes()
        elif case=='zero':
            saved,path=put_copy(s,logged,lambda x:x['result']['damageLog'].update(entries=[],totalDamage=0));before=path.read_bytes()
        elif case!='uncollected':p.route(pattern,fault)
        display(s,p,saved);p.wait_for_selector('#log-character-select');text=p.locator('#damage-log-container').inner_text()
        s.save('log-'+case,dict(text=text,replayId=saved['id'],errors=s.report['errors'][start:],requests=faults))
        s.check('log '+case+' no JS exception',len(s.report['errors'])==start,s.report['errors'][start:])
        s.check('log '+case+' no graph',p.locator('#damage-graph-shell').count()==0)
        s.check('log '+case+' no raw error','QA English' not in text and 'qa_unregistered' not in text)
        expected='지원하지 않는 로그 형식' if case.startswith('unsupported') else '피해 기록 0' if case=='zero' else '피해 로그를 불러오지 못했습니다' if case.startswith('http') or case=='transport' else '로그 미수집'
        s.check('log '+case+' correct Korean state',expected in text,dict(expected=expected,text=text))
        s.check('log '+case+' preview opt-in only',p.locator('#btn-load-mock-preview').count()==(1 if case in ['uncollected','empty-http'] else 0))
        s.check('log '+case+' storage unchanged',before==path.read_bytes()==s.call('runtime/skill-replays/'+saved['id'])[0].body())
        p.locator('#damage-log-container').screenshot(path=str(s.run/('log-'+case+'.png')))
        if case!='uncollected':p.unroute(pattern)
        display(s,p,logged);p.wait_for_selector('#damage-graph-shell');s.check('log '+case+' restores collected graph',p.locator('[data-view-audit]').count()>0)
        p.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);p.add_argument('--allowlist',action='store_true');p.add_argument('--phase',choices=['operations','messages','logs','all'],default='all');a=p.parse_args();s=Session(a.dotnet);s.allowlist=a.allowlist;s.report.update(product='5243062' if a.allowlist else '8da098f',scope='U-FIX-7 independent family expansion '+a.phase,responseMocks='Explicit QA fault injections only')
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport=dict(width=1500,height=1000));ctx.tracing.start(screenshots=True,snapshots=True,sources=True)
            try:
                s.start(ctx.request);assert s.call('accounts/synthetic-account/formation',dict(slots=s.ids),'PUT')[0].ok
                for name,fn in [('operations',operations),('messages',messages),('logs',logs)]:
                    if a.phase in [name,'all']:fn(s,ctx)
            finally:
                ctx.tracing.stop(path=str(s.run/'trace.zip'));browser.close()
    except Exception as ex:s.report.update(status='aborted',error=repr(ex));raise
    finally:s.finish()
    return 0 if s.report['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())

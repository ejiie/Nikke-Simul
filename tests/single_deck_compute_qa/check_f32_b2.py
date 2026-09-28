"""Independent real Chromium + isolated API Q-F32 B2. No UI mock/test imports.
Synthetic connection/raw metadata are persisted in new dataRoot, never response mocks.
The v2 rendering check transforms only an outgoing request, forwarding it to the API.
"""
import argparse,hashlib,json,math,os,socket,sqlite3,subprocess,time,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright
from public_fixture import create,read,digest
from check_f32_b1 import normalized
from check_client_f32 import context as independent_hit
from actual_stats import metric

ROOT=Path(__file__).resolve().parents[2]

def main():
    p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);p.add_argument('--stats-only',action='store_true');a=p.parse_args()
    run=ROOT/'artifacts/single-deck-qa'/('f32-b2-'+uuid.uuid4().hex[:12]);data=run/'data';data.mkdir(parents=True)
    source=ROOT/'artifacts/single-deck-qa/load1000-3db71912a601/data'
    hashes,game,snapshot,ids=create(source,data)
    rawid=uuid.uuid4().hex;snapshot['rawManifestId']=rawid
    connection=dict(id='qa-browser-connection',accountId=snapshot['accountId'],status='ready',nickname='QA synthetic',area=1,updatedAt='2026-09-28T00:00:00Z',choices=[dict(area=1,label='QA synthetic',characterCount=5,openId='synthetic')])
    with sqlite3.connect(data/'accounts.db') as db:
        db.execute('UPDATE snapshots SET payload=? WHERE id=?',(json.dumps(snapshot),snapshot['id']))
        db.execute('CREATE TABLE connections(id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        db.execute('INSERT INTO connections VALUES(?,?)',(connection['id'],json.dumps(connection)))
    rawdir=data/'raw'/rawid;rawdir.mkdir(parents=True)
    raw=json.dumps(dict(source='QA_SYNTHETIC_NO_GAME_ACCOUNT',characters=[dict(name_code=i,combat=0) for i in ids]))
    (rawdir/'envelope.json').write_text(raw,encoding='utf-8')
    (rawdir/'manifest.json').write_text(json.dumps(dict(envelopeHash=hashlib.sha256(raw.encode()).hexdigest())),encoding='utf-8')
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    assert port not in (5180,5181)
    env=dict(os.environ,NIKKE_PROJECT_ROOT=str(ROOT),NIKKE_DATA_ROOT=str(data),NIKKE_PORT=str(port),NIKKE_TEST_FIXTURE='1');env.pop('NIKKE_GAME_CATALOG',None)
    report=dict(status='running',port=port,checks=[],errors=[],scope='synthetic real browser and API',responseMocks=False)
    def save(name,obj):(run/(name+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    def check(name,ok,detail=None):
        report['checks'].append(dict(name=name,passed=bool(ok),detail=detail));save('summary',report);print(name+(': PASS' if ok else ': FAIL'),flush=True)
    log=(run/'api.log').open('w',encoding='utf-8')
    process=subprocess.Popen([a.dotnet,str(ROOT/'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));report['ownedPid']=process.pid
    base=f'http://127.0.0.1:{port}';traffic=[]
    try:
      with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        ctx=browser.new_context(viewport=dict(width=1500,height=1000),accept_downloads=True)
        ctx.tracing.start(screenshots=True,snapshots=True,sources=True)
        api=ctx.request
        for _ in range(300):
            try:
                boot=api.get(base+'/api/bootstrap').json();break
            except Exception:time.sleep(.1)
        else:raise AssertionError('startup')
        headers={'X-Nikke-Token':boot['token']}
        def call(path,payload=None,method='GET'):
            r=api.fetch(base+'/api/'+path,method=method,data=payload,headers=headers);return r
        assert call('accounts/synthetic-account/formation',dict(slots=ids),'PUT').ok
        tactic=dict(schemaVersion=1,allowedCharacterIds=ids,stage1Priority=[ids[0]],stage2Priority=[ids[1]],stage3Priority=ids[2:],burst3Rotation=[ids[2],ids[4]],unavailablePolicy='next_ready')
        assert call('accounts/synthetic-account/burst-tactic',dict(snapshotId=snapshot['id'],formationSlots=ids,tactic=tactic),'PUT').ok
        def record(response):
            if '/api/' not in response.url:return
            if any(s in response.url for s in ['/calculations/hit','/skill-replays','/compute/experiments']):
                try:traffic.append(dict(url=response.url,status=response.status,request=response.request.post_data_json if response.request.post_data else None,response=response.json()))
                except Exception:pass
        def attach(page):page.on('response',record);page.on('pageerror',lambda e:report['errors'].append(str(e)))
        def shot(page,name):page.screenshot(path=str(run/(name+'.png')),full_page=True)
        def resize(page,label):
            for width in [1500,850,500]:
                page.set_viewport_size(dict(width=width,height=1000));page.wait_for_timeout(100)
                overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                check(label+' width '+str(width),not overflow);shot(page,label+'-'+str(width))
            page.set_viewport_size(dict(width=1500,height=1000))
        if not a.stats_only:
            web=ctx.new_page();attach(web);web.goto(base+'/legacy/');web.locator('[data-character="5004"]').click();web.locator('#scenario-level').fill('400');web.locator('#load-stats').click();web.locator('.hit-workbench summary').first.click()
            web.locator('[name="statDamageRatio"]').wait_for()
            check('web default and experimental labels',web.locator('[name="roundingPolicy"]').input_value()=='client_f32' and web.locator('[name="statDamageRatio"]').input_value()=='1' and web.locator('[name="defenceRatioRate"]').input_value()=='0' and '미확정' in web.locator('.experimental-inputs').inner_text())
            def submit(label):
                with web.expect_response(lambda r:r.url.endswith('/api/calculations/hit') and r.request.method=='POST') as pending:web.locator('.hit-form button[type="submit"]').click()
                response=pending.value;value=response.json();web.wait_for_timeout(150);save(label,value);return response,value
            web.locator('[name="attack-buffs"]').fill('14.5');web.locator('[name="statDamageRatio"]').fill('2');web.locator('[name="defenceRatioRate"]').fill('0.25')
            response,value=submit('web-normal');expected=independent_hit(normalized(response.request.post_data_json['input']))
            check('web real request raw string and independent damage',response.status==200 and response.request.post_data_json['input']['runtimeAttackBuffs'][0]['rawRate10000']=='1450' and value['candidates'][0]['exactDamage']==str(expected['damage']))
            def compare_render(value,label):
                text=web.locator('.hit-result').inner_text()
                check(label+' exact attack',format(int(value['exactEffectiveAttack']),',') in web.locator('.effective-attack').inner_text())
                for c in value['candidates']:
                    check(label+' candidate '+c['policy'],(format(int(c['exactDamage'] or c['damage']),',') in text) if c['status']=='available' else '계산 불가' in text and c['errorCode'] in text)
                rows=web.locator('.hit-audit tbody tr');check(label+' audit rows',rows.count()==len(value['selectedCandidate']['terms']))
                cells=rows.evaluate_all('(rows)=>rows.map(r=>({name:r.dataset.term,before:r.cells[1].innerText,after:r.cells[2].innerText}))')
                check(label+' audit values',all(x['name']==t['name'] and all(math.isclose(float(x[k].replace(',','')),t[k],rel_tol=1e-12,abs_tol=1e-7) for k in ['before','after']) for x,t in zip(cells,value['selectedCandidate']['terms'])))
                save('web-dom-'+label,dict(text=text,terms=cells))
                check(label+' saved equality',call('calculations/hit/'+value['id']).json()==value)
            compare_render(value,'normal')
            with web.expect_download() as downloaded:web.locator('.export-calculation').click()
            downloaded.value.save_as(str(run/'web-export.json'))
            check('download preserves saved response',read(run/'web-export.json')['comparison']==value)
            resize(web,'web-normal')
            for policy in ['legacy_term_floor','final_round_even','nested_floor']:
                web.locator('[name="roundingPolicy"]').select_option(policy);r,v=submit('web-'+policy)
                check('historical selected '+policy,v['selectedPolicy']==policy and policy in web.locator('.hit-audit').inner_text())
                compare_render(v,policy)
            web.locator('[name="attack-buffs"]').fill('1.234')
            before=len([r for r in traffic if r['url'].endswith('/calculations/hit')]);web.locator('.hit-form button[type="submit"]').click();web.wait_for_timeout(150)
            check('overprecision rejected before HTTP',len([r for r in traffic if r['url'].endswith('/calculations/hit')])==before and '0.01' in web.locator('.hit-result').inner_text())
            web.locator('[name="attack-buffs"]').fill('');web.locator('[name="statAttack"]').fill('100.5');r,v=submit('web-400')
            check('real 400 rendered',r.status==400 and 'statAttack_must_be_integer_never_truncated' in web.locator('.hit-result').inner_text() and '정수' in web.locator('.hit-result').inner_text());shot(web,'web-400')
            # Legitimate form-only large integer: checked products fit int64, summed attack exceeds JS safe integer.
            web.locator('[name="roundingPolicy"]').select_option('client_f32');web.locator('[name="statAttack"]').fill('999999999997');web.locator('[name="defense"]').fill('0');web.locator('[name="coefficient"]').fill('100');web.locator('[name="statDamageRatio"]').fill('1');web.locator('[name="defenceRatioRate"]').fill('0')
            web.locator('[name="attack-buffs"]').fill(','.join(str(x*100) for x in list(range(900,890,-1))+[889]))
            for field in ['crit','core','fullCharge','properDistance','fullBurst','pierce','parts','elementAdvantage']:web.locator('[name="'+field+'"]').uncheck()
            r,v=submit('web-large');check('large response actual API',r.status==200)
            if r.status==200:
                compare_render(v,'large');check('large odd exact not rounded',int(v['exactEffectiveAttack'])>2**53 and int(v['exactEffectiveAttack'])%2==1 and format(int(v['exactEffectiveAttack']),',') in web.locator('.effective-attack').inner_text())
                check('all three unavailable reasons rendered',all(c['status']=='unavailable' for c in v['candidates'][1:]) and web.locator('.hit-result').inner_text().count('계산 불가')>=3)
                resize(web,'web-large')
            # Real v2 request to actual API; no response fulfillment or fabricated candidates.
            def v2route(route):
                body=route.request.post_data_json;body['inputSchemaVersion']=2
                body['input'].pop('statDamageRatio',None);body['input'].pop('defenceRatioRate',None)
                route.continue_(post_data=json.dumps(body))
            web.locator('[name="statAttack"]').fill('100');web.locator('[name="attack-buffs"]').fill('14.5')
            web.route('**/api/calculations/hit',v2route);r,v=submit('web-v2');web.unroute('**/api/calculations/hit',v2route)
            check('v2 conversion real response rendered',r.status==200 and v['conversion']['converted'] and web.locator('.hit-conversion').count()==1 and '2' in web.locator('.hit-conversion').inner_text() and '3' in web.locator('.hit-conversion').inner_text());shot(web,'web-v2')
            desktop=ctx.new_page();attach(desktop);desktop.goto(base+'/editor/');desktop.wait_for_selector('body[data-ready="true"]')
            desktop.locator('[data-tab="raid"]').click();desktop.locator('#replay-form').wait_for()
            check('desktop policy default and history options',desktop.locator('[name="rounding"]').input_value()=='client_f32' and desktop.locator('[name="rounding"] option').count()==4)
            desktop.locator('[name="seconds"]').fill('20');desktop.locator('[name="core"]').check()
            def replay(label):
                with desktop.expect_response(lambda r:'/api/runtime/skill-replays' in r.url and r.request.method=='POST',timeout=60000) as pending:desktop.locator('#run-replay').click()
                res=pending.value;value=res.json();save(label,value);desktop.locator('[data-view-audit]').first.wait_for(timeout=30000);return res,value
            r,v=replay('desktop-client-replay')
            save('desktop-replay-request',r.request.post_data_json)
            check('desktop replay level400 and policy',r.status==200 and r.request.post_data_json['scenarioLevel']==400 and r.request.post_data_json['conditions']['roundingPolicy']=='client_f32')
            # Select actual stored first hit, open product audit, compare all displayed term values.
            entries=v['result']['damageLog']['entries'];selected=next(e for e in entries if e['hit']['fullBurst'] and e['hit']['core'])
            desktop.locator('[data-view-audit="'+str(selected['hitId'])+'"]').click();desktop.locator('.audit-steps').wait_for();shot(desktop,'desktop-audit')
            save('desktop-audit-dom',dict(text=desktop.locator('#replay-result').inner_text(),terms=desktop.locator('.audit-steps tr[data-term]').evaluate_all('(rows)=>rows.map(r=>({name:r.dataset.term,before:r.cells[1].innerText,after:r.cells[2].innerText}))')))
            check('desktop client audit ten terms',desktop.locator('.audit-steps tr[data-term]').count()==10 and '저장된 발당 피해와 일치' in desktop.locator('#replay-result').inner_text())
            cells=desktop.locator('.audit-steps tr[data-term]').evaluate_all('(rows)=>rows.map(r=>({name:r.dataset.term,before:r.cells[1].innerText,after:r.cells[2].innerText}))')
            check('desktop fullburst audit exact saved values',all(x['name']==t['name'] and all(math.isclose(float(x[k].replace(',','')),t[k],rel_tol=1e-13,abs_tol=1e-10) for k in ['before','after']) for x,t in zip(cells,selected['calculation']['terms'])))
            check('desktop every logged hit independent',all(independent_hit(normalized(e['hit']))['damage']==e['damage'] for e in entries))
            check('desktop saved replay equality',call('runtime/skill-replays/'+v['id']).json()==v)
            save('selected-desktop-hit',selected)
            resize(desktop,'desktop-client')
            desktop.locator('#btn-close-audit').click();desktop.locator('[name="rounding"]').select_option('legacy_term_floor');r,old=replay('desktop-legacy-replay');desktop.locator('[data-view-audit]').first.click()
            check('legacy damage log retained',desktop.locator('.audit-steps tr[data-term="B2"]').count()==1 and '비교 후보 정책' in desktop.locator('#replay-result').inner_text());shot(desktop,'desktop-legacy')
            desktop.locator('#btn-close-audit').click();desktop.locator('[name="rounding"]').select_option('client_f32');desktop.locator('[name="seconds"]').fill('10')
        else:
            desktop=ctx.new_page();attach(desktop);desktop.goto(base+'/editor/');desktop.wait_for_selector('body[data-ready="true"]')
            desktop.locator('[data-tab="raid"]').click();desktop.locator('[name="seconds"]').fill('10');desktop.locator('[name="core"]').check()
        desktop.locator('[data-tab="stats"]').click();desktop.locator('#compute-runs').fill('1');desktop.locator('.compute-advanced summary').click();desktop.locator('#compute-worker-limit').fill('1')
        with desktop.expect_response(lambda r:r.url.endswith('/api/compute/experiments') and r.request.method=='POST',timeout=60000) as pending:desktop.locator('#compute-start').click()
        b=pending.value.json();save('desktop-batch-created',b)
        for _ in range(300):
            state=call('compute/experiments/'+b['id']).json()
            if state['state'] in ['completed','failed','cancelled']:break
            desktop.wait_for_timeout(200)
        save('desktop-batch',state);desktop.wait_for_timeout(2000)
        text=desktop.locator('#stats-content').inner_text();save('desktop-stats-dom',dict(text=text))
        st=call('compute/experiments/'+b['id']+'/statistics?cut=0').json();rows=call('compute/experiments/'+b['id']+'/results').json()['runs'];save('desktop-statistics',st);save('desktop-runs',rows)
        metric(st['team'],[r['teamDamage'] for r in rows],0)
        check('stats actual completed n1 and independent mean',state['state']=='completed' and st['team']['n']==1)
        check('stats version policy rendered',all(s in text for s in ['client_f32','schema 3','cpu-summary.2-client-f32',state['input']['fingerprint']]))
        check('stats available mean and quantiles visible',all(format(int(st['team'][key]),',') in text for key in ['mean','median','p5','p95']),dict(apiMean=st['team']['mean'],apiReason=st['team']['unsupportedReason']))
        check('completed API not labeled disconnected','compute API 미연결' not in text)
        resize(desktop,'desktop-statistics')
        # Actual warmup batch produces a real 409 statistics refusal, then UI recovery via saved ID.
        req=next(t['request'] for t in traffic if t['url'].endswith('/api/compute/experiments') and t['status']==202)
        req['phase']='warmup';req['runs']=1
        warm=call('compute/experiments',req,'POST').json()
        for _ in range(300):
            s=call('compute/experiments/'+warm['id']).json()
            if s['state'] in ['completed','failed','cancelled']:break
            desktop.wait_for_timeout(150)
        assert call('compute/experiments/'+warm['id']+'/statistics').status==409
        desktop.evaluate('(id)=>localStorage.setItem("nikke-single-deck-experiment",id)',warm['id']);desktop.reload();desktop.wait_for_selector('body[data-ready="true"]');desktop.locator('[data-tab="stats"]').click()
        desktop.wait_for_function('document.querySelector("#stats-content").innerText.includes("warmup_excluded_from_statistics")',timeout=30000)
        check('real 409 explained in stats', '워밍업' in desktop.locator('#stats-content').inner_text() or 'warmup' in desktop.locator('#stats-content').inner_text());shot(desktop,'desktop-409')
        from f32_ufix_acceptance import verify
        verify(desktop,call,check,save,shot,traffic,base,b,st,warm)
        check('no browser exceptions',not report['errors'],report['errors'])
        ctx.tracing.stop(path=str(run/'trace.zip'));browser.close()
        report['status']='passed' if all(x['passed'] for x in report['checks']) else 'failed'
    except Exception as ex:
        report['status']='aborted';report['error']=repr(ex);raise
    finally:
        process.terminate();process.wait(timeout=30);log.close();report['ownApiStopped']=True
        report['sourceChanges']=[r for r,h in hashes.items() if digest(source/r)!=h]
        save('traffic',traffic);save('source-hashes',hashes);save('summary',report);print('EVIDENCE '+str(run),flush=True)
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())

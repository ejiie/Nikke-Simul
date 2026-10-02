"""Independent missing-step labels and fallback log retrieval browser paths."""
import argparse,json,uuid
from copy import deepcopy
from playwright.sync_api import sync_playwright
from check_f2_conditions import Session,ROOT
from public_fixture import read

def run(s,ctx):
    s.start(ctx.request);assert s.call('accounts/synthetic-account/formation',dict(slots=s.ids),'PUT')[0].ok
    (s.data/'skill-replays').mkdir(exist_ok=True)
    source=read(ROOT/'artifacts/single-deck-qa/f2-ufix3-554048887882/data/skill-replays/b41c653c67fa48dfa35cb46547de88ab.json')
    page=ctx.new_page();page.on('pageerror',lambda e:s.report['errors'].append(dict(message=str(e),stack=e.stack)))
    page.goto(s.base+'/editor/');page.wait_for_selector('body[data-ready="true"]');page.locator('[data-tab="raid"]').click()
    for fault in ['no-terms','missing-difference','missing-log']:
        saved=deepcopy(source);saved['id']=uuid.uuid4().hex;entry=saved['result']['damageLog']['entries'][0]
        if fault=='no-terms':entry['calculation'].pop('terms')
        elif fault=='missing-difference':entry['calculation']['terms']=[t for t in entry['calculation']['terms'] if t['name']!='difference']
        else:
            saved=s.replay(dict(snapshotId=s.snapshot['id'],characterIds=s.ids,conditionProfile='legacy',conditions=dict(roundingPolicy='client_f32',combat=dict(durationFrames=120,enemyDefense=30925,critMode='off',pelletCoefficientPolicy='per_trigger'))),'created-without-log')
            assert not saved['result'].get('damageLog')
        path=s.data/'skill-replays'/(saved['id']+'.json');path.write_text(json.dumps(saved,ensure_ascii=False),encoding='utf-8');before=path.read_bytes()
        def redirect(route):route.continue_(url=s.base+'/api/runtime/skill-replays/'+saved['id'],method='GET',post_data='')
        page.route('**/api/runtime/skill-replays',redirect)
        failures=[]
        def abort_log(route):failures.append(route.request.url);route.abort('failed')
        if fault=='missing-log':page.route('**/damage-log?*',abort_log)
        with page.expect_response(lambda r:r.url.endswith('/api/runtime/skill-replays/'+saved['id'])) as pending:page.locator('#run-replay').click()
        assert pending.value.status==200
        page.unroute('**/api/runtime/skill-replays',redirect)
        if fault!='missing-log':page.locator('[data-view-audit="'+str(entry['hitId'])+'"]').click();page.wait_for_selector('.damage-audit-panel')
        else:page.wait_for_timeout(800)
        text=page.locator('#replay-result').inner_text();s.save(fault,dict(text=text,replayId=saved['id'],errors=s.report['errors'],faultRequests=failures))
        if fault=='missing-log':
            s.check('real replay without log requested fallback endpoint',len(failures)==1,failures)
            s.check('log query transport Korean','요청을 처리하지 못했습니다' in text,text)
        s.check(fault+' no raw paths/keys',all(x not in text for x in ['calculation.terms','terms[]','effectiveAttack','effectiveDefense','difference','Failed to fetch','(hit']))
        if fault=='no-terms':s.check('missing terms neutral guidance','저장된 단계별' in text)
        if fault=='missing-difference':s.check('missing name Korean','공방차' in text)
        s.check(fault+' private saved file and GET preserved',path.read_bytes()==before==s.call('runtime/skill-replays/'+saved['id'])[0].body())
        page.screenshot(path=str(s.run/(fault+'.png')),full_page=True)
    page.close();s.check('missing paths no JS exceptions',not s.report['errors'],s.report['errors'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args();s=Session(a.dotnet);s.report.update(product='b401421',scope='own persisted missing records and log transport fault')
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport=dict(width=1500,height=1000));ctx.tracing.start(screenshots=True,snapshots=True,sources=True)
            run(s,ctx);ctx.tracing.stop(path=str(s.run/'trace.zip'));browser.close()
    except Exception as ex:s.report.update(status='aborted',error=repr(ex));raise
    finally:s.finish()
    return 0 if s.report['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())

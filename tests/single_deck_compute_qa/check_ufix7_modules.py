"""QA-owned ESM/parser negative control and real application navigation.

No UI tests are imported. Node receives actual file bytes on stdin as ESM.
Browser imports use the isolated server; saved variants use the real GET route.
"""
import argparse,subprocess,shutil
from playwright.sync_api import sync_playwright
from check_f2_conditions import ROOT,Session
from check_ufix7_families import display,put_copy,request

def run(s,ctx):
    files=sorted((ROOT/'apps/desktop-ui').glob('*.js'));node=shutil.which('node');assert node
    syntax=[]
    for f in files:
        result=subprocess.run([node,'--input-type=module','--check'],input=f.read_bytes(),capture_output=True)
        row=dict(file=f.name,exitCode=result.returncode,stderr=result.stderr.decode('utf-8',errors='replace'));syntax.append(row)
        s.check('ESM syntax '+f.name,result.returncode==0,row)
    broken=subprocess.run(['git','show','a92e454:apps/desktop-ui/local-lab-detail.js'],cwd=ROOT,capture_output=True,check=True).stdout
    control=subprocess.run([node,'--input-type=module','--check'],input=broken,capture_output=True)
    s.check('ESM negative control rejects a92e454 local-lab-detail',control.returncode!=0 and b'SyntaxError' in control.stderr,dict(exitCode=control.returncode,stderr=control.stderr.decode('utf-8',errors='replace')))
    s.save('syntax',dict(node=node,checks=syntax,negativeControl=control.stderr.decode('utf-8',errors='replace')))
    s.start(ctx.request);assert s.call('accounts/synthetic-account/formation',dict(slots=s.ids),'PUT')[0].ok
    p=ctx.new_page();p.on('pageerror',lambda e:s.report['errors'].append(dict(message=str(e),stack=e.stack)))
    console=[];failures=[]
    p.on('console',lambda m:console.append(dict(type=m.type,text=m.text)))
    p.on('requestfailed',lambda r:failures.append(dict(url=r.url,error=r.failure)))
    response=p.goto(s.base+'/editor/');p.wait_for_selector('body[data-ready="true"]')
    s.check('actual editor entry ready',response.status==200)
    for f in files:
        r=ctx.request.get(s.base+'/editor/'+f.name)
        s.check('actual served module '+f.name,r.status==200 and r.body()==f.read_bytes(),dict(status=r.status))
    imports=p.evaluate('async names => {const out=[];for(const name of names){try{const m=await import("/editor/"+name);out.push({name,ok:true,exports:Object.keys(m)})}catch(e){out.push({name,ok:false,error:String(e)})}}return out}',[f.name for f in files])
    for row in imports:s.check('browser ESM import '+row['name'],row['ok'],row)
    s.save('browser-imports',imports)
    for tab,selector in [('home','#account-list'),('nikkes','#nikke-card-list'),('raid','#raid-content'),('stats','#stats-content'),('advanced','#advanced-content'),('import','#import-content')]:
        p.locator('[data-tab="'+tab+'"]').click();p.wait_for_selector(selector)
        text=p.locator(selector).inner_text();s.check('main screen '+tab+' rendered',len(text.strip())>10,text)
        p.screenshot(path=str(s.run/('main-'+tab+'.png')),full_page=True)
    p.locator('[data-tab="nikkes"]').click();p.locator('#nikke-card-list [data-character-uid="5004"]').click();p.wait_for_selector('#nikke-core-panel input')
    text=p.locator('body').inner_text();s.check('local-lab detail active Korean equipment',all(t in text for t in ['앨리스','머리','몸통','팔','다리']),text)
    p.screenshot(path=str(s.run/'local-lab-detail.png'),full_page=True)
    p.locator('[data-tab="raid"]').click()
    for popup in ['distance','element']:
        p.locator('[data-cond-open="'+popup+'"]').click();p.wait_for_selector('dialog[open]')
        text=p.locator('dialog[open]').inner_text();s.check('main popup '+popup+' rendered',('0~100' in text if popup=='distance' else '작열' in text),text)
        p.screenshot(path=str(s.run/('main-popup-'+popup+'.png')),full_page=True);p.locator('dialog[open] [data-cond-cancel]').click()
    source=s.replay(request(s),'module-flow-source');display(s,p,source);p.wait_for_selector('#damage-graph-shell')
    s.check('main damage graph actual collected',p.locator('[data-view-audit]').count()>0)
    hit=source['result']['damageLog']['entries'][0];p.locator('[data-view-audit="'+str(hit['hitId'])+'"]').click();p.wait_for_selector('.audit-steps')
    s.check('main damage audit Korean steps',all('저장된 연산 미확인' not in x for x in p.locator('.audit-steps tr[data-term]').all_inner_texts()))
    p.screenshot(path=str(s.run/'main-audit.png'),full_page=True)
    # Own-key change applies to audit names too; raw names belong only to data-term.
    for key in ['constructor','toString','__proto__','hasOwnProperty','valueOf']:
        def modify(saved):saved['result']['damageLog']['entries'][0]['calculation']['terms'][0]['name']=key
        saved,path=put_copy(s,source,modify);before=path.read_bytes();display(s,p,saved)
        p.locator('[data-view-audit="'+str(hit['hitId'])+'"]').click();p.wait_for_selector('.audit-steps')
        row=p.locator('.audit-steps [data-term="'+key+'"]').inner_text()
        s.check('inherited audit name '+key+' generic','기록된 계산 항목' in row and key not in row and '[native code]' not in row and '[object Object]' not in row,row)
        s.check('inherited audit name '+key+' storage kept',before==path.read_bytes()==s.call('runtime/skill-replays/'+saved['id'])[0].body())
        s.save('audit-name-'+key,dict(row=row,replayId=saved['id']))
    for i,label in enumerate(['이전 방식(고정 방어력)','검사 필요: terms[0].operation','constructor']):
        saved,path=put_copy(s,source,lambda x:x['battleConditions'].update(label=label));before=path.read_bytes();display(s,p,saved)
        text=p.locator('#replay-result [data-saved-combat]').inner_text();s.save('battle-label-'+str(i),dict(label=label,text=text,replayId=saved['id']))
        s.check('saved battle label '+str(i)+' registered or generic',('이전 방식(고정 방어력)' if i==0 else '전투 조건') in text and (i==0 or label not in text) and '30,925' in text and '2초' in text,text)
        s.check('saved battle label '+str(i)+' bytes retained',before==path.read_bytes()==s.call('runtime/skill-replays/'+saved['id'])[0].body())
    s.save('browser-load-observations',dict(console=console,failedRequests=failures,errors=s.report['errors']))
    s.check('major screen JS errors absent',not s.report['errors'],s.report['errors'])
    s.check('module network failures absent',not any('.js' in x['url'] for x in failures),failures)
    s.check('module console errors absent',not any(x['type']=='error' and any(t in x['text'].lower() for t in ['syntaxerror','unexpected token','module script','does not provide an export']) for x in console),console)
    p.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dotnet',required=True);a=parser.parse_args();s=Session(a.dotnet);s.report.update(product='42f4329',scope='independent ESM and major screens; private saved field variants')
    try:
        with sync_playwright() as pw:
            b=pw.chromium.launch(headless=True);ctx=b.new_context(viewport=dict(width=1500,height=1000));ctx.tracing.start(screenshots=True,snapshots=True,sources=True)
            try:run(s,ctx)
            finally:ctx.tracing.stop(path=str(s.run/'trace.zip'));b.close()
    except Exception as ex:s.report.update(status='aborted',error=repr(ex));raise
    finally:s.finish()
    return 0 if s.report['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())

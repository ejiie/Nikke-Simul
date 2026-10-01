"""Independent U-FIX-7 persisted replay + real browser audit.

Reuses only QA-owned fixture plumbing. No implementation/reviewer tests or mocks.
Fault cases write NEW copies of our own synthetic saved results, then real GET.
"""
import argparse, json, re, uuid, math
from copy import deepcopy
from playwright.sync_api import sync_playwright
from check_f2_conditions import Session, ROOT
from public_fixture import read, digest

FORBIDDEN = ['calculation.terms', 'terms[]', 'effectiveAttack', 'effectiveDefense',
             'multiply', 'identity', 'native +', 'checked int64', 'float32 left', '(hit']
UNKNOWN = '저장된 연산 미확인'

def run(s, ctx):
    s.start(ctx.request)
    s.check('API health projectRoot is QA checkout', s.call('health')[1]['projectRoot'] == str(ROOT))
    s.check('served UI equals checked out source', ctx.request.get(s.base+'/editor/damage-log-adapter.js').body() == (ROOT/'apps/desktop-ui/damage-log-adapter.js').read_bytes())
    assert s.call('accounts/synthetic-account/formation', dict(slots=s.ids), 'PUT')[0].ok
    page=ctx.new_page(); page.on('pageerror', lambda e:s.report['errors'].append(str(e)))
    page.goto(s.base+'/editor/');page.wait_for_selector('body[data-ready="true"]');page.locator('[data-tab="raid"]').click()
    def open_entry(saved, entry):
        def redirect(route):route.continue_(url=s.base+'/api/runtime/skill-replays/'+saved['id'],method='GET',post_data='')
        page.route('**/api/runtime/skill-replays',redirect)
        with page.expect_response(lambda r:r.url.endswith('/api/runtime/skill-replays/'+saved['id'])) as event:page.locator('#run-replay').click()
        s.check('real GET '+saved['id'], event.value.status==200 and event.value.json()==saved)
        page.unroute('**/api/runtime/skill-replays',redirect)
        page.locator('[data-view-audit="'+str(entry['hitId'])+'"]').click();page.wait_for_selector('.audit-steps')
    def observe(label, saved, entry, unknown=False):
        terms=entry['calculation']['terms']
        rows=page.locator('.audit-steps tr[data-term]').evaluate_all('(rs)=>rs.map(r=>({key:r.dataset.term,label:r.cells[0].innerText,before:r.cells[1].innerText,after:r.cells[2].innerText,description:r.cells[3].innerText}))')
        text=page.locator('.damage-audit-panel').inner_text()
        s.save(label,dict(replayId=saved['id'],hitId=entry['hitId'],terms=terms,rows=rows,text=text))
        s.check(label+' no wire text', not [t for t in FORBIDDEN if t.lower() in text.lower()])
        # The brief explicitly permits formula notation. The defenceRatio formula is
        # not a raw operation/key dump; do not reject it for having no Hangul.
        s.check(label+' every row Korean or allowed formula',len(rows)==len(terms) and all(re.search('[가-힣]',r['label']) and (re.search('[가-힣]',r['description']) or r['description']=='1 − defenceRatioRate (float32)') for r in rows),rows)
        s.check(label+' keys and values unchanged',len(rows)==len(terms) and all(r['key']==t['name'] and all(math.isclose(float(r[k].replace(',','')),t[k],rel_tol=1e-13,abs_tol=1e-10) for k in ['before','after']) for r,t in zip(rows,terms)))
        if unknown:s.check(label+' all operations unconfirmed without guessing',all(r['description']==UNKNOWN for r in rows), rows)
        path=s.data/'skill-replays'/(saved['id']+'.json');before=path.read_bytes()
        for suffix in ['', '/export.json']:
            s.check(label+' saved/API bytes '+suffix,s.call('runtime/skill-replays/'+saved['id']+suffix)[0].body()==before)
        for ext in ['json','csv']:
            expected=s.call('runtime/skill-replays/'+saved['id']+'/damage-log/export.'+ext)[0].body()
            with page.expect_download() as dl:page.locator('#btn-export-'+ext).click()
            dest=s.run/(label+'-download.'+ext);dl.value.save_as(dest)
            s.check(label+' browser download '+ext,dest.read_bytes()==expected)
        s.check(label+' storage not rewritten',path.read_bytes()==before)
        return rows
    # True UI POST -> API calculation/storage -> audit panel for every policy.
    originals=[]
    for policy in ['client_f32','legacy_term_floor','final_round_even','nested_floor']:
        page.locator('[name="rounding"]').select_option(policy)
        def short(route):
            body=route.request.post_data_json;body['conditionProfile']='legacy';body['conditions']['combat'].update(durationFrames=180,enemyDefense=30925,defenseMode='fixed',core=True,critMode='off')
            route.continue_(post_data=json.dumps(body))
        page.route('**/api/runtime/skill-replays',short)
        with page.expect_response(lambda r:r.url.endswith('/api/runtime/skill-replays') and r.request.method=='POST') as event:page.locator('#run-replay').click()
        saved=event.value.json();assert event.value.status==200,saved
        page.unroute('**/api/runtime/skill-replays',short)
        s.save('created-'+policy,saved)
        entries=saved['result']['damageLog']['entries'];entry=entries[0];originals.append((policy,saved,entry))
        page.locator('[data-view-audit="'+str(entry['hitId'])+'"]').click();page.wait_for_selector('.audit-steps')
        observe('current-'+policy,saved,entry)
        page.locator('.audit-steps').screenshot(path=str(s.run/('current-'+policy+'.png')))
    source=ROOT/'artifacts/single-deck-qa/f2-ufix3-554048887882/data/skill-replays/b41c653c67fa48dfa35cb46547de88ab.json'
    before=source.read_bytes();saved=read(source);(s.data/'skill-replays'/source.name).write_bytes(before)
    entry=next(e for e in saved['result']['damageLog']['entries'] if e['hit']['fullBurst'] and e['hit']['core'])
    open_entry(saved,entry);observe('prior-archive',saved,entry)
    for width in [1500,850,500]:
        page.set_viewport_size(dict(width=width,height=1000));page.locator('.audit-steps').screenshot(path=str(s.run/f'prior-archive-{width}.png'))
    page.set_viewport_size(dict(width=1500,height=1000))
    s.check('prior archive original unchanged',source.read_bytes()==before)
    s.save('prior-archive-hash',dict(sha256=digest(source),totalDamage=saved['result']['totalDamage']))
    # Every actual saved term in all four policies: unknown, null and omitted.
    for policy,original,original_entry in originals:
        for fault in ['unknown','null','omitted']:
            saved=deepcopy(original);saved['id']=uuid.uuid4().hex;entry=saved['result']['damageLog']['entries'][0]
            for t in entry['calculation']['terms']:
                if fault=='omitted':t.pop('operation',None)
                else:t['operation']=None if fault=='null' else 'qa_unregistered_operation'
            (s.data/'skill-replays'/(saved['id']+'.json')).write_text(json.dumps(saved,ensure_ascii=False),encoding='utf-8')
            open_entry(saved,entry);observe(policy+'-'+fault,saved,entry,True)
    # Registered multiply grammar is exactly `multiply <factor>` or `multiply <factor>; floor`.
    # These changed suffixes describe DIFFERENT/unknown operations and must not be interpreted as old ones.
    policy,original,_=originals[-1]
    for suffix in ['; qa_unknown_transform','; floor_if_qa_condition','unexpected']:
        saved=deepcopy(original);saved['id']=uuid.uuid4().hex;entry=saved['result']['damageLog']['entries'][0]
        targets=[t for t in entry['calculation']['terms'] if t['name'] in ['B3','B4','B5']]
        assert len(targets)==3
        for t in targets:t['operation']='multiply 1.25'+suffix
        (s.data/'skill-replays'/(saved['id']+'.json')).write_text(json.dumps(saved,ensure_ascii=False),encoding='utf-8')
        open_entry(saved,entry);label='multiply-suffix-'+str(len(s.report['checks']));rows=observe(label,saved,entry)
        actual=[r for r in rows if r['key'] in ['B3','B4','B5']]
        s.check(label+' unregistered full operation must stay unknown',all(r['description']==UNKNOWN for r in actual),dict(operation=targets[0]['operation'],rows=actual))
        page.locator('.audit-steps').screenshot(path=str(s.run/(label+'.png')))
    # Unknown term names + automatic burst reasons persist in private copies only.
    saved=deepcopy(originals[0][1]);saved['id']=uuid.uuid4().hex;entry=saved['result']['damageLog']['entries'][0]
    entry['calculation']['terms'][0]['name']='qa_private_term_path'
    saved['result']['teamBurst']['waitingReason']='qa_summary_wait_reason'
    saved['result']['teamBurst']['timeline'].append(dict(kind='waiting',reason='qa_timeline_wait_reason',frame=1,step=1,characterId=s.ids[0],readyAtFrame=None))
    (s.data/'skill-replays'/(saved['id']+'.json')).write_text(json.dumps(saved,ensure_ascii=False),encoding='utf-8')
    open_entry(saved,entry);rows=observe('unknown-name-and-burst',saved,entry)
    s.check('unknown name neutral label',rows[0]['label']=='기록된 계산 항목' and rows[0]['description']==UNKNOWN)
    detail=page.locator('details').filter(has=page.get_by_text('충전 기여·시전·대기 기록',exact=True));detail.locator('summary').click()
    visible=page.locator('#replay-result').inner_text();s.save('burst-unknown-visible',dict(text=visible))
    s.check('unknown waiting reasons both neutral',visible.count('대기 사유 미확인')==2 and not any(x in visible for x in ['qa_summary_wait_reason','qa_timeline_wait_reason','qa_private_term_path']))
    s.check('hit number preserved','타격 #'+str(entry['hitId']) in visible)
    page.screenshot(path=str(s.run/'burst-unknown.png'),full_page=True)
    page.locator('#log-character-select').select_option(s.ids[0]);page.wait_for_timeout(300)
    s.check('replay ID preserved in missing target state',saved['id'] in page.locator('#damage-log-container').inner_text())
    s.check('no browser exceptions',not s.report['errors'],s.report['errors']);page.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args();s=Session(a.dotnet)
    s.report.update(product='b401421',scope='U-FIX-7 independent real POST/storage/GET/browser + corrupted own saved copies')
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport=dict(width=1500,height=1000),accept_downloads=True);ctx.tracing.start(screenshots=True,snapshots=True,sources=True)
            run(s,ctx);ctx.tracing.stop(path=str(s.run/'trace.zip'));browser.close()
    except Exception as ex:s.report.update(status='aborted',error=repr(ex));raise
    finally:s.finish()
    return 0 if s.report['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())

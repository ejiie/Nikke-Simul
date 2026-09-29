"""F2-Q-6 minimal real stored GET: visible audit wire keys and server operations.

Own previous synthetic archive only. No response mock or product oracle.
Formula symbols/English scientific units themselves are not the rejection rule.
"""
import argparse,shutil
from playwright.sync_api import sync_playwright
from check_f2_conditions import Session,ROOT
from public_fixture import read,digest

def verify(s,ctx):
 source=ROOT/'artifacts/single-deck-qa/f2-ufix3-554048887882/data/skill-replays/b41c653c67fa48dfa35cb46547de88ab.json'
 before=source.read_bytes();stored=read(source);s.start(ctx.request)
 target=s.data/'skill-replays'/source.name;target.parent.mkdir(exist_ok=True);shutil.copyfile(source,target)
 assert s.call('accounts/synthetic-account/formation',dict(slots=s.ids),'PUT')[0].ok
 page=ctx.new_page();page.goto(s.base+'/editor/');page.wait_for_selector('body[data-ready="true"]');page.locator('[data-tab="raid"]').click()
 def get_saved(route):route.continue_(url=s.base+'/api/runtime/skill-replays/'+stored['id'],method='GET',post_data='')
 page.route('**/api/runtime/skill-replays',get_saved)
 with page.expect_response(lambda r:r.url.endswith('/api/runtime/skill-replays/'+stored['id'])) as pending:page.locator('#run-replay').click()
 r=pending.value;s.check('F2-Q-6 real GET of prior QA archive',r.status==200 and r.request.method=='GET' and r.json()==stored)
 entry=next(e for e in stored['result']['damageLog']['entries'] if e['hit']['fullBurst'] and e['hit']['core'])
 page.locator('[data-view-audit="'+str(entry['hitId'])+'"]').click();page.wait_for_selector('.audit-steps')
 text=page.locator('.damage-audit-panel').inner_text()
 rows=page.locator('.audit-steps tr[data-term]').evaluate_all('(rows)=>rows.map(r=>({visibleKey:r.cells[0].querySelector("small").innerText,visibleOperation:r.cells[3].innerText,label:r.cells[0].innerText}))')
 wire=entry['calculation']['terms'];rawkeys=[row['visibleKey'] for row in rows if row['visibleKey'] in {t['name'] for t in wire}]
 rawops=[row['visibleOperation'] for row in rows if row['visibleOperation'] in {t['operation'] for t in wire}]
 s.save('audit-wire-vs-visible',dict(replayId=stored['id'],hitId=entry['hitId'],terms=wire,rows=rows,text=text,rawKeys=rawkeys,rawServerOperations=rawops))
 s.check('F2-Q-6 internal calculation path absent from screen','calculation.terms' not in text)
 s.check('F2-Q-6 raw stored term keys absent from screen',not rawkeys,rawkeys)
 s.check('F2-Q-6 raw server operations absent from screen',not rawops,rawops)
 for width in [1500,850,500]:
  page.set_viewport_size(dict(width=width,height=1000));page.locator('.audit-steps').screenshot(path=str(s.run/('audit-raw-'+str(width)+'.png')))
 s.check('F2-Q-6 raw GET source/copy/total preserved',source.read_bytes()==target.read_bytes()==before==s.call('runtime/skill-replays/'+stored['id'])[0].body() and r.json()['result']['totalDamage']==stored['result']['totalDamage'])
 s.save('archive',dict(sha256=digest(source),totalDamage=stored['result']['totalDamage']));page.close()

def main():
 p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args();s=Session(a.dotnet);s.report['scope']='F2-Q-6 actual stored GET minimal audit raw text reproduction'
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport=dict(width=1500,height=1000));ctx.tracing.start(screenshots=True,snapshots=True,sources=True);verify(s,ctx);ctx.tracing.stop(path=str(s.run/'trace.zip'));browser.close()
 except Exception as ex:s.report.update(status='aborted',error=repr(ex));raise
 finally:s.finish()
 return 0 if s.report['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())

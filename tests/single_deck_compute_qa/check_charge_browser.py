"""Real UI manual-full-charge selection, actual API response, saved damage rows."""
import argparse,json,re,sqlite3,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from check_charge_api import ChargeSession,OUT,ROOT
from check_ufix7_families import open_page
from public_fixture import read
p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args();s=ChargeSession(a.dotnet)
s.report.update(product='d932716',scope='E-BUG-1 actual UI controls and damage log')
(OUT/'browser-evidence.txt').write_text(str(s.run),encoding='utf-8')
for relative in read(OUT/'public-hashes-before.json'):
 target=s.data/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OUT/'public-copy'/relative,target)
for member in s.snapshot['characters']:
 for equipment in member['equipment']:
  equipment['tier']=0;equipment['lines']=[dict(lineIndex=i,presence='absent') for i in range(1,4)]
with sqlite3.connect(s.data/'accounts.db') as db:db.execute('UPDATE snapshots SET payload=?',(json.dumps(s.snapshot),))
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport=dict(width=1550,height=1100));ctx.tracing.start(screenshots=True,snapshots=True,sources=True)
  s.start_binary(ctx.request,ROOT/'src/Nikke.Api/bin/Release/net10.0')
  assert s.call('accounts/synthetic-account/formation',dict(slots=s.ids),'PUT')[0].ok
  page=open_page(s,ctx);page.locator('[name="manualCharacter"]').select_option('5004');page.locator('[name="manualStyle"]').select_option('full_charge');page.locator('[name="core"]').check()
  with page.expect_response(lambda r:r.url.endswith('/api/runtime/skill-replays') and r.request.method=='POST',timeout=120000) as pending:page.locator('#run-replay').click()
  r=pending.value;wire=r.request.post_data_json;v=r.json();s.save('browser-replay',v)
  s.check('real UI sends Alice manual full charge',r.status==200 and wire['conditions']['combat']['manualCharacterId']=='5004' and wire['conditions']['combat']['manualStyle']=='full_charge',wire)
  page.wait_for_selector('#damage-log-container');page.wait_for_selector('tr[data-hit-id]')
  s.check('saved API GET equals browser response',s.call('runtime/skill-replays/'+v['id'])[1]==v)
  entries={str(e['hitId']):e for e in v['result']['damageLog']['entries']}
  for label,filter in [('all','all'),('self-burst','both'),('outside-burst','none')]:
   page.locator('[data-filter-burst="'+filter+'"]').click()
   rows=page.locator('tr[data-hit-id]').evaluate_all('(rs)=>rs.map(r=>({id:r.dataset.hitId,time:r.cells[0].innerText,text:r.innerText}))')
   exact=all(str(entries[row['id']]['frame'])+'F' in row['time'] for row in rows)
   frames=[entries[row['id']]['frame'] for row in rows if entries[row['id']].get('shotId') is not None]
   gaps=[y-x for x,y in zip(frames,frames[1:])]
   s.check('displayed frame numbers exact '+label,exact and len(rows)>3,dict(rows=len(rows),firstFrames=frames[:14],gaps=gaps[:13]))
   if label=='self-burst':s.check('self-burst display no 2F collapse',gaps and min(gaps)>=19,dict(min=min(gaps),firstGaps=gaps[:13]))
   s.save('rows-'+label,rows);page.locator('#damage-log-container').screenshot(path=str(s.run/('damage-'+label+'.png')))
  page.locator('[data-filter-burst="all"]').click();first=page.locator('[data-view-audit]').first;first.click();page.wait_for_selector('.damage-audit-panel')
  s.check('damage audit Korean and matching saved result','저장된 발당 피해와 일치' in page.locator('.damage-audit-panel').inner_text())
  s.check('no browser module errors',not s.report['errors'],s.report['errors'])
  ctx.tracing.stop(path=str(s.run/'trace.zip'));browser.close()
except Exception as ex:s.report.update(status='aborted',error=repr(ex));raise
finally:s.finish()
raise SystemExit(s.report['status']!='passed')

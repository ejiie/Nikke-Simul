"""Small real malformed-profile regression after F2. Own immutable runtime copies only."""
import hashlib,json,sqlite3
from copy import deepcopy
from public_fixture import read,digest

def verify(s,ctx):
 pointer=s.data/'runtime/current.json';original=pointer.read_bytes();catalog=read(s.data/'runtime'/read(pointer)['id']/'catalog.json')
 def counts():
  with sqlite3.connect(s.data/'compute/batches.db') as db:n=db.execute('select count(*) from experiments').fetchone()[0]
  return n,{str(p):digest(p) for p in (s.data/'skill-replays').glob('*.json')}
 try:
  for field in ['bonusRangeMin','bonusRangeMax','element']:
   s.stop();bad=deepcopy(catalog);bad['combatProfiles']['characters']['5004'].pop(field)
   payload=json.dumps(bad,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();id=hashlib.sha256(payload).hexdigest();folder=s.data/'runtime'/id;folder.mkdir(exist_ok=True);(folder/'catalog.json').write_bytes(payload);pointer.write_text(json.dumps(dict(id=id,file='catalog.json',schemaVersion=1)),encoding='utf-8');s.start(ctx.request)
   before=counts();request=dict(snapshotId=s.snapshot['id'],characterIds=s.ids,scenarioLevel=400,conditions=dict(combat=dict(bossDistance=35,bossWeakElement='Fire')))
   for path,body in [('runtime/combat-conditions',None),('snapshots/'+s.snapshot['id']+'/combat-conditions?characterIds='+','.join(s.ids),None),('runtime/skill-replays',request),('compute/experiments',dict(request,runs=1,phase='pilot',execution=dict(requested='cpu',maxWorkers=1)))]:
    r,v=s.call(path,body);s.check('F-COND missing '+field+' '+path,r.status==409 and v.get('code')=='combat_profile_invalid' and v.get('characterId')=='5004' and v.get('field')=='combatProfiles.characters.5004.'+field and v.get('reason')=='missing',v)
   s.check('F-COND missing '+field+' no storage',counts()==before)
   if field=='bonusRangeMin':
    page=ctx.new_page();page.goto(s.base+'/editor/');page.wait_for_selector('body[data-ready="true"]');page.locator('[data-tab="raid"]').click();page.locator('[data-cond-open="distance"]').click();page.wait_for_selector('[data-cond-error="members"]');text=page.locator('dialog[open]').inner_text();s.check('F-COND real Korean malformed popup',all(x in text for x in ['앨리스(#5004)','bonusRangeMin','prepare_combat_conditions.py']));page.screenshot(path=str(s.run/'regression-malformed-popup.png'),full_page=True);page.locator('dialog[open] button[type="submit"]').click();page.locator('[data-cond-open="element"]').click();page.locator('[data-cond-element="fire"]').click();page.locator('[data-tab="stats"]').click();page.locator('#compute-runs').fill('1')
    with page.expect_response(lambda r:r.url.endswith('/api/compute/experiments') and r.request.method=='POST') as pending:page.locator('#compute-start').click()
    page.wait_for_function('document.querySelector("#stats-content").innerText.includes("사거리·속성 데이터 오류")');text=page.locator('#stats-content').inner_text();s.check('F-COND real409 keeps API connected',pending.value.status==409 and '실제 API 응답' in text and 'compute API 미연결' not in text);s.save('profile-error-browser',dict(text=text,response=pending.value.json()));page.close()
 finally:s.stop();pointer.write_bytes(original)

if __name__=='__main__':
 import argparse
 from playwright.sync_api import sync_playwright
 from check_f2_conditions import Session
 p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args();s=Session(a.dotnet)
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport=dict(width=1500,height=1000));s.start(ctx.request)
   assert s.call('accounts/synthetic-account/formation',dict(slots=s.ids),'PUT')[0].ok
   verify(s,ctx);browser.close();s.report['status']='passed' if all(c['passed'] for c in s.report['checks']) else 'failed'
 except Exception as ex:s.report['status']='aborted';s.report['error']=repr(ex);raise
 finally:s.finish()
 raise SystemExit(0 if s.report['status']=='passed' else 1)

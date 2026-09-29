"""U-FIX-6 own persisted diagnostics and malformed catalog, real HTTP/Chromium.

Synthetic diagnostic rows live in the QA-created account; no response is mocked.
Faults mutate only immutable runtime copies under this new QA dataRoot.
"""
import argparse,hashlib,json,sqlite3
from copy import deepcopy
from playwright.sync_api import sync_playwright
from check_f2_conditions import Session
from check_f2_ufix3 import scan_codes
from public_fixture import read,digest

def screen(s,page,label):
 scan_codes(s,page,label)
 for width in [1500,850,500]:
  page.set_viewport_size(dict(width=width,height=1000))
  s.check('U-FIX-6 layout '+label+' '+str(width),not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'))
  page.screenshot(path=str(s.run/(label+'-'+str(width)+'.png')),full_page=True)
 page.set_viewport_size(dict(width=1500,height=1000))

def diagnostics(s,ctx):
 # Directly authored QA account diagnostics, preserving private issue paths and
 # equipment slot source keys in actual storage/API while asserting screen text.
 s.snapshot['issues']=[dict(code='qa_missing_equipment',path='characters.5004.equipment.head',message='앨리스의 머리 장비를 확인하세요.')]
 s.snapshot['changes']=['앨리스: '+slot+' 장비/잠금 변경' for slot in ['head','torso','arm','arms','leg','legs']]
 with sqlite3.connect(s.data/'accounts.db') as db:db.execute('UPDATE snapshots SET payload=?',(json.dumps(s.snapshot),))
 s.start(ctx.request);assert s.call('accounts/synthetic-account/formation',dict(slots=s.ids),'PUT')[0].ok
 page=ctx.new_page();page.on('pageerror',lambda e:s.report['errors'].append(str(e)))
 page.goto(s.base+'/editor/');page.wait_for_selector('body[data-ready="true"]');page.locator('[data-tab="advanced"]').click()
 text=page.locator('#advanced-content').inner_text();s.save('advanced-persisted-input-and-text',dict(snapshot=s.snapshot,text=text))
 s.check('U-FIX-6 diagnostic name and Korean slots',all(x in text for x in ['앨리스','머리','몸통','팔','다리']) and all(x+' 장비' not in text for x in ['head','torso','arm','arms','leg','legs']),text)
 s.check('U-FIX-6 private diagnostic path retained in DOM attribute',page.locator('[data-issue-path]').get_attribute('data-issue-path')=='characters.5004.equipment.head')
 screen(s,page,'advanced')
 with sqlite3.connect(s.data/'accounts.db') as db:saved=json.loads(db.execute('SELECT payload FROM snapshots').fetchone()[0])
 s.check('U-FIX-6 diagnostics display does not rewrite persisted values',saved['issues']==s.snapshot['issues'] and saved['changes']==s.snapshot['changes'])
 page.locator('[data-tab="raid"]').click()
 # Real validation failures through outgoing request changes. Product API
 # supplies every response; no synthetic success/error response is substituted.
 for label,modify,meaning in [
  ('unknown-boss',lambda b:b.update(bossId='qa-does-not-exist'),'보스'),
  ('wrong-duration',lambda b:b['conditions']['combat'].update(durationFrames=120),'180'),
  ('unknown-profile',lambda b:b.update(conditionProfile='qa-invalid'),'전투 조건')]:
  def alter(route):
   body=route.request.post_data_json;modify(body);route.continue_(post_data=json.dumps(body))
  page.route('**/api/runtime/skill-replays',alter)
  with page.expect_response(lambda r:r.url.endswith('/api/runtime/skill-replays') and r.request.method=='POST') as pending:page.locator('#run-replay').click()
  r=pending.value;page.unroute('**/api/runtime/skill-replays',alter);page.wait_for_timeout(200)
  text=page.locator('#replay-result').inner_text();s.save(label,dict(status=r.status,server=r.json(),text=text))
  s.check('U-FIX-6 real400 translated '+label,r.status==400 and meaning in text and '_' not in text,text);screen(s,page,label)
 page.locator('[data-tab="stats"]').click();page.wait_for_timeout(800);page.locator('#compute-runs').fill('1')
 # Ineligible hardware is intentionally not selectable. Force only the outgoing
 # request to test the real API refusal, without inventing an enabled GPU option.
 def force_gpu(route):
  body=route.request.post_data_json;body.setdefault('execution',{}).update(requested='gpu',maxWorkers=1);route.continue_(post_data=json.dumps(body))
 page.route('**/api/compute/experiments',force_gpu)
 with page.expect_response(lambda r:r.url.endswith('/api/compute/experiments') and r.request.method=='POST') as pending:page.locator('#compute-start').click()
 r=pending.value;page.unroute('**/api/compute/experiments',force_gpu);page.wait_for_timeout(300);text=page.locator('#stats-content').inner_text()
 s.save('gpu-refusal',dict(status=r.status,response=r.json(),text=text))
 s.check('U-FIX-6 real GPU refusal stays connected and Korean',r.status==409 and 'GPU 사용 불가' in text and '실제 API 응답' in text and 'compute API 미연결' not in text,text)
 screen(s,page,'gpu-refusal');page.close();s.stop()

def profiles(s,ctx):
 pointer=s.data/'runtime/current.json';original=pointer.read_bytes();catalog=read(s.data/'runtime'/read(pointer)['id']/'catalog.json')
 def counts():
  with sqlite3.connect(s.data/'compute/batches.db') as db:n=db.execute('SELECT count(*) FROM experiments').fetchone()[0]
  return n,{p.name:digest(p) for p in (s.data/'skill-replays').glob('*.json')}
 try:
  for label in ['element-null','catalog-missing']:
   bad=deepcopy(catalog)
   if label=='element-null':bad['combatProfiles']['characters']['5004']['element']=None
   else:bad.pop('combatProfiles')
   payload=json.dumps(bad,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();id=hashlib.sha256(payload).hexdigest();folder=s.data/'runtime'/id;folder.mkdir(exist_ok=True);(folder/'catalog.json').write_bytes(payload);pointer.write_text(json.dumps(dict(id=id,file='catalog.json',schemaVersion=1)),encoding='utf-8');s.start(ctx.request)
   before=counts();request=dict(snapshotId=s.snapshot['id'],characterIds=s.ids,scenarioLevel=400,conditions=dict(combat=dict(bossDistance=35,bossWeakElement='Fire')))
   for path,body in [('runtime/combat-conditions',None),('runtime/skill-replays',request),('compute/experiments',dict(request,runs=1,phase='pilot',execution=dict(requested='cpu',maxWorkers=1)))]:
    r,v=s.call(path,body);s.check('U-FIX-6 '+label+' 409 '+path,r.status==409 and (label!='element-null' or v.get('code')=='combat_profile_invalid' and v.get('characterId')=='5004' and v.get('field')=='combatProfiles.characters.5004.element' and bool(v.get('reason'))),v)
   page=ctx.new_page();page.goto(s.base+'/editor/');page.wait_for_selector('body[data-ready="true"]');page.locator('[data-tab="raid"]').click()
   for popup in ['distance','element']:
    page.locator('[data-cond-open="'+popup+'"]').click();page.wait_for_selector('[data-cond-error="members"]');text=page.locator('dialog[open]').inner_text()
    s.check('U-FIX-6 '+label+' '+popup+' meaningful Korean guidance','prepare_combat_conditions.py' in text and ('앨리스' in text and '속성' in text if label=='element-null' else '준비되지' in text),text)
    screen(s,page,label+'-'+popup)
    if popup=='distance':page.locator('dialog[open] button[type="submit"]').click()
    else:page.locator('[data-cond-element="fire"]').click()
   with page.expect_response(lambda r:r.url.endswith('/api/runtime/skill-replays') and r.request.method=='POST') as pending:page.locator('#run-replay').click()
   page.wait_for_selector('[data-profile-error]');s.check('U-FIX-6 '+label+' browser replay409',pending.value.status==409);screen(s,page,label+'-replay')
   page.locator('[data-tab="stats"]').click();page.locator('#compute-runs').fill('1')
   with page.expect_response(lambda r:r.url.endswith('/api/compute/experiments') and r.request.method=='POST') as pending:page.locator('#compute-start').click()
   page.wait_for_timeout(300);text=page.locator('#stats-content').inner_text();s.check('U-FIX-6 '+label+' browser stats409 connected',pending.value.status==409 and '실제 API 응답' in text and 'compute API 미연결' not in text)
   screen(s,page,label+'-stats');s.check('U-FIX-6 '+label+' no replay/compute storage',counts()==before);page.close();s.stop()
 finally:s.stop();pointer.write_bytes(original)

def main():
 p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args();s=Session(a.dotnet);s.report['scope']='U-FIX-6 actual diagnostics, real400/409, malformed catalog'
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport=dict(width=1500,height=1000));ctx.tracing.start(screenshots=True,snapshots=True,sources=True)
   diagnostics(s,ctx);profiles(s,ctx);s.check('U-FIX-6 no browser exceptions',not s.report['errors'],s.report['errors']);ctx.tracing.stop(path=str(s.run/'trace.zip'));browser.close()
 except Exception as ex:s.report.update(status='aborted',error=repr(ex));raise
 finally:s.finish()
 return 0 if s.report['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())

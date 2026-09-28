"""Independent B-FIX-2 and F-COND-Q stage2. Actual HTTP/Chromium, no response mocks."""
import argparse,json,os,sys,socket,sqlite3,subprocess,time,uuid,hashlib,shutil
from pathlib import Path
from copy import deepcopy
from playwright.sync_api import sync_playwright
from public_fixture import create,read,digest
from check_client_f32 import context as hit_reference
from check_f32_b1 import normalized
from actual_stats import metric
ROOT=Path(__file__).resolve().parents[2]

def main():
 p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args()
 run=ROOT/'artifacts/single-deck-qa'/('conditions-browser-'+uuid.uuid4().hex[:12]);data=run/'data';data.mkdir(parents=True)
 source=ROOT/'artifacts/single-deck-qa/load1000-3db71912a601/data';hashes,game,snapshot,ids=create(source,data)
 record=next(r for r in read(ROOT/'docs/p03-source-manifest.json') if r.get('inputKey')=='sourceRoles');rosterpath=Path(record['sourceRoot'])/record['path'];roster=read(rosterpath)['roster'];assert digest(rosterpath)==record['sha256']
 subprocess.run([sys.executable,str(ROOT/'tools/data-pipeline/prepare_combat_conditions.py'),'--runtime-root',str(data/'runtime'),'--source-roster',str(rosterpath)],check=True,capture_output=True)
 pointer=data/'runtime/current.json';normalpointer=pointer.read_bytes();catalog=read(data/'runtime'/read(pointer)['id']/'catalog.json')
 assets=ROOT/'artifacts/image-collection-qa/fixed-a2f67a4db2b94cbe8c3661dfbcaec694/origin/presentation/assets/ui';asset_hashes={}
 for element in ['fire','water','wind','iron','electric']:
  name='code-'+element+'.png';asset_hashes[name]=digest(assets/name);target=data/'presentation/assets/ui'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(assets/name,target)
 rawid=uuid.uuid4().hex;snapshot['rawManifestId']=rawid
 connection=dict(id='qa-conditions-connection',accountId=snapshot['accountId'],status='ready',nickname='QA synthetic',area=1,updatedAt='2026-09-29T00:00:00Z',choices=[dict(area=1,label='QA synthetic',characterCount=5,openId='synthetic')])
 with sqlite3.connect(data/'accounts.db') as db:
  db.execute('UPDATE snapshots SET payload=?',(json.dumps(snapshot),));db.execute('CREATE TABLE connections(id TEXT PRIMARY KEY,payload TEXT NOT NULL)');db.execute('INSERT INTO connections VALUES(?,?)',(connection['id'],json.dumps(connection)))
 rawdir=data/'raw'/rawid;rawdir.mkdir(parents=True);raw=json.dumps(dict(source='QA_SYNTHETIC',characters=[dict(name_code=id,combat=0) for id in ids]));(rawdir/'envelope.json').write_text(raw,encoding='utf-8');(rawdir/'manifest.json').write_text(json.dumps(dict(envelopeHash=hashlib.sha256(raw.encode()).hexdigest())),encoding='utf-8')
 report=dict(status='running',checks=[],errors=[],responseMocks=False);traffic=[];process=None;log=None;token=''
 def save(name,value):(run/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
 def check(name,ok,detail=None):report['checks'].append(dict(name=name,passed=bool(ok),detail=detail));save('summary',report);print(name+(': PASS' if ok else ': FAIL'),flush=True)
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 assert port not in(5180,5181);base=f'http://127.0.0.1:{port}';report['port']=port
 env=dict(os.environ,NIKKE_PROJECT_ROOT=str(ROOT),NIKKE_DATA_ROOT=str(data),NIKKE_PORT=str(port),NIKKE_TEST_FIXTURE='1');env.pop('NIKKE_GAME_CATALOG',None)
 def start(api):
  nonlocal process,log,token
  log=(run/f'api-{time.time_ns()}.log').open('w',encoding='utf-8');process=subprocess.Popen([a.dotnet,str(ROOT/'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));report.setdefault('ownedPids',[]).append(process.pid)
  for _ in range(300):
   try:token=api.get(base+'/api/bootstrap').json()['token'];return
   except Exception:time.sleep(.1)
  raise AssertionError('API startup')
 def stop():
  nonlocal process,log
  if process:process.terminate();process.wait(timeout=30);process=None
  if log:log.close();log=None
 def publish(c):
  payload=json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();id=hashlib.sha256(payload).hexdigest();folder=data/'runtime'/id;folder.mkdir(exist_ok=True);(folder/'catalog.json').write_bytes(payload);pointer.write_text(json.dumps(dict(id=id,file='catalog.json',schemaVersion=1)),encoding='utf-8')
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport=dict(width=1500,height=1000));ctx.tracing.start(screenshots=True,snapshots=True,sources=True);api=ctx.request
   def call(path,body=None):
    r=api.fetch(base+'/api/'+path,method='GET' if body is None else 'POST',data=body,headers={'X-Nikke-Token':token});value=r.json() if r.text() else None;traffic.append(dict(path=path,status=r.status,request=body,response=value));return r.status,value
   start(api)
   api.put(base+'/api/accounts/synthetic-account/formation',data=dict(slots=ids),headers={'X-Nikke-Token':token})
   tactic=dict(schemaVersion=1,allowedCharacterIds=ids,stage1Priority=[ids[0]],stage2Priority=[ids[1]],stage3Priority=ids[2:],burst3Rotation=ids[2:],unavailablePolicy='next_ready')
   api.put(base+'/api/accounts/synthetic-account/burst-tactic',data=dict(snapshotId=snapshot['id'],formationSlots=ids,tactic=tactic),headers={'X-Nikke-Token':token})
   def page_new():
    page=ctx.new_page();page.on('pageerror',lambda e:report['errors'].append(str(e)));page.goto(base+'/editor/');page.wait_for_selector('body[data-ready="true"]');page.locator('[data-tab="raid"]').click();return page
   page=page_new()
   def shot(label):page.screenshot(path=str(run/(label+'.png')),full_page=True)
   def distance(value=None):
    page.locator('[data-cond-open="distance"]').click();page.locator('dialog[open] [name="distance"]').wait_for()
    if value is not None:page.locator('dialog[open] [name="distance"]').fill(str(value))
   def apply():page.locator('dialog[open] button[type="submit"]').click()
   def element(value):page.locator('[data-cond-open="element"]').click();page.locator('[data-cond-element="'+value.lower()+'"]').click()
   def layout(label):
    for width in [1500,850,500]:
     page.set_viewport_size(dict(width=width,height=1000));page.wait_for_timeout(100)
     dims=page.evaluate('''()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,dialogs:[...document.querySelectorAll('dialog[open]')].map(e=>{let r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&r.top>=0&&r.bottom<=innerHeight+1;})})''')
     check(label+' layout '+str(width),not dims['overflow'] and all(dims['dialogs']));shot(label+'-'+str(width))
    page.set_viewport_size(dict(width=1500,height=1000))
   sizes=page.locator('.cond-icon-btn').evaluate_all('(es)=>es.map(e=>{let r=e.getBoundingClientRect();return [r.width,r.height]})')
   check('square icon controls no old checkboxes',len(sizes)==2 and all(w==h==32 for w,h in sizes) and page.locator('#replay-form input[name="element"]').count()==0)
   page.locator('[data-cond-open="distance"]').focus();page.keyboard.press('Enter');page.wait_for_selector('.cond-range-table');page.wait_for_selector('.cond-member-list [data-member]')
   text=page.locator('dialog[open]').inner_text();check('real range table SR exception RL provisional',all(s in text for s in ['5042','25–45','0–0','보너스 없음','확인 필요']) and page.locator('.cond-range-table tbody tr').count()==6)
   page.locator('dialog[open] [name="distance"]').fill('35')
   preview=page.locator('.cond-member-list li').evaluate_all('(es)=>es.map(e=>({id:e.dataset.member,kind:e.dataset.distanceKind,text:e.innerText}))');save('normal-preview',preview)
   check('member distance preview independently correct',all(x['kind']==('in' if roster[x['id']]['bonusrange_min']<=35<=roster[x['id']]['bonusrange_max'] else 'out') for x in preview) and len(preview)==5)
   layout('distance');apply();check('apply focus restored',page.locator('[data-cond-open="distance"]').evaluate('(e)=>e===document.activeElement'))
   for i in range(5):
    page.keyboard.press('Enter');page.locator('dialog[open] [name="distance"]').fill('50');page.keyboard.press('Escape');page.wait_for_function('!document.querySelector("dialog[open]")')
    check('ESC focus and no apply '+str(i),page.locator('[data-cond-open="distance"]').evaluate('(e)=>e===document.activeElement') and '35' in page.locator('[data-cond-value="distance"]').inner_text())
   distance(101);apply();check('out of range stays in dialog',page.locator('dialog[open]').count()==1);page.locator('dialog[open] [data-cond-cancel]').click();page.wait_for_function('!document.querySelector("dialog[open]") && document.activeElement?.dataset.condOpen==="distance"')
   page.locator('[data-cond-open="element"]').focus();page.keyboard.press('Enter');page.wait_for_timeout(500);save('element-opening',page.evaluate('()=>({active:document.activeElement.outerHTML,dialogs:[...document.querySelectorAll("dialog")].map(e=>e.outerHTML)})'));shot('element-opening')
   opened=page.locator('[data-cond-element="fire"]').is_visible();check('element keyboard opens after distance cancel',opened)
   if not opened:page.locator('[data-cond-open="element"]').click()
   page.wait_for_selector('[data-cond-element="fire"]')
   check('weakness warning text','보스의 약점 속성 — 이 속성 니케가 우월 코드 보너스를 받습니다' in page.locator('dialog[open]').inner_text())
   check('five actual images loaded',page.locator('.cond-element img').evaluate_all('(es)=>es.length===5&&es.every(e=>e.complete&&e.naturalWidth>0)'))
   firetext=page.locator('[data-cond-element="fire"]').inner_text();check('Fire member preview','앨리스' in firetext and '모더니아' in firetext and '리타' not in firetext);layout('element')
   page.locator('[data-cond-element="fire"]').focus();page.keyboard.press('Enter');check('element keyboard selection focus',page.locator('[data-cond-open="element"]').evaluate('(e)=>e===document.activeElement') and 'Fire' in page.locator('[data-cond-value="element"]').inner_text())
   page.locator('[name="seconds"]').fill('20');page.locator('[name="core"]').check()
   def replay(label):
    with page.expect_response(lambda r:r.url.endswith('/api/runtime/skill-replays') and r.request.method=='POST',timeout=60000) as response:page.locator('#run-replay').click()
    r=response.value;v=r.json();save(label,dict(status=r.status,request=r.request.post_data_json,response=v));return r,v
   r,v=replay('normal-replay');c=r.request.post_data_json['conditions']['combat']
   check('actual replay new wire and mode',r.status==200 and c['bossDistance']==35 and c['bossWeakElement']=='Fire' and not any(k in c for k in ['properDistance','elementAdvantage']) and v['conditionCompatibility']['mode']=='per_member')
   page.wait_for_selector('[data-view-audit]');entries=v['result']['damageLog']['entries'];check('independent actual hits and flags',all(not e['hit']['properDistance'] and e['hit']['elementAdvantage'] and hit_reference(normalized(e['hit']))['damage']==e['damage'] for e in entries))
   chosen=next(e for e in entries if e['hit']['fullBurst']);page.locator('[data-view-audit="'+str(chosen['hitId'])+'"]').click();check('400 fullburst audit existing regression',r.request.post_data_json['scenarioLevel']==400 and page.locator('.audit-steps tr').count()>=10 and '저장된 발당 피해와 일치' in page.locator('#replay-result').inner_text());shot('audit');page.locator('#btn-close-audit').click()
   check('saved replay matches',call('runtime/skill-replays/'+v['id'])[1]==v);layout('normal-form')
   distance();page.locator('[data-cond-unset]').click();apply();element('');r,v=replay('null-replay');c=r.request.post_data_json['conditions']['combat'];check('explicit null real wire preserved',c['bossDistance'] is None and c['bossWeakElement'] is None and v['conditionCompatibility']['mode']=='per_member')
   def legacy(route):
    req=route.request.post_data_json;c=req['conditions']['combat'];c.pop('bossDistance');c.pop('bossWeakElement');c.update(properDistance=True,elementAdvantage=False);route.continue_(post_data=json.dumps(req))
   page.route('**/api/runtime/skill-replays',legacy);r,v=replay('legacy-replay');page.unroute('**/api/runtime/skill-replays',legacy);page.wait_for_function('document.querySelector("#replay-result").innerText.includes("이전 방식(전원 적용)")');check('real legacy response visibly labeled',v['conditionCompatibility']['mode']=='legacy_global' and '우월 코드 미적용' in page.locator('#replay-result').inner_text());shot('legacy')
   distance(35);apply();element('Fire');page.locator('[name="seconds"]').fill('10');page.locator('[data-tab="stats"]').click();page.locator('#compute-runs').fill('1');page.locator('.compute-advanced summary').click();page.locator('#compute-worker-limit').fill('1')
   with page.expect_response(lambda r:r.url.endswith('/api/compute/experiments') and r.request.method=='POST',timeout=60000) as pending:page.locator('#compute-start').click()
   response=pending.value;b=response.json();save('compute-request',response.request.post_data_json)
   for _ in range(600):
    _,state=call('compute/experiments/'+b['id'])
    if state['state'] in ['completed','failed','cancelled']:break
    page.wait_for_timeout(100)
   page.wait_for_selector('[data-comparison-state="no_baseline"]',timeout=30000);_,st=call('compute/experiments/'+b['id']+'/statistics');_,rows=call('compute/experiments/'+b['id']+'/results');metric(st['team'],[x['teamDamage'] for x in rows['runs']]);save('normal-statistics',dict(batch=state,statistics=st,results=rows,text=page.locator('#stats-content').inner_text()))
   c=response.request.post_data_json['conditions']['combat'];text=page.locator('#stats-content').inner_text();check('actual statistics wire stored values and connection',state['state']=='completed' and c['bossDistance']==35 and c['bossWeakElement']=='Fire' and not any(k in c for k in ['properDistance','elementAdvantage']) and state['input']['conditionCompatibility']['mode']=='per_member' and '실제 API 응답' in text and format(int(st['team']['mean']),',') in text and '저장된 실험 조건' in text);layout('statistics');page.close();stop()
   # Independent invalid catalogue matrix; each case is a new immutable version, no source modifications.
   matrix=[]
   for field in ['bonusRangeMin','bonusRangeMax','element']:
    for reason,value in [('missing',None),('null',None),('wrong_type',{}),('wrong_type',True)]:matrix.append((field,reason,value))
   matrix.extend([('bonusRangeMin','out_of_range',-1),('bonusRangeMax','out_of_range',101),('element','unsupported_value','Electric'),('characterId','id_mismatch','wrong')])
   for index,(field,reason,value) in enumerate(matrix):
    bad=deepcopy(catalog);profile=bad['combatProfiles']['characters']['5004']
    if reason=='missing':profile.pop(field)
    else:profile[field]=value
    publish(bad);start(api)
    def counts():
     with sqlite3.connect(data/'compute/batches.db') as db:return db.execute('SELECT count(*) FROM experiments').fetchone()[0]
    before=counts();files={str(f.relative_to(data)):digest(f) for d in ['skill-replays','weapon-replays'] for f in (data/d).glob('*.json')}
    combat=dict(durationFrames=120,enemyDefense=30925,critMode='off',pelletCoefficientPolicy='per_trigger',bossDistance=35,bossWeakElement='Fire');req=dict(snapshotId=snapshot['id'],characterIds=ids,scenarioLevel=400,conditions=dict(combat=combat))
    compute=dict(snapshotId=snapshot['id'],characterIds=ids,runs=1,phase='pilot',conditions=dict(combat=combat),execution=dict(requested='cpu',maxWorkers=1))
    for route,body in [('runtime/combat-conditions',None),('snapshots/'+snapshot['id']+'/combat-conditions?characterIds='+','.join(ids),None),('runtime/skill-replays',req),('compute/experiments',compute)]:
     status,error=call(route,body);check(f'invalid{index} {route}',status==409 and error.get('code')=='combat_profile_invalid' and error.get('characterId')=='5004' and error.get('field')=='combatProfiles.characters.5004.'+field and error.get('reason')==reason,error)
    check('invalid no calculation storage '+str(index),counts()==before and files=={str(f.relative_to(data)):digest(f) for d in ['skill-replays','weapon-replays'] for f in (data/d).glob('*.json')})
    if index in [0,5]:
     page=page_new();distance(35);page.wait_for_selector('[data-cond-error="members"]');text=page.locator('dialog[open]').inner_text();check('Korean distance error '+str(index),'앨리스(#5004)' in text and field in text and 'prepare_combat_conditions.py' in text);layout('error-distance-'+str(index));apply();page.locator('[data-cond-open="element"]').click();page.wait_for_selector('[data-cond-error="members"]');check('Korean weakness error '+str(index),'앨리스(#5004)' in page.locator('dialog[open]').inner_text());page.locator('[data-cond-element="fire"]').click();page.locator('[name="seconds"]').fill('2');r,v=replay('error-replay-'+str(index));page.wait_for_selector('[data-profile-error]');check('Korean replay error '+str(index),r.status==409 and field in page.locator('[data-profile-error]').inner_text())
     page.locator('[data-tab="stats"]').click();page.locator('#compute-runs').fill('1')
     with page.expect_response(lambda r:r.url.endswith('/api/compute/experiments') and r.request.method=='POST') as result:page.locator('#compute-start').click()
     page.wait_for_function('document.querySelector("#stats-content").innerText.includes("사거리·속성 데이터 오류")');text=page.locator('#stats-content').inner_text();check('Korean compute409 reachable '+str(index),result.value.status==409 and '실제 API 응답' in text and 'compute API 미연결' not in text and '앨리스(#5004)' in text);layout('error-statistics-'+str(index));page.close()
    stop()
   # Actual missing catalog and missing whole-member, beyond field-invalid wire.
   for label in ['catalog-missing','member-missing']:
    bad=deepcopy(catalog)
    if label=='catalog-missing':bad.pop('combatProfiles')
    else:bad['combatProfiles']['characters'].pop('5004')
    publish(bad);start(api);page=page_new();distance(35);page.wait_for_selector('[data-cond-error="members"]');text=page.locator('dialog[open]').inner_text();save(label+'-dialog',dict(text=text));check(label+' real Korean diagnostic',('준비되지 않았습니다' if label=='catalog-missing' else '앨리스(#5004)') in text and 'prepare_combat_conditions.py' in text);apply();element('Fire');page.locator('[name="seconds"]').fill('2');r,v=replay(label+'-replay');page.wait_for_selector('[data-profile-error]');check(label+' actual rejected replay',r.status==(409 if label=='catalog-missing' else 400));page.locator('[data-tab="stats"]').click();page.locator('#compute-runs').fill('1')
    with page.expect_response(lambda r:r.url.endswith('/api/compute/experiments') and r.request.method=='POST') as result:page.locator('#compute-start').click()
    page.wait_for_timeout(700);text=page.locator('#stats-content').inner_text();check(label+' contract reachable',result.value.status==(409 if label=='catalog-missing' else 400) and '실제 API 응답' in text and 'compute API 미연결' not in text);shot(label);page.close();stop()
   pointer.write_bytes(normalpointer);check('no browser exceptions',not report['errors'],report['errors']);ctx.tracing.stop(path=str(run/'trace.zip'));browser.close();report['status']='passed' if all(x['passed'] for x in report['checks']) else 'failed'
 except Exception as ex:report['status']='aborted';report['error']=repr(ex);raise
 finally:
  stop();pointer.write_bytes(normalpointer);report['ownApiStopped']=True;report['sourceChanges']=[str(k) for k,v in hashes.items() if digest(source/k)!=v];report['assetsUnchanged']=all(digest(assets/k)==v for k,v in asset_hashes.items());report['rosterUnchanged']=digest(rosterpath)==record['sha256'];save('summary',report);save('traffic',traffic);save('source-hashes',hashes);save('asset-hashes',asset_hashes);print('EVIDENCE '+str(run),flush=True)
 return 0 if report['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())

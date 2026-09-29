"""U-FIX-4 independent source-label acceptance using actual API and Chromium.

Source families absent from the public fixture are supplied as explicit synthetic
AttackBuffWindow source strings to the real engine. No HTTP response is mocked.
These rows test label transport, not actual cube/collection stat activation.
"""
import argparse,json,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from check_f2_conditions import Session,ROOT,clean_hit
from check_client_f32 import context as independent_hit
from check_f2_ufix3 import scan_codes,record_identifiers
from public_fixture import read,digest

# Expected Korean concepts are authored from the user request, not owner tests.
CASES=[
 ('overload:5004:arm:2:StatChargeTime',['앨리스','팔','2번 줄','차지 속도']),
 ('overload:9999:leg:3:UnknownStat',['이름 미확인','다리','3번 줄','오버로드 옵션']),
 ('cube:qa-cube:StatAtk',['큐브','공격력']),
 ('cube:qa-cube:UnknownStat',['큐브 효과']),
 ('collection:qa-doll:StatCriticalDamage',['소장품','크리티컬 대미지']),
 ('collection:qa-doll:UnknownStat',['소장품 효과']),
 ('equipment:torso',['장비','몸통']),
 ('equipment:arms',['장비','팔']),
 ('equipment:legs',['장비','다리']),
 ('equipment:unknown',['장비']),
 ('manual:attack:3',['직접 입력한 버프','3']),
 ('manual:attack:unknown',['직접 입력한 버프']),
 ('function:1234567',['스킬 효과']),
 ('function:227111001',['누아르','스킬 1']),
 ('function:unknown',['스킬 효과']),
 ('skill:5009:22711100',['누아르','스킬']),
 ('unrecognized:5004:qa-secret',['기타 효과']),
]

def run_checks(s,ctx):
 s.start(ctx.request)
 assert s.call('accounts/synthetic-account/formation',dict(slots=s.ids),'PUT')[0].ok
 page=ctx.new_page();page.on('pageerror',lambda e:s.report['errors'].append(str(e)))
 page.goto(s.base+'/editor/');page.wait_for_selector('body[data-ready="true"]')
 page.locator('[data-tab="raid"]').click()
 raw_open=[]
 for policy in ['client_f32','legacy_term_floor','final_round_even','nested_floor']:
  req=dict(snapshotId=s.snapshot['id'],characterIds=s.ids,scenarioLevel=400,conditionProfile='legacy',conditions=dict(roundingPolicy=policy,damageLog=dict(characterId='5004'),combat=dict(durationFrames=120,enemyDefense=30925,critMode='off',pelletCoefficientPolicy='per_trigger',attackBuffWindows=[dict(characterId='5004',buff=dict(source=key,rate=.01),startFrame=1,endFrame=121) for key,_ in CASES])))
  def outgoing(route):route.continue_(post_data=json.dumps(req))
  page.route('**/api/runtime/skill-replays',outgoing)
  with page.expect_response(lambda r:r.url.endswith('/api/runtime/skill-replays') and r.request.method=='POST',timeout=60000) as pending:page.locator('#run-replay').click()
  response=pending.value;assert response.status==200,response.text();replay=response.json()
  page.unroute('**/api/runtime/skill-replays',outgoing)
  archive=s.data/'skill-replays'/(replay['id']+'.json');before=archive.read_bytes()
  s.save('source-families-'+policy,dict(request=req,response=replay))
  entries=replay['result']['damageLog']['entries']
  entry=next(e for e in entries if set(k for k,_ in CASES).issubset({b['source'] for b in e['hit'].get('runtimeAttackBuffs',[])}))
  actual_keys=[b['source'] for b in entry['hit']['runtimeAttackBuffs']]
  s.check('U-FIX-4 '+policy+' actual API keys preserved',all(k in actual_keys for k,_ in CASES),actual_keys)
  if policy=='client_f32':s.check('U-FIX-4 source-families independent hit arithmetic',all(independent_hit(clean_hit(e['hit']))['damage']==e['damage'] for e in entries),len(entries))
  page.wait_for_selector('[data-view-audit="'+str(entry['hitId'])+'"]');page.locator('[data-view-audit="'+str(entry['hitId'])+'"]').click();page.wait_for_selector('[data-audit-group="attack"]')
  text=page.locator('[data-audit-group="attack"]').inner_text();rows=page.locator('[data-audit-group="attack"] li').all_inner_texts()
  for key,words in CASES:
   s.check('U-FIX-4 '+policy+' Korean source '+key,any(all(w in row for w in words) for row in rows) and key not in text,dict(expectedConcepts=words,rows=rows))
  s.check('U-FIX-4 '+policy+' natural overload label','앨리스 · 머리 1번 줄 · 공격력' in text and 'overload:' not in text)
  s.check('U-FIX-4 '+policy+' all raw source keys absent',all(k not in text for k in actual_keys) and not any(x in text for x in ['5004','5009','9999','qa-secret','UnknownStat']),text)
  panel=page.locator('.damage-audit-panel').inner_text()
  s.check('U-FIX-5 '+policy+' no function numbers in complete panel',not any(x in panel for x in ['1234567','227111001','22711100','219121001']) and '함수' not in panel,panel)
  for width in [1500,850,500]:
   page.set_viewport_size(dict(width=width,height=1000));scan_codes(s,page,'sources '+policy+' '+str(width));s.check('U-FIX-4 '+policy+' source layout '+str(width),not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'));page.locator('.damage-audit-panel').screenshot(path=str(s.run/f'sources-{policy}-{width}.png'))
  page.set_viewport_size(dict(width=1500,height=1000))
  r,after=s.call('runtime/skill-replays/'+replay['id']);export,_=s.call('runtime/skill-replays/'+replay['id']+'/export.json')
  s.check('U-FIX-4 '+policy+' display preserves archive/API/export/total',archive.read_bytes()==before==r.body()==export.body() and after==replay and after['result']['totalDamage']==replay['result']['totalDamage'])
  if policy=='client_f32':
   for extension in ['json','csv']:
    exported,_=s.call('runtime/skill-replays/'+replay['id']+'/damage-log/export.'+extension)
    with page.expect_download() as pending_download:page.locator('#btn-export-'+extension).click()
    download=s.run/('damage-log-download.'+extension);pending_download.value.save_as(str(download))
    s.check('U-FIX-6 real '+extension+' download matches API and archive unchanged',exported.ok and download.read_bytes()==exported.body() and archive.read_bytes()==before)
  s.save('source-panel-'+policy,dict(rows=rows,archiveSha256=digest(archive),totalDamage=replay['result']['totalDamage']))
  rawtext=page.locator('#replay-result').inner_text()
  exposed=[k for k,_ in CASES if k in rawtext]
  raw_open.append(dict(policy=policy,exposedSourceKeys=exposed,rawBlockCount=page.locator('#replay-result pre').count()))
  s.check('F2-Q-4 '+policy+' no raw saved JSON screen',not exposed and '저장 결과 원문' not in rawtext and page.locator('#replay-result pre').count()==0)
 s.save('raw-result-view-observation',raw_open)
 s.check('U-FIX-4 expanded raw result has no source keys',not any(x['exposedSourceKeys'] for x in raw_open),raw_open)

 # Prior QA archive is a synthetic saved result, never the user's account/session.
 previous=ROOT/'artifacts/single-deck-qa/f2-ufix3-554048887882'
 old=read(previous/'browser-normal.json')['response'];original=previous/'data/skill-replays'/(old['id']+'.json');sourcehash=digest(original)
 target=s.data/'skill-replays'/original.name;shutil.copyfile(original,target);oldbytes=target.read_bytes()
 def saved_get(route):route.continue_(url=s.base+'/api/runtime/skill-replays/'+old['id'],method='GET',post_data='')
 page.route('**/api/runtime/skill-replays',saved_get)
 with page.expect_response(lambda r:r.url.endswith('/api/runtime/skill-replays/'+old['id'])) as pending:page.locator('#run-replay').click()
 result=pending.value;page.unroute('**/api/runtime/skill-replays',saved_get)
 s.check('U-FIX-4 prior archive actual GET without recalculation',result.status==200 and result.request.method=='GET' and result.json()==old)
 chosen=next(e for e in old['result']['damageLog']['entries'] if e['hit']['fullBurst'] and e['hit']['core'])
 page.wait_for_selector('[data-view-audit="'+str(chosen['hitId'])+'"]');page.locator('[data-view-audit="'+str(chosen['hitId'])+'"]').click();page.wait_for_selector('[data-audit-group="attack"]')
 for width in [1500,850,500]:
  page.set_viewport_size(dict(width=width,height=1000));text=page.locator('[data-audit-group="attack"]').inner_text()
  s.check('U-FIX-4 prior archive Korean source '+str(width),'앨리스 · 머리 1번 줄 · 공격력 +4.77%' in text and 'overload:5004' not in text,text)
  panel=page.locator('.damage-audit-panel').inner_text();s.check('U-FIX-5 prior archive no function numbers '+str(width),'함수' not in panel and not any(x in panel for x in ['108231001','119131002','227111001','219121001']),panel)
  page.locator('.damage-audit-panel').screenshot(path=str(s.run/f'previous-saved-{width}.png'));record_identifiers(s,page.locator('body').inner_text(),'prior saved '+str(width))
 s.check('U-FIX-4 prior source/copy/API/total unchanged',digest(original)==sourcehash and original.read_bytes()==target.read_bytes()==oldbytes==s.call('runtime/skill-replays/'+old['id'])[0].body() and result.json()['result']['totalDamage']==old['result']['totalDamage'])
 s.save('prior-archive-preservation',dict(original=str(original),sha256=sourcehash,copied=str(target),replayId=old['id'],totalDamage=old['result']['totalDamage'],transport='real API GET via outbound request method/url redirect; no response replacement'))
 s.check('U-FIX-4 no Chromium exceptions',not s.report['errors'],s.report['errors']);page.close()

def inspect_archive(s,ctx,source):
 source=source.resolve();assert source.is_relative_to(ROOT/'artifacts/single-deck-qa')
 old=read(source);before=source.read_bytes();s.start(ctx.request)
 assert s.call('accounts/synthetic-account/formation',dict(slots=s.ids),'PUT')[0].ok
 target=s.data/'skill-replays'/source.name;target.parent.mkdir(exist_ok=True);shutil.copyfile(source,target)
 page=ctx.new_page();page.goto(s.base+'/editor/');page.wait_for_selector('body[data-ready="true"]');page.locator('[data-tab="raid"]').click()
 def get_saved(route):route.continue_(url=s.base+'/api/runtime/skill-replays/'+old['id'],method='GET',post_data='')
 page.route('**/api/runtime/skill-replays',get_saved)
 with page.expect_response(lambda r:r.url.endswith('/api/runtime/skill-replays/'+old['id'])) as response:page.locator('#run-replay').click()
 s.check('raw-view stored replay actual GET',response.value.request.method=='GET' and response.value.json()==old)
 page.wait_for_selector('[data-view-audit]')
 text=page.locator('#replay-result').inner_text()
 s.check('F2-Q-4 stored replay no raw JSON block','저장 결과 원문' not in text and 'overload:5004' not in text and page.locator('#replay-result pre').count()==0)
 scan_codes(s,page,'stored replay normal full screen')
 # Inventory of a real missing-character-log state, without enabling the mock button.
 page.locator('#log-character-select').select_option('5011');page.wait_for_timeout(800)
 text=page.locator('#damage-log-container').inner_text();scan_codes(s,page,'stored replay other-character log state',selector='#damage-log-container')
 s.check('F2-Q-3 missing log names and Replay ID',all(w in text for w in ['앨리스','리타','Replay ID:']) and all(w not in text for w in ['5004','5011']),text)
 s.save('replay-identifier-state',dict(text=text,hasReplayId='Replay ID:' in text));page.screenshot(path=str(s.run/'replay-identifier-state.png'),full_page=True)
 s.check('raw-view source/copy/API preserved',source.read_bytes()==before==target.read_bytes()==s.call('runtime/skill-replays/'+old['id'])[0].body());page.close()

def main():
 p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);p.add_argument('--inspect-archive',type=Path);a=p.parse_args();s=Session(a.dotnet);s.report['scope']='U-FIX-6 actual source families + API/archive preservation' if not a.inspect_archive else 'F2-Q-3/4 minimal saved replay reproduction'
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport=dict(width=1500,height=1000));ctx.tracing.start(screenshots=True,snapshots=True,sources=True)
   if a.inspect_archive:inspect_archive(s,ctx,a.inspect_archive)
   else:run_checks(s,ctx)
   ctx.tracing.stop(path=str(s.run/'trace.zip'));browser.close()
 except Exception as ex:s.report.update(status='aborted',error=repr(ex));raise
 finally:s.finish()
 return 0 if s.report['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())

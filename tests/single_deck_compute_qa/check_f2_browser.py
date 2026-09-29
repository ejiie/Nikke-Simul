"""Own Chromium checks against actual F2 API. Only outbound synthetic requests are modified."""
import json,math,re,time
from copy import deepcopy
from check_client_f32 import context as reference
from check_f2_conditions import clean_hit
from actual_stats import metric
from check_f2_ufix3 import scan_codes,planned,verify_defense

def browser_checks(s,ctx):
 check=s.check;page=ctx.new_page();page.on('pageerror',lambda e:s.report['errors'].append(str(e)))
 def record(r):
  if '/api/' in r.url and r.request.method=='POST':
   try:s.traffic.append(dict(url=r.url,status=r.status,request=r.request.post_data_json,response=r.json()))
   except Exception:pass
 page.on('response',record);page.goto(s.base+'/editor/');page.wait_for_selector('body[data-ready="true"]');page.locator('[data-tab="raid"]').click();page.wait_for_selector('[data-boss-open]')
 def shot(name):
  page.screenshot(path=str(s.run/(name+'.png')),full_page=True)
  scan_codes(s,page,name)
 def layout(label):
  for width in [1500,850,500]:
   page.set_viewport_size(dict(width=width,height=1000));page.wait_for_timeout(100)
   dims=page.evaluate('''()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,dialogs:[...document.querySelectorAll('dialog[open]')].map(e=>{let r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&r.top>=0&&r.bottom<=innerHeight+1;})})''')
   check(label+' width '+str(width),not dims['overflow'] and all(dims['dialogs']));shot(label+'-'+str(width))
  page.set_viewport_size(dict(width=1500,height=1000))
 def source_free(label):check(label+' no removed source label','Nikke-Local-Lab' not in page.locator('body').inner_text())
 check('R3 R4 R7 removed inputs',page.locator('[name="seconds"],[name="defense"],[name="pellet"],[name="pelletCoefficientPolicy"]').count()==0)
 check('R5 crit sample default',page.locator('[name="crit"]').input_value()=='sample' and page.locator('[name="crit"] option:checked').inner_text()=='확률 적용')
 check('R6 client_f32 and three historical candidates',page.locator('[name="rounding"]').input_value()=='client_f32' and page.locator('[name="rounding"] option').evaluate_all('(es)=>es.map(e=>e.value)')==['client_f32','legacy_term_floor','final_round_even','nested_floor'])
 check('R8 default dummy below policy',page.locator('[data-boss-open]').inner_text().startswith('더미 보스') and page.locator('#raid-boss').bounding_box()['y']>page.locator('[name="rounding"]').bounding_box()['y'])
 note=page.locator('[data-conditions-note]').inner_text();check('fixed 180s pellet and strict greater guidance',all(x in note for x in ['180초','발사 1회','30,925','31,784','20억을 넘은 뒤','400']))
 planned(s,page)
 source_free('raid form');layout('raid-form')
 page.locator('[data-cond-open="distance"]').focus();page.keyboard.press('Enter');page.wait_for_selector('.cond-range-table');page.wait_for_selector('.cond-member-list [data-member]')
 text=page.locator('dialog[open]').inner_text();check('R2 Korean exception/header/no uncertain source',all(x in text for x in ['적정 사거리','하란: 25–45','0–0 · 보너스 없음']) and not any(x.lower() in text.lower() for x in ['Harran','5042','(다수)','sha256','출처','원천','확인 필요','잠정','실게임 검증 전','양끝']))
 check('R2 six weapon images loaded',page.locator('.cond-range-table .cond-weapon img').evaluate_all('(es)=>es.length===6&&es.every(e=>e.complete&&e.naturalWidth>0)'))
 page.locator('dialog[open] [name="distance"]').fill('35')
 preview=page.locator('.cond-member-list li').evaluate_all('(es)=>es.map(e=>({id:e.dataset.member,kind:e.dataset.distanceKind,text:e.innerText}))')
 check('F-COND member range independent',len(preview)==5 and all(x['kind']==('in' if s.roster[x['id']]['bonusrange_min']<=35<=s.roster[x['id']]['bonusrange_max'] else 'out') for x in preview));s.save('browser-range-preview',preview);layout('distance-popup')
 page.locator('dialog[open] button[type="submit"]').click();check('distance focus return',page.locator('[data-cond-open="distance"]').evaluate('(e)=>e===document.activeElement'))
 page.keyboard.press('Enter');page.locator('dialog[open] [name="distance"]').fill('50');page.keyboard.press('Escape');page.wait_for_function('!document.querySelector("dialog[open]")');check('distance ESC no change','35' in page.locator('[data-cond-value="distance"]').inner_text())
 page.locator('[data-cond-open="element"]').focus();page.keyboard.press('Enter');page.wait_for_selector('[data-cond-element="fire"]')
 text=page.locator('dialog[open]').inner_text();check('R1 warning retained other explanation removed','보스의 약점 속성 — 이 속성 니케가 우월 코드 보너스를 받습니다' in text and not any(x in text for x in ['니케 자신의','보스 자신의']))
 check('R1 five Korean elements only',all(x in text for x in ['작열','수냉','풍압','철갑','전격']) and not re.search(r'Fire|Water|Wind|Iron|Electronic',text))
 check('F-COND element images and matching members',page.locator('.cond-element img').evaluate_all('(es)=>es.length===5&&es.every(e=>e.complete&&e.naturalWidth>0)') and '앨리스' in page.locator('[data-cond-element="fire"]').inner_text());layout('weakness-popup')
 page.locator('[data-cond-element="fire"]').focus();page.keyboard.press('Enter');check('R1 selected Korean and focus','작열' in page.locator('[data-cond-value="element"]').inner_text() and 'Fire' not in page.locator('[data-cond-value="element"]').inner_text() and page.locator('[data-cond-open="element"]').evaluate('(e)=>e===document.activeElement'))
 page.locator('[data-boss-open]').focus();page.keyboard.press('Enter');page.wait_for_selector('dialog[open] [data-boss-id="solo-raid-42"]')
 check('R8 actual 43 cards Korean matching API',page.locator('dialog[open] [data-boss-id]').count()==43 and all(page.locator('dialog[open] [data-boss-id="'+b['id']+'"] strong').inner_text()==b['name'] for b in s.bosses['bosses']))
 # Scroll lazy images into view, then independently verify each loaded resource.
 for img in page.locator('dialog[open] .boss-pick-image').all():img.scroll_into_view_if_needed();img.evaluate('(e)=>e.loading="eager"')
 page.wait_for_function('[...document.querySelectorAll("dialog[open] .boss-pick-image")].every(e=>e.complete&&e.naturalWidth>0)')
 check('R8 42 actual browser images loaded',page.locator('dialog[open] .boss-pick-image').count()==42)
 text=page.locator('dialog[open]').inner_text();check('R8 no source/English/fallback notice',not any(x in text.lower() for x in ['enikk','http','sha256','mother whale','altruia','준비 중']))
 layout('boss-popup');page.locator('dialog[open] [data-boss-id="solo-raid-42"]').focus();page.keyboard.press('Enter');check('R8 keyboard selection focus','앨트루이아' in page.locator('[data-boss-open]').inner_text() and page.locator('[data-boss-open]').evaluate('(e)=>e===document.activeElement'))
 page.keyboard.press('Enter');page.keyboard.press('Escape');check('R8 ESC retains selection','앨트루이아' in page.locator('[data-boss-open]').inner_text());page.locator('[name="core"]').check()
 def replay(label):
  with page.expect_response(lambda r:r.url.endswith('/api/runtime/skill-replays') and r.request.method=='POST',timeout=120000) as pending:page.locator('#run-replay').click()
  r=pending.value;v=r.json();s.save(label,dict(status=r.status,request=r.request.post_data_json,response=v));page.wait_for_selector('[data-saved-combat]',timeout=30000);return r,v
 r,v=replay('browser-normal');c=r.request.post_data_json['conditions']['combat'];saved=page.locator('[data-saved-combat]').inner_text()
 check('UI new request wire fixed defaults and boss',r.status==200 and r.request.post_data_json['bossId']=='solo-raid-42' and r.request.post_data_json['scenarioLevel']==400 and c['durationFrames']==10800 and c['pelletCoefficientPolicy']=='per_trigger' and c['critMode']=='sample' and c['bossDistance']==35 and c['bossWeakElement']=='Fire' and 'defenseMode' not in c and 'enemyDefense' not in c and 'conditionProfile' not in r.request.post_data_json)
 check('UI saved conditions boss actual values',all(x in saved for x in ['180초','확률 적용','앨트루이아','30,925','31,784','발사 1회']) and s.call('runtime/skill-replays/'+v['id'])[1]==v)
 check('UI no-switch matches API',v['result']['defense']['switchAfterHit'] is None and '전환 없음' in page.locator('[data-defense-result]').inner_text())
 entries=v['result']['damageLog']['entries'];check('regression independently checked browser hits',all(reference(clean_hit(e['hit']))['damage']==e['damage'] for e in entries))
 chosen=next(e for e in entries if e['hit']['fullBurst'] and e['hit']['core']);page.locator('[data-view-audit="'+str(chosen['hitId'])+'"]').click();page.wait_for_selector('.audit-steps')
 check('client_f32 fullburst audit exact result',page.locator('.audit-steps tr[data-term]').count()==10 and '저장된 발당 피해와 일치' in page.locator('#replay-result').inner_text());shot('browser-audit');page.locator('#btn-close-audit').click()
 def boost(route):
  body=route.request.post_data_json;body['conditions']['combat'].update(deepcopy(s.req['conditions']['combat']));body['conditions']['autoBurst'].update(stageDelayMinFrames=1,stageDelayMaxFrames=1);route.continue_(post_data=json.dumps(body))
 page.route('**/api/runtime/skill-replays',boost);r,v=replay('browser-synthetic-crossing');page.unroute('**/api/runtime/skill-replays',boost)
 change=v['result']['defense']['switchAfterHit'];text=page.locator('[data-defense-result]').inner_text();check('actual switch frame character cumulative displayed',change is not None and all(x in text for x in ['30,925 → 31,784',format(change['frame'],',')+'프레임',s.game['names'][change['characterId']],format(int(change['cumulativeDamage']),',')]))
 layout('switch-result');source_free('switch-result')
 def legacy(route):route.continue_(post_data=json.dumps(s.legacyRequest))
 page.route('**/api/runtime/skill-replays',legacy);r,v=replay('browser-legacy');page.unroute('**/api/runtime/skill-replays',legacy)
 text=page.locator('[data-saved-combat]').inner_text();check('legacy fixed time pellet visible',all(x in text for x in ['2초','이전 방식(고정 방어력)','31,784','펠릿마다','크리티컬 끔']) and '방어력 31,784 고정' in page.locator('[data-defense-result]').inner_text());shot('legacy-result')
 # Actual statistics, n1 then n2; it reads conditions from the retained new form.
 page.locator('[data-tab="stats"]').click();page.locator('#compute-runs').fill('1');page.locator('.compute-advanced summary').click();page.locator('#compute-worker-limit').fill('1')
 for n in [1,2]:
  page.locator('#compute-runs').fill(str(n))
  with page.expect_response(lambda r:r.url.endswith('/api/compute/experiments') and r.request.method=='POST',timeout=60000) as pending:page.locator('#compute-start').click()
  r=pending.value;b=r.json();assert r.status==202,b
  for _ in range(600):
   _,state=s.call('compute/experiments/'+b['id'])
   if state['state'] in ['completed','failed','cancelled']:break
   page.wait_for_timeout(100)
  page.wait_for_selector('[data-comparison-state="no_baseline"]',timeout=30000);page.wait_for_timeout(700)
  _,stats=s.call('compute/experiments/'+b['id']+'/statistics');_,rows=s.call('compute/experiments/'+b['id']+'/results');metric(stats['team'],[e['teamDamage'] for e in rows['runs']]);text=page.locator('#stats-content').inner_text();s.save('browser-statistics-'+str(n),dict(request=r.request.post_data_json,batch=state,statistics=stats,results=rows,text=text))
  check('stats n'+str(n)+' complete independent actual mean and connection',state['state']=='completed' and stats['team']['n']==n and format(int(stats['team']['mean']),',') in text and '실제 API 응답' in text and 'compute API 미연결' not in text and '비교 기준 없음' in text)
  check('stats n'+str(n)+' boss/conditions persisted',r.request.post_data_json['bossId']=='solo-raid-42' and state['input']['boss']['id']=='solo-raid-42' and all(x in text for x in ['앨트루이아','180초','30,925','31,784','샷건 계수 발사 1회']))
  check('stats n'+str(n)+' CI support correct',(stats['team']['meanCi'] is None and ('표본 2' in text or 'n ≥ 2' in text or '2회' in text or 'mean_ci_requires_n_at_least_2' in text)) if n==1 else stats['team']['meanCi'] is not None)
  layout('stats-n'+str(n));source_free('stats')
  # Only the current read is changed; next start uses a fresh batch.
  if n==1:page.locator('#compute-new').click() if page.locator('#compute-new').count() else None
 # Recovery compares the actual GET and saved fingerprint; the UI does not display batch IDs.
 page.reload();page.wait_for_selector('body[data-ready="true"]');page.locator('[data-tab="stats"]').click();page.wait_for_selector('[data-comparison-state="no_baseline"]')
 check('saved batch recovered after page reload',page.evaluate('localStorage.getItem("nikke-single-deck-experiment")')==b['id'] and state['input']['fingerprint'] in page.locator('#stats-content').inner_text())
 # A confirmed >2B batch disproves any interpretation that the old fixed-policy
 # subtitle describes an actual no-switch run. No response data is substituted.
 from public_fixture import read
 crossing=read(s.run/'automatic-batch.json');cid=crossing['batch']['id'];page.evaluate('(id)=>localStorage.setItem("nikke-single-deck-experiment",id)',cid)
 page.reload();page.wait_for_selector('body[data-ready="true"]');page.locator('[data-tab="stats"]').click();page.wait_for_selector('[data-comparison-state="no_baseline"]')
 cards=page.locator('#stats-content .metric-card').evaluate_all('(es)=>Object.fromEntries(es.map(e=>[e.querySelector("span").textContent,e.innerText]))');s.save('defect-F2-Q-1',dict(batchId=cid,batch=crossing['batch'],runs=crossing['results']['runs'],cards=cards,text=page.locator('#stats-content').inner_text()));shot('defect-F2-Q-1')
 check('F2-Q-1 automatic policy must not say no transition',all(r['defense']['switchAfterHit'] is not None for r in crossing['results']['runs']) and '자동 20억 전환 없음' not in cards['DEF 정책'],cards['DEF 정책'])
 verify_defense(s,ctx,page)
 check('no Chromium page exceptions',not s.report['errors'],s.report['errors']);page.close()

"""Independent U-FIX-3 display oracle. Actual API results, no owner helpers or mocks."""
import re,time
from copy import deepcopy
from public_fixture import read

def scan_codes(s,page,label,selector='body'):
 text=page.locator(selector).inner_text()
 record_identifiers(s,text,label)
 # The final user rule permits event/replay identifiers, not character codes in
 # visible diagnostic field paths. Do not confuse hit #5004 with character #5004.
 allowed=[]
 def permit(m):allowed.append(m.group(0));return ' [allowed internal/event identifier] '
 text=re.sub(r'(?i)#\d+\s*\(Hit\s*#\d+\)',permit,text)
 text=re.sub(r'(?i)(?:타격|발사|시전|hit|shot|replay|버스트 시전)\s*(?:(?:이벤트|ID)\s*)?#\s*\d+',permit,text)
 pattern=r'(?<![\dA-Za-z])#?(?:'+('|'.join(re.escape(x) for x in s.ids+['5042']))+r')(?![\dA-Za-z])'
 found=[dict(token=m.group(0),context=text[max(0,m.start()-55):m.end()+55]) for m in re.finditer(pattern,text)]
 s.report.setdefault('codeScans',[]).append(dict(label=label,selector=selector,violations=found,allowed=allowed))
 s.check('U-FIX-3 no character codes '+label,not found,found)
 functions=re.findall(r'(?:함수\s*#?\s*\d+|\bfunction:\d+)',text)
 s.check('U-FIX-5 no function numbers '+label,not functions,functions)
 # This scan covers source/error keys, not every possible wire field. The audit
 # table's calculation path and stored term strings have their own minimal test.
 # /legacy is excluded; policy/script identifiers are explicit user exceptions.
 if '/legacy/' not in page.url:
  raw_pattern=r'overload:|cube:|collection:|equipment:|manual:attack:|skill:\d|function:|combatProfiles|bonusRangeMin|bonusRangeMax|서버 원문|저장 결과 원문|\bStat[A-Z]\w*'
  raw=[m.group(0) for m in re.finditer(raw_pattern,text)]
  allowed_keys={'client_f32','legacy_term_floor','final_round_even','nested_floor','prepare_combat_conditions','prepare_solo_raid_bosses'}
  snake=[x for x in re.findall(r'\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b',text) if x not in allowed_keys]
  s.report.setdefault('visibleTextScans',[]).append(dict(label=label,url=page.url,text=text,raw=raw,snake=snake))
  s.check('U-FIX-6 no raw keys/server codes '+label,not raw and not snake,dict(raw=raw,snake=snake))

def record_identifiers(s,text,label):
 # Inventory only; the later U-FIX-5 decision is enforced separately by scan_codes.
 patterns={'hit/shot':r'(?:타격|발사|Hit|hit|shot)[^\n]{0,70}|#\d+\s*\(Hit #\d+\)',
  'function':r'[^\n]*함수\s*#?\d+[^\n]*','replay':r'Replay ID:[^\n]*',
  'fingerprint/version':r'[^\n]*(?:fingerprint|cpu-summary|p03\.skills|p04\.team|schema|규칙 p03)[^\n]*|\b[0-9a-f]{64}\b',
  'policy':r'[^\n]*(?:client_f32|legacy_term_floor|final_round_even|nested_floor)[^\n]*'}
 found={kind:list(dict.fromkeys(re.findall(pattern,text,re.I)))[:12] for kind,pattern in patterns.items()}
 s.report.setdefault('identifierInventory',[]).append(dict(label=label,classification='inventory; U-FIX-5 forbids functions, permits hit/shot/replay/fingerprint/version/policy',observed=found))

def cards(page):
 return page.locator('#stats-content .metric-card').evaluate_all('(es)=>Object.fromEntries(es.map(e=>[e.querySelector("span").textContent,e.innerText]))')

def planned(s,page):
 page.locator('[data-tab="stats"]').click();page.wait_for_selector('#compute-start')
 card=cards(page)['DEF 정책'];s.save('ufix3-planned',dict(card=card,text=page.locator('#stats-content').inner_text()))
 s.check('U-FIX-3 planned automatic strict next-hit',all(v in card for v in ['자동 전환','30,925','31,784','20억 초과 후 다음 타격']) and '전환 없음' not in card and '고정' not in card,card)
 scan_codes(s,page,'planned statistics');page.locator('[data-tab="raid"]').click()

def verify_defense(s,ctx,page):
 # Additional actual one-run requests to exercise singular text and stored DEF31784.
 def run_one(request,label):
  req=dict(deepcopy(request),runs=1,phase='pilot',useSavedTactic=False,execution=dict(requested='cpu',maxWorkers=1));req.pop('scenarioLevel',None)
  r,b=s.call('compute/experiments',req);assert r.status==202,b
  for _ in range(600):
   _,b=s.call('compute/experiments/'+b['id'])
   if b['state'] in ['completed','failed','cancelled']:break
   time.sleep(.1)
  assert b['state']=='completed' and b['valid']==1,b
  _,rows=s.call('compute/experiments/'+b['id']+'/results');record=dict(request=req,batch=b,results=rows);s.save(label,record);return record
 single=run_one(s.req,'ufix3-crossing-single')
 legacy=run_one(s.legacyRequest,'ufix3-legacy-31784')
 data=[('none-one',read(s.run/'browser-statistics-1.json')),('none-two',read(s.run/'browser-statistics-2.json')),('crossing-two',read(s.run/'automatic-batch.json')),('crossing-one',single),('fixed-30925',read(s.run/'fixed-batch.json')),('fixed-31784',legacy)]
 for label,d in data:
  b=d['batch'];rows=d['results']['runs'];_,prior=s.call('compute/experiments/'+b['id']+'/results')
  page.evaluate('(id)=>localStorage.setItem("nikke-single-deck-experiment",id)',b['id']);page.reload();page.wait_for_selector('body[data-ready="true"]');page.locator('[data-tab="stats"]').click();page.wait_for_selector('[data-comparison-state="no_baseline"]')
  card=cards(page)['DEF 정책'];bc=b['input']['battleConditions'];switches=[r['defense']['switchAfterHit'] for r in rows if r['defense']['switchAfterHit']]
  if bc['defenseMode']=='fixed':
   ok=all(v in card for v in ['이전 방식',format(int(bc['initialDefense']),','),'고정','당시 조건']) and '자동 전환' not in card
  elif not switches:
   ok=all(v in card for v in ['자동 전환','30,925','31,784','전환 없음',str(len(rows))+'회 모두 누적 20억 이하']) and all(r['defense']['finalDefense']==30925 and r['teamDamage']<=2000000000 for r in rows)
  else:
   first=switches[0];seconds=first['frame']/60;shown=round(seconds+1e-12,2);seconds_text=f'{shown:,.2f}'.rstrip('0').rstrip('.')
   expected=[format(int(first['previousDefense']),',')+' → '+format(int(first['newDefense']),','),seconds_text+'초',format(first['frame'],',')+'프레임',s.game['names'][first['characterId']],format(int(first['cumulativeDamage']),','),'타격 후 전환']
   if len(rows)>1:expected.append(str(len(rows))+'회 중 '+str(len(switches))+'회 전환')
   ok=all(v in card for v in expected) and '전환 없음' not in card and '고정' not in card and all(r['defense']['finalDefense']==31784 for r in rows)
  s.check('U-FIX-3 stored DEF '+label,ok,dict(card=card,defenses=[r['defense'] for r in rows]));scan_codes(s,page,'stored DEF '+label)
  s.save('ufix3-display-'+label,dict(batch=b,runs=rows,card=card,text=page.locator('#stats-content').inner_text()))
  for width in [1500,850,500]:
   page.set_viewport_size(dict(width=width,height=1000));s.check('U-FIX-3 '+label+' layout '+str(width),not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'));page.screenshot(path=str(s.run/f'ufix3-{label}-{width}.png'),full_page=True)
  page.set_viewport_size(dict(width=1500,height=1000));s.check('U-FIX-3 reads preserve stored results '+label,s.call('compute/experiments/'+b['id']+'/results')[1]==prior)
 s.save('ufix3-code-scans',s.report['codeScans'])

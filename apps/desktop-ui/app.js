import { connectRenderer, renderNikkeCards, appendPortrait } from './cards.js';
import { mountCalculation } from './generated/calculation.js';

const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=v=>v==null?'미확인':Number(v).toLocaleString('ko-KR',{maximumFractionDigits:4});
const time=v=>new Date(v).toLocaleString('ko-KR');
const parts={head:'머리',torso:'몸통',arm:'팔',leg:'다리'};
const consoles={'1001':'공용','1101':'화력형','1102':'방어형','1103':'지원형','1201':'엘리시온','1202':'미실리스','1203':'테트라','1204':'필그림','1205':'어브노멀'};
const optionNames={StatAtk:'공격력',IncElementDmg:'우월 코드',StatAmmoLoad:'장탄 수',StatCritical:'크리티컬 확률',StatCriticalDamage:'크리티컬 대미지',StatChargeTime:'차지 시간',StatChargeDamage:'차지 대미지',StatAccuracyCircle:'명중',IncHurtDef:'방어력',StatDef:'방어력'};
const pageTitles={home:['지휘관 관리','홈'],account:['계정 정보','계정 설정'],nikkes:['전체 니케','니케 관리'],raid:['대미지 검산','솔로 레이드'],import:['블라블라 연결','계정 가져오기'],advanced:['문제 해결','고급 진단']};
const state={presentation:{characters:[]},presentationByCharacter:new Map(),combatPowerByCharacter:new Map(),currentProfile:null,selectedNikkeUid:null};
let boot={token:'',connections:[],jobs:[]},snapshot=null,busy=false,refreshing=false;
let connectionId=localStorage.getItem('nikke-sync-connection'),snapshotId=null,selectedPage='home',detailSequence=0;
let imageStatus='idle',imageRevision=0,lastReplay=null;
const build=id=>snapshot?.characters.find(c=>c.characterId===id);
const connection=()=>boot.connections.find(c=>c.id===connectionId)??boot.connections.find(c=>c.status==='ready')??boot.connections[0];
const job=()=>boot.jobs.find(j=>j.connectionId===connection()?.id);
const active=j=>j&&['queued','running','cancelling'].includes(j.status);
connectRenderer({state,effectiveProfileValue:(field,id)=>({integerValue:build(id)?.[field==='limit_break'?'limitBreak':'core']}),
  configuredCharacterLevel:id=>build(id)?.level,openNikkeDetail});

async function api(path,method='GET',body){
  const response=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json','X-Nikke-Token':boot.token},...(body===undefined?{}:{body:JSON.stringify(body)})});
  if(response.status===204)return null;
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(data.message??`요청 실패 (${response.status})`);
  return data;
}
function status(message){$('status').textContent=message;}
async function act(action){
  if(busy)return;busy=true;renderSync();
  try{await action();}catch(error){status(error.message);}
  finally{busy=false;await refresh(true);}
}
function setPage(tab){
  selectedPage=tab;
  document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===tab)));
  document.querySelectorAll('[data-tab-panel]').forEach(p=>p.hidden=p.dataset.tabPanel!==tab);
  $('page-eyebrow').textContent=pageTitles[tab][0];$('page-title').textContent=pageTitles[tab][1];
}
async function loadPresentation(){
  state.presentation=await api('/presentation');
  state.presentationByCharacter=new Map(state.presentation.characters.map(c=>[c.characterUid,c]));
  // Saved builds unknown to the current public catalog stay visible with an explicit image fallback.
  includeSavedCharacters();
}
function includeSavedCharacters(){
  for(const c of snapshot?.characters??[]){
    if(!state.presentationByCharacter.has(c.characterId)){
      const item={characterUid:c.characterId,displayName:c.name,portraitPath:null};
      state.presentation.characters.push(item);state.presentationByCharacter.set(c.characterId,item);
    }
  }
}
async function refresh(force=false){
  if(refreshing)return;refreshing=true;
  try{
    boot=await api('/bootstrap');$('test-banner').hidden=!boot.testMode;const selected=connection();
    if(selected){connectionId=selected.id;localStorage.setItem('nikke-sync-connection',selected.id);}
    const next=selected?.accountId?await api(`/accounts/${selected.accountId}/snapshot`):null;
    if(force||next?.id!==snapshotId){
      snapshot=next;snapshotId=next?.id??null;
      state.currentProfile={values:(snapshot?.characters??[]).map(c=>({fieldCode:'character_level',subjectUid:c.characterId}))};
      includeSavedCharacters();renderNikkeCards();renderAccount();renderDiagnostics();
      if(state.selectedNikkeUid&&!$('nikke-detail').hidden)await openNikkeDetail(state.selectedNikkeUid,false);
    }
    renderAccounts();renderSync();
    const update=await api('/presentation/status');
    if(update.status!==imageStatus||update.revision!==imageRevision){
      imageStatus=update.status;imageRevision=update.revision;
      if(imageStatus!=='idle')status(update.message);
      if(['succeeded','partial'].includes(imageStatus)){await loadPresentation();renderNikkeCards();renderDiagnostics();}
    }
    document.body.dataset.ready='true';
  }catch(error){status(error.message);}finally{refreshing=false;}
}
function renderAccounts(){
  const current=connection();
  $('top-account-name').textContent=current?`계정 ${boot.connections.indexOf(current)+1}`:'계정을 연결하세요';
  $('top-account-detail').textContent=current?.choices.find(c=>c.area===current.area)?.label??'로컬 전용';
  $('account-list').innerHTML=boot.connections.length?boot.connections.map((c,i)=>`<li><button type="button" class="account-card ${c.id===current?.id?'selected':''}" data-connection="${esc(c.id)}"><span class="commander-avatar">C</span><span><strong>계정 ${i+1} · ${esc(c.choices.find(a=>a.area===c.area)?.label??'연결 중')}</strong><small>${c.id===current?.id&&snapshot?`보유 ${snapshot.characters.length}명 · 싱크로 Lv. ${num(snapshot.synchroLevel)}`:esc(c.message??'저장된 스펙 열기')}</small></span><span class="status-pill neutral">${c.id===current?.id?'선택됨':'선택'}</span></button></li>`).join(''):'<li class="surface empty-state">아직 연결된 계정이 없습니다. 계정 가져오기에서 블라블라에 로그인하세요.</li>';
  $('account-list').querySelectorAll('[data-connection]').forEach(b=>b.onclick=()=>act(async()=>{connectionId=b.dataset.connection;localStorage.setItem('nikke-sync-connection',connectionId);}));
}
function renderSync(){
  const c=connection(),j=job();
  let content='<p>처음 한 번 로그인하면 수집 → 정제 → 저장이 자동으로 진행됩니다.</p>';
  if(c?.status==='awaiting_login')content=`<p role="status">${esc(c.message??'열린 브라우저에서 로그인하세요.')}</p>`;
  else if(c?.status==='select_account')content=`<p>사용할 서버를 선택하세요.</p><div class="action-row">${c.choices.map(a=>`<button data-area="${a.area}">${esc(a.label)} · ${a.characterCount}명</button>`).join('')}</div>`;
  else if(c?.status==='reauth_required')content=`<p>${esc(c.message)}</p><button id="reauth" class="primary">다시 로그인</button>`;
  else if(active(j))content=`<p>${j.stage==='validating'?'정제·검증 중':'스펙 수집 중'} · ${j.collected} / ${j.expected||'확인 중'}명</p><progress value="${j.collected}" max="${j.expected||1}"></progress><button id="cancel-sync">수집 취소</button>`;
  else if(j&&j.status!=='succeeded')content=`<p>${esc(j.message??'수집이 중단되었습니다. 다시 시도하세요.')}</p>`;
  else if(snapshot)content=`<p>마지막 수집 ${time(snapshot.observedAt)} · 저장 이력 ${snapshot.revision}회 · ${snapshot.characters.length}명</p>`;
  $('import-content').innerHTML=`<div class="section-heading"><div><p class="eyebrow">ACCOUNT SYNC</p><h2>계정 가져오기</h2><p>블라블라 계정의 육성 현황을 이 PC에 저장합니다.</p></div></div><article class="surface"><div class="action-row"><button id="connect" class="primary" ${busy||c?.status==='awaiting_login'?'disabled':''}>${c?'다른 계정 연결':'블라블라 계정 연결'}</button><button id="sync" ${busy||c?.status!=='ready'||active(j)?'disabled':''}>내 스펙 동기화</button></div>${content}</article><article class="surface"><h3>캐릭터·분류 이미지</h3><p>출처: 블라블라 · 저장된 이미지는 오프라인에서도 표시됩니다.</p><button id="refresh-images" ${imageStatus==='running'?'disabled':''}>${imageStatus==='running'?'이미지 수집 중…':'블라블라 이미지 갱신'}</button></article>`;
  $('connect').onclick=()=>act(async()=>{const c=await api('/connections','POST');connectionId=c.id;});
  $('sync').onclick=()=>act(()=>api('/sync-jobs','POST',{connectionId:c.id}));
  if($('reauth'))$('reauth').onclick=()=>act(()=>api(`/connections/${c.id}/reauth`,'POST'));
  if($('cancel-sync'))$('cancel-sync').onclick=()=>act(()=>api(`/sync-jobs/${j.id}/cancel`,'POST'));
  document.querySelectorAll('[data-area]').forEach(b=>b.onclick=()=>act(()=>api(`/connections/${c.id}`,'PATCH',{area:Number(b.dataset.area)})));
  $('refresh-images').onclick=()=>act(async()=>{const result=await api('/presentation/refresh','POST');imageStatus=result.status;status(result.message);});
}
function renderAccount(){
  const target=$('account-content');
  if(!snapshot){target.innerHTML='<div class="surface empty-state">계정을 연결하면 싱크로와 리사이클 룸 정보가 표시됩니다.</div>';return;}
  target.innerHTML=`<div class="section-heading"><div><p class="eyebrow">계정 정보</p><h2>계정 설정</h2><p>수집 값에 누락이 있으면 실제 게임 값을 입력해 보완하세요.</p></div><span class="status-pill neutral">저장 ${snapshot.revision}회</span></div><form id="account-form"><article class="surface profile-summary"><div class="commander-avatar">C</div><div class="profile-name-block"><strong>현재 계정</strong><small>마지막 수집 ${time(snapshot.observedAt)}</small></div><label>싱크로 레벨<input name="synchro" type="number" min="1" max="10000" value="${snapshot.synchroLevel??''}"></label></article><article class="surface console-panel"><div class="card-title"><div><h3>리사이클 룸 콘솔</h3><p>빈칸은 미확인 값입니다.</p></div></div><div class="form-grid">${Object.entries(consoles).map(([id,name])=>`<label>${name}<input name="console-${id}" type="number" min="0" max="10000" value="${snapshot.consoles?.[id]??''}"></label>`).join('')}</div></article><div class="account-save-bar surface"><div><strong>변경 사항 저장</strong><span>새 스냅샷으로 저장합니다.</span></div><button class="primary" type="submit">Save</button></div></form>`;
  const expected=snapshot.id,account=snapshot.accountId;
  $('account-form').onsubmit=e=>{e.preventDefault();const form=new FormData(e.currentTarget),values={};for(const id of Object.keys(consoles)){const v=form.get('console-'+id);if(v!=='')values[id]=Number(v);}act(async()=>{await api(`/accounts/${account}/overrides`,'POST',{expectedSnapshotId:expected,synchroLevel:form.get('synchro')===''?null:Number(form.get('synchro')),consoles:values});status('계정 스탯을 저장했습니다.');});};
}
async function openNikkeDetail(id,scroll=true){
  const sequence=++detailSequence;state.selectedNikkeUid=id;
  const item=state.presentationByCharacter.get(id),c=build(id);
  $('nikke-browser').hidden=true;$('nikke-detail').hidden=false;
  if(scroll)window.scrollTo({top:0,behavior:'instant'});
  $('nikke-selected-name').textContent=item?.displayName??c?.name??'이름 미확인';
  const portrait=$('selected-nikke-portrait');portrait.replaceChildren();appendPortrait(portrait,item?.portraitPath,item?.displayName);
  $('nikke-selected-tags').innerHTML=[['job',item?.combatClassCode],['burst',item?.burstStep===5?'p':item?.burstStep],['code',item?.elementCode]].filter(x=>x[1]).map(([type,code])=>`<img class="detail-system-icon" src="/editor/assets/ui/${type}-${esc(code)}.png" alt="${esc(code)}">`).join('');
  $('nikke-core-panel').innerHTML=c?`<span>레벨 <strong>${num(c.level)}</strong></span><span>한계돌파 <strong>${num(c.limitBreak)}</strong></span><span>코어 강화 <strong>${c.core===7?'MAX':num(c.core)}</strong></span><span>호감도 <strong>${num(c.bond)}</strong></span>`:'<p>미보유 니케</p>';
  $('equipment-summary').replaceChildren();$('equipment-list').replaceChildren();$('skill-editor').replaceChildren();$('collection-editor').replaceChildren();
  if(!c){$('equipment-summary').textContent='보유 계정 스펙이 없습니다.';return;}
  $('equipment-list').innerHTML=c.equipment.map(eq=>`<article class="surface equipment-card"><div class="equipment-card-header"><span class="equipment-icon">${esc(parts[eq.slot]??eq.slot)}<span class="equipment-tier-badge">T${num(eq.tier)}</span></span><div class="equipment-stat-panel"><strong>${esc(parts[eq.slot]??eq.slot)} 장비</strong><p>수집된 장비 · T${num(eq.tier)}</p></div><label class="equipment-enhancement">강화<input value="${num(eq.level)}" readonly aria-label="${esc(parts[eq.slot])} 강화"></label></div><div class="overload-list"><strong class="equipment-column-title overload-column-title">장비 효과</strong><small class="equipment-effect-notice">효과의 수치는 전투 진입 시 적용됩니다.</small>${eq.lines.map(line=>`<div class="overload-row simul-option-row overload-level-${line.valueTier??0}"><span>${esc(line.presence==='absent'?'옵션 없음':optionNames[line.optionType]??line.optionType??'미확인')}</span><strong>${line.presence==='absent'?'—':line.normalizedValue==null?'미확인':num(line.normalizedValue*(line.unit==='ratio'?100:1))+(line.unit==='ratio'?'%':'')}</strong><select aria-label="${esc(parts[eq.slot])} ${line.lineIndex}줄 잠금" data-lock-slot="${esc(eq.slot)}" data-line="${line.lineIndex}" ${line.presence!=='present'?'disabled':''}>${[['unknown','미확인'],['locked','잠금'],['unlocked','해제']].map(([v,l])=>`<option value="${v}" ${line.lockState===v?'selected':''}>${l}</option>`).join('')}</select></div>`).join('')}</div></article>`).join('');
  const expected=snapshot.id,account=snapshot.accountId;
  $('equipment-list').querySelectorAll('[data-lock-slot]').forEach(select=>select.onchange=()=>{const eq=c.equipment.find(x=>x.slot===select.dataset.lockSlot);act(async()=>{await api(`/accounts/${account}/overrides`,'POST',{expectedSnapshotId:expected,characterId:id,slot:eq.slot,lineIndex:Number(select.dataset.line),lockState:select.value,fingerprint:eq.fingerprint});status('잠금 상태를 새 스냅샷에 저장했습니다.');});});
  $('skill-editor').innerHTML=Object.entries(c.skills).map(([slot,lv])=>`<article class="surface skill-card"><p class="eyebrow">${slot==='3'?'BURST':'SKILL '+esc(slot)}</p><h3>${slot==='3'?'버스트 스킬':'스킬 '+esc(slot)}</h3><strong class="simul-large">Lv. ${num(lv)}</strong></article>`).join('');
  $('collection-editor').innerHTML=`<h3>소장품·하모니 큐브</h3><div class="form-grid"><div>소장품 등급 <strong>${esc(c.collectionGrade??'미확인')}</strong></div><div>소장품 레벨 <strong>${num(c.collectionLevel)}</strong></div><div>애장품 단계 <strong>${num(c.favoriteStage)}</strong></div><div>큐브 레벨 <strong>${num(c.cubeLevel)}</strong></div></div>`;
  mountCalculation($('equipment-summary'),snapshot.id,id,api);
  if(sequence===detailSequence)$('equipment-summary').querySelector('#load-stats')?.click();
}
function renderDiagnostics(){
  const issues=(snapshot?.issues??[]).filter(i=>i.code!=='duplicate_identical');
  $('advanced-content').innerHTML=`<div class="section-heading"><div><h2>고급 진단</h2><p>누락된 스펙과 저장 출처를 확인합니다.</p></div></div><article class="surface"><h3>수집 확인</h3>${issues.length?`<ul>${issues.map(i=>`<li>${esc(i.path)} · ${esc(i.message)}</li>`).join('')}</ul>`:'<p>검토할 항목이 없습니다.</p>'}</article><article class="surface"><h3>최근 변경</h3><ul>${(snapshot?.changes??[]).slice(0,30).map(v=>`<li>${esc(v)}</li>`).join('')}</ul></article><article class="surface"><h3>화면·이미지 출처</h3><p>화면: Nikke-Local-Lab · 이미지: 블라블라 및 사용자 제공 ZIP</p><p>캐릭터 ${state.presentation.characters.length}명 · ZIP 연결 ${state.presentation.importedPortraits??0}명 · 미수집 ${state.presentation.unresolved?.length??0}개</p></article>`;
}
function renderRaid(){
  const ids=['5011','5008','5009','5004','5044'];
  $('raid-content').innerHTML=`<div class="section-heading"><div><p class="eyebrow">SOLO RAID CHALLENGE</p><h2>솔로 레이드 검산</h2><p>현재 5인의 평타·스킬 효과를 조건별로 검산합니다. 팀 게이지와 자동 버스트 사이클은 준비 중입니다.</p></div></div><form id="replay-form"><article class="surface"><h3>편성</h3><div class="simul-team">${ids.map(id=>`<label><input type="checkbox" name="member" value="${id}" checked>${esc(state.presentationByCharacter.get(id)?.displayName??id)}</label>`).join('')}</div></article><article class="surface"><h3>전투 조건</h3><div class="form-grid"><label>시간 (초)<input name="seconds" type="number" value="180" min="1" max="600" required></label><label>적 방어력<select name="defense"><option value="30925">30,925 · 누적 20억 전</option><option value="31784">31,784 · 누적 20억 후</option></select></label><label>크리티컬<select name="crit"><option value="off">끔</option><option value="sample">확률 적용</option><option value="on">항상 크리</option></select></label><label>정수화<select name="rounding"><option value="legacy_term_floor">C# 항별 내림</option><option value="final_round_even">최종 반올림</option><option value="nested_floor">항별 + 단계별 내림</option></select></label><label>샷건 계수<select name="pellet"><option value="per_trigger">발사 1회</option><option value="per_pellet">펠릿마다</option></select></label><label>검산 레벨 (선택)<input name="level" type="number" min="1" max="10000" placeholder="계정 레벨"></label></div><div class="action-row">${[['core','코어 명중'],['distance','적정 거리'],['element','우월 코드']].map(([v,l])=>`<label><input name="${v}" type="checkbox">${l}</label>`).join('')}</div><p class="microcopy">방어력은 이번 검산 전체에 고정됩니다. 누적 대미지에 따른 자동 전환은 아직 적용하지 않습니다.</p></article><article class="surface"><h3>버스트 시점 지정</h3><div class="form-grid"><label>버스트 사용<select name="burst"><option value="none">사용 안 함</option><option value="5004">리타 → 블랑 → 앨리스 (1회)</option><option value="5044">리타 → 블랑 → 모더니아 (1회)</option></select></label><label>시작 시점 (초)<input name="burstAt" type="number" min="0.1" step="0.1" value="10"></label></div><p class="microcopy">선택 시 지정 시점의 버스트와 풀버스트 구간을 입력으로 저장합니다. 자동 사이클 결과가 아닙니다.</p></article><div class="account-save-bar surface"><div><strong>검산 후 자동 저장</strong><span>편성·실제 스킬 레벨·조건·구성원별 효과 대미지를 보존합니다.</span></div><button id="run-replay" class="primary" type="submit">대미지 검산</button></div></form><div id="replay-result" aria-live="polite"></div>`;
  $('replay-form').onsubmit=async e=>{
    e.preventDefault();if(!snapshot){status('계정을 먼저 연결하세요.');return;}
    const form=new FormData(e.currentTarget),members=form.getAll('member'),b3=form.get('burst');
    const seconds=Number(form.get('seconds')),frame=Math.round(Number(form.get('burstAt'))*60);
    if(b3!=='none'&&!['5011','5008',b3].every(id=>members.includes(id))){status('버스트 순서에 포함된 니케를 모두 편성하세요.');return;}
    const windows=b3==='none'?[]:[{startFrame:frame+2,endFrame:Math.min(seconds*60,frame+2+(b3==='5044'?900:600))}];
    if(windows.some(w=>w.startFrame>=w.endFrame)){status('버스트 시점은 전투 종료보다 앞서야 합니다.');return;}
    const request={snapshotId:snapshot.id,characterIds:members,scenarioLevel:form.get('level')===''?null:Number(form.get('level')),
      conditions:{roundingPolicy:form.get('rounding'),casts:b3==='none'?[]:['5011','5008',b3].map((id,i)=>({frame:frame+i,characterId:id,slot:'burst'})),
        combat:{durationFrames:seconds*60,enemyDefense:Number(form.get('defense')),critMode:form.get('crit'),core:form.has('core'),properDistance:form.has('distance'),elementAdvantage:form.has('element'),pelletCoefficientPolicy:form.get('pellet'),fullBurstWindows:windows,trace:false,targetLabel:'solo_raid_challenge'}}};
    $('run-replay').disabled=true;$('replay-result').textContent='검산 중…';
    try{lastReplay=await api('/runtime/skill-replays','POST',request);renderReplay(lastReplay);status('검산 결과를 저장했습니다.');}
    catch(error){$('replay-result').textContent=error.message;}
    finally{$('run-replay').disabled=false;}
  };
}
function renderReplay(saved){
  $('replay-result').innerHTML=`<article class="surface"><p class="eyebrow">검산 결과 · ${time(saved.createdAt)}</p><h2>총 대미지 ${num(saved.result.totalDamage)}</h2><p>실측 오차 검증 전 · 지정한 조건의 시뮬레이션 결과</p><div class="simul-result-grid">${saved.result.members.map(m=>`<article><h3>${esc(state.presentationByCharacter.get(m.characterId)?.displayName??m.characterId)}</h3><strong>${num(m.damage)}</strong><dl>${Object.entries(m.effects).map(([effect,dmg],index)=>`<div><dt>${esc(effectLabel(saved,m.characterId,effect,index))}</dt><dd>${num(dmg)}</dd></div>`).join('')}</dl></article>`).join('')}</div><details><summary>저장 결과 원문</summary><pre>${esc(JSON.stringify(saved,null,2))}</pre></details></article>`;
}
function effectLabel(saved,id,effect,index){
  if(effect==='normal_attack')return '평타';
  const [kind,rawId,mode]=effect.split(':'),effectId=Number(rawId);
  const slots=saved.inputs.find(input=>input.weapon.characterId===id)?.skills.slots??{};
  for(const [slot,definition] of Object.entries(slots)){
    if(kind==='skill'&&definition.skillId===effectId||kind==='function'&&definition.functionIds.includes(effectId))
      return ({skill1:'스킬 1',skill2:'스킬 2',burst:'버스트'}[slot]??'스킬')+(mode==='weapon'?' 중 평타':' 대미지');
  }
  return `추가 효과 ${index+1}`;
}

document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>setPage(b.dataset.tab));
document.querySelectorAll('[data-jump]').forEach(b=>b.onclick=()=>setPage(b.dataset.jump));
$('refresh-accounts').onclick=()=>refresh(true);
$('nikke-search').oninput=()=>renderNikkeCards();
document.querySelectorAll('[id^="nikke-filter-"]').forEach(s=>s.onchange=()=>renderNikkeCards());
document.querySelectorAll('[data-filter-select]').forEach(b=>b.onclick=()=>{const id=b.dataset.filterSelect;$(id).value=b.dataset.filterValue;document.querySelectorAll(`[data-filter-select="${id}"]`).forEach(x=>x.setAttribute('aria-pressed',String(x===b)));renderNikkeCards();});
$('nikke-detail-back').onclick=()=>{detailSequence++;$('nikke-detail').hidden=true;$('nikke-browser').hidden=false;renderNikkeCards();};
document.querySelectorAll('[data-detail-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-detail-tab]').forEach(x=>x.setAttribute('aria-selected',String(x===b)));document.querySelectorAll('[data-detail-pane]').forEach(p=>p.hidden=p.dataset.detailPane!==b.dataset.detailTab);});
try{await loadPresentation();renderRaid();await refresh(true);if(!boot.connections.length)setPage('import');}catch(error){status(error.message);}
setInterval(()=>refresh(),2000);

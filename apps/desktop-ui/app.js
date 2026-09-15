import { createFormation } from './formation.js';
import { mountAccountCards, accountCubeDrafts } from './local-lab-account.js';
import { connectRenderer, renderNikkeCards, appendPortrait } from './cards.js';
import { renderLocalLabDetail, updateDetailReport, detailPreviewFailed, detailDirty } from './local-lab-adapter.js';
import { createBurstTacticsManager } from './burst-tactics.js';
import { createDamageLogViewer } from './damage-log.js';
import { toServerTacticDto } from './damage-log-adapter.js';
import { createSingleDeckStatsView } from './single-deck-stats.js';

const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=v=>v==null?'미확인':Number(v).toLocaleString('ko-KR',{maximumFractionDigits:4});
const time=v=>new Date(v).toLocaleString('ko-KR');
const parts={head:'머리',torso:'몸통',arm:'팔',leg:'다리'};
const consoles={'1001':'공용','1101':'화력형','1102':'방어형','1103':'지원형','1201':'엘리시온','1202':'미실리스','1203':'테트라','1204':'필그림','1205':'어브노멀'};
const pageTitles={home:['NIKKE SIMUL','홈'],account:['계정 정보','계정 설정'],nikkes:['전체 니케','니케 관리'],raid:['대미지 검산','솔로 레이드'],stats:['단일 덱 통계','반복 실행 통계'],formation:['솔로 레이드','편성'],import:['블라블라 연결','계정 가져오기'],advanced:['문제 해결','고급 진단']};
const state={presentation:{characters:[]},presentationByCharacter:new Map(),combatPowerByCharacter:new Map(),currentProfile:null,selectedNikkeUid:null};
let boot={token:'',connections:[],jobs:[]},snapshot=null,busy=false,refreshing=false;
let connectionId=localStorage.getItem('nikke-sync-connection'),snapshotId=null,selectedPage='home',detailSequence=0;
let imageStatus='idle',imageRevision=0,lastReplay=null;
let detailOrigin={page:'nikkes',scroll:0};
const build=id=>snapshot?.characters.find(c=>c.characterId===id);
const connection=()=>boot.connections.find(c=>c.id===connectionId)??boot.connections.find(c=>c.status==='ready')??boot.connections[0];
const job=()=>boot.jobs.find(j=>j.connectionId===connection()?.id);
const accountAvatar=c=>`<span class="commander-avatar account-profile-avatar">${c?.avatarPath?`<img src="${esc(c.avatarPath)}" alt="${esc(c.nickname||'계정')} 대표 캐릭터">`:'<span aria-label="대표 이미지 미수집">—</span>'}</span>`;
const active=j=>j&&['queued','running','cancelling'].includes(j.status);
const formation=createFormation({api,getSnapshot:()=>snapshot,getItem:id=>state.presentationByCharacter.get(id),getBuild:build,status,
  showSelector:()=>{setPage('formation');window.scrollTo({top:0,behavior:'instant'});},
  showRaid:()=>{setPage('raid');window.scrollTo({top:0,behavior:'instant'});},renderCards:renderNikkeCards});
const getMembersWithMeta=()=>{
  const members=formation.members();
  const defaultSteps={'5011':1,'5008':2,'5009':3,'5004':3,'5044':3};
  return members.map(id=>{
    const p=state.presentationByCharacter.get(id);
    const b=build(id);
    return {
      id,
      displayName:p?.displayName||b?.name||id,
      burstStep:p?.burstStep||defaultSteps[id]||3,
      weaponCode:p?.weaponCode||'sniper_rifle'
    };
  });
};
const tacticsManager=createBurstTacticsManager({api,getSnapshot:()=>snapshot,getMembersWithMeta,getFormationSlots:()=>formation.slots(),status});
const damageLogViewer=createDamageLogViewer({api,getSnapshot:()=>snapshot,getMembersWithMeta,getToken:()=>boot.token,status});
const statsView=createSingleDeckStatsView({api,getSnapshot:()=>snapshot,getMembersWithMeta,status,
  getTacticSummary:()=>{
    const tactics=tacticsManager.getTactics?.();
    const order=(tactics?.burst3Rotation?.length?tactics.burst3Rotation:tactics?.priority?.stage3)??[];
    return order.map(id=>state.presentationByCharacter.get(id)?.displayName??id).join(' → ');
  },
  getConditions:()=>{
    const form=$('replay-form');
    if(!form)return{};
    const data=new FormData(form),seconds=Number(data.get('seconds')),defense=Number(data.get('defense'));
    return {durationSeconds:Number.isFinite(seconds)&&seconds>0?Math.min(180,seconds):180,
      enemyDefense:Number.isFinite(defense)?defense:null};
  }});
let statsMounted=false;
connectRenderer({state,isSelecting:()=>selectedPage==='formation',isChosen:id=>formation.contains(id),selectCharacter:id=>formation.select(id),effectiveProfileValue:(field,id)=>({integerValue:build(id)?.[field==='limit_break'?'limitBreak':'core']}),
  configuredCharacterLevel:id=>build(id)?.level,openNikkeDetail});

async function api(path,method='GET',body){
  const response=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json','X-Nikke-Token':boot.token},...(body===undefined?{}:{body:JSON.stringify(body)})});
  if(response.status===204)return null;
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(data.message??`요청 실패 (${response.status})`);
  return data;
}
Object.defineProperty(api,'token',{get:()=>boot.token,configurable:true});
api.getToken=()=>boot.token;
function status(message){$('status').textContent=message;}
async function act(action){
  if(busy)return;busy=true;renderSync();
  try{await action();}catch(error){status(error.message);}
  finally{busy=false;await refresh(true);}
}
function setPage(tab){
  selectedPage=tab;
  detailSequence++;
  $('nikke-detail').hidden=true;$('nikke-browser').hidden=false;
  $('formation-editor').hidden=tab!=='formation';
  if(tab==='nikkes'||tab==='formation')renderNikkeCards();
  if(tab==='raid'){formation.render();tacticsManager.render('burst-tactics-container');}
  if(tab==='stats'){
    if(statsMounted)statsView.render('stats-content');
    else{statsMounted=true;statsView.mount('stats-content');}
  }
  const panel=tab==='formation'?'nikkes':tab,nav=tab==='formation'?'raid':tab;
  document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===nav)));
  document.querySelectorAll('[data-tab-panel]').forEach(p=>p.hidden=p.dataset.tabPanel!==panel);
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
  document.body.dataset.ready='false';
  try{
    boot=await api('/bootstrap');$('test-banner').hidden=!boot.testMode;const selected=connection();
    if(selected){connectionId=selected.id;localStorage.setItem('nikke-sync-connection',selected.id);}
    else{connectionId=null;localStorage.removeItem('nikke-sync-connection');}
    const next=selected?.accountId?await api(`/accounts/${selected.accountId}/snapshot`):null;
    if(force||next?.id!==snapshotId){
      const powers=next?await api(`/snapshots/${next.id}/combat-powers`):{};
      state.combatPowerByCharacter=new Map(Object.entries(powers));
      const accountChanged=snapshot?.accountId!==next?.accountId;
      snapshot=next;snapshotId=next?.id??null;
      if(accountChanged){detailSequence++;state.selectedNikkeUid=null;$('nikke-detail').hidden=true;$('nikke-browser').hidden=false;}
      state.currentProfile={values:(snapshot?.characters??[]).map(c=>({fieldCode:'character_level',subjectUid:c.characterId}))};
      includeSavedCharacters();renderNikkeCards();renderAccount();renderDiagnostics();
      try{await formation.load();}catch(error){status(`편성을 불러오지 못했습니다. ${error.message}`);}
      formation.render();
      if(state.selectedNikkeUid&&!$('nikke-detail').hidden&&!detailDirty())await openNikkeDetail(state.selectedNikkeUid,false);
      try{await tacticsManager.syncFromServer();}catch(error){}
      if(selectedPage==='raid'){tacticsManager.render('burst-tactics-container');}
    }else{
      try{await formation.load();}catch(error){status(`편성을 불러오지 못했습니다. ${error.message}`);}
    }
    renderAccounts();renderSync();
    const update=await api('/presentation/status');
    if(update.status!==imageStatus||update.revision!==imageRevision){
      imageStatus=update.status;imageRevision=update.revision;
      if(imageStatus!=='idle')status(update.message);
      if(['succeeded','partial'].includes(imageStatus)){await loadPresentation();renderNikkeCards();formation.render();renderDiagnostics();}
    }
    document.body.dataset.ready='true';
  }catch(error){status(error.message);}finally{refreshing=false;}
}
function renderAccounts(){
  const current=connection();
  $('top-account-name').textContent=current?(current.nickname?.trim()||'닉네임 미수집'):'계정을 연결하세요';
  $('top-account-detail').textContent=current?.choices.find(c=>c.area===current.area)?.label??'로컬 전용';
  $('account-list').innerHTML=boot.connections.length?boot.connections.map(c=>`<li><button type="button" class="account-card ${c.id===current?.id?'selected':''}" data-connection="${esc(c.id)}">${accountAvatar(c)}<span><strong>${esc(c.nickname?.trim()||'닉네임 미수집')} · ${esc(c.choices.find(a=>a.area===c.area)?.label??'연결 중')}</strong><small>${c.id===current?.id&&snapshot?`보유 ${snapshot.characters.length}명 · 싱크로 Lv. ${num(snapshot.synchroLevel)}`:esc(c.message??'저장된 스펙 열기')}</small></span><span class="status-pill neutral">${c.id===current?.id?'선택됨':'선택'}</span></button></li>`).join(''):'<li class="surface empty-state">아직 연결된 계정이 없습니다. 계정 가져오기에서 블라블라에 로그인하세요.</li>';
  $('account-list').querySelectorAll('[data-connection]').forEach(b=>b.onclick=()=>act(async()=>{connectionId=b.dataset.connection;localStorage.setItem('nikke-sync-connection',connectionId);}));
}
function renderSync(){
  const c=connection(),j=job();
  const failure=boot.connectionFailure?`<p role="alert">${esc(boot.connectionFailure.message)}</p>`:'';
  let content='<p>처음 한 번 로그인하면 수집 → 정제 → 저장이 자동으로 진행됩니다.</p>';
  if(c?.status==='awaiting_login')content=`<p role="status">${esc(c.message??'열린 브라우저에서 로그인하세요.')}</p>`;
  else if(c?.status==='select_account')content=`<p>사용할 서버를 선택하세요.</p><div class="action-row">${c.choices.map(a=>`<button data-area="${a.area}">${esc(a.label)} · ${a.characterCount}명</button>`).join('')}</div>`;
  else if(c?.status==='reauth_required')content=`<p>${esc(c.message)}</p><button id="reauth" class="primary">다시 로그인</button>`;
  else if(active(j))content=`<p>${j.stage==='validating'?'정제·검증 중':'스펙 수집 중'} · ${j.collected} / ${j.expected||'확인 중'}명</p><progress value="${j.collected}" max="${j.expected||1}"></progress><button id="cancel-sync">수집 취소</button>`;
  else if(j&&j.status!=='succeeded')content=`<p>${esc(j.message??'수집이 중단되었습니다. 다시 시도하세요.')}</p>`;
  else if(snapshot)content=`<p>마지막 수집 ${time(snapshot.observedAt)} · 저장 이력 ${snapshot.revision}회 · ${snapshot.characters.length}명</p>`;
  $('import-content').innerHTML=`<div class="section-heading"><div><p class="eyebrow">ACCOUNT SYNC</p><h2>계정 가져오기</h2><p>블라블라 계정의 육성 현황을 이 PC에 저장합니다.</p></div></div><article class="surface"><div class="action-row"><button id="connect" class="primary" ${busy||c?.status==='awaiting_login'?'disabled':''}>${c?'다른 계정 연결':'블라블라 계정 연결'}</button><button id="sync" ${busy||c?.status!=='ready'||active(j)?'disabled':''}>내 스펙 동기화</button></div>${failure}${content}</article><article class="surface"><h3>캐릭터·분류 이미지</h3><p>출처: 블라블라 · 저장된 이미지는 오프라인에서도 표시됩니다.</p><button id="refresh-images" ${imageStatus==='running'?'disabled':''}>${imageStatus==='running'?'이미지 수집 중…':'블라블라 이미지 갱신'}</button></article>`;
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
  target.innerHTML=`<div class="section-heading"><div><p class="eyebrow">계정 정보</p><h2>계정 설정</h2><p>수집 값에 누락이 있으면 실제 게임 값을 입력해 보완하세요.</p></div><span class="status-pill neutral">저장 ${snapshot.revision}회</span></div><form id="account-form"><article class="surface profile-summary">${accountAvatar(connection())}<div class="profile-name-block"><strong>현재 계정</strong><small>마지막 수집 ${time(snapshot.observedAt)}</small></div><label>싱크로 레벨<input name="synchro" type="number" min="1" max="10000" value="${snapshot.synchroLevel??''}"></label></article><div id="account-cards"></div><div class="account-save-bar surface"><div><strong>변경 사항 저장</strong><span>새 스냅샷으로 저장합니다.</span></div><button class="primary" type="submit">Save</button></div></form>`;
  mountAccountCards($('account-cards'),snapshot,state.presentation);
  const expected=snapshot.id,account=snapshot.accountId;
  $('account-form').onsubmit=e=>{e.preventDefault();const form=new FormData(e.currentTarget),values={};for(const id of Object.keys(consoles)){const v=form.get('console-'+id);if(v!==null&&v!=='')values[id]=Number(v);}act(async()=>{await api(`/accounts/${account}/overrides`,'POST',{expectedSnapshotId:expected,synchroLevel:form.get('synchro')===''?null:Number(form.get('synchro')),consoles:values,cubeLevels:accountCubeDrafts()});status('계정 스탯을 저장했습니다.');});};
}
async function openNikkeDetail(id,scroll=true){
  if(scroll && $('nikke-detail').hidden)detailOrigin={page:selectedPage,scroll:window.scrollY};
  $('nikke-detail-back').textContent=detailOrigin.page==='formation'?'‹ 편성':'‹ 니케 도감';
  const sequence=++detailSequence;state.selectedNikkeUid=id;
  const item=state.presentationByCharacter.get(id),c=build(id);
  renderLocalLabDetail(null,item);
  $('equipment-summary').textContent='스펙을 불러오는 중…';
  $('nikke-browser').hidden=true;$('nikke-detail').hidden=false;
  if(scroll)window.scrollTo({top:0,behavior:'instant'});
  $('nikke-selected-name').textContent=item?.displayName??c?.name??'이름 미확인';
  const portrait=$('selected-nikke-portrait');portrait.replaceChildren();appendPortrait(portrait,item?.portraitPath,item?.displayName);
  const expected=snapshot?.id,account=snapshot?.accountId;
  let previewTimer;
  const handlers={accountId:account,cubeLevels:snapshot?.cubeLevels,
    onChange:(draft,revision)=>{
      clearTimeout(previewTimer);
      previewTimer=setTimeout(async()=>{
        try{const report=await api(`/accounts/${account}/characters/${id}/preview`,'POST',{expectedSnapshotId:expected,build:draft});
          if(sequence===detailSequence)updateDetailReport(report,revision);
        }catch(error){if(sequence===detailSequence){detailPreviewFailed(error.message,revision);status(error.message);}}
      },200);
    },
    onSave:async draft=>{
      clearTimeout(previewTimer);
      await api(`/accounts/${account}/characters/${id}/edit`,'POST',{expectedSnapshotId:expected,build:draft});
      renderLocalLabDetail(null,item); // End the saved draft before refreshing the new revision.
      await refresh(true);status('변경한 스펙을 새 스냅샷으로 저장했습니다.');
    }};
  if(c){
    try{
      const report=await api(`/snapshots/${snapshot.id}/characters/${id}/stats`);
      if(sequence===detailSequence)renderLocalLabDetail(c,item,state.combatPowerByCharacter.get(id),report,state.presentation,handlers);
    }catch(error){if(sequence===detailSequence){renderLocalLabDetail(c,item,state.combatPowerByCharacter.get(id),null,state.presentation,handlers);detailPreviewFailed(error.message,0);status(error.message);}}
  }else renderLocalLabDetail(null,item);

}
const origFormationRender=formation.render;
formation.render=()=>{
  origFormationRender();
  tacticsManager.render('burst-tactics-container');
};

function renderDiagnostics(){
  const issues=(snapshot?.issues??[]).filter(i=>i.code!=='duplicate_identical');
  $('advanced-content').innerHTML=`<div class="section-heading"><div><h2>고급 진단</h2><p>누락된 스펙과 저장 출처를 확인합니다.</p></div></div><article class="surface"><h3>수집 확인</h3>${issues.length?`<ul>${issues.map(i=>`<li>${esc(i.path)} · ${esc(i.message)}</li>`).join('')}</ul>`:'<p>검토할 항목이 없습니다.</p>'}</article><article class="surface"><h3>최근 변경</h3><ul>${(snapshot?.changes??[]).slice(0,30).map(v=>`<li>${esc(v)}</li>`).join('')}</ul></article><article class="surface"><h3>화면·이미지 출처</h3><p>화면: Nikke-Local-Lab · 이미지: 블라블라 및 사용자 제공 ZIP</p><p>캐릭터 ${state.presentation.characters.length}명 · ZIP 연결 ${state.presentation.importedPortraits??0}명 · 미수집 ${state.presentation.unresolved?.length??0}개</p></article>`;
}
function renderRaid(){
  $('raid-content').innerHTML=`<div class="section-heading"><div><p class="eyebrow">SOLO RAID CHALLENGE</p><h2>솔로 레이드 검산</h2><p>평타·스킬 효과를 조건별로 검산합니다. 현재 검산 지원: 리타·블랑·누아르·앨리스·모더니아. 팀 게이지 충전부터 풀버스트 종료 후 재충전까지 자동으로 실행합니다. 게이지·타이밍은 실측 검증 전입니다.</p></div></div><form id="replay-form"><article class="surface"><h3>편성</h3><div id="raid-team" class="formation-slots" aria-label="저장된 편성"></div></article><article class="surface" id="burst-tactics-section"><div id="burst-tactics-container"></div></article><article class="surface"><h3>전투 조건</h3><div class="form-grid"><label>시간 (초)<input name="seconds" type="number" value="180" min="1" max="180" required></label><label>적 방어력<select name="defense"><option value="30925">30,925 · 누적 20억 전</option><option value="31784">31,784 · 누적 20억 후</option></select></label><label>크리티컬<select name="crit"><option value="off">끔</option><option value="sample">확률 적용</option><option value="on">항상 크리</option></select></label><label>정수화<select name="rounding"><option value="legacy_term_floor">C# 항별 내림</option><option value="final_round_even">최종 반올림</option><option value="nested_floor">항별 + 단계별 내림</option></select></label><label>샷건 계수<select name="pellet"><option value="per_trigger">발사 1회</option><option value="per_pellet">펠릿마다</option></select></label></div><div class="action-row">${[['core','코어 명중'],['distance','적정 거리'],['element','우월 코드']].map(([v,l])=>`<label><input name="${v}" type="checkbox">${l}</label>`).join('')}</div><p class="microcopy">엔진 한도: 최대 180초. 방어력은 이번 검산 전체에 고정됩니다. 누적 대미지에 따른 자동 전환은 아직 적용하지 않습니다. 검산 스탯은 싱크로 레벨 400 고정입니다.</p></article><article class="surface"><h3>사격 조작</h3><div class="form-grid"><label>직접 조작<select name="manualCharacter"><option value="">모두 자동</option><option value="5011">리타</option><option value="5008">블랑</option><option value="5009">누아르</option><option value="5004">앨리스</option><option value="5044">모더니아</option></select></label><label>차지 방식<select name="manualStyle"><option value="full_charge">풀차지</option><option value="tap">톡톡이</option></select></label></div></article><div class="account-save-bar surface"><div><strong>검산 후 자동 저장</strong><span>편성·실제 스킬 레벨·조건·구성원별 효과 대미지를 보존합니다.</span></div><button id="run-replay" class="primary" type="submit">대미지 검산</button></div></form><div id="replay-result" aria-live="polite"></div>`;
  formation.render();
  $('replay-form').onsubmit=async e=>{
    e.preventDefault();if(!snapshot){status('계정을 먼저 연결하세요.');return;}
    const form=new FormData(e.currentTarget),members=formation.members();
    if(!members.length){status('니케를 선택하고 편성을 저장하세요.');return;}
    const currentTactics=tacticsManager.getTactics();
    const seconds=Math.min(180,Math.max(1,Number(form.get('seconds'))));
    const serverTactic = toServerTacticDto(currentTactics, getMembersWithMeta());
    const autoBurstPayload = { tactic: serverTactic };
    const targetDamageLogCharId = (typeof damageLogViewer !== 'undefined' && damageLogViewer?.getSelectedCharacterId?.()) || '5004';
    // Solo raid challenge always calculates at synchro level 400; the form has no level field.
    const SOLO_RAID_SCENARIO_LEVEL = 400;
    const request = {
      snapshotId: snapshot.id,
      characterIds: members,
      scenarioLevel: SOLO_RAID_SCENARIO_LEVEL,
      conditions: {
        damageLog: { characterId: targetDamageLogCharId },
        autoBurst: autoBurstPayload,
        roundingPolicy: form.get('rounding'),
        casts: [],
        combat: {
          manualCharacterId: form.get('manualCharacter'),
          manualStyle: form.get('manualStyle'),
          durationFrames: seconds * 60,
          enemyDefense: Number(form.get('defense')),
          critMode: form.get('crit'),
          core: form.has('core'),
          properDistance: form.has('distance'),
          elementAdvantage: form.has('element'),
          pelletCoefficientPolicy: form.get('pellet'),
          fullBurstWindows: [],
          trace: false,
          targetLabel: 'solo_raid_challenge'
        }
      }
    };
    $('run-replay').disabled=true;$('replay-result').textContent='검산 중…';
    try{lastReplay=await api('/runtime/skill-replays','POST',request);renderReplay(lastReplay);status('검산 결과를 저장했습니다.');}
    catch(error){$('replay-result').textContent=error.message;}
    finally{$('run-replay').disabled=false;}
  };
}
function renderReplay(saved){
  $('replay-result').innerHTML=`<article class="surface"><p class="eyebrow">검산 결과 · ${time(saved.createdAt)}</p><h2>총 대미지 ${num(saved.result.totalDamage)}</h2><p>실측 오차 검증 전 · 지정한 조건의 시뮬레이션 결과</p><div id="burst-timeline-comparison"></div>${renderBurstSummary(saved.result.teamBurst)}<div class="simul-result-grid">${saved.result.members.map(m=>`<article><h3>${esc(state.presentationByCharacter.get(m.characterId)?.displayName??m.characterId)}</h3><strong>${num(m.damage)}</strong><dl>${Object.entries(m.effects).map(([effect,dmg],index)=>`<div><dt>${esc(effectLabel(saved,m.characterId,effect,index))}</dt><dd>${num(dmg)}</dd></div>`).join('')}</dl></article>`).join('')}</div><div id="damage-log-container"></div><details><summary>저장 결과 원문</summary><pre>${esc(JSON.stringify(saved,null,2))}</pre></details></article>`;
  tacticsManager.renderTimelineComparison($('burst-timeline-comparison'),saved.result?.teamBurst?.fullBursts,getMembersWithMeta());
  damageLogViewer.setReplay(saved);
}
function renderBurstSummary(team){
  if(!team)return '';
  const name=id=>esc(state.presentationByCharacter.get(id)?.displayName??id??'—');
  const seconds=frame=>num(frame/60);
  const reasons={missing_stage_1:'버스트 I 니케 없음',missing_stage_2:'버스트 II 니케 없음',missing_stage_3:'버스트 III 니케 없음',cooldown_stage_1:'버스트 I 쿨다운 대기',cooldown_stage_2:'버스트 II 쿨다운 대기',cooldown_stage_3:'버스트 III 쿨다운 대기'};
  const events=team.timeline.filter(e=>['burst_cast','waiting','stage_expired'].includes(e.kind));
  return `<section class="surface"><h3>자동 버스트 사이클</h3><p>풀버스트 ${num(team.fullBursts.length)}회 · 유지 ${seconds(team.fullBurstFrames)}초${team.waitingReason?' · '+esc(reasons[team.waitingReason]??team.waitingReason):''}</p><div class="table-scroll"><table><thead><tr><th>회차</th><th>버스트 III</th><th>풀버스트 진입</th><th>종료</th><th>구간 대미지</th></tr></thead><tbody>${team.fullBursts.map(w=>`<tr><td>${w.cycle}</td><td>${name(w.caster)}</td><td>${seconds(w.startFrame)}초</td><td>${w.endFrame===null?'진행 중 (예정 '+seconds(w.plannedEndFrame)+'초)':seconds(w.endFrame)+'초'}</td><td>${num(Object.values(w.memberDamage).reduce((sum,v)=>sum+v,0))}</td></tr>`).join('')}</tbody></table></div><details><summary>충전 기여·시전·대기 기록</summary><p>${Object.entries(team.acceptedGaugeByMember).map(([id,value])=>name(id)+' '+num(value/team.sourceConstants.capacityRaw*100)+'%').join(' · ')}</p><p class="microcopy">충전 기여는 전투 전체에서 실제 게이지에 반영된 누적량입니다.</p><div class="table-scroll"><table><thead><tr><th>시각</th><th>단계</th><th>동작</th><th>니케</th><th>쿨다운 종료</th></tr></thead><tbody>${events.map(e=>`<tr><td>${seconds(e.frame)}초</td><td>${['충전','I','II','III','풀버스트'][e.step]}</td><td>${e.kind==='burst_cast'?'시전':e.kind==='stage_expired'?'단계 대기 만료':esc(reasons[e.reason]??e.reason)}</td><td>${name(e.characterId)}</td><td>${e.readyAtFrame===null?'—':seconds(e.readyAtFrame)+'초'}</td></tr>`).join('')}</tbody></table></div>${team.timelineTruncated?'<p>상세 기록 상한 도달 · 사이클 합계는 전체 전투 기준입니다.</p>':''}</details></section>`;
}
function effectLabel(saved,id,effect,index){
  if(effect==='normal_attack')return '평타';
  const [kind,rawId,mode]=effect.split(':'),effectId=Number(rawId);
  const slots=saved.inputs?.find(input=>input?.weapon?.characterId===id)?.skills?.slots??{};
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
$('nikke-detail-back').onclick=()=>{setPage(detailOrigin.page);formation.render();window.scrollTo({top:detailOrigin.scroll,behavior:'instant'});};
document.querySelectorAll('[data-detail-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-detail-tab]').forEach(x=>x.setAttribute('aria-selected',String(x===b)));document.querySelectorAll('[data-detail-pane]').forEach(p=>p.hidden=p.dataset.detailPane!==b.dataset.detailTab);});
try{await loadPresentation();renderRaid();await refresh(true);if(!boot.connections.length)setPage('import');}catch(error){status(error.message);}
setInterval(()=>refresh(),2000);

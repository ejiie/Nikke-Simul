// Local Lab projections and edit callbacks, backed by versioned Nikke-Simul snapshots.
import { renderEquipmentDetail, renderSkillDetail, renderCollectionDetail, numericEditor } from './local-lab-detail.js';
const slots={head:'head',torso:'torso',arm:'arms',leg:'legs'};
const company={elysion:1,missilis:2,tetra:3,pilgrim:4,abnormal:7};
const byId=id=>document.getElementById(id);
export const state={presentation:{supportDefinitions:[],overloadOptions:[]},presentationBySupport:new Map(),presentationByOverload:new Map(),presentationByCharacter:new Map(),editOperations:[]};
let values=new Map(),session=null,revision=0;
const draftsByCharacter=new Map();
export const effectiveProfileValue=field=>values.get(field);
export const configuredSynchroLevel=()=>session?.draft.level;
export const detailDraft=()=>session?structuredClone(session.draft):null;
export const detailDirty=()=>session&&JSON.stringify(session.base)!==JSON.stringify(session.draft);
export function queueIntegerValue(field,uid,value){upsertProfileOperations([{fieldCode:field,integerValue:Number(value)}]);}
export function queueControlledValue(field,uid,value){upsertProfileOperations([{fieldCode:field,controlledValue:value}]);}
export function queueReferenceValue(field,uid,value){upsertProfileOperations([{fieldCode:field,referenceUid:value}]);}
export function queueExactValue(field,uid,value,scale){upsertProfileOperations([{fieldCode:field,unscaledValue:Number(value),decimalScale:scale}]);}
export function upsertProfileOperations(operations){for(const op of operations){values.set(op.fieldCode,op);const i=state.editOperations.findIndex(e=>e.fieldCode===op.fieldCode);if(i>=0)state.editOperations[i]=op;else state.editOperations.push(op);}}
export function renderEditOperations(){}
function project(){
  const c=session.draft;values=new Map();state.editOperations=[];
  for(const [field,v] of Object.entries({character_level:c.level,bond_level:c.bond,limit_break:c.core>0?3:c.limitBreak,core_level:c.core,skill_1_level:c.skills['1'],skill_2_level:c.skills['2'],burst_level:c.skills['3']}))values.set(field,{integerValue:v});
  for(const e of c.equipment){
    const p=`equipment.${slots[e.slot]}`;
    values.set(p+'.definition',{referenceUid:e.itemId==='0'?null:e.itemId});values.set(p+'.enhancement_level',{integerValue:e.level});
    for(const l of e.lines){const q=`${p}.overload.${l.lineIndex}`;
      values.set(q+'.state',{controlledValue:l.presence});
      if(l.presence!=='present')continue;
      values.set(q+'.definition',{referenceUid:l.optionType==='StatDef'?'IncHurtDef':l.optionType});
      if(l.normalizedValue!=null)values.set(q+'.value',{unscaledValue:Math.round(Math.abs(l.normalizedValue)*10000),decimalScale:4});
    }
  }
  values.set('collection.definition',{referenceUid:c.collectionId});
  values.set('collection.kind',{controlledValue:c.favoriteStage>0?'favorite':c.collectionId&&c.collectionId!=='0'?'generic_collection':'none'});
  values.set('collection.level',{integerValue:c.favoriteStage>0?c.favoriteStage:c.collectionLevel});
}
function applyOperations(){
  const c=session.draft;
  for(const [field,key] of Object.entries({character_level:'level',bond_level:'bond',limit_break:'limitBreak',core_level:'core'}))if(values.get(field)?.integerValue!=null)c[key]=values.get(field).integerValue;
  for(const [field,key] of [['skill_1_level','1'],['skill_2_level','2'],['burst_level','3']])c.skills[key]=values.get(field)?.integerValue;
  for(const e of c.equipment){
    const p=`equipment.${slots[e.slot]}`,uid=values.get(p+'.definition')?.referenceUid;
    const def=state.presentationBySupport.get(uid),replaced=uid&&uid!==e.itemId;
    if(replaced&&def){e.itemId=uid;e.tier=def.tier;e.manufacturer=0;}
    e.level=values.get(p+'.enhancement_level')?.integerValue??e.level;
    for(let i=1;i<=3;i++){
      const q=`${p}.overload.${i}`,prior=e.lines.find(l=>l.lineIndex===i),present=values.get(q+'.state')?.controlledValue;
      const type=values.get(q+'.definition')?.referenceUid,option=state.presentationByOverload.get(type),v=values.get(q+'.value');
      let line=prior;
      if(present==='absent'&&prior?.presence!=='absent')line={lineIndex:i,presence:'absent',optionId:'0',lockState:'not_applicable',source:'manual'};
      else if(present==='present'&&option&&v){
        const signed=option.sign*v.unscaledValue/10**v.decimalScale;
        if(replaced||prior?.optionType!==type&&!(type==='IncHurtDef'&&prior?.optionType==='StatDef')||signed!==prior?.normalizedValue)
          line={lineIndex:i,presence:'present',optionType:type,normalizedValue:signed,unit:'ratio',valueTier:option.legalValues.findIndex(x=>x.unscaledValue===v.unscaledValue)+1,lockState:'unknown',source:'manual'};
      }
      e.lines[e.lines.findIndex(l=>l.lineIndex===i)]=line;
    }
  }
  const collection=values.get('collection.definition')?.referenceUid;
  if(collection==='0')Object.assign(c,{collectionId:'0',collectionGrade:'none',collectionLevel:0,favoriteStage:0});
  else if(collection){const def=state.presentationBySupport.get(collection);if(def){const favorite=def.kindCode==='favorite',level=values.get('collection.level')?.integerValue??0;
    Object.assign(c,{collectionId:collection,collectionGrade:def.rarityCode?.toUpperCase()??c.collectionGrade,collectionLevel:favorite?Math.max(1,level)-1:level,favoriteStage:favorite?Math.max(1,level):0});}}
}
export function renderNikkeDetail(){applyOperations();changed();}
function changed(){revision++;session.report=null;project();render();session.onChange?.(detailDraft(),revision);}
export function updateDetailReport(report,expectedRevision){
  if(!session||expectedRevision!==revision)return;session.report=report;
  const final=byId('detail-final-stats');
  if(final)final.textContent=report?.nativeStats?`체력 ${report.nativeStats.hp.toLocaleString('ko-KR')} · 공격력 ${report.nativeStats.atk.toLocaleString('ko-KR')} · 방어력 ${report.nativeStats.def.toLocaleString('ko-KR')}`:'스탯 계산 자료를 확인하세요.';
  for(const [i,slot] of ['head','torso','arm','leg'].entries()){
    const stat=report?.steps?.find(s=>s.name===`equipment:${slot}`)?.value,target=byId('equipment-list').children[i]?.querySelector('.equipment-stat-rows');
    if(!stat||!target)continue;target.replaceChildren();
    for(const [key,label] of Object.entries({hp:'체력',atk:'공격력',def:'방어력'}))if(stat[key]>0){const row=document.createElement('div'),name=document.createElement('span'),value=document.createElement('strong');name.textContent=label;value.textContent=stat[key].toLocaleString('ko-KR');row.append(name,value);target.append(row);}
  }
}
export function detailPreviewFailed(message,expectedRevision){
  if(!session||expectedRevision!==revision)return;
  byId('detail-final-stats').textContent=message;
}
export function renderLocalLabDetail(character,item={},power=null,report=null,catalog={},handlers={}){
  if(!character){session=null;for(const id of ['nikke-core-panel','equipment-summary','equipment-list','skill-editor','collection-editor'])byId(id).replaceChildren();byId('equipment-summary').textContent='보유 계정 스펙이 없습니다.';byId('nikke-detail-power').textContent='—';byId('nikke-selected-tags').textContent='';for(const id of ['character-save-bar','character-cube-editor','detail-final-stats'])byId(id)?.remove();return;}
  const cacheKey=`${handlers.accountId??''}:${character.characterId}`;
  const cached=draftsByCharacter.get(cacheKey);
  revision=0;session=cached&&JSON.stringify(cached.base)===JSON.stringify(character)
    ?{...cached,item,power,catalog,...handlers}:{base:structuredClone(character),draft:structuredClone(character),item,power,report,catalog,...handlers};
  draftsByCharacter.set(cacheKey,session);project();render();
  if(detailDirty()&&!session.report)session.onChange?.(detailDraft(),revision);
}
function render(){
  const {draft:c,item,report,catalog}=session,id=c.characterId;
  const supports=structuredClone(catalog.supportDefinitions??[]);
  supports.push({definitionUid:'0',kindCode:'collection',displayName:'소장품 없음',rarityCode:'none',levels:[]});
  for(const e of c.equipment){
    let def=supports.find(d=>d.definitionUid===e.itemId&&d.kindCode==='equipment');
    if(!def){def={definitionUid:e.itemId??`unknown:${e.slot}`,kindCode:'equipment',displayName:'장비 정보 미확인',slotCode:slots[e.slot],combatClassCode:item.combatClassCode,tier:e.tier,stats:[]};supports.push(def);}
    const stat=report?.steps?.find(s=>s.name===`equipment:${e.slot}`)?.value;
    if(stat){def.stats=Object.entries({hp:'체력',atk:'공격력',def:'방어력'}).filter(([key])=>stat[key]>0).map(([key,label])=>({label,value:String(stat[key]),baseValue:stat[key]}));def.enhancementStatIncreaseBasisPointsPerLevel=0;}
    else if(e.manufacturer===company[item.manufacturerCode]){def.stats=(def.stats??[]).map(s=>({...s,baseValue:Math.round(s.baseValue*(1.3+e.level*.1)),value:String(Math.round(s.baseValue*(1.3+e.level*.1)))}));def.enhancementStatIncreaseBasisPointsPerLevel=0;}
  }
  state.presentation={supportDefinitions:supports,overloadOptions:catalog.overloadOptions??[]};
  state.presentationBySupport=new Map(supports.map(s=>[s.definitionUid,s]));state.presentationByOverload=new Map(state.presentation.overloadOptions.map(s=>[s.definitionUid,s]));state.presentationByCharacter=new Map([[id,item]]);
  const names={elysion:'엘리시온',missilis:'미실리스',tetra:'테트라',pilgrim:'필그림',abnormal:'어브노멀',attacker:'화력형',defender:'방어형',supporter:'지원형',fire:'작열',water:'수냉',wind:'풍압',electric:'전격',iron:'철갑'};
  byId('nikke-selected-tags').textContent=[item.rarityCode?.toUpperCase(),item.burstStep?`버스트 ${{1:'Ⅰ',2:'Ⅱ',3:'Ⅲ',5:'P'}[item.burstStep]}`:null,names[item.manufacturerCode],names[item.combatClassCode],names[item.elementCode]].filter(Boolean).join(' · ');
  byId('nikke-detail-power').textContent=session.power==null?'미확인':session.power.toLocaleString('ko-KR');byId('nikke-detail-power').previousElementSibling.textContent='수집 전투력';
  let final=byId('detail-final-stats');if(!final){final=document.createElement('p');final.id='detail-final-stats';final.className='selected-tags';byId('nikke-detail-power').parentElement.after(final);}
  final.textContent=report?.nativeStats?`체력 ${report.nativeStats.hp.toLocaleString('ko-KR')} · 공격력 ${report.nativeStats.atk.toLocaleString('ko-KR')} · 방어력 ${report.nativeStats.def.toLocaleString('ko-KR')}`:report?'스탯 계산 자료를 확인하세요.':'스탯 계산 중…';
  byId('nikke-core-panel').replaceChildren(numericEditor('레벨','character_level',id,1,10000),numericEditor('호감도','bond_level',id,0,item.maximumBondLevel??40),growthEditor());
  renderEquipmentDetail(id);renderSkillDetail(id);renderCollectionDetail(id,item);
  for(const input of byId('skill-editor').querySelectorAll('input'))input.max='10';
  for(const e of c.equipment){
    const card=byId('equipment-list').children[['head','torso','arm','leg'].indexOf(e.slot)];if(!card)continue;
    if(e.tier!==10)for(const select of card.querySelectorAll('.overload-row select'))select.disabled=true;
    if(e.tier===9){const label=document.createElement('label');label.className='equipment-manufacturer';const input=document.createElement('input');input.type='checkbox';input.checked=e.manufacturer===company[item.manufacturerCode];label.append(input,'기업 장비 일치');card.querySelector('.equipment-stat-panel').append(label);input.onchange=()=>{e.manufacturer=input.checked?company[item.manufacturerCode]:0;changed();};}
  }
  const collectionLevel=byId('collection-editor').querySelector('input');if(collectionLevel){collectionLevel.disabled=c.collectionId==='0'||c.collectionId==null;collectionLevel.min=c.favoriteStage>0?'1':'0';}
  const grade=byId('collection-editor').querySelector('.collection-phase strong');if(grade)grade.textContent=c.favoriteStage>0?'애장품':c.collectionGrade==='none'?'':c.collectionGrade??'미확인';
  renderCube();renderSave();
}
function growthEditor(){
  const c=session.draft,maxLimit=session.item.rarityCode==='ssr'?3:session.item.rarityCode==='sr'?2:0,max=maxLimit===3?10:maxLimit;
  const progress=c.core>0?3+c.core:c.limitBreak??0;
  const group=document.createElement('div');group.className='growth-visual-field growth-progress-row';const title=document.createElement('span');title.textContent='돌파 · 코어 강화';
  const controls=document.createElement('div');controls.className='growth-progress-controls';
  function set(n){c.limitBreak=Math.min(maxLimit,n);c.core=Math.max(0,n-3);changed();}
  const minus=document.createElement('button');minus.type='button';minus.textContent='−';minus.setAttribute('aria-label','돌파·코어 강화 하락');minus.disabled=progress<=0;minus.onclick=()=>set(progress-1);
  const plus=document.createElement('button');plus.type='button';plus.textContent='+';plus.setAttribute('aria-label','돌파·코어 강화 상승');plus.disabled=progress>=max;plus.onclick=()=>set(progress+1);
  const joined=document.createElement('div');joined.className='growth-joined';const stars=document.createElement('div');stars.className='growth-stars';
  for(let i=1;i<=maxLimit;i++){const b=document.createElement('button');b.type='button';b.title=`${i}돌파`;b.setAttribute('aria-label',`${i}돌파`);b.setAttribute('aria-pressed',String(i<=c.limitBreak));const img=document.createElement('img');img.className='growth-star-image';img.alt='';img.src=`/editor/assets/ui/star-${i<=c.limitBreak?'filled':'empty'}.png`;b.append(img);b.onclick=()=>set(i===progress?i-1:i);stars.append(b);}
  joined.append(stars);
  if(c.core>=1){const badge=document.createElement('span');badge.className='core-evolve detail-core-evolve';badge.style.backgroundImage="url('/editor/assets/ui/evolve.png')";badge.textContent=c.core===7?'MAX':String(c.core);badge.setAttribute('aria-label',`코어 강화 ${c.core}`);joined.append(badge);}
  controls.append(minus,joined,plus);group.append(title,controls);return group;
}
function renderCube(){
  let card=byId('character-cube-editor');if(!card){card=document.createElement('article');card.id='character-cube-editor';card.className='surface cube-panel';byId('collection-editor').after(card);}card.replaceChildren();
  const {draft:c,catalog}=session,label=document.createElement('label');label.textContent='장착 큐브';const select=document.createElement('select');select.setAttribute('aria-label','장착 큐브');
  for(const d of [{definitionUid:'0',displayName:'큐브 없음'},...(catalog.cubes??[])]){const o=document.createElement('option');o.value=d.definitionUid;o.textContent=d.displayName;select.append(o);}select.value=c.cubeId??'';label.append(select);
  const cube=(catalog.cubes??[]).find(d=>d.definitionUid===c.cubeId),levelLabel=document.createElement('label');levelLabel.textContent='큐브 레벨';const level=document.createElement('select');level.setAttribute('aria-label','장착 큐브 레벨');for(const d of cube?.levels??[]){const o=document.createElement('option');o.value=d.level;o.textContent=`Lv. ${d.level}`;level.append(o);}level.value=String(c.cubeLevel);level.disabled=!cube;levelLabel.append(level);
  if(cube){const img=document.createElement('img');img.src=cube.imagePath;img.className='cube-image';img.alt=cube.displayName;card.append(img);}
  card.append(label,levelLabel);select.onchange=()=>{c.cubeId=select.value;c.cubeLevel=select.value==='0'?0:session.cubeLevels?.[select.value]??1;changed();};level.onchange=()=>{c.cubeLevel=Number(level.value);changed();};
}
function renderSave(){
  let bar=byId('character-save-bar');if(!bar){bar=document.createElement('div');bar.id='character-save-bar';bar.className='account-save-bar surface';byId('nikke-detail').append(bar);}bar.replaceChildren();
  const message=document.createElement('span');message.textContent=detailDirty()?'변경한 스펙을 저장하세요.':'저장된 스펙';
  const cancel=document.createElement('button');cancel.type='button';cancel.textContent='변경 취소';cancel.disabled=!detailDirty();cancel.onclick=()=>{session.draft=structuredClone(session.base);changed();};
  const save=document.createElement('button');save.type='button';save.className='primary';save.textContent='Save';save.disabled=!detailDirty();
  save.onclick=async()=>{
    for(const input of byId('nikke-detail').querySelectorAll('input,select')){
      if(!input.disabled&&!input.checkValidity()){message.textContent='입력한 스펙의 범위를 확인하세요.';input.reportValidity();return;}
    }
    save.disabled=true;
    try{await session.onSave(detailDraft());}catch(e){message.textContent=e.message;save.disabled=false;}
  };
  bar.append(message,cancel,save);
}

// Account cards adapted from Local Lab c05fc1c editor.js; same markup/classes.
const byId=id=>document.getElementById(id);
let state={presentation:{supportDefinitions:[]},currentProfile:null};
let selectedAccountCubeUid=null,levels={},drafts={};
function accountCubeLevel(cube){return drafts[cube.definitionUid]??levels[cube.definitionUid]??null;}
export function accountCubeDrafts(){return {...drafts};}
export function mountAccountCards(target,snapshot,presentation){
  target.innerHTML=accountPanels;selectedAccountCubeUid=null;drafts={};levels={};
  for(const c of snapshot.characters??[]){
    if(c.cubeId&&c.cubeId!=='0'&&c.cubeLevel>=1)levels[c.cubeId]=Math.max(levels[c.cubeId]??0,c.cubeLevel);
  }
  Object.assign(levels,snapshot.cubeLevels??{});
  state={presentation:{supportDefinitions:(presentation.cubes??[]).map(c=>({...c,kindCode:'cube'}))},currentProfile:snapshot};
  const groups=byId('console-card-groups'),select=byId('general-console'),input=byId('general-console-level');
  groups.replaceChildren();
  const consoleValues={...snapshot.consoles};
  for(const [group,label,codes] of [['common-class','공용 · 클래스',['common','attacker','defender','supporter']],['manufacturer','기업',['elysion','missilis','tetra','pilgrim','abnormal']]]){
    const section=document.createElement('section');section.className='console-group';section.dataset.consoleGroup=group;
    const heading=document.createElement('h4');heading.textContent=label;
    const grid=document.createElement('div');grid.className='console-grid';
    const options=document.createElement('optgroup');options.label=label;
    for(const code of codes){
      const item=(presentation.consoles??[]).find(c=>c.coordinateCode===code);if(!item)continue;
      const option=document.createElement('option');option.value=item.id;option.textContent=item.displayName;options.append(option);
      const card=document.createElement('button');card.type='button';card.className='console-card';card.dataset.consoleUid=item.id;
      const artwork=document.createElement('span');artwork.className='console-artwork';
      appendPresentationImage(artwork,item.imagePath,'console-image','','이미지 없음');
      const name=document.createElement('strong');name.className='console-name';name.textContent=item.displayName;
      const level=document.createElement('span');level.className='console-level';
      level.textContent=consoleValues[item.id]==null?'미확인':`Lv. ${consoleValues[item.id]}`;
      const selected=document.createElement('span');selected.className='console-selected-mark';selected.textContent='✓';selected.setAttribute('aria-hidden','true');
      card.append(artwork,name,level,selected);card.onclick=()=>{select.value=item.id;showConsole();};grid.append(card);
      const stored=document.createElement('input');stored.type='hidden';stored.name='console-'+item.id;stored.value=consoleValues[item.id]??'';target.append(stored);
    }
    section.append(heading,grid);groups.append(section);select.append(options);
  }
  function showConsole(){
    input.value=consoleValues[select.value]??'';
    for(const card of groups.querySelectorAll('.console-card'))card.setAttribute('aria-pressed',String(card.dataset.consoleUid===select.value));
  }
  select.onchange=showConsole;showConsole();input.max='10000';
  input.oninput=()=>{
    if(!input.checkValidity())return;
    const id=select.value;if(!id)return;
    consoleValues[id]=input.value===''?null:Number(input.value);
    target.querySelector(`[name="console-${id}"]`).value=input.value;
    const card=[...groups.querySelectorAll('.console-card')].find(c=>c.dataset.consoleUid===id);
    card.querySelector('.console-level').textContent=input.value===''?'미확인':`Lv. ${input.value}`;
  };
  renderCubeCards();
  byId('cube-owned-count').textContent=`레벨 확인 ${Object.keys(levels).length}종`;
  byId('account-cube-level').onchange=e=>{
    if(!selectedAccountCubeUid||e.target.value==='')return;
    drafts[selectedAccountCubeUid]=Number(e.target.value);renderCubeCardState();
  };
}
function appendPresentationImage(container, path, className, alt, fallbackText = "?") {
  const image = document.createElement("img");
  image.className = className;
  image.src = path;
  image.alt = alt || "";
  image.loading = "lazy";
  image.addEventListener("error", () => {
    image.remove();
    if (!fallbackText) return;
    const fallback = document.createElement("span");
    fallback.className = `${className} presentation-image-fallback`;
    fallback.textContent = fallbackText;
    container.appendChild(fallback);
  }, { once: true });
  container.appendChild(image);
  return image;
}

function cubeDefinitions() {
  return (state.presentation.supportDefinitions || []).filter((item) => item.kindCode === "cube")
    .sort((left, right) => (left.displayOrder ?? 0) - (right.displayOrder ?? 0) || left.displayName.localeCompare(right.displayName, "ko"));
}

function cubeLevels(cube) {
  return (cube.levels || []).filter((entry) => Number.isInteger(entry.level) && entry.level >= 1 && entry.level <= 15)
    .sort((left, right) => left.level - right.level);
}

function cubeEffect(cube) {
  return cubeLevels(cube).find((entry) => entry.level === accountCubeLevel(cube))?.primaryEffect || "효과 정보를 확인할 수 없습니다.";
}

function renderCubeCards() {
  const grid = byId("cube-cards");
  grid.replaceChildren();
  const cubes = state.currentProfile ? cubeDefinitions() : [];
  byId("cube-owned-count").textContent = cubes.length ? `${cubes.length}종 보유` : "";
  if (!cubes.some((cube) => cube.definitionUid === selectedAccountCubeUid)) selectedAccountCubeUid = null;
  if (!cubes.length) {
    const empty = document.createElement("p");
    empty.className = "console-empty";
    empty.textContent = state.currentProfile ? "큐브 카탈로그가 없습니다." : "계정을 선택하면 큐브가 표시됩니다.";
    grid.appendChild(empty);
  }
  for (const cube of cubes) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "cube-card";
    card.dataset.cubeUid = cube.definitionUid;
    card.setAttribute("aria-controls", "account-cube-editor");
    card.disabled = !cubeLevels(cube).length;
    const artwork = document.createElement("span");
    artwork.className = "cube-artwork";
    appendPresentationImage(artwork, cube.imagePath, "cube-image", "", "이미지 없음");
    const name = document.createElement("strong");
    name.className = "cube-name";
    name.textContent = cube.displayName;
    const level = document.createElement("span");
    level.className = "cube-level";
    const effect = document.createElement("span");
    effect.className = "cube-effect";
    card.append(artwork, name, level, effect);
    card.addEventListener("click", () => {
      selectedAccountCubeUid = cube.definitionUid;
      renderCubeCardState();
      byId("account-cube-level").focus();
    });
    grid.appendChild(card);
  }
  renderCubeCardState();
}

function renderCubeCardState() {
  const cubes = cubeDefinitions();
  for (const card of document.querySelectorAll(".cube-card")) {
    const cube = cubes.find((item) => item.definitionUid === card.dataset.cubeUid);
    if (!cube) continue;
    card.setAttribute("aria-pressed", String(cube.definitionUid === selectedAccountCubeUid));
    card.querySelector(".cube-level").textContent = `Lv. ${accountCubeLevel(cube) ?? "—"}`;
    card.querySelector(".cube-effect").textContent = cubeEffect(cube);
  }
  const cube = state.currentProfile && cubes.find((item) => item.definitionUid === selectedAccountCubeUid);
  byId("account-cube-editor").hidden = !cube;
  if (!cube) return;
  byId("account-cube-name").textContent = cube.displayName;
  byId("account-cube-effect").textContent = cubeEffect(cube);
  const select = byId("account-cube-level");
  select.replaceChildren();
  for (const entry of cubeLevels(cube)) {
    const option = document.createElement("option");
    option.value = String(entry.level);
    option.textContent = `Lv. ${entry.level}`;
    select.appendChild(option);
  }
  select.value = String(accountCubeLevel(cube));
}

const accountPanels='          <article class="surface console-panel">\n            <div class="card-title"><div><h3>리사이클 룸 콘솔</h3><p>콘솔 카드를 선택해 레벨을 설정합니다.</p></div></div>\n            <div id="console-card-groups" class="console-card-groups" aria-label="콘솔 현황"><p class="console-empty">계정을 선택하면 콘솔이 표시됩니다.</p></div>\n            <div class="console-editor"><label>선택한 콘솔 <select id="general-console"></select></label><label>레벨 <input id="general-console-level" type="number" min="0"></label></div>\n          </article>\n          <article class="surface cube-panel">\n            <div class="card-title"><div><h3>하모니 큐브</h3><p>카드를 선택해 계정 공통 레벨을 설정하세요.</p></div><span class="cube-owned-badge" id="cube-owned-count"></span></div>\n            <div class="cube-editor" id="account-cube-editor" hidden>\n              <div><strong id="account-cube-name"></strong><p id="account-cube-effect"></p></div>\n              <label>큐브 레벨 <select id="account-cube-level" aria-describedby="account-cube-hint"></select></label>\n            </div>\n            <p class="cube-hint" id="account-cube-hint">레벨 변경은 같은 큐브를 장착한 모든 니케에 적용됩니다. 아래 Save로 저장하세요.</p>\n            <div id="cube-cards" class="cube-grid" aria-label="하모니 큐브 목록"></div>\n          </article>\n';

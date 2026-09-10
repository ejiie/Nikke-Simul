import { appendPortrait } from './cards.js';

const $ = id => document.getElementById(id);
const empty = () => Array(5).fill(null);
const asset = name => `/editor/assets/ui/${name}.png`;
const weapons = { assault_rifle: '소총', machine_gun: '머신건', rocket_launcher: '런처',
  shotgun: '샷건', sniper_rifle: '저격소총', submachine_gun: '기관단총' };
const elements = { fire: '작열', water: '수냉', wind: '풍압', electric: '전격', iron: '철갑' };

export function createFormation({ api, getSnapshot, getItem, getBuild, status, showSelector, showRaid, renderCards }) {
  let account = null, saved = empty(), draft = empty(), loaded = false, saving = false, generation = 0;

  function drawSlots(target, slots, editing) {
    if (!target) return;
    target.replaceChildren();
    slots.forEach((id, index) => {
      const item = getItem(id), build = getBuild(id);
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'formation-slot';
      button.dataset.slot = index;
      button.dataset.characterUid = id ?? '';
      button.disabled = !loaded || saving;
      button.setAttribute('aria-label', `${index + 1}번 칸 · ${id ? item?.displayName ?? build?.name ?? '니케' : '빈칸'} · ${editing && id ? '편성 해제' : '니케 선택'}`);
      if (!id) {
        button.classList.add('formation-slot-empty'); button.textContent = '+';
      } else {
        const face = document.createElement('span'); face.className = 'formation-face';
        appendPortrait(face, item?.portraitPath, item?.displayName);
        button.append(face);
        const icon = (kind, name, label, hex = false) => {
          if (!name) return;
          const img = document.createElement('img');
          img.src = asset(name); img.alt = label;
          if (hex) {
            const badge = document.createElement('span');
            badge.className = `formation-icon formation-hex formation-${kind}`;
            badge.title = label; badge.append(img); button.append(badge);
          } else {
            img.className = `formation-icon formation-${kind}`; button.append(img);
          }
        };
        icon('weapon', weapons[item?.weaponCode] && `weapon-${item.weaponCode}`, weapons[item?.weaponCode], true);
        const burst = { 1: '1', 2: '2', 3: '3', 5: 'p' }[item?.burstStep];
        icon('burst', burst && `burst-${burst}`, `버스트 ${burst?.toUpperCase()}`, true);
        icon('element', elements[item?.elementCode] && `code-${item.elementCode}`, elements[item?.elementCode]);
        const growth = document.createElement('span'); growth.className = 'formation-growth';
        const limit = build?.core > 0 ? 3 : build?.limitBreak ?? 0;
        growth.setAttribute('aria-label', `돌파 ${limit} · 코어 강화 ${build?.core ?? 0}`);
        for (let n = 0; n < 3; n++) {
          const star = document.createElement('img'); star.src = asset(n < limit ? 'star-filled' : 'star-empty'); star.alt = '';
          growth.append(star);
        }
        if (build?.core >= 1) {
          const core = document.createElement('span'); core.className = 'core-evolve';
          core.style.backgroundImage = `url('${asset('evolve')}')`; core.textContent = build.core >= 7 ? 'MAX' : build.core;
          growth.append(core);
        }
        const name = document.createElement('span'); name.className = 'formation-name'; name.textContent = item?.displayName ?? build?.name ?? '니케';
        button.append(growth, name);
      }
      button.onclick = () => {
        if (!editing) { draft = [...saved]; showSelector(); render(); renderCards(); }
        else if (id) { draft[index] = null; render(); renderCards(); }
        else $('nikke-search').focus({ preventScroll: true });
      };
      target.append(button);
    });
  }
  function render() {
    drawSlots($('raid-team'), saved, false);
    drawSlots($('formation-team'), draft, true);
    $('formation-save').disabled = !loaded || saving;
    $('formation-save').textContent = saving ? '저장 중…' : '편성 저장';
    $('formation-cancel').disabled = saving;
    $('formation-count').textContent = `${draft.filter(Boolean).length} / 5`;
  }
  $('formation-save').onclick = async () => {
    if (!loaded || saving) return;
    const expected = generation;
    saving = true; render();
    try {
      const result = await api(`/accounts/${account}/formation`, 'PUT', { slots: [...draft] });
      if (expected !== generation) return;
      saved = [...result.slots]; draft = [...saved]; showRaid(); status('편성을 저장했습니다.');
    } catch (error) { if (expected === generation) status(error.message); }
    finally { if (expected === generation) { saving = false; render(); renderCards(); } }
  };
  $('formation-cancel').onclick = () => { draft = [...saved]; showRaid(); render(); };
  return {
    render,
    contains: id => draft.includes(id),
    members: () => saved.filter(Boolean),
    select(id) {
      if (!loaded || saving) return;
      if (!getBuild(id)) { status('보유한 니케만 편성할 수 있습니다.'); return; }
      if (draft.includes(id)) { status('이미 편성한 니케입니다. 위의 편성 칸을 누르면 해제됩니다.'); return; }
      const index = draft.indexOf(null);
      if (index < 0) { status('5칸이 모두 찼습니다. 위의 편성 칸을 눌러 해제하세요.'); return; }
      draft[index] = id; render(); renderCards();
    },
    async load() {
      const next = getSnapshot()?.accountId ?? null;
      if (next === account && loaded) return;
      const expected = ++generation;
      account = next; saved = empty(); draft = empty(); loaded = false; saving = false; render();
      if (!account) return;
      const result = await api(`/accounts/${account}/formation`);
      if (expected !== generation || getSnapshot()?.accountId !== next) return;
      saved = [...result.slots]; draft = [...saved]; loaded = true; render();
    }
  };
}

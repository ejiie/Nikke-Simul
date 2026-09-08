import './upstream-theme.css';
import './styles.css';
import { active, escape as e, lineValue, options, parts, selectedConnection, value, type Character, type Connection, type Job, type Snapshot } from './model';

type Boot = { token: string; connections: Connection[]; jobs: Job[]; game: { characters: number }; testMode: boolean };
const app = document.querySelector<HTMLDivElement>('#app')!;
let boot: Boot = { token: '', connections: [], jobs: [], game: { characters: 0 }, testMode: false };
let snapshot: Snapshot | null = null;
let connectionId = localStorage.getItem('nikke-sync-connection');
let characterId = '';
let search = '';
let message = '';
let busy = false;
let lastState = '';
let refreshSequence = 0;
let connectionError = false;
const connection = () => selectedConnection(boot.connections, connectionId);
const currentJob = () => boot.jobs.find(j => j.connectionId === connection()?.id);
const time = (s: string) => new Date(s).toLocaleString('ko-KR');
const consoleNames: Record<string, string> = { '1001': '공통', '1101': '화력형', '1102': '방어형', '1103': '지원형', '1201': '엘리시온', '1202': '미실리스', '1203': '테트라', '1204': '필그림', '1205': '어브노말' };

async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, { method, headers: { 'Content-Type': 'application/json', 'X-Nikke-Token': boot.token }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  if (response.status === 204) return null as T;
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.message ?? `요청 실패 (${response.status})`);
  return payload as T;
}
async function refresh(force = false) {
  const sequence = ++refreshSequence;
  try {
    const next = await api<Boot>('/bootstrap');
    if (sequence !== refreshSequence) return;
    if (connectionError) { message = ''; connectionError = false; showMessage(); }
    const signature = JSON.stringify(next);
    if (!force && signature === lastState) return;
    const selected = selectedConnection(next.connections, connectionId);
    const nextSnapshot = selected?.accountId ? await api<Snapshot | null>(`/accounts/${selected.accountId}/snapshot`) : null;
    if (sequence !== refreshSequence) return;
    boot = next; lastState = signature;
    if (selected) { connectionId = selected.id; localStorage.setItem('nikke-sync-connection', selected.id); }
    snapshot = nextSnapshot;
    render();
  } catch (error) { if (sequence !== refreshSequence) return; connectionError = true; message = error instanceof Error ? error.message : '백엔드에 연결하지 못했습니다.'; showMessage(); }
}
async function act(action: () => Promise<unknown>) {
  if (busy) return;
  busy = true; message = ''; render();
  try { await action(); } catch (error) { message = error instanceof Error ? error.message : '처리하지 못했습니다.'; }
  finally { busy = false; await refresh(true); }
}
function showMessage() { const box = document.querySelector<HTMLElement>('#notice'); if (box) { box.textContent = message; box.hidden = !message; } }
function statusPanel(c?: Connection, job?: Job): string {
  if (c?.status === 'awaiting_login') return `<div class="status"><span class="pulse"></span><div><strong>로그인 대기 중</strong><p>${e(c.message ?? '열린 브라우저에서 로그인하세요.')}</p></div></div>`;
  if (c?.status === 'select_account') return `<div class="status"><div><strong>사용할 서버 선택</strong><p>서버별 스펙을 별도로 관리합니다.</p><div class="actions">${c.choices.map(x => `<button data-area="${x.area}">${e(x.label)} · ${x.characterCount}명</button>`).join('')}</div></div></div>`;
  if (c?.status === 'reauth_required') return `<div class="status warning"><div><strong>다시 로그인이 필요합니다</strong><p>${e(c.message)}</p><button id="reauth">다시 로그인</button></div></div>`;
  if (job && active(job)) return `<div class="status"><span class="pulse"></span><div class="grow"><strong>${job.stage === 'validating' ? '정제·검증 중' : job.status === 'cancelling' ? '취소 중' : '계정 스펙 수집 중'}</strong><p>상세 ${job.collected} / ${job.expected || '확인 중'}명</p><progress ${job.expected ? `value="${job.collected}" max="${job.expected}"` : ''}></progress></div><button id="cancel">취소</button></div>`;
  if (job && job.status !== 'succeeded') return `<div class="status warning"><div><strong>동기화를 완료하지 못했습니다</strong><p>${e(job.message ?? '작업이 중단되었습니다. 다시 시도하세요.')}</p><small>이전에 저장된 정상 스펙을 유지합니다.</small></div></div>`;
  return `<div class="status"><span class="status-dot"></span><div><strong>${snapshot ? '저장된 스펙을 사용할 수 있습니다' : '계정을 연결하면 스펙을 자동으로 가져옵니다'}</strong><p>${snapshot ? `마지막 수집 ${time(snapshot.observedAt)}` : '처음 한 번 로그인한 뒤, 버튼 하나로 갱신하세요.'}</p></div></div>`;
}
function render() {
  const c = connection(), job = currentJob();
  app.innerHTML = `<main class="shell">
    <header class="top"><a class="brand" href="/">NIKKE<span>SIMUL</span></a><span class="chip">SOLO RAID · 스펙 관리</span></header>
    <section class="hero"><div><p class="eyebrow">ACCOUNT SYNC</p><h1>내 스펙을,<br><span>한 번에.</span></h1><p class="lede">수집부터 저장까지 자동으로.<br>육성 현황과 장비 옵션을 한곳에서 확인하세요.</p></div><div class="hero-actions"><button class="primary" id="sync" ${busy || !c || c.status !== 'ready' || (job && active(job)) ? 'disabled' : ''}>↻ 내 스펙 동기화</button><button id="connect" ${busy || c?.status === 'awaiting_login' ? 'disabled' : ''}>${c ? '다른 계정 연결' : '계정 연결'}</button><small>스펙은 이 PC에 저장됩니다</small></div></section>
    ${boot.testMode ? '<div class="test-banner">검증용 데이터 · 실제 계정 수집 결과가 아닙니다</div>' : ''}
    <div id="notice" class="notice" role="alert" ${message ? '' : 'hidden'}>${e(message)}</div>
    <section class="account-bar"><label>연결 계정 <select id="connection" aria-label="연결 계정">${boot.connections.length ? boot.connections.map((x, i) => `<option value="${e(x.id)}" ${x.id === c?.id ? 'selected' : ''}>계정 ${boot.connections.length - i} · ${e(x.choices.find(a => a.area === x.area)?.label ?? '연결 중')}</option>`).join('') : '<option>연결된 계정 없음</option>'}</select></label><span>${snapshot ? `${snapshot.characters.length}명 수집` : '수집 전'}</span><span>${snapshot ? `저장 이력 ${snapshot.revision}회` : '로그인 필요'}</span></section>
    <section aria-live="polite">${statusPanel(c, job)}</section>
    <section class="metrics"><div><span>보유 니케</span><strong>${snapshot?.characters.length ?? '—'}<small>명</small></strong></div><div><span>싱크로 레벨</span><strong>${snapshot?.synchroLevel ?? '미확인'}</strong></div><div><span>검토할 항목</span><strong>${snapshot?.issues.filter(i => i.severity === 'warning' && i.code !== 'duplicate_identical').length ?? '—'}<small>건</small></strong></div><div><span>원천 옵션 보존</span><strong>4 <small>부위 ×</small> 3 <small>줄</small></strong></div></section>
    <section class="workspace"><aside class="roster panel"><div class="panel-heading"><h2>내 니케</h2><span>${snapshot?.characters.length ?? 0}</span></div><input id="search" type="search" placeholder="이름으로 찾기" aria-label="니케 검색" value="${e(search)}"><div id="roster-list"></div></aside><article id="detail" class="detail panel"></article></section>
    <section class="bottom-grid"><div class="panel"><h2>최근 변경</h2>${snapshot ? `<ul>${snapshot.changes.slice(0, 30).map(x => `<li>${e(x)}</li>`).join('')}</ul>` : '<p class="muted">첫 동기화를 완료하면 변경 내역이 표시됩니다.</p>'}</div><div class="panel"><h2>수집 확인</h2>${renderIssues(job)}</div></section>
    ${snapshot ? `<details class="panel account-edit"><summary>계정 스탯 확인·수동 보완</summary><p class="muted">수집되지 않은 값은 빈칸으로 표시됩니다. 실제 값을 확인한 뒤 저장하세요.</p><form id="account-form"><div class="fields"><label>싱크로 레벨<input type="number" name="synchro" min="1" max="10000" value="${snapshot.synchroLevel ?? ''}"></label>${Object.entries(consoleNames).map(([id, label]) => `<label>${e(label)} 연구실<input type="number" name="console-${id}" min="0" max="10000" value="${snapshot!.consoles?.[id] ?? ''}"></label>`).join('')}</div><button type="submit" ${busy ? 'disabled' : ''}>계정 스탯 보완 저장</button><small>현재 출처: ${snapshot.accountStatsSource.includes('manual') ? '수동 보완 포함' : 'API 수집'}</small></form></details>` : ''}
    <footer><span>대미지 계산과 추천 기능은 후속 단계에서 연결됩니다.</span><a href="https://github.com/Moris-kr/nikke-calc" target="_blank" rel="noreferrer">UI 테마 출처 · nikke-calc / MIT</a></footer>
  </main>`;
  renderRoster(); renderDetail(); bind();
}
function renderIssues(job?: Job): string {
  const issues = (job?.status === 'failed' ? job.issues : snapshot?.issues) ?? [];
  const meaningful = issues.filter(i => i.code !== 'duplicate_identical');
  if (!snapshot && !meaningful.length) return '<p class="muted">수집 후 누락·미지원 항목을 확인할 수 있습니다.</p>';
  return meaningful.length ? `<ul class="issues">${meaningful.slice(0, 30).map(i => `<li><b>${e(i.path)}</b> ${e(i.message)}</li>`).join('')}</ul>` : '<p class="muted">필수 수집 검증을 통과했습니다. OL 잠금 상태는 장비에서 별도로 확인하세요.</p>';
}
function renderRoster() {
  const list = snapshot?.characters.filter(c => c.name.toLowerCase().includes(search.toLowerCase())) ?? [];
  const el = document.querySelector('#roster-list')!;
  el.innerHTML = list.length ? list.map(c => `<button class="character ${c.characterId === characterId ? 'selected' : ''}" data-character="${e(c.characterId)}"><span class="avatar">${e(c.name.slice(0, 1))}</span><span><strong>${e(c.name)}</strong><small>Lv. ${value(c.level)} · 스킬 ${Object.values(c.skills).map(value).join('/')}</small></span><span class="arrow">›</span></button>`).join('') : '<div class="empty small">표시할 니케가 없습니다.</div>';
  el.querySelectorAll<HTMLButtonElement>('[data-character]').forEach(b => b.onclick = () => { characterId = b.dataset.character!; renderRoster(); renderDetail(); });
}
function renderDetail() {
  const c: Character | undefined = snapshot?.characters.find(c => c.characterId === characterId) ?? snapshot?.characters[0];
  const el = document.querySelector('#detail')!;
  if (!c) { el.innerHTML = '<div class="empty"><div class="empty-icon">＋</div><h2>육성 현황을 불러오세요</h2><p>계정을 연결하면 보유 니케와<br>장비별 오버로드 옵션이 여기에 표시됩니다.</p></div>'; return; }
  if (characterId !== c.characterId) { characterId = c.characterId; renderRoster(); }
  el.innerHTML = `<div class="detail-heading"><div><p class="eyebrow">CHARACTER BUILD</p><h2>${e(c.name)}</h2></div><span class="chip">${c.catalogKnown ? '목록 매핑 확인' : '미등록 캐릭터'}</span></div><div class="stat-line"><span>레벨 <b>${value(c.level)}</b></span><span>돌파 <b>${value(c.limitBreak)}</b></span><span>코강 <b>${value(c.core)}</b></span><span>호감도 <b>${value(c.bond)}</b></span><span>스킬 <b>${Object.values(c.skills).map(value).join(' / ')}</b></span></div>
    <div class="equipment-grid">${c.equipment.map(eq => `<section class="equipment"><div class="panel-heading"><h3>${e(parts[eq.slot])}</h3><span>${eq.tier === 0 ? '미장착' : `T${value(eq.tier)} +${value(eq.level)}`}</span></div>${eq.lines.map(line => `<div class="option-line"><span class="line-no">0${line.lineIndex}</span><div class="grow"><strong>${line.presence === 'absent' ? '옵션 없음' : e(options[line.optionType ?? ''] ?? line.optionType ?? '옵션 미확인')}</strong><small>${line.presence === 'present' ? `${e(lineValue(line))} · ${line.valueTier === null ? '단계 미확인' : line.valueTier + '단계'}` : '—'}</small></div>${line.presence === 'present' ? `<select data-lock="${eq.slot}:${line.lineIndex}" aria-label="${e(parts[eq.slot])} ${line.lineIndex}줄 잠금" ${busy ? 'disabled' : ''}>${[['unknown','잠금 미확인'],['unlocked','잠금 해제'],['locked','잠금']].map(([v,l]) => `<option value="${v}" ${v === line.lockState ? 'selected' : ''}>${l}</option>`).join('')}</select>` : ''}</div>`).join('')}</section>`).join('')}</div>
    <div class="accessories"><div><span>현재 장착 큐브</span><strong>${c.cubeId === '0' ? '미장착' : `ID ${value(c.cubeId)} · Lv. ${value(c.cubeLevel)}`}</strong></div><div><span>소장품 / 애장품</span><strong>${c.collectionId === '0' ? '미장착' : `${value(c.collectionGrade)} · Lv. ${value(c.collectionLevel)}${c.favoriteStage ? ` · 애장품 ${c.favoriteStage}단계` : ''}`}</strong></div></div><p class="detail-note">잠금 선택은 수동 보완으로 저장됩니다. 장비 옵션이 변경되면 다시 확인합니다.</p>`;
  el.querySelectorAll<HTMLSelectElement>('[data-lock]').forEach(select => select.onchange = () => {
    const [slot, index] = select.dataset.lock!.split(':');
    const request = { expectedSnapshotId: snapshot!.id, characterId: c.characterId, slot, lineIndex: Number(index), lockState: select.value, fingerprint: c.equipment.find(x => x.slot === slot)!.fingerprint };
    void act(async () => { await api(`/accounts/${snapshot!.accountId}/overrides`, 'POST', request); });
  });
}
function bind() {
  const on = (id: string, fn: () => void) => { const el = document.getElementById(id); if (el) el.onclick = fn; };
  on('connect', () => void act(async () => { const c = await api<Connection>('/connections', 'POST', {}); connectionId = c.id; }));
  on('sync', () => void act(() => api('/sync-jobs', 'POST', { connectionId: connection()!.id })));
  on('reauth', () => void act(() => api(`/connections/${connection()!.id}/reauth`, 'POST', {})));
  on('cancel', () => void act(() => api(`/sync-jobs/${currentJob()!.id}/cancel`, 'POST', {})));
  document.querySelectorAll<HTMLButtonElement>('[data-area]').forEach(b => b.onclick = () => void act(() => api(`/connections/${connection()!.id}`, 'PATCH', { area: Number(b.dataset.area) })));
  document.querySelector<HTMLSelectElement>('#connection')!.onchange = ev => { connectionId = (ev.target as HTMLSelectElement).value; search = ''; characterId = ''; void refresh(true); };
  document.querySelector<HTMLInputElement>('#search')!.oninput = ev => { search = (ev.target as HTMLInputElement).value; renderRoster(); };
  const form = document.querySelector<HTMLFormElement>('#account-form');
  if (form) form.onsubmit = ev => {
    ev.preventDefault(); const fields = new FormData(form); const consoles: Record<string, number> = {};
    for (const id of Object.keys(consoleNames)) { const text = String(fields.get('console-' + id) ?? '').trim(); if (text !== '') consoles[id] = Number(text); }
    const synchro = String(fields.get('synchro') ?? '').trim();
    void act(() => api(`/accounts/${snapshot!.accountId}/overrides`, 'POST', { expectedSnapshotId: snapshot!.id,
      synchroLevel: synchro ? Number(synchro) : null, consoles: Object.keys(consoles).length ? consoles : null }));
  };
}
render();
void refresh(true);
setInterval(() => { if (!busy) void refresh(); }, 1200);

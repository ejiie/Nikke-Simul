/**
 * Burst Tactics Configuration Component (U2 Integration Edition)
 *
 * Allows users to configure and synchronize:
 * - Burst allowlist (used Nikkes) vs excluded Nikkes
 * - Clear distinction between "Alice First (우선)" and "Alice Only (전용)"
 * - Per-stage candidate priority order (I, II, III)
 * - Stage III rotation and first caster derived from checked priority order
 * - Fixed next_ready fallback; no hidden strategy controls
 * - Server API integration (PUT /api/accounts/{id}/burst-tactic & GET) with local cache fallback
 * - Cross-comparison of actual burst timeline vs user tactic settings
 */

import {
  auditBurstTactics,
  createDefaultTactics,
  toServerTacticDto,
  fromServerTacticDto,
  saveBurstTacticToServer,
  loadBurstTacticFromServer
} from './damage-log-adapter.js';

const $ = id => document.getElementById(id);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// The compact UI has one source of truth: checked members in displayed order.
// Keep the general API adapter backward-compatible; normalize only this editor.
export function normalizeVisibleBurstTactics(tactics, members) {
  const allowedStage3 = new Set(members.filter(m => m.burstStep === 3 && tactics.allowlist[m.id] !== false).map(m => m.id));
  tactics.stage3Mode = 'alternate';
  tactics.burst3Rotation = (tactics.priority.stage3 ?? []).filter(id => allowedStage3.has(id));
  tactics.firstCaster = tactics.burst3Rotation[0] ?? null;
  tactics.fallbackPolicy = 'next_ready';
  return tactics;
}

export function createBurstTacticsManager({ api, getSnapshot, getMembersWithMeta, getFormationSlots, onTacticsChanged, status }) {
  let tactics = null;
  let lastAccount = null;
  let serverSyncStatus = 'idle'; // 'idle' | 'saving' | 'saved' | 'local_only' | 'stale' | 'error'
  let serverMessage = '';
  let serverIssues = [];
  let isServerStale = false;
  let activeSyncId = 0;

  function storageKey(accountId) {
    return `nikke-burst-tactics-${accountId || 'default'}`;
  }

  function loadLocalTactics(account, members) {
    let loaded = null;
    try {
      const raw = localStorage.getItem(storageKey(account));
      if (raw) loaded = JSON.parse(raw);
    } catch {
      loaded = null;
    }

    if (!loaded || loaded.version !== 2) {
      tactics = createDefaultTactics(members);
    } else {
      tactics = loaded;
      if (!tactics.allowlist) tactics.allowlist = {};
      // Ensure all current formation members exist in allowlist
      for (const m of members) {
        if (tactics.allowlist[m.id] === undefined) {
          if (m.burstStep === 3 && tactics.stage3Mode === 'priority_only' && tactics.burst3Rotation?.length === 1 && !tactics.burst3Rotation.includes(m.id)) {
            tactics.allowlist[m.id] = false;
          } else {
            tactics.allowlist[m.id] = true;
          }
        }
      }
      for (const m of members) {
        const stageKey = `stage${m.burstStep}`;
        if (tactics.priority?.[stageKey] && !tactics.priority[stageKey].includes(m.id)) {
          tactics.priority[stageKey].push(m.id);
        }
      }
    }
    normalizeVisibleBurstTactics(tactics, members);
  }

  async function syncFromServer() {
    const account = getSnapshot()?.accountId;
    if (!api || !account) return;

    const members = getMembersWithMeta();
    if (!members.length) return;

    const syncId = ++activeSyncId;
    const initialTacticJson = JSON.stringify(tactics);
    const result = await loadBurstTacticFromServer(api, account, members);

    // Guard against race conditions:
    // 1. A newer sync has been started
    if (syncId !== activeSyncId) return;
    // 2. Account changed during network flight
    if (account !== getSnapshot()?.accountId) return;
    // 3. User edited tactics locally during flight
    if (JSON.stringify(tactics) !== initialTacticJson) return;

    if (result.ok && result.tactics) {
      tactics = normalizeVisibleBurstTactics(result.tactics, members);
      lastAccount = account;
      isServerStale = result.stale;
      serverSyncStatus = result.stale ? 'stale' : (result.executionStatus === 'draft_incomplete' ? 'draft_incomplete' : 'saved');
      serverMessage = result.stale ? '편성이 변경되어 이전 저장 설정과 불일치합니다 (Stale).' : '서버에 저장된 설정을 불러왔습니다.';
      try {
        localStorage.setItem(storageKey(account), JSON.stringify(tactics));
      } catch {}
      render();
    } else if (result.ok && !result.tactics) {
      serverSyncStatus = 'local_only';
      serverMessage = '서버에 저장된 전술이 없습니다 (로컬 기본값 사용).';
    } else {
      serverSyncStatus = 'local_only';
      serverMessage = result.error || '서버 조회 실패 (로컬 설정 사용).';
    }
  }

  function loadTactics() {
    const account = getSnapshot()?.accountId ?? 'local';
    const members = getMembersWithMeta();
    if (!members.length) {
      tactics = createDefaultTactics([]);
      return tactics;
    }

    const accountChanged = lastAccount !== account;
    loadLocalTactics(account, members);
    if (accountChanged) {
      lastAccount = account;
      if (account !== 'local' && api) {
        syncFromServer();
      }
    }

    return tactics;
  }

  async function saveTactics() {
    const account = getSnapshot()?.accountId ?? 'local';
    const snapshotId = getSnapshot()?.id ?? 'snap-local';
    const slots = getFormationSlots ? getFormationSlots() : getMembersWithMeta().map(m => m.id);
    const members = getMembersWithMeta();

    normalizeVisibleBurstTactics(tactics, members);

    // 1. Immediate local storage persistence
    try {
      localStorage.setItem(storageKey(account), JSON.stringify(tactics));
    } catch (e) {
      status?.(`로컬 저장 실패: ${e.message}`);
    }

    // 2. Server API synchronization
    if (api && account !== 'local') {
      serverSyncStatus = 'saving';
      render();
      const res = await saveBurstTacticToServer(api, account, snapshotId, slots, tactics, members);
      if (res.ok) {
        const savedData = res.data;
        isServerStale = Boolean(savedData?.stale);
        serverIssues = savedData?.issues || [];
        serverSyncStatus = savedData?.executionStatus === 'draft_incomplete' ? 'draft_incomplete' : (isServerStale ? 'stale' : 'saved');
        serverMessage = serverSyncStatus === 'saved'
          ? '버스트 전술을 서버에 저장했습니다.'
          : (serverSyncStatus === 'draft_incomplete' ? '초안으로 서버에 저장되었습니다 (일부 단계 미완성).' : '서버에 저장되었으나 편성과 불일치합니다.');
        status?.(serverMessage);
      } else {
        serverSyncStatus = 'local_only';
        serverMessage = `서버 저장 실패 (${res.error}). 로컬에 임시 보존되었습니다.`;
        status?.(serverMessage);
      }
    } else {
      serverSyncStatus = 'local_only';
      status?.('버스트 전술 설정을 로컬에 저장했습니다.');
    }

    if (onTacticsChanged) onTacticsChanged(tactics);
    render();
  }

  function applyPreset(presetType) {
    const members = getMembersWithMeta();
    const stage3Members = members.filter(m => m.burstStep === 3);
    const hasAlice = stage3Members.some(m => m.id === '5004');

    if (presetType === 'alice_only') {
      if (!hasAlice) {
        status?.('현재 편성에 앨리스가 없습니다.');
        return;
      }
      for (const m of stage3Members) {
        tactics.allowlist[m.id] = (m.id === '5004');
      }
      tactics.firstCaster = '5004';
      tactics.stage3Mode = 'priority_only';
      tactics.priority.stage3 = ['5004', ...stage3Members.filter(m => m.id !== '5004').map(m => m.id)];
      tactics.burst3Rotation = ['5004'];
      status?.('프리셋 적용: [앨리스만 사용] (다른 버스트 III 니케는 발동 제외)');
    } else if (presetType === 'alice_first') {
      if (!hasAlice) {
        status?.('현재 편성에 앨리스가 없습니다.');
        return;
      }
      for (const m of stage3Members) {
        tactics.allowlist[m.id] = true;
      }
      tactics.firstCaster = '5004';
      tactics.stage3Mode = 'alternate';
      tactics.priority.stage3 = ['5004', ...stage3Members.filter(m => m.id !== '5004').map(m => m.id)];
      tactics.burst3Rotation = [...tactics.priority.stage3];
      status?.('프리셋 적용: [앨리스 우선순위 1위 + 교대 순환]');
    } else if (presetType === 'formation_order') {
      tactics = createDefaultTactics(members);
      status?.('프리셋 적용: [편성 순서대로 발동]');
    }

    saveTactics();
  }

  function movePriority(stage, id, direction) {
    const list = tactics.priority[`stage${stage}`];
    const idx = list.indexOf(id);
    if (idx < 0) return;
    const targetIdx = idx + direction;
    if (targetIdx < 0 || targetIdx >= list.length) return;

    const temp = list[idx];
    list[idx] = list[targetIdx];
    list[targetIdx] = temp;

    if (stage === 3 && tactics.stage3Mode === 'alternate') {
      tactics.burst3Rotation = [...tactics.priority.stage3];
    }

    saveTactics();
  }

  function toggleAllow(id, allowed) {
    tactics.allowlist[id] = allowed;
    saveTactics();
  }

  function render(containerId = 'burst-tactics-container') {
    const container = $(containerId);
    if (!container) return;

    loadTactics();
    const members = getMembersWithMeta();
    const audit = auditBurstTactics(members, tactics);

    // Diagnostics banner
    let alertHtml = '';
    const allIssues = [...audit.issues];
    if (isServerStale) {
      allIssues.push({ code: 'server_stale', level: 'warning', message: '서버에 저장된 전술 설정의 편성과 현재 편성이 다릅니다 (Stale).' });
    }
    if (allIssues.length > 0) {
      alertHtml = `<div class="tactic-alerts" role="alert">
        ${allIssues.map(i => `<div class="tactic-alert-item ${i.level}"><span class="badge ${i.level}">${i.level === 'error' ? '오류' : '주의'}</span> <span>${esc(i.message)}</span></div>`).join('')}
      </div>`;
    }

    // Clean stale button if stale IDs exist
    const staleActionHtml = audit.staleIds?.length > 0 ? `
      <button type="button" id="btn-clean-stale" class="ghost small-btn">제외된 니케 설정 정리 (${audit.staleIds.length}명)</button>
    ` : '';

    // Server status badge
    let serverBadgeHtml = '';
    if (serverSyncStatus === 'saved') {
      serverBadgeHtml = '<span class="status-pill green">서버 저장 완료 (PUT v1)</span>';
    } else if (serverSyncStatus === 'saving') {
      serverBadgeHtml = '<span class="status-pill cyan">서버 저장 중…</span>';
    } else if (serverSyncStatus === 'draft_incomplete') {
      serverBadgeHtml = '<span class="status-pill warning">초안 저장 (단계 미완성)</span>';
    } else if (serverSyncStatus === 'stale') {
      serverBadgeHtml = '<span class="status-pill warning">편성 변경 불일치 (Stale)</span>';
    } else {
      serverBadgeHtml = '<span class="status-pill neutral">로컬 임시 보존 (서버 미동기화)</span>';
    }

    // Stages 1, 2, 3 cards
    const stagesHtml = [1, 2, 3].map(stage => {
      const stageName = ['I', 'II', 'III'][stage - 1];
      const stageMembers = members.filter(m => m.burstStep === stage);
      const priorityList = (tactics.priority[`stage${stage}`] ?? []).filter(id => stageMembers.some(m => m.id === id));
      for (const m of stageMembers) {
        if (!priorityList.includes(m.id)) priorityList.push(m.id);
      }

      const rowsHtml = priorityList.map((id, index) => {
        const item = stageMembers.find(m => m.id === id);
        const isAllowed = tactics.allowlist[id] !== false;
        const isFirst = index === 0;
        const isLast = index === priorityList.length - 1;

        return `
          <div class="tactic-nikke-row ${isAllowed ? '' : 'disabled-row'}">
            <label class="allow-label">
              <input type="checkbox" data-tactic-allow="${id}" ${isAllowed ? 'checked' : ''}>
              <span class="nikke-name">${esc(item?.displayName || id)}</span>
            </label>
            <div class="priority-badges">
              <span class="rank-pill">${index + 1}순위</span>
              ${!isAllowed ? '<span class="status-pill warning">발동 제외</span>' : ''}
              ${stage === 3 && tactics.firstCaster === id ? '<span class="status-pill cyan">첫 시전자</span>' : ''}
            </div>
            <div class="priority-buttons">
              <button type="button" class="ghost-icon-btn" data-move-stage="${stage}" data-move-id="${id}" data-move-dir="-1" ${isFirst ? 'disabled' : ''} title="순위 올리기">▲</button>
              <button type="button" class="ghost-icon-btn" data-move-stage="${stage}" data-move-id="${id}" data-move-dir="1" ${isLast ? 'disabled' : ''} title="순위 내리기">▼</button>
            </div>
          </div>
        `;
      }).join('');

      return `
        <div class="tactic-stage-card">
          <div class="stage-header">
            <h4>버스트 ${stageName}단계</h4>
            <span class="stage-count">${stageMembers.length}명 편성</span>
          </div>
          <div class="stage-members-list">
            ${rowsHtml || '<p class="empty-hint">편성된 니케가 없습니다.</p>'}
          </div>
        </div>
      `;
    }).join('');

    container.innerHTML = `
      <div class="tactic-manager-shell">
        <div class="tactic-header-bar">
          <div>
            <h4>버스트 사용 니케 및 순서 설정</h4>
            <p class="microcopy">체크한 니케만 버스트를 사용합니다. III단계는 위에서부터 순환하며, 준비되지 않으면 다음 사용 가능한 니케가 발동합니다.</p>
          </div>
          <div class="tactic-presets">
            <span class="preset-label">빠른 설정:</span>
            <button type="button" class="ghost small-btn" id="preset-alice-only" title="앨리스만 발동하고 다른 3버스트 니케는 제외합니다">앨리스만 사용</button>
            <button type="button" class="ghost small-btn" id="preset-alice-first" title="앨리스를 1순위로 교대 순환합니다">앨리스 우선</button>
            <button type="button" class="ghost small-btn" id="preset-formation">편성 순서대로</button>
            <button type="button" class="primary small-btn" id="btn-force-save-server" title="현재 설정을 백엔드 서버에 저장합니다">서버에 저장</button>
            ${staleActionHtml}
          </div>
        </div>

        <div class="status-badges-row">
          ${serverBadgeHtml}
          <span class="status-pill neutral">외부 규격 v1 (B1/E1 매핑 완료)</span>
        </div>

        ${alertHtml}

        <div class="tactic-stages-grid">
          ${stagesHtml}
        </div>

      </div>
    `;

    // Event listeners
    container.querySelectorAll('[data-tactic-allow]').forEach(cb => {
      cb.onchange = e => toggleAllow(cb.dataset.tacticAllow, e.target.checked);
    });

    container.querySelectorAll('[data-move-stage]').forEach(btn => {
      btn.onclick = () => {
        const stage = Number(btn.dataset.moveStage);
        const id = btn.dataset.moveId;
        const dir = Number(btn.dataset.moveDir);
        movePriority(stage, id, dir);
      };
    });

    const btnAliceOnly = $('preset-alice-only');
    if (btnAliceOnly) btnAliceOnly.onclick = () => applyPreset('alice_only');

    const btnAliceFirst = $('preset-alice-first');
    if (btnAliceFirst) btnAliceFirst.onclick = () => applyPreset('alice_first');

    const btnFormation = $('preset-formation');
    if (btnFormation) btnFormation.onclick = () => applyPreset('formation_order');

    const btnSaveServer = $('btn-force-save-server');
    if (btnSaveServer) btnSaveServer.onclick = () => saveTactics();

    const btnCleanStale = $('btn-clean-stale');
    if (btnCleanStale) {
      btnCleanStale.onclick = () => {
        const memberIds = new Set(members.map(m => m.id));
        for (const k of Object.keys(tactics.allowlist)) {
          if (!memberIds.has(k)) delete tactics.allowlist[k];
        }
        for (const s of [1, 2, 3]) {
          tactics.priority[`stage${s}`] = tactics.priority[`stage${s}`].filter(id => memberIds.has(id));
        }
        if (!memberIds.has(tactics.firstCaster)) {
          tactics.firstCaster = members.find(m => m.burstStep === 3)?.id || null;
        }
        saveTactics();
        status?.('제외된 니케 설정을 정리했습니다.');
      };
    }
  }

  /**
   * Renders side-by-side comparison between user tactics and actual simulation timeline.
   */
  function renderTimelineComparison(targetElement, fullBursts, membersWithMeta) {
    if (!targetElement) return;
    if (!fullBursts || !fullBursts.length) {
      targetElement.innerHTML = '<p class="empty-hint">버스트 실행 이력이 없습니다.</p>';
      return;
    }

    const nameMap = new Map(membersWithMeta.map(m => [m.id, m.displayName]));
    const rows = fullBursts.map((fb, idx) => {
      const casterName = nameMap.get(fb.caster) ?? fb.caster;
      return `
        <tr>
          <td>${fb.cycle || idx + 1}회차</td>
          <td><strong>${esc(casterName)}</strong></td>
          <td>${fb.startFrame ? (fb.startFrame / 60).toFixed(1) + '초' : '—'}</td>
          <td>${fb.endFrame ? (fb.endFrame / 60).toFixed(1) + '초' : '—'}</td>
        </tr>
      `;
    }).join('');

    targetElement.innerHTML = `
      <div class="tactic-comparison-box surface">
        <h4>실제 버스트 발동 기록</h4>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>회차</th>
                <th>발동 니케 (버스트 III)</th>
                <th>풀버스트 시작</th>
                <th>풀버스트 종료</th>
              </tr>
            </thead>
            <tbody>
              ${rows}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  return {
    loadTactics,
    saveTactics,
    syncFromServer,
    getServerStatus: () => ({ status: serverSyncStatus, message: serverMessage, isStale: isServerStale }),
    getTactics: () => tactics || loadTactics(),
    render,
    renderTimelineComparison
  };
}

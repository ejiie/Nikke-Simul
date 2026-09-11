/**
 * Burst Tactics Configuration Component
 *
 * Allows users to configure:
 * - Burst allowlist (used Nikkes) vs excluded Nikkes
 * - Clear distinction between "Alice First (우선)" and "Alice Only (전용)"
 * - Per-stage candidate priority order (I, II, III)
 * - Stage III rotation policy (Alternate vs Priority-only) and First Caster
 * - Fallback policy (wait_preferred vs next_ready)
 * - Saving & restoring configuration per account/formation
 * - Cross-comparison of actual burst timeline vs user tactic settings
 */

import { auditBurstTactics, createDefaultTactics } from './damage-log-adapter.js';

const $ = id => document.getElementById(id);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export function createBurstTacticsManager({ getSnapshot, getMembersWithMeta, onTacticsChanged, status }) {
  let tactics = null;
  let lastAccount = null;

  function storageKey(accountId) {
    return `nikke-burst-tactics-${accountId || 'default'}`;
  }

  function loadTactics() {
    const account = getSnapshot()?.accountId ?? 'local';
    const members = getMembersWithMeta();
    if (!members.length) {
      tactics = createDefaultTactics([]);
      return tactics;
    }

    try {
      const raw = localStorage.getItem(storageKey(account));
      if (raw) {
        tactics = JSON.parse(raw);
      }
    } catch {
      tactics = null;
    }

    if (!tactics || tactics.version !== 2) {
      tactics = createDefaultTactics(members);
    } else {
      // Ensure all current formation members exist in allowlist
      for (const m of members) {
        if (tactics.allowlist[m.id] === undefined) {
          tactics.allowlist[m.id] = true;
        }
      }
      // Ensure stage priority arrays include new members
      for (const m of members) {
        const stageKey = `stage${m.burstStep}`;
        if (tactics.priority?.[stageKey] && !tactics.priority[stageKey].includes(m.id)) {
          tactics.priority[stageKey].push(m.id);
        }
      }
    }

    lastAccount = account;
    return tactics;
  }

  function saveTactics() {
    const account = getSnapshot()?.accountId ?? 'local';
    try {
      localStorage.setItem(storageKey(account), JSON.stringify(tactics));
      status?.('버스트 전술 설정을 저장했습니다.');
    } catch (e) {
      status?.(`설정 저장 실패: ${e.message}`);
    }
    if (onTacticsChanged) onTacticsChanged(tactics);
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
      status?.('프리셋 적용: [앨리스 우선순위 1위 + 교대 순환]');
    } else if (presetType === 'formation_order') {
      tactics = createDefaultTactics(members);
      status?.('프리셋 적용: [편성 순서대로 발동]');
    }

    saveTactics();
    render();
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

    saveTactics();
    render();
  }

  function toggleAllow(id, allowed) {
    tactics.allowlist[id] = allowed;
    saveTactics();
    render();
  }

  function render(containerId = 'burst-tactics-container') {
    const container = $(containerId);
    if (!container) return;

    loadTactics();
    const members = getMembersWithMeta();
    const audit = auditBurstTactics(members, tactics);

    // Diagnostics banner
    let alertHtml = '';
    if (audit.issues.length > 0) {
      alertHtml = `<div class="tactic-alerts" role="alert">
        ${audit.issues.map(i => `<div class="tactic-alert-item ${i.level}"><span class="badge ${i.level}">${i.level === 'error' ? '오류' : '주의'}</span> <span>${esc(i.message)}</span></div>`).join('')}
      </div>`;
    }

    // Clean stale button if stale IDs exist
    const staleActionHtml = audit.staleIds?.length > 0 ? `
      <button type="button" id="btn-clean-stale" class="ghost small-btn">제외된 니케 설정 정리 (${audit.staleIds.length}명)</button>
    ` : '';

    // Stages 1, 2, 3 cards
    const stagesHtml = [1, 2, 3].map(stage => {
      const stageName = ['I', 'II', 'III'][stage - 1];
      const stageMembers = members.filter(m => m.burstStep === stage);
      const priorityList = (tactics.priority[`stage${stage}`] ?? []).filter(id => stageMembers.some(m => m.id === id));
      // Append any members not yet in priorityList
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

    // Stage 3 specific rotation options
    const stage3Members = members.filter(m => m.burstStep === 3 && tactics.allowlist[m.id] !== false);
    const firstCasterOptions = stage3Members.map(m => `
      <option value="${m.id}" ${tactics.firstCaster === m.id ? 'selected' : ''}>${esc(m.displayName)} (버스트 III)</option>
    `).join('');

    container.innerHTML = `
      <div class="tactic-manager-shell">
        <div class="tactic-header-bar">
          <div>
            <h4>버스트 사용 니케 및 순서 설정</h4>
            <p class="microcopy">각 단계별 발동 허용 니케(Allowlist)와 우선순위, 순환 방식을 설정합니다.</p>
          </div>
          <div class="tactic-presets">
            <span class="preset-label">빠른 설정:</span>
            <button type="button" class="ghost small-btn" id="preset-alice-only" title="앨리스만 발동하고 다른 3버스트 니케는 제외합니다">앨리스만 사용</button>
            <button type="button" class="ghost small-btn" id="preset-alice-first" title="앨리스를 1순위로 교대 순환합니다">앨리스 우선</button>
            <button type="button" class="ghost small-btn" id="preset-formation">편성 순서대로</button>
            ${staleActionHtml}
          </div>
        </div>

        ${alertHtml}

        <div class="tactic-stages-grid">
          ${stagesHtml}
        </div>

        <div class="tactic-options-grid">
          <label>
            <span>버스트 III 순환 정책</span>
            <select id="tactic-stage3-mode">
              <option value="alternate" ${tactics.stage3Mode === 'alternate' ? 'selected' : ''}>교대 순환 (1순위 ↔ 2순위 교대)</option>
              <option value="priority_only" ${tactics.stage3Mode === 'priority_only' ? 'selected' : ''}>우선순위 고정 (항상 최우선 니케 우선)</option>
            </select>
          </label>
          <label>
            <span>버스트 III 첫 시전자</span>
            <select id="tactic-first-caster">
              ${firstCasterOptions || '<option value="">허용된 니케 없음</option>'}
            </select>
          </label>
          <label>
            <span>우선 니케 미준비(쿨다운) 시</span>
            <select id="tactic-fallback-policy">
              <option value="next_ready" ${tactics.fallbackPolicy === 'next_ready' ? 'selected' : ''}>사용 가능한 다음 니케 발동 (제외 니케는 미발동)</option>
              <option value="wait_preferred" ${tactics.fallbackPolicy === 'wait_preferred' ? 'selected' : ''}>우선 니케 쿨다운 대기 (지연 감수)</option>
            </select>
          </label>
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

    const modeSel = $('tactic-stage3-mode');
    if (modeSel) modeSel.onchange = e => { tactics.stage3Mode = e.target.value; saveTactics(); render(); };

    const firstSel = $('tactic-first-caster');
    if (firstSel) firstSel.onchange = e => { tactics.firstCaster = e.target.value; saveTactics(); render(); };

    const fallbackSel = $('tactic-fallback-policy');
    if (fallbackSel) fallbackSel.onchange = e => { tactics.fallbackPolicy = e.target.value; saveTactics(); render(); };

    const btnAliceOnly = $('preset-alice-only');
    if (btnAliceOnly) btnAliceOnly.onclick = () => applyPreset('alice_only');

    const btnAliceFirst = $('preset-alice-first');
    if (btnAliceFirst) btnAliceFirst.onclick = () => applyPreset('alice_first');

    const btnFormation = $('preset-formation');
    if (btnFormation) btnFormation.onclick = () => applyPreset('formation_order');

    const btnCleanStale = $('btn-clean-stale');
    if (btnCleanStale) {
      btnCleanStale.onclick = () => {
        const memberIds = new Set(members.map(m => m.id));
        // Remove stale from allowlist
        for (const k of Object.keys(tactics.allowlist)) {
          if (!memberIds.has(k)) delete tactics.allowlist[k];
        }
        // Remove stale from priority lists
        for (const s of [1, 2, 3]) {
          tactics.priority[`stage${s}`] = tactics.priority[`stage${s}`].filter(id => memberIds.has(id));
        }
        if (!memberIds.has(tactics.firstCaster)) {
          tactics.firstCaster = members.find(m => m.burstStep === 3)?.id || null;
        }
        saveTactics();
        render();
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
    const stage3Priority = tactics?.priority?.stage3 ?? [];

    const rows = fullBursts.map((fb, idx) => {
      const casterName = nameMap.get(fb.caster) ?? fb.caster;
      const rank = stage3Priority.indexOf(fb.caster);
      const isExpected = (tactics.stage3Mode === 'alternate')
        ? (idx % 2 === 0 ? fb.caster === tactics.firstCaster : fb.caster !== tactics.firstCaster)
        : (rank === 0);

      const statusBadge = isExpected
        ? '<span class="status-pill neutral">설정 일치</span>'
        : '<span class="status-pill warning">대체/대기 발생</span>';

      return `
        <tr>
          <td>${fb.cycle || idx + 1}회차</td>
          <td><strong>${esc(casterName)}</strong></td>
          <td>${fb.startFrame ? (fb.startFrame / 60).toFixed(1) + '초' : '—'}</td>
          <td>${fb.endFrame ? (fb.endFrame / 60).toFixed(1) + '초' : '—'}</td>
          <td>${statusBadge}</td>
        </tr>
      `;
    }).join('');

    targetElement.innerHTML = `
      <div class="tactic-comparison-box surface">
        <h4>실제 버스트 발동 vs 설정 대조</h4>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>회차</th>
                <th>발동 니케 (버스트 III)</th>
                <th>풀버스트 시작</th>
                <th>풀버스트 종료</th>
                <th>설정 대조 판정</th>
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
    getTactics: () => tactics || loadTactics(),
    render,
    renderTimelineComparison
  };
}

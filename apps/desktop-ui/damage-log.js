/**
 * Detailed Per-Shot Damage Log & Interactive Timeline Graph Component (U2 Edition)
 *
 * Conforms to:
 * - Backend contract: docs/damage-log-api-contract.ko.md (bf19679)
 * - Engine contract: docs/damage-log-engine-contract.ko.md (908047f)
 *
 * Features:
 * - Default selection of Alice (5004), switchable to any formation Nikke
 * - Distinct handling of:
 *   * Collected real log (수집 완료)
 *   * Uncollected / legacy replay (미수집 상태)
 *   * Zero damage (피해 0)
 *   * Truncated (로그 상한 도달)
 *   * Explicit synthetic mock preview (사용자가 명시적으로 선택 시에만 로드)
 * - Clear distinction between Shot Count (발사 수) and Hit Count (명중 수)
 * - Interactive SVG time-series graph with clear distinction between:
 *   * Self Burst Active windows (자체 버스트 효과 구간)
 *   * Team Full Burst windows (팀 풀버스트 구간)
 *   * Overlapping windows
 * - Cumulative damage tracking
 * - Detailed table with interactive filters (burst window, charge status, crit, core)
 * - Calculation audit inspection (base atk, buffs, enemy def, multipliers, rounding policy)
 * - Server-first JSON and CSV export with local fallback
 * - 180s engine limit and provisional accuracy notice
 */

import {
  fetchDamageLog,
  exportDamageLogToJson,
  exportDamageLogToCsv,
  DAMAGE_LOG_PROVISIONAL_NOTICE
} from './damage-log-adapter.js';

const $ = id => document.getElementById(id);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const num = v => v == null ? '—' : Number(v).toLocaleString('ko-KR');

export function createDamageLogViewer({ api, getSnapshot, getMembersWithMeta, getToken, status }) {
  let activeReplay = null;
  let activeLogData = null;
  let logStatus = 'idle'; // 'idle' | 'collected' | 'uncollected' | 'no_damage'
  let logMessage = '';
  let isMockMode = false;
  let isTruncated = false;
  let selectedCharacterId = '5004';
  let filterBurst = 'all'; // all | self_only | team_only | both | none
  let filterHitType = 'all'; // all | full_charge | non_full_charge | crit | core
  let minDamageFilter = 0;
  let selectedHit = null;

  async function loadForCharacter(characterId, allowMock = false) {
    selectedCharacterId = characterId;
    selectedHit = null;
    if (!activeReplay) return;

    status?.('발당 피해 로그를 불러오는 중…');
    const members = getMembersWithMeta();
    const result = await fetchDamageLog(api, activeReplay.id, selectedCharacterId, activeReplay, members, { allowMock });

    logStatus = result.status;
    isMockMode = result.isMock;
    isTruncated = result.truncated;
    logMessage = result.message || '';
    activeLogData = result.log;

    render();

    if (result.status === 'collected') {
      status?.(result.isMock ? '합성 검증용 피해 로그가 준비되었습니다 (Mock).' : '실제 피해 로그를 불러왔습니다.');
    } else if (result.status === 'uncollected') {
      status?.(logMessage || '피해 로그가 수집되지 않은 리플레이입니다.');
    } else if (result.status === 'no_damage') {
      status?.('해당 니케의 피해 기록이 0입니다.');
    }
  }

  function setReplay(replay) {
    activeReplay = replay;
    const members = getMembersWithMeta();
    const embeddedChar = replay?.result?.damageLog?.characterId;
    if (embeddedChar && members.some(m => m.id === embeddedChar)) {
      selectedCharacterId = embeddedChar;
    } else {
      const hasAlice = members.some(m => m.id === '5004');
      selectedCharacterId = hasAlice ? '5004' : (members[0]?.id ?? '5004');
    }
    // Default: try real log first, do not force mock
    loadForCharacter(selectedCharacterId, false);
  }

  function render(containerId = 'damage-log-container') {
    const container = $(containerId);
    if (!container) return;

    if (!activeReplay) {
      container.innerHTML = `
        <div class="surface empty-state">
          대미지 검산을 실행하면 선택한 니케의 시간별 발당 피해 그래프와 검산 근거가 표시됩니다.
        </div>
      `;
      return;
    }

    const members = getMembersWithMeta();
    const currentMember = members.find(m => m.id === selectedCharacterId);
    const memberName = currentMember?.displayName || (selectedCharacterId === '5004' ? '앨리스' : selectedCharacterId);

    const nikkeOptions = members.map(m => `
      <option value="${m.id}" ${m.id === selectedCharacterId ? 'selected' : ''}>
        ${esc(m.displayName)} (${m.burstStep ? `버스트 ${['I', 'II', 'III'][m.burstStep - 1]}` : ''})
      </option>
    `).join('');

    // If uncollected or no_damage and not in mock mode:
    if (logStatus === 'uncollected' && !activeLogData) {
      container.innerHTML = `
        <section class="surface damage-log-section">
          <div class="damage-log-topbar">
            <div>
              <h3>시간별 발당 피해 분석 & 검산</h3>
              <p class="microcopy">180초 동안의 타격별 피해, 버스트 효과 구간, 계산 근거를 확인합니다.</p>
            </div>
            <div class="topbar-controls">
              <label class="nikke-select-label">
                <span>대상 니케:</span>
                <select id="log-character-select">${nikkeOptions}</select>
              </label>
            </div>
          </div>
          <div class="status-badges-row">
            <span class="status-pill warning">로그 미수집 상태 (서버 E1/B1 연동 대기)</span>
            <span class="status-pill neutral">Replay ID: ${esc(activeReplay.id)}</span>
          </div>
          <div class="surface empty-state" style="padding:24px;text-align:center;">
            <p><strong>${esc(memberName)}</strong>의 시간별 발당 피해 로그가 서버에 저장되어 있지 않습니다.</p>
            <p class="microcopy">${esc(logMessage)}</p>
            <div style="margin-top:16px;">
              <button type="button" class="primary small-btn" id="btn-load-mock-preview">합성 Mock 미리보기 (UI 검증용)</button>
            </div>
          </div>
        </section>
      `;
      $('log-character-select').onchange = e => loadForCharacter(e.target.value, false);
      const btnMock = $('btn-load-mock-preview');
      if (btnMock) btnMock.onclick = () => loadForCharacter(selectedCharacterId, true);
      return;
    }

    if (logStatus === 'no_damage' && (!activeLogData || activeLogData.totalHits === 0)) {
      container.innerHTML = `
        <section class="surface damage-log-section">
          <div class="damage-log-topbar">
            <div>
              <h3>시간별 발당 피해 분석 & 검산</h3>
              <p class="microcopy">180초 동안의 타격별 피해, 버스트 효과 구간, 계산 근거를 확인합니다.</p>
            </div>
            <div class="topbar-controls">
              <label class="nikke-select-label">
                <span>대상 니케:</span>
                <select id="log-character-select">${nikkeOptions}</select>
              </label>
            </div>
          </div>
          <div class="status-badges-row">
            <span class="status-pill neutral">피해 기록 0 (No Damage)</span>
          </div>
          <div class="surface empty-state" style="padding:24px;text-align:center;">
            <p><strong>${esc(memberName)}</strong>는 전투 중 발생한 피해가 없습니다 (총 피해량: 0).</p>
          </div>
        </section>
      `;
      $('log-character-select').onchange = e => loadForCharacter(e.target.value, false);
      return;
    }

    // Collected / Mock log display
    const hits = activeLogData?.hits || [];
    const critCount = hits.filter(h => h.isCritical).length;
    const coreCount = hits.filter(h => h.isCore).length;
    const fullChargeCount = hits.filter(h => h.isFullCharge).length;
    const avgDamage = hits.length ? Math.round((activeLogData.totalDamage || 0) / hits.length) : 0;

    // Distinguish Shots vs Hits (direct skill hits without shotId are not counted as fired shots)
    const uniqueShots = new Set(hits.map(h => h.shotId).filter(v => v !== null && v !== undefined)).size;

    const graphSvg = generateGraphSvg(activeLogData);

    const filteredHits = hits.filter(h => {
      if (minDamageFilter > 0 && h.damage < minDamageFilter) return false;
      if (filterBurst === 'self_only' && (!h.isSelfBurstActive || h.isTeamFullBurst)) return false;
      if (filterBurst === 'team_only' && (!h.isTeamFullBurst || h.isSelfBurstActive)) return false;
      if (filterBurst === 'both' && (!h.isSelfBurstActive || !h.isTeamFullBurst)) return false;
      if (filterBurst === 'none' && (h.isSelfBurstActive || h.isTeamFullBurst)) return false;

      if (filterHitType === 'full_charge' && !h.isFullCharge) return false;
      if (filterHitType === 'non_full_charge' && h.isFullCharge) return false;
      if (filterHitType === 'crit' && !h.isCritical) return false;
      if (filterHitType === 'core' && !h.isCore) return false;
      return true;
    });

    const rowsHtml = filteredHits.slice(0, 100).map(h => {
      const isSelected = selectedHit?.hitId === h.hitId;
      return `
        <tr class="${isSelected ? 'selected-row' : ''}" data-hit-id="${h.hitId}">
          <td>${h.seconds}초 <small>(${h.frame}F)</small></td>
          <td>#${h.shotId ?? '—'} <small>(Hit #${h.hitId})</small></td>
          <td><strong>${num(h.damage)}</strong></td>
          <td>${num(h.cumulativeDamage)}</td>
          <td>${h.isFullCharge ? '<span class="pill-badge green">풀차지</span>' : '<span class="pill-badge gray">비풀차지</span>'}</td>
          <td>
            ${h.isCritical ? '<span class="pill-badge red">크리</span>' : ''}
            ${h.isCore ? '<span class="pill-badge yellow">코어</span>' : ''}
            ${!h.isCritical && !h.isCore ? '<span class="text-muted">일반</span>' : ''}
          </td>
          <td>
            ${h.isSelfBurstActive ? '<span class="pill-badge amber">자체 버스트</span>' : ''}
            ${h.isTeamFullBurst ? '<span class="pill-badge cyan">팀 풀버스트</span>' : ''}
            ${!h.isSelfBurstActive && !h.isTeamFullBurst ? '<span class="text-muted">—</span>' : ''}
          </td>
          <td><button type="button" class="ghost small-btn" data-view-audit="${h.hitId}">근거 보기</button></td>
        </tr>
      `;
    }).join('');

    let auditHtml = '';
    if (selectedHit) {
      const a = selectedHit.audit;
      auditHtml = `
        <div class="damage-audit-panel surface">
          <div class="audit-header">
            <h4>발당 피해 검산 근거 (타격 #${selectedHit.hitId} · 발사 #${selectedHit.shotId ?? '—'} · ${selectedHit.seconds}초)</h4>
            <button type="button" class="ghost-close-btn" id="btn-close-audit">✕</button>
          </div>
          <div class="audit-stats-grid">
            <div class="audit-stat-card">
              <span class="audit-label">기초 공격력 (Base ATK)</span>
              <strong class="audit-val">${num(a?.baseAtk)}</strong>
            </div>
            <div class="audit-stat-card">
              <span class="audit-label">버프 적용 공격력 (Buffed ATK)</span>
              <strong class="audit-val text-cyan">${num(a?.buffedAtk)}</strong>
            </div>
            <div class="audit-stat-card">
              <span class="audit-label">적 방어력 (Target DEF)</span>
              <strong class="audit-val">${num(a?.effectiveDefense)}</strong>
            </div>
            <div class="audit-stat-card">
              <span class="audit-label">공방차 (ATK - DEF)</span>
              <strong class="audit-val text-green">${num(a?.statDiff)}</strong>
            </div>
            <div class="audit-stat-card">
              <span class="audit-label">스킬 계수</span>
              <strong class="audit-val">${(a?.skillMultiplier * 100).toFixed(1)}%</strong>
            </div>
            <div class="audit-stat-card">
              <span class="audit-label">차지 배율</span>
              <strong class="audit-val">${a?.chargeMultiplier}x</strong>
            </div>
            <div class="audit-stat-card">
              <span class="audit-label">크리티컬 배율</span>
              <strong class="audit-val">${a?.critMultiplier}x</strong>
            </div>
            <div class="audit-stat-card">
              <span class="audit-label">코어 타격 배율</span>
              <strong class="audit-val">${a?.coreMultiplier}x</strong>
            </div>
            <div class="audit-stat-card">
              <span class="audit-label">팀 풀버스트 보너스</span>
              <strong class="audit-val">${a?.fullBurstMultiplier}x</strong>
            </div>
            <div class="audit-stat-card">
              <span class="audit-label">정수화 정책</span>
              <strong class="audit-val font-mono">${esc(a?.roundingPolicy)}</strong>
            </div>
          </div>
          <div class="audit-buffs-box">
            <h5>적용된 버프 목록 (${a?.activeBuffs?.length ?? 0}건)</h5>
            <ul>
              ${(a?.activeBuffs ?? []).map(b => `
                <li><strong>${esc(b.source)}</strong>: ${esc(b.type)} +${Math.round(b.value * 100)}% ${b.remainingFrames ? `(잔여 ${b.remainingFrames}F)` : '(상시)'}</li>
              `).join('')}
            </ul>
          </div>
          <p class="audit-formula-hint">
            산식: <code>(버프적용공격력 - 방어력) × 계수 × 차지배율 × 크리배율 × 코어배율 × 풀버스트배율</code> 후 정수화 정책 적용
          </p>
        </div>
      `;
    }

    container.innerHTML = `
      <section class="surface damage-log-section">
        <div class="damage-log-topbar">
          <div>
            <h3>시간별 발당 피해 분석 & 검산</h3>
            <p class="microcopy">180초 동안의 타격별 피해, 버스트 효과 구간, 계산 근거를 확인합니다.</p>
          </div>
          <div class="topbar-controls">
            <label class="nikke-select-label">
              <span>대상 니케:</span>
              <select id="log-character-select">${nikkeOptions}</select>
            </label>
            <div class="export-buttons">
              <button type="button" class="ghost small-btn" id="btn-export-csv">CSV 내보내기</button>
              <button type="button" class="ghost small-btn" id="btn-export-json">JSON 내보내기</button>
            </div>
          </div>
        </div>

        <div class="status-badges-row">
          <span class="status-pill cyan">180초 엔진 한도 준수</span>
          <span class="status-pill warning">${DAMAGE_LOG_PROVISIONAL_NOTICE}</span>
          ${isMockMode ? '<span class="status-pill neutral">합성 Mock Fixture (명시적 미리보기)</span>' : '<span class="status-pill green">서버 로그 연동 (schema v1)</span>'}
          ${isTruncated ? '<span class="status-pill red">로그 상한 도달 (잘림 발생)</span>' : ''}
        </div>

        <div class="summary-metrics-grid">
          <div class="metric-card">
            <span>${esc(memberName)} 총 피해</span>
            <strong>${num(activeLogData.totalDamage)}</strong>
          </div>
          <div class="metric-card">
            <span>발사 / 명중 횟수</span>
            <strong>${num(uniqueShots)}회 발사 / ${num(hits.length)}회 명중</strong>
          </div>
          <div class="metric-card">
            <span>평균 발당 피해</span>
            <strong>${num(avgDamage)}</strong>
          </div>
          <div class="metric-card">
            <span>크리티컬 / 코어율</span>
            <strong>${hits.length ? Math.round(critCount / hits.length * 100) : 0}% / ${hits.length ? Math.round(coreCount / hits.length * 100) : 0}%</strong>
          </div>
          <div class="metric-card">
            <span>풀차지 비율</span>
            <strong>${hits.length ? Math.round(fullChargeCount / hits.length * 100) : 0}%</strong>
          </div>
        </div>

        <div class="graph-legend-bar">
          <span class="legend-item"><span class="color-box self-burst"></span> 자체 버스트 활성 구간</span>
          <span class="legend-item"><span class="color-box team-burst"></span> 팀 풀버스트 구간</span>
          <span class="legend-item"><span class="color-box overlap-burst"></span> 두 효과 중첩 구간</span>
          <span class="legend-item"><span class="dot-sample crit"></span> 크리티컬</span>
          <span class="legend-item"><span class="dot-sample normal"></span> 일반</span>
        </div>

        <div class="damage-graph-container" id="damage-graph-shell">
          ${graphSvg}
          <div id="graph-tooltip" class="graph-tooltip" hidden></div>
        </div>

        ${auditHtml}

        <div class="log-filter-bar">
          <div class="filter-group">
            <span class="filter-title">버스트 구간:</span>
            <button type="button" class="filter-chip ${filterBurst === 'all' ? 'active' : ''}" data-filter-burst="all">전체</button>
            <button type="button" class="filter-chip ${filterBurst === 'self_only' ? 'active' : ''}" data-filter-burst="self_only">자체 버스트만</button>
            <button type="button" class="filter-chip ${filterBurst === 'team_only' ? 'active' : ''}" data-filter-burst="team_only">팀 풀버스트만</button>
            <button type="button" class="filter-chip ${filterBurst === 'both' ? 'active' : ''}" data-filter-burst="both">중첩 구간만</button>
            <button type="button" class="filter-chip ${filterBurst === 'none' ? 'active' : ''}" data-filter-burst="none">비버스트 평타</button>
          </div>
          <div class="filter-group">
            <span class="filter-title">타격 종류:</span>
            <button type="button" class="filter-chip ${filterHitType === 'all' ? 'active' : ''}" data-filter-hit="all">전체</button>
            <button type="button" class="filter-chip ${filterHitType === 'full_charge' ? 'active' : ''}" data-filter-hit="full_charge">풀차지</button>
            <button type="button" class="filter-chip ${filterHitType === 'non_full_charge' ? 'active' : ''}" data-filter-hit="non_full_charge">비풀차지</button>
            <button type="button" class="filter-chip ${filterHitType === 'crit' ? 'active' : ''}" data-filter-hit="crit">크리티컬</button>
            <button type="button" class="filter-chip ${filterHitType === 'core' ? 'active' : ''}" data-filter-hit="core">코어 명중</button>
          </div>
        </div>

        <div class="table-scroll log-table-shell">
          <table>
            <thead>
              <tr>
                <th>시간</th>
                <th>발사 / Hit</th>
                <th>발당 피해</th>
                <th>누적 피해</th>
                <th>차지 상태</th>
                <th>판정</th>
                <th>버스트 효과</th>
                <th>검산 근거</th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml || '<tr><td colspan="8" class="empty-hint">조건에 일치하는 타격이 없습니다.</td></tr>'}
            </tbody>
          </table>
        </div>
        ${filteredHits.length > 100 ? `<p class="microcopy text-center">성능을 위해 상위 100건을 표시 중입니다. (전체 ${filteredHits.length}건은 CSV/JSON 내보내기로 확인 가능합니다)</p>` : ''}
      </section>
    `;

    $('log-character-select').onchange = e => loadForCharacter(e.target.value, isMockMode);

    container.querySelectorAll('[data-filter-burst]').forEach(btn => {
      btn.onclick = () => { filterBurst = btn.dataset.filterBurst; render(); };
    });

    container.querySelectorAll('[data-filter-hit]').forEach(btn => {
      btn.onclick = () => { filterHitType = btn.dataset.filterHit; render(); };
    });

    container.querySelectorAll('[data-view-audit]').forEach(btn => {
      btn.onclick = () => {
        const hitId = Number(btn.dataset.viewAudit);
        selectedHit = activeLogData.hits.find(h => h.hitId === hitId);
        render();
        $('btn-close-audit')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      };
    });

    const btnCloseAudit = $('btn-close-audit');
    if (btnCloseAudit) btnCloseAudit.onclick = () => { selectedHit = null; render(); };

    // Export handlers with raw server endpoint response Blob download
    $('btn-export-json').onclick = async () => {
      if (!isMockMode && api && activeReplay?.id) {
        try {
          const token = (typeof getToken === 'function' ? getToken() : (api?.token || ''));
          const headers = token ? { 'X-Nikke-Token': token } : {};
          const res = await fetch(`/api/runtime/skill-replays/${activeReplay.id}/damage-log/export.json`, { headers });
          if (res.ok) {
            const blob = await res.blob();
            downloadBlob(blob, `server-damage-log-${selectedCharacterId}-${Date.now()}.json`, 'application/json');
            status?.('서버 원본 JSON 로그를 내보냈습니다.');
            return;
          }
          const errText = await res.text().catch(() => '');
          throw new Error(`서버 로그 내보내기 실패 (${res.status}): ${errText}`);
        } catch (err) {
          status?.(err.message || 'JSON 내보내기 실패');
          return;
        }
      }

      const json = exportDamageLogToJson({
        snapshotId: getSnapshot()?.id,
        replayId: activeReplay?.id,
        characterId: selectedCharacterId,
        roundingPolicy: activeReplay?.conditions?.roundingPolicy,
        rawReplay: activeReplay
      }, activeLogData);
      downloadBlob(json, `nikke-damage-log-${selectedCharacterId}-${Date.now()}.json`, 'application/json');
      status?.('JSON 로그 파일을 내보냈습니다.');
    };

    $('btn-export-csv').onclick = async () => {
      if (!isMockMode && api && activeReplay?.id) {
        try {
          // Direct download link from server if available
          const token = (typeof getToken === 'function' ? getToken() : (api?.token || ''));
          const headers = token ? { 'X-Nikke-Token': token } : {};
          const res = await fetch(`/api/runtime/skill-replays/${activeReplay.id}/damage-log/export.csv`, { headers });
          if (res.ok) {
            const blob = await res.blob();
            downloadBlob(blob, `server-damage-log-${selectedCharacterId}-${Date.now()}.csv`, 'text/csv;charset=utf-8;');
            status?.('서버 원본 CSV 로그를 내보냈습니다.');
            return;
          }
          const errText = await res.text().catch(() => '');
          throw new Error(`서버 로그 내보내기 실패 (${res.status}): ${errText}`);
        } catch (err) {
          status?.(err.message || 'CSV 내보내기 실패');
          return;
        }
      }

      const csv = exportDamageLogToCsv(activeLogData, {
        snapshotId: getSnapshot()?.id,
        replayId: activeReplay?.id,
        rawReplay: activeReplay
      });
      downloadBlob(csv, `nikke-damage-log-${selectedCharacterId}-${Date.now()}.csv`, 'text/csv;charset=utf-8;');
      status?.('CSV 로그 파일을 내보냈습니다.');
    };

    bindGraphInteractions(container);
  }

  function downloadBlob(content, filename, type) {
    const blob = content instanceof Blob ? content : new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function generateGraphSvg(data) {
    const hits = data?.hits || [];
    const width = 1000;
    const height = 300;
    const padL = 60;
    const padR = 20;
    const padT = 20;
    const padB = 40;
    const plotW = width - padL - padR;
    const plotH = height - padT - padB;

    const maxTime = 180;
    const maxDmg = hits.length ? Math.max(...hits.map(h => h.damage)) * 1.15 : 500000;

    const getX = sec => padL + (sec / maxTime) * plotW;
    const getY = dmg => padT + plotH - (dmg / maxDmg) * plotH;

    const teamBands = (data.fullBursts || []).map(fb => {
      const startSec = (fb.startFrame || 0) / 60;
      const endSec = (fb.endFrame || (fb.startFrame + 600)) / 60;
      const x1 = getX(startSec);
      const x2 = getX(Math.min(maxTime, endSec));
      const w = Math.max(2, x2 - x1);
      return `<rect x="${x1}" y="${padT}" width="${w}" height="${plotH}" fill="rgba(22, 173, 242, 0.12)" class="band-team-burst" />`;
    }).join('');

    // Extract actual self-burst active spans directly from hits where isSelfBurstActive is true
    // Never invent startFrame + 600 or arbitrary +10s spans
    const selfBurstSpans = [];
    let currentSpan = null;
    for (const h of hits) {
      if (h.isSelfBurstActive) {
        if (!currentSpan) {
          currentSpan = { startSec: h.seconds, endSec: h.seconds };
        } else if (h.seconds - currentSpan.endSec <= 3.0) {
          currentSpan.endSec = h.seconds;
        } else {
          selfBurstSpans.push(currentSpan);
          currentSpan = { startSec: h.seconds, endSec: h.seconds };
        }
      } else if (currentSpan) {
        selfBurstSpans.push(currentSpan);
        currentSpan = null;
      }
    }
    if (currentSpan) selfBurstSpans.push(currentSpan);

    const selfBands = selfBurstSpans.map(span => {
      const x1 = getX(span.startSec);
      const x2 = getX(Math.min(maxTime, span.endSec + 0.5));
      const w = Math.max(3, x2 - x1);
      return `<rect x="${x1}" y="${padT}" width="${w}" height="${plotH}" fill="rgba(244, 162, 97, 0.18)" class="band-self-burst" />`;
    }).join('');

    let gridLines = '';
    for (let s = 0; s <= 180; s += 30) {
      const x = getX(s);
      gridLines += `
        <line x1="${x}" y1="${padT}" x2="${x}" y2="${padT + plotH}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
        <text x="${x}" y="${padT + plotH + 18}" font-size="11" fill="#64748b" text-anchor="middle">${s}초</text>
      `;
    }

    for (let i = 1; i <= 4; i++) {
      const val = Math.round(maxDmg * (i / 4));
      const y = getY(val);
      gridLines += `
        <line x1="${padL}" y1="${y}" x2="${padL + plotW}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
        <text x="${padL - 8}" y="${y + 4}" font-size="10" fill="#64748b" text-anchor="end">${(val / 10000).toFixed(0)}만</text>
      `;
    }

    let cumulativePath = '';
    if (hits.length > 1) {
      const maxCum = data.totalDamage || 1;
      const points = hits.map(h => `${getX(h.seconds)},${padT + plotH - (h.cumulativeDamage / maxCum) * plotH * 0.35}`).join(' ');
      cumulativePath = `<polyline points="${points}" fill="none" stroke="#94a3b8" stroke-width="1.5" opacity="0.4" stroke-dasharray="4,2" />`;
    }

    const hitPoints = hits.map(h => {
      const cx = getX(h.seconds);
      const cy = getY(h.damage);
      const r = h.isFullCharge ? 4.5 : 3.0;
      const color = h.isCritical ? '#ef4444' : '#2563eb';
      const stroke = h.isCore ? '#f59e0b' : '#ffffff';
      const strokeWidth = h.isCore ? 2 : 1;

      return `
        <circle cx="${cx}" cy="${cy}" r="${r}" fill="${color}" stroke="${stroke}" stroke-width="${strokeWidth}"
          class="graph-hit-dot" data-hit-id="${h.hitId}" data-seconds="${h.seconds}" data-dmg="${h.damage}"
          data-crit="${h.isCritical}" data-core="${h.isCore}" data-full="${h.isFullCharge}"
          data-self="${h.isSelfBurstActive}" data-team="${h.isTeamFullBurst}" />
      `;
    }).join('');

    return `
      <svg viewBox="0 0 ${width} ${height}" class="damage-graph-svg" preserveAspectRatio="xMidYMid meet" aria-label="시간별 발당 대미지 그래프">
        ${teamBands}
        ${selfBands}
        ${gridLines}
        <line x1="${padL}" y1="${padT + plotH}" x2="${padL + plotW}" y2="${padT + plotH}" stroke="#94a3b8" stroke-width="1.5" />
        <line x1="${padL}" y1="${padT}" x2="${padL}" y2="${padT + plotH}" stroke="#94a3b8" stroke-width="1.5" />
        ${cumulativePath}
        ${hitPoints}
      </svg>
    `;
  }

  function bindGraphInteractions(container) {
    const tooltip = $('graph-tooltip');
    if (!tooltip) return;

    container.querySelectorAll('.graph-hit-dot').forEach(dot => {
      dot.onmouseenter = e => {
        const sec = dot.dataset.seconds;
        const dmg = Number(dot.dataset.dmg).toLocaleString('ko-KR');
        const crit = dot.dataset.crit === 'true' ? '크리티컬 ' : '';
        const core = dot.dataset.core === 'true' ? '코어명중 ' : '';
        const full = dot.dataset.full === 'true' ? '풀차지 ' : '비풀차지 ';
        const self = dot.dataset.self === 'true' ? '자체버스트 ' : '';
        const team = dot.dataset.team === 'true' ? '팀풀버스트 ' : '';

        tooltip.innerHTML = `
          <strong>${sec}초 · ${dmg} 대미지</strong><br>
          <small>${crit}${core}${full}${self}${team}</small>
        `;
        tooltip.hidden = false;
        const rect = container.getBoundingClientRect();
        tooltip.style.left = `${e.clientX - rect.left + 12}px`;
        tooltip.style.top = `${e.clientY - rect.top - 36}px`;
      };

      dot.onmouseleave = () => {
        tooltip.hidden = true;
      };

      dot.onclick = () => {
        const hitId = Number(dot.dataset.hitId);
        selectedHit = activeLogData.hits.find(h => h.hitId === hitId);
        render();
        $('btn-close-audit')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      };
    });
  }

  return {
    setReplay,
    loadForCharacter,
    getSelectedCharacterId: () => selectedCharacterId,
    render
  };
}

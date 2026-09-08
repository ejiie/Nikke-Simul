import { escape as e } from './model';

type Vector = { hp: number; atk: number; def: number };
type Hit = Record<string, number | string | boolean>;
type Report = { accountSnapshotId: string; gameSnapshotId: string; calculationDataId: string; characterId: string; name: string;
  accountLevel: number; appliedLevel: number; levelSource: string; status: string; issues: { message: string }[];
  steps: { name: string; value: Vector; source: string }[]; total: Vector | null; basicHit: Hit | null; deferredEffects: string[] };
type Comparison = { rulesVersion: string; status: string; input: Hit; observedDamage: number | null;
  candidates: { policy: string; damage: number; residual: number | null; relativeError: number | null;
    terms: { name: string; before: number; after: number; operation: string }[] }[] };
type Api = <T>(path: string, method?: string, body?: unknown) => Promise<T>;
const n = (v: number) => v.toLocaleString('ko-KR', { maximumFractionDigits: 8 });
const stepNames: Record<string, string> = { level: '레벨 기본', limitBreak: '돌파 증가', bond: '호감도', console: '연구실', coreEnhancement: '코어 강화 증가',
  'equipment:head': '머리', 'equipment:torso': '몸통', 'equipment:arm': '팔', 'equipment:leg': '다리', cube: '큐브 고정 스탯', collection: '소장품 고정 스탯', accessoryRates: '큐브·소장품 비율 증가', overload: '오버로드 증가' };
const policies: Record<string, string> = { legacy_term_floor: 'C# 항별 내림', final_round_even: '최종 반올림 (절반은 짝수)', nested_floor: '항별 + 단계별 내림' };
const numbers = [['attack','적용 공격력',false], ['defense','적용 적 방어력',false], ['coefficient','타격 계수 (%)',true],
  ['chargeBase','기본 차지 배율 (%)',true], ['chargeMultiplierBonus','차지 배율 증가 (%)',true], ['chargeAdd','차지 가산 (%)',true],
  ['critBonus','크리 추가 배율 (%)',true], ['coreBonus','코어 추가 배율 (%)',true], ['distanceBonus','거리 보너스 (%)',true], ['burstBonus','풀버스트 보너스 (%)',true],
  ['attackDamage','공격 대미지 증가 (%)',true], ['pierceDamage','관통 대미지 증가 (%)',true], ['partsDamage','파츠 대미지 증가 (%)',true],
  ['dotDamage','지속 대미지 증가 (%)',true], ['sequentialDamage','연속 대미지 증가 (%)',true], ['trueDamage','방어 무시 대미지 증가 (%)',true],
  ['damageTaken','적 받는 대미지 증가 (%)',true], ['distributionDamage','분배 대미지 증가 (%)',true], ['elementBase','기본 우월 보너스 (%)',true], ['elementBonus','추가 우월 보너스 (%)',true]] as const;
const flags = [['crit','크리 명중'], ['core','코어 명중'], ['fullCharge','풀차지'], ['properDistance','적정 거리'], ['fullBurst','풀버스트 중'], ['pierce','관통 타격'], ['parts','파츠 타격'], ['elementAdvantage','우월 코드'], ['canCrit','크리 허용'], ['canCore','코어 허용'], ['chargeApplicable','차지 적용 가능']] as const;

export function mountCalculation(container: HTMLElement, snapshotId: string, characterId: string, api: Api) {
  const section = document.createElement('section'); section.className = 'calculation'; container.append(section);
  section.innerHTML = '<h3>스탯·단일 히트 검산</h3><p class="muted">저장된 스펙의 계산 과정과 정수화 후보를 비교합니다. 캐릭터 스킬·팀 버프는 아직 자동 적용되지 않습니다.</p><label>검산용 적용 레벨 <input id="scenario-level" type="number" min="1" max="10000" placeholder="비워두면 계정 레벨"></label><button id="load-stats">스탯 계산</button><div class="calc-output" aria-live="polite"></div>';
  let sequence = 0;
  section.querySelector<HTMLButtonElement>('#load-stats')!.onclick = async () => {
    const current = ++sequence; const output = section.querySelector<HTMLElement>('.calc-output')!;
    const level = section.querySelector<HTMLInputElement>('#scenario-level')!.value;
    output.textContent = '계산 중…';
    try {
      const report = await api<Report>(`/snapshots/${encodeURIComponent(snapshotId)}/characters/${encodeURIComponent(characterId)}/stats${level ? `?scenarioLevel=${encodeURIComponent(level)}` : ''}`);
      if (!section.isConnected || current !== sequence) return;
      output.innerHTML = `<p>계정 Lv. ${report.accountLevel} → 적용 Lv. <b>${report.appliedLevel}</b> · ${level ? '검산용 레벨 지정' : '계정 스냅샷 레벨'}</p>${report.issues.map(i => `<p class="notice">${e(i.message)}</p>`).join('')}`;
      if (!report.total || !report.basicHit) return;
      output.innerHTML += `<div class="calc-table"><table><thead><tr><th>기여 항목</th><th>HP</th><th>공격력</th><th>방어력</th></tr></thead><tbody>${report.steps.map(s => `<tr title="${e(s.source)}"><td>${e(stepNames[s.name] ?? s.name)}</td><td>${n(s.value.hp)}</td><td>${n(s.value.atk)}</td><td>${n(s.value.def)}</td></tr>`).join('')}<tr class="calc-total"><th>합계</th><td>${n(report.total.hp)}</td><td>${n(report.total.atk)}</td><td>${n(report.total.def)}</td></tr></tbody></table></div>
      <form class="hit-form"><h3>한 번의 명중 조건</h3><p class="muted">방어력 0인 고정 표적을 기본으로 사용합니다. 적 방어력과 버프를 실제 조건에 맞게 입력하세요. SG는 원천 계수 1회 적용값이며 펠릿 분할은 후속 검증 대상입니다.</p>
      <div class="fields">${numbers.slice(0, 3).map(([key, label, percent]) => field(key, label, Number(report.basicHit![key]) * (percent ? 100 : 1))).join('')}
      <label>타격 유형<select name="damageType">${[['normal','평타'],['skill','스킬'],['dot','지속'],['sequential','연속'],['distribution','분배'],['true','방어 무시']].map(([v,l]) => `<option value="${v}">${l}</option>`).join('')}</select></label></div>
      <div class="hit-flags">${flags.map(([key, label]) => `<label><input type="checkbox" name="${key}" ${report.basicHit![key] ? 'checked' : ''}> ${label}</label>`).join('')}</div>
      <details><summary>세부 배율·효과 조건</summary><div class="fields">${numbers.slice(3).map(([key,label,percent]) => field(key,label,Number(report.basicHit![key]) * (percent ? 100 : 1))).join('')}</div></details>
      <div class="fields"><label>실측 대미지 (선택)<input type="number" name="observed" min="1" step="1" placeholder="추후 입력 가능"></label><label>측정 조건 메모<input name="notes" maxlength="2000" placeholder="대상·스킬·버프·측정 시점"></label></div>
      <button type="submit" class="primary">정수화 후보 비교</button></form><div class="hit-result" aria-live="polite"></div>
      <details><summary>현재 계산 범위와 출처</summary><p>기초 스탯: 기존 C# 연산 · 소장품: 등급별 표 · 히트 정수화: 미확정</p><p>자동 처리 보류: ${e(report.deferredEffects.join(', '))}</p><p class="calc-id">계정 스냅샷 ${e(report.accountSnapshotId)}<br>계산 자료 ${e(report.calculationDataId)}</p></details>`;
      let hitSequence = 0;
      const hitForm = output.querySelector<HTMLFormElement>('.hit-form')!;
      hitForm.oninput = () => { hitSequence++; output.querySelector<HTMLElement>('.hit-result')!.textContent = '입력이 변경되었습니다. 다시 비교하세요.'; };
      hitForm.onsubmit = async event => {
        event.preventDefault(); const form = event.currentTarget as HTMLFormElement; if (!form.reportValidity()) return;
        const hitRequestSequence = ++hitSequence;
        const data = new FormData(form); const hit = { ...report.basicHit! };
        for (const [key,,percent] of numbers) hit[key] = Number(data.get(key)) / (percent ? 100 : 1);
        for (const [key] of flags) hit[key] = data.has(key);
        hit.damageType = String(data.get('damageType'));
        const observed = String(data.get('observed') ?? '').trim();
        const result = output.querySelector<HTMLElement>('.hit-result')!;
        const request = { input: hit, observedDamage: observed ? Number(observed) : null };
        try {
          const comparison = await api<Comparison>('/calculations/hit', 'POST', request);
          if (!section.isConnected || hitRequestSequence !== hitSequence) return;
          result.innerHTML = `<p class="notice">정수화 미확정 · 동일한 입력에 대한 후보 비교입니다.</p><div class="calc-table"><table><thead><tr><th>정수화 후보</th><th>대미지</th><th>실측 차이</th><th>상대오차</th></tr></thead><tbody>${comparison.candidates.map(c => `<tr><td>${e(policies[c.policy])}</td><td>${n(c.damage)}</td><td>${c.residual === null ? '—' : n(c.residual)}</td><td>${c.relativeError === null ? '—' : n(c.relativeError * 100) + '%'}</td></tr>`).join('')}</tbody></table></div>${comparison.candidates.map(c => `<details><summary>${e(policies[c.policy])} 계산 과정</summary><div class="calc-table"><table><thead><tr><th>항</th><th>계산 전</th><th>계산 후</th><th>연산</th></tr></thead><tbody>${c.terms.map(t => `<tr><td>${e(t.name)}</td><td>${n(t.before)}</td><td>${n(t.after)}</td><td>${e(t.operation)}</td></tr>`).join('')}</tbody></table></div></details>`).join('')}<button class="export-calculation">검산 기록 저장 (JSON)</button>`;
          result.querySelector<HTMLButtonElement>('.export-calculation')!.onclick = () => {
            const editedFields = Object.keys(hit).filter(key => hit[key] !== report.basicHit![key]);
            const artifact = { schemaVersion: 1, kind: 'single_hit_calibration', createdAt: new Date().toISOString(), notes: String(data.get('notes')), stats: report, editedFields, comparison };
            const url = URL.createObjectURL(new Blob([JSON.stringify(artifact, null, 2)], { type: 'application/json' }));
            const a = document.createElement('a'); a.href = url; a.download = `nikke-hit-${characterId}-${Date.now()}.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
          };
        } catch (error) { if (section.isConnected && hitRequestSequence === hitSequence) result.textContent = error instanceof Error ? error.message : '검산 실패'; }
      };
    } catch (error) { if (section.isConnected && current === sequence) output.textContent = error instanceof Error ? error.message : '계산 실패'; }
  };
}
function field(key: string, label: string, value: number) {
  return `<label>${e(label)}<input type="number" name="${key}" step="any" required value="${Number(value.toPrecision(14))}"></label>`;
}

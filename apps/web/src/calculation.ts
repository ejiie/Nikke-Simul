import { escape as e } from './model';
import { changedHitFields, parseAttackBuffs, type Hit } from './calculation-model';

type Vector = { hp: number; atk: number; def: number };
type Report = { accountSnapshotId: string; gameSnapshotId: string; calculationDataId: string; characterId: string; name: string;
  accountLevel: number; appliedLevel: number; levelSource: string; status: string; issues: { message: string }[];
  statRulesVersion: string; nativeStats: Vector | null; basicHit: Hit | null };
type Comparison = { rulesVersion: string; status: string; input: Hit; effectiveAttack: number; observedDamage: number | null;
  candidates: { policy: string; damage: number; residual: number | null; relativeError: number | null;
    terms: { name: string; before: number; after: number; operation: string }[] }[] };
type Api = <T>(path: string, method?: string, body?: unknown) => Promise<T>;
const n = (v: number) => v.toLocaleString('ko-KR', { maximumFractionDigits: 8 });
const policies: Record<string, string> = { legacy_term_floor: 'C# 항별 내림', final_round_even: '최종 반올림 (절반은 짝수)', nested_floor: '항별 + 단계별 내림' };
const numbers = [['statAttack','스탯 공격력',false], ['defense','적용 적 방어력',false], ['coefficient','타격 계수 (%)',true],
  ['chargeBase','기본 차지 배율 (%)',true], ['chargeMultiplierBonus','차지 배율 증가 (%)',true], ['chargeAdd','차지 가산 (%)',true],
  ['critBonus','크리 추가 배율 (%)',true], ['coreBonus','코어 추가 배율 (%)',true], ['distanceBonus','거리 보너스 (%)',true], ['burstBonus','풀버스트 보너스 (%)',true],
  ['attackDamage','공격 대미지 증가 (%)',true], ['pierceDamage','관통 대미지 증가 (%)',true], ['partsDamage','파츠 대미지 증가 (%)',true],
  ['dotDamage','지속 대미지 증가 (%)',true], ['sequentialDamage','연속 대미지 증가 (%)',true], ['trueDamage','방어 무시 대미지 증가 (%)',true],
  ['damageTaken','적 받는 대미지 증가 (%)',true], ['distributionDamage','분배 대미지 증가 (%)',true], ['elementBase','기본 우월 보너스 (%)',true], ['elementBonus','추가 우월 보너스 (%)',true]] as const;
const flags = [['crit','크리 명중'], ['core','코어 명중'], ['fullCharge','풀차지'], ['properDistance','적정 거리'], ['fullBurst','풀버스트 중'], ['pierce','관통 타격'], ['parts','파츠 타격'], ['elementAdvantage','우월 코드'], ['canCrit','크리 허용'], ['canCore','코어 허용'], ['chargeApplicable','차지 적용 가능']] as const;

export function mountCalculation(container: HTMLElement, snapshotId: string, characterId: string, api: Api) {
  const section = document.createElement('section'); section.className = 'calculation'; container.append(section);
  section.innerHTML = '<h3>최종 스탯</h3><label>검산용 적용 레벨 <input id="scenario-level" type="number" min="1" max="10000" placeholder="비워두면 계정 레벨"></label><button id="load-stats">스탯 계산</button><div class="calc-output" aria-live="polite"></div>';
  let sequence = 0;
  section.querySelector<HTMLButtonElement>('#load-stats')!.onclick = async () => {
    const current = ++sequence; const output = section.querySelector<HTMLElement>('.calc-output')!;
    const level = section.querySelector<HTMLInputElement>('#scenario-level')!.value;
    output.textContent = '계산 중…';
    try {
      const report = await api<Report>(`/snapshots/${encodeURIComponent(snapshotId)}/characters/${encodeURIComponent(characterId)}/stats${level ? `?scenarioLevel=${encodeURIComponent(level)}` : ''}`);
      if (!section.isConnected || current !== sequence) return;
      output.innerHTML = `<p class="muted">적용 Lv. ${report.appliedLevel}</p>${report.issues.map(i => `<p class="notice">${e(i.message)}</p>`).join('')}`;
      if (!report.nativeStats || !report.basicHit) return;
      output.innerHTML += `<dl class="final-stats"><div><dt>HP</dt><dd data-stat="hp">${n(report.nativeStats.hp)}</dd></div><div><dt>공격력</dt><dd data-stat="atk">${n(report.nativeStats.atk)}</dd></div><div><dt>방어력</dt><dd data-stat="def">${n(report.nativeStats.def)}</dd></div></dl>
      <p class="muted">버프 적용 전 스탯입니다. 오버로드와 스킬 공증은 타격 계산에서 합산합니다.</p>
      <details class="hit-workbench"><summary>단일 히트 검산</summary>
      <form class="hit-form"><h3>한 번의 명중 조건</h3><p class="muted">방어력 0인 고정 표적을 기본으로 사용합니다. 적 방어력과 버프를 실제 조건에 맞게 입력하세요. SG는 원천 계수 1회 적용값이며 펠릿 분할은 후속 검증 대상입니다.</p>
      <p class="muted">공격력 증가 옵션 ${n(report.basicHit.attackBuffs.reduce((sum, buff) => sum + buff.rate * buff.stacks, 0) * 100)}% 자동 적용 · 스킬·팀 버프는 직접 입력합니다.</p>
      <div class="fields">${numbers.slice(0, 3).map(([key, label, percent]) => field(key, label, Number(report.basicHit![key]) * (percent ? 100 : 1))).join('')}
      <label>추가 공격력 버프 (%)<input name="attack-buffs" placeholder="예: 50, 30" autocomplete="off"></label>
      <label>타격 유형<select name="damageType">${[['normal','평타'],['skill','스킬'],['dot','지속'],['sequential','연속'],['distribution','분배'],['true','방어 무시']].map(([v,l]) => `<option value="${v}">${l}</option>`).join('')}</select></label></div>
      <div class="hit-flags">${flags.map(([key, label]) => `<label><input type="checkbox" name="${key}" ${report.basicHit![key] ? 'checked' : ''}> ${label}</label>`).join('')}</div>
      <details><summary>세부 배율·효과 조건</summary><div class="fields">${numbers.slice(3).map(([key,label,percent]) => field(key,label,Number(report.basicHit![key]) * (percent ? 100 : 1))).join('')}</div></details>
      <div class="fields"><label>실측 대미지 (선택)<input type="number" name="observed" min="1" step="1" placeholder="추후 입력 가능"></label><label>측정 조건 메모<input name="notes" maxlength="2000" placeholder="대상·스킬·버프·측정 시점"></label></div>
      <button type="submit" class="primary">정수화 후보 비교</button></form><div class="hit-result" aria-live="polite"></div></details>`;
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
        try {
          hit.runtimeAttackBuffs = parseAttackBuffs(String(data.get('attack-buffs') ?? ''));
          const request = { inputSchemaVersion: 2, input: hit, observedDamage: observed ? Number(observed) : null };
          const comparison = await api<Comparison>('/calculations/hit', 'POST', request);
          if (!section.isConnected || hitRequestSequence !== hitSequence) return;
          result.innerHTML = `<p>버프 적용 공격력 <strong class="effective-attack">${n(comparison.effectiveAttack)}</strong></p><p class="muted">정수화 미확정 · 동일한 입력에 대한 후보 비교입니다.</p><div class="calc-table"><table><thead><tr><th>정수화 후보</th><th>대미지</th><th>실측 차이</th><th>상대오차</th></tr></thead><tbody>${comparison.candidates.map(c => `<tr><td>${e(policies[c.policy])}</td><td>${n(c.damage)}</td><td>${c.residual === null ? '—' : n(c.residual)}</td><td>${c.relativeError === null ? '—' : n(c.relativeError * 100) + '%'}</td></tr>`).join('')}</tbody></table></div><button class="export-calculation">검산 기록 저장 (JSON)</button>`;
          result.querySelector<HTMLButtonElement>('.export-calculation')!.onclick = () => {
            const editedFields = changedHitFields(hit, report.basicHit!);
            const artifact = { schemaVersion: 2, inputSchemaVersion: 2, kind: 'single_hit_calibration', createdAt: new Date().toISOString(), notes: String(data.get('notes')), stats: report, editedFields, comparison };
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

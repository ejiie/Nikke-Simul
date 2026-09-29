/**
 * Korean display labels for internal keys (U-FIX-4). API and stored keys stay as they are; only on-screen text uses
 * these labels. Character codes and raw key strings are never returned; unknown shapes get a generic Korean label.
 */

export const SLOT_LABELS = Object.freeze({ head: '머리', torso: '몸통', arm: '팔', arms: '팔', leg: '다리', legs: '다리' });

// Overload/option definition ids -> Korean (same wording as the equipment editor, without "증가").
export const OPTION_LABELS = Object.freeze({
  StatAtk: '공격력', IncHurtDef: '방어력', StatDef: '방어력', StatAmmoLoad: '최대 장탄 수', StatAmmo: '최대 장탄 수',
  StatCritical: '크리티컬 확률', StatCriticalDamage: '크리티컬 대미지', StatChargeDamage: '차지 대미지',
  StatChargeTime: '차지 속도', IncElementDmg: '우월코드 대미지', StatAccuracyCircle: '명중률'
});

export const BASIS_LABELS = Object.freeze({
  native_recipient: '수혜자 기초 스탯 기준', native_caster: '시전자 기초 스탯 기준',
  native_caster_flat_at_application: '시전자 기준 · 부여 시점 고정값',
  caster_final_max_hp_at_application: '시전자 최종 최대 HP 기준 · 부여 시점 고정',
  caster_charge_centiseconds: '시전자 차지 시간 기준'
});

export const slotLabel = key => SLOT_LABELS[key] ?? '장비';
export const optionLabel = key => OPTION_LABELS[key] ?? null;
export const basisLabel = key => key ? BASIS_LABELS[key] ?? '적용 기준 미확인' : '적용 기준 미기록';

/**
 * Display text for a buff source key such as `overload:5004:head:1:StatAtk`, `cube:<id>:<type>`,
 * `collection:<id>:<type>`, `equipment:<slot>`, `manual:attack:<n>`, `function:<id>` (resolved by `resolveFunction`, else
 * "스킬 효과"; function numbers are never shown). `skill:<character>:<function>`
 * is handled by the caller (it knows the skill slots); here it becomes the character name only.
 * `nameOf(characterId)` returns a Korean name or null.
 */
export function describeSourceKey(source, { nameOf = () => null, resolveFunction = () => null } = {}) {
  const parts = String(source ?? '').split(':');
  const name = id => (id && nameOf(String(id))) || '이름 미확인';
  switch (parts[0]) {
    case 'overload': {
      const line = /^\d+$/.test(parts[3] ?? '') ? ` ${parts[3]}번 줄` : '';
      return `${name(parts[1])} · ${slotLabel(parts[2])}${line} · ${optionLabel(parts[4]) ?? '오버로드 옵션'}`;
    }
    case 'cube': return optionLabel(parts[2]) ? `큐브 · ${optionLabel(parts[2])}` : '큐브 효과';
    case 'collection': return optionLabel(parts[2]) ? `소장품 · ${optionLabel(parts[2])}` : '소장품 효과';
    case 'equipment': return `장비 · ${slotLabel(parts[1])}`;
    case 'manual': return /^\d+$/.test(parts[2] ?? '') ? `직접 입력한 버프 ${parts[2]}` : '직접 입력한 버프';
    // U-FIX-5: never the function number; the caller may resolve it to "character · slot".
    case 'function': return (/^\d+$/.test(parts[1] ?? '') && resolveFunction(parts[1])) || '스킬 효과';
    case 'skill': return `${name(parts[1])} · 스킬 효과`;
    default: return '기타 효과';
  }
}

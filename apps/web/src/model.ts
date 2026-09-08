export type Issue = { severity: string; code: string; path: string; message: string };
export type Connection = { id: string; status: string; area: number | null; accountId: string | null; message: string | null; choices: { area: number; label: string; characterCount: number }[] };
export type Job = { id: string; connectionId: string; status: string; stage: string; collected: number; expected: number; message: string | null; issues: Issue[]; snapshotId: string | null };
export type Line = { lineIndex: number; presence: string; optionId: string | null; optionType: string | null; rawValue: number | null; normalizedValue: number | null; unit: string | null; valueTier: number | null; lockState: string; source: string };
export type Equipment = { slot: string; tier: number | null; level: number | null; manufacturer: number | null; fingerprint: string; lines: Line[] };
export type Character = { characterId: string; name: string; catalogKnown: boolean; level: number | null; nativeLevel: number | null; limitBreak: number | null; core: number | null; bond: number | null; skills: Record<string, number | null>; cubeId: string | null; cubeLevel: number | null; collectionId: string | null; collectionGrade: string | null; collectionLevel: number | null; favoriteStage: number | null; equipment: Equipment[] };
export type Snapshot = { id: string; accountId: string; area: number; revision: number; savedAt: string; observedAt: string; synchroLevel: number | null; consoles: Record<string, number> | null; accountStatsSource: string; characters: Character[]; issues: Issue[]; changes: string[] };
export const parts: Record<string, string> = { head: '머리', torso: '몸통', arm: '팔', leg: '다리' };
export const options: Record<string, string> = { StatAtk: '공격력', IncElementDmg: '우월 코드', StatAmmoLoad: '장탄 수', StatCritical: '크리티컬 확률', StatCriticalDamage: '크리티컬 대미지', StatChargeTime: '차지 시간', StatChargeDamage: '차지 대미지', StatAccuracyCircle: '명중', IncHurtDef: '방어력', StatDef: '방어력' };
export const escape = (v: unknown): string => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
export const value = (v: unknown): string => v === null || v === undefined ? '미확인' : escape(v);
export const active = (j: Job): boolean => ['queued', 'running', 'cancelling'].includes(j.status);
export function lineValue(line: Line): string {
  if (line.presence === 'absent') return '옵션 없음';
  if (line.normalizedValue === null) return '수치 미확인';
  return line.unit === 'ratio' ? `${Number((line.normalizedValue * 100).toFixed(4))}%` : String(line.normalizedValue);
}
export function selectedConnection(connections: Connection[], saved: string | null): Connection | undefined {
  return connections.find(c => c.id === saved) ?? connections.find(c => c.status === 'ready') ?? connections[0];
}

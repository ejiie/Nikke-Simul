import { expect, test } from 'vitest';
import { escape, lineValue, selectedConnection, type Line, type Connection } from './model';
test('API text cannot create HTML', () => expect(escape('<img src=x onerror="bad">')).toBe('&lt;img src=x onerror=&quot;bad&quot;&gt;'));
test('percent presentation preserves small and signed values', () => {
  expect(lineValue({ presence: 'present', normalizedValue: -0.014, unit: 'ratio' } as Line)).toBe('-1.4%');
  expect(lineValue({ presence: 'present', normalizedValue: 0.1181, unit: 'ratio' } as Line)).toBe('11.81%');
});
test('absent, unknown and zero remain distinct', () => {
  expect(lineValue({ presence: 'absent' } as Line)).toBe('옵션 없음');
  expect(lineValue({ presence: 'present', normalizedValue: null } as Line)).toBe('수치 미확인');
  expect(lineValue({ presence: 'present', normalizedValue: 0, unit: 'integer' } as Line)).toBe('0');
});
test('explicit connection preference wins over another ready account', () => {
  const connections = [{id:'a',status:'ready'}, {id:'b',status:'select_account'}] as Connection[];
  expect(selectedConnection(connections, 'b')?.id).toBe('b');
  expect(selectedConnection(connections, null)?.id).toBe('a');
});

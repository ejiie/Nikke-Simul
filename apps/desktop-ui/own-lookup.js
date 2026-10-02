/**
 * Own-key lookup for label/text tables (U-FIX-7 QA 3rd block). A plain `TABLE[key]` also finds inherited members, so a
 * data key such as `constructor`, `toString` or `__proto__` would return a function or object and reach the screen.
 * `own` returns the table value only for an own property and `undefined` otherwise, so every caller falls back to its
 * Korean "unknown" text. Tables here are plain objects; `Map` is not used.
 */
export const own = (table, key) => (
  table !== null && typeof table === 'object'
  && (typeof key === 'string' || typeof key === 'number') && Object.hasOwn(table, key) ? table[key] : undefined
);

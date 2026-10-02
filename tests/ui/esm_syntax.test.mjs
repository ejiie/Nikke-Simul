// U-FIX-7 review block 3: every apps/desktop-ui/*.js must parse as an ES module and every named import must resolve
// to an export of the imported module. A plain `node --check file.js` does not parse as a module and misses a broken
// import declaration, and the other UI tests import only some modules (browser globals keep the rest out of Node).
// No browser, no network. Usage: node tests/ui/esm_syntax.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const dir = path.resolve(import.meta.dirname, '../../apps/desktop-ui');
const files = fs.readdirSync(dir).filter(name => name.endsWith('.js')).sort();
const checks = [];
async function check(name, fn) {
  try { await fn(); checks.push({ name, passed: true }); }
  catch (error) { checks.push({ name, passed: false, error: String(error.message).split('\n').slice(0, 6).join(' | ') }); }
}
const read = name => fs.readFileSync(path.join(dir, name), 'utf8');
const stripComments = text => text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

function exportsOf(name) {
  const text = stripComments(read(name));
  const names = new Set();
  for (const m of text.matchAll(/^export\s+(?:async\s+)?(?:const|let|var|function\*?|class)\s+([A-Za-z_$][\w$]*)/gm)) names.add(m[1]);
  for (const m of text.matchAll(/^export\s*\{([^}]*)\}/gm))
    for (const part of m[1].split(',')) { const alias = part.trim().split(/\s+as\s+/).pop(); if (alias) names.add(alias); }
  return names;
}

await check('files_found', () => assert.ok(files.length >= 15 && files.includes('app.js') && files.includes('local-lab-detail.js'), files.join(',')));

for (const file of files) {
  await check(`esm_parse:${file}`, () => {
    const result = spawnSync(process.execPath, ['--input-type=module', '--check'], { input: read(file), encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr.split('\n').slice(0, 4).join(' | '));
  });
  await check(`imports_resolve:${file}`, () => {
    const text = stripComments(read(file));
    for (const m of text.matchAll(/import\s*\{([^}]*)\}\s*from\s*['"](\.\/[^'"]+)['"]/g)) {
      const target = path.basename(m[2]);
      assert.ok(files.includes(target), `${file}: missing module ${m[2]}`);
      const available = exportsOf(target);
      for (const part of m[1].split(',')) {
        const imported = part.trim().split(/\s+as\s+/)[0];
        if (imported) assert.ok(available.has(imported), `${file}: ${target} has no export ${imported}`);
      }
    }
  });
}

const failed = checks.filter(c => !c.passed);
console.log(JSON.stringify({ total: checks.length, failed: failed.length, checks }, null, 2));
if (failed.length) process.exit(1);

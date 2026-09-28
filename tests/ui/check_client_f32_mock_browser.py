"""Browser rendering check for the client_f32 UI preparation (I-UI stage A). Evidence type: MOCK ONLY.

Renders, in Chromium, with the real desktop stylesheets:
- desktop damage audit panel (apps/desktop-ui/damage-log.js) for client_f32 mock entries and a legacy entry;
- the web single-hit comparison table and experimental-input fieldset markup
  (apps/web/src/calculation-model.ts, type-stripped by Node) against the same mock candidates,
  in both the live (unconfirmed wire) and the stage-B (confirmed wire) modes.
Data comes from tests/ui/fixtures/client-f32-mock.json (Python binary32 UI fixture). No API, no account
data, no network. Passing here is NOT an end-to-end API acceptance.

Output: artifacts/ui/client-f32-mock/run-<id>/ (git-ignored). Exit code 1 means NOT accepted.
"""
import asyncio
import http.server
import json
from pathlib import Path
import socket
import socketserver
import subprocess
import threading
import uuid

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = [1500, 850, 500]

HARNESS = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="/apps/desktop-ui/editor.css"><link rel="stylesheet" href="/apps/desktop-ui/simul.css">
<link rel="stylesheet" href="/apps/web/src/calculation.css"></head>
<body><main style="padding:16px"><section id="replay-result"><div id="desktop"></div></section><section class="calculation" id="web"></section></main>
<script type="module">
import { renderDamageAuditPanel } from '/apps/desktop-ui/damage-log.js';
import { buildHitAudit } from '/apps/desktop-ui/damage-log-adapter.js';
import { comparisonTableHtml, EXPERIMENTAL_INPUTS, HIT_WIRE } from './calculation-model.js';
const mock = await (await fetch('/tests/ui/fixtures/client-f32-mock.json')).json();
const params = new URLSearchParams(location.search);
const c = mock.cases[params.get('case')];
const calc = c.comparison.candidates.find(x => x.policy === params.get('policy'));
const entry = { hitId: 1, frame: 600, damage: calc.damage, hit: c.hit, calculation: calc, buffs: [
  { effect: { source: '5008', target: 'boss', functionId: 127031004, type: 42, value: 0.3926, stacks: 1, basis: 'native_caster', expiresAt: null }, appliedAtFrame: 0 }] };
document.getElementById('desktop').innerHTML = renderDamageAuditPanel({ hitId: 1, shotId: 2, seconds: 10 }, buildHitAudit(entry, null));
const wire = { ...HIT_WIRE, confirmed: params.get('wire') === 'confirmed' };
document.getElementById('web').innerHTML = `<fieldset class="experimental-inputs" ${wire.confirmed ? '' : 'disabled'}><legend>실험 입력 · 미확정 공식 항</legend><div class="fields">${EXPERIMENTAL_INPUTS.map(s => `<label>${s.key}<input name="${s.key}" type="number" value="${s.neutral}"><small>${s.note}</small></label>`).join('')}</div></fieldset>` + comparisonTableHtml(c.comparison.candidates, wire);
document.body.dataset.ready = '1';
</script></body></html>"""

PROBE = """() => {
  const panel = document.querySelector('.damage-audit-panel');
  const cards = Object.fromEntries([...panel.querySelectorAll('.audit-stat-card')].map(c =>
    [c.querySelector('.audit-label')?.textContent.trim(), c.querySelector('.audit-val')?.textContent.trim()]));
  const steps = [...panel.querySelectorAll('tr[data-term]')].map(r => r.dataset.term);
  const rows = [...document.querySelectorAll('#web tr[data-policy]')].map(r => ({ policy: r.dataset.policy, text: r.innerText.replace(/\\s+/g, ' ').trim() }));
  const inputs = [...document.querySelectorAll('#web .experimental-inputs input')].map(i => ({ name: i.name, value: i.value, disabled: i.matches(':disabled') }));
  const shells = [...document.querySelectorAll('.table-scroll, .calc-table')];
  const outside = [...panel.querySelectorAll('*')].filter(e => !shells.some(s => s.contains(e)))
    .filter(e => e.getBoundingClientRect().right > panel.getBoundingClientRect().right + 1).length;
  return { text: panel.innerText, cards, steps, rows, inputs,
    axes: [...panel.querySelectorAll('[data-audit-group="applied"] .pill-badge')].map(b => b.textContent.trim()),
    overflow: { document: document.documentElement.scrollWidth - window.innerWidth, outsideElements: outside } };
}"""


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def serve():
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def end_headers(self):
            self.send_header('Cache-Control', 'no-store')
            super().end_headers()

        def log_message(self, *args):
            pass

    Handler.extensions_map['.js'] = 'text/javascript'
    httpd = socketserver.TCPServer(('127.0.0.1', free_port()), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f'http://127.0.0.1:{httpd.server_address[1]}'


def strip_ts(source, target):
    script = ("const m=require('node:module'),fs=require('node:fs');"
              "fs.writeFileSync(process.argv[2],m.stripTypeScriptTypes(fs.readFileSync(process.argv[1],'utf8'))"
              ".replace(/from '\\.\\/(\\w[\\w-]*)'/g,\"from './$1.js'\"));")
    subprocess.run(['node', '-e', script, str(source), str(target)], check=True)


async def run():
    out = ROOT / 'artifacts/ui/client-f32-mock' / f'run-{uuid.uuid4().hex[:12]}'
    out.mkdir(parents=True)
    for name in ('calculation-model', 'model'):
        strip_ts(ROOT / f'apps/web/src/{name}.ts', out / f'{name}.js')
    (out / 'harness.html').write_text(HARNESS, encoding='utf-8')
    rel = out.relative_to(ROOT).as_posix()
    httpd, base = serve()
    problems, results = [], []
    scenarios = [
        ('client', 'crit_core_fullburst_distance', 'client_f32', 'confirmed'),
        ('client_defence_quarter', 'crit_core_fullburst_distance__defence_ratio_quarter', 'client_f32', 'confirmed'),
        ('client_minimum', 'minimum_damage', 'client_f32', 'confirmed'),
        ('legacy_live', 'crit_core_fullburst_distance', 'legacy_term_floor', 'live'),
    ]
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for label, case, policy, wire in scenarios:
                for width in WIDTHS:
                    page = await browser.new_page(viewport={'width': width, 'height': 1000})
                    errors = []
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
                    await page.goto(f'{base}/{rel}/harness.html?case={case}&policy={policy}&wire={wire}')
                    await page.wait_for_selector('body[data-ready="1"]', timeout=10000)
                    probe = await page.evaluate(PROBE)
                    await page.screenshot(path=str(out / f'{label}-{width}.png'), full_page=True)
                    await page.close()
                    tag = f'{label}@{width}'
                    if errors:
                        problems.append(f'{tag}: page errors {errors}')
                    if probe['overflow']['document'] > 0 or probe['overflow']['outsideElements']:
                        problems.append(f'{tag}: horizontal overflow {probe["overflow"]}')
                    rows = [r['policy'] for r in probe['rows']]
                    if policy == 'client_f32':
                        if rows != ['client_f32', 'legacy_term_floor', 'final_round_even', 'nested_floor'] and case.endswith('distance'):
                            problems.append(f'{tag}: web candidate order {rows}')
                        if 'B3 × B4 × B5' in probe['cards']:
                            problems.append(f'{tag}: earlier B3~B5 card on client_f32')
                        for key in ('statDamageRatio', '1 − defenceRatioRate', 'B (float32 누적)', 'extra', '정수화 전 곱 (float32)'):
                            if key not in probe['cards']:
                                problems.append(f'{tag}: missing card {key}')
                        if probe['steps'] != ['effectiveAttack', 'effectiveDefense', 'difference', 'base', 'B', 'extra', 'reduction', 'defenceRatio', 'product', 'final']:
                            problems.append(f'{tag}: steps {probe["steps"]}')
                        if '실험·미확정' not in probe['text']:
                            problems.append(f'{tag}: experimental label missing')
                        if 'damageReductionRate · 받는 대미지' not in probe['axes']:
                            problems.append(f'{tag}: effect axis {probe["axes"]}')
                        if any(i['disabled'] for i in probe['inputs']) or [i['value'] for i in probe['inputs']] != ['1', '0']:
                            problems.append(f'{tag}: experimental inputs {probe["inputs"]}')
                        if case.endswith('distance') and not any('비교 후보' in r['text'] for r in probe['rows']):
                            problems.append(f'{tag}: comparison tag missing')
                    else:
                        if 'B3 × B4 × B5' not in probe['cards']:
                            problems.append(f'{tag}: legacy panel changed')
                        if not all(i['disabled'] for i in probe['inputs']):
                            problems.append(f'{tag}: experimental inputs enabled before wire confirmation')
                        if any('비교 후보' in r['text'] for r in probe['rows']):
                            problems.append(f'{tag}: comparison tag shown before wire confirmation')
                    if label == 'client_minimum' and '최소 피해 1 적용' not in probe['text']:
                        problems.append(f'{tag}: max(1) note missing')
                    if label == 'client_defence_quarter' and '입력 0.25' not in probe['text']:
                        problems.append(f'{tag}: defenceRatioRate input not shown')
                    results.append({'scenario': tag, 'rows': probe['rows'], 'cards': probe['cards'], 'axes': probe['axes'],
                                    'inputs': probe['inputs'], 'overflow': probe['overflow']})
            await browser.close()
    finally:
        httpd.shutdown()
    report = {'evidence': 'mock_only_not_api', 'fixture': 'tests/ui/fixtures/client-f32-mock.json',
              'accepted': not problems, 'problems': problems, 'results': results}
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(out), 'accepted': not problems, 'scenarios': len(results), 'problems': problems}, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(run()))

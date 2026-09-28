"""Browser check for the single-deck statistics screen (apps/desktop-ui/single-deck-stats.js).

Routes follow Backend contract v1 (Backend commit f2327e5): /api/compute/hardware and
/api/compute/experiments{,/{id},/cancel,/resume,/statistics,/comparison}. The responses here are
synthetic fixtures, so this is a mock pass, not an end-to-end API pass; the summary records
evidenceKind=synthetic_http_fixture for exactly that reason.

States covered: GPU present but not eligible (not_implemented / FP64 unsupported), CPU-only, probe
failure, run -> running -> completed with statistics + comparison, cancel -> partial, resume -> second
attempt, restart recovery from the stored experiment id, 409 analysis_not_integrated, forced-GPU
409 gpu_unavailable, and the responsive widths 1500/850/500.

Output: artifacts/ui/single-deck-stats/run-<id>/ (git-ignored). Exit code 1 means NOT accepted.
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
FIXTURES = ROOT / 'tests/ui/fixtures/single-deck-compute'
IDS = ['5011', '5008', '5009', '5004', '5044']
NAMES = ['리타', '블랑', '누아르', '앨리스', '모더니아']
WIDTHS = [1500, 850, 500]


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def serve(directory):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def end_headers(self):
            self.send_header('Cache-Control', 'no-store')
            super().end_headers()

        def translate_path(self, path):
            return super().translate_path(path[len('/editor'):] if path.startswith('/editor/') else path)

        def log_message(self, *args):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', free_port()), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f'http://127.0.0.1:{httpd.server_address[1]}'


class ComputeMock:
    """Scripted compute endpoints in contract shape; each poll advances the batch lifecycle."""

    def __init__(self):
        self.hardware = load('hardware-profiles.json')
        self.batches = load('batches.json')
        self.statistics = load('statistics.json')
        self.comparisons = load('ol-comparison.json')
        self.profile_key = 'gpuNotImplemented'
        self.analysis_integrated = True
        self.reject_forced_gpu = True
        self.state = None
        self.polls = 0
        self.requests = []

    def start(self, body):
        self.requests.append(body)
        requested = (body or {}).get('execution', {}).get('requested')
        if requested == 'gpu' and self.reject_forced_gpu:
            return 409, {'message': '요청 실패 (409): gpu_unavailable', 'errorCode': 'gpu_unavailable'}
        self.state, self.polls = 'queued', 0
        return 202, self.batches['queued']

    def poll(self):
        self.polls += 1
        if self.state in ('cancelled', 'resumed'):
            return self.batches['cancelledPartial' if self.state == 'cancelled' else 'resumedAttempt']
        if self.polls >= 2:
            self.state = 'completed'
            return self.batches['completed']
        self.state = 'running'
        return self.batches['running']

    def cancel(self):
        self.state = 'cancelled'
        return self.batches['cancelledPartial']

    def resume(self):
        self.state, self.polls = 'resumed', 0
        return self.batches['resumedAttempt']

    def analysis(self, kind):
        if not self.analysis_integrated:
            return 409, {'message': '요청 실패 (409): analysis_not_integrated', 'errorCode': 'analysis_not_integrated'}
        if kind == 'statistics':
            return 200, self.statistics['partialUnsupported' if self.state == 'cancelled' else 'normal']
        return 200, self.comparisons['conflictingVerdict' if self.state == 'cancelled' else 'improved']


async def route_api(page, mock):
    async def fulfil(route, body, status=200):
        await route.fulfill(status=status, json=body)

    async def compute(route):
        url, method = route.request.url, route.request.method
        if url.endswith('/api/compute/hardware'):
            return await fulfil(route, mock.hardware[mock.profile_key])
        if url.endswith('/api/compute/experiments') and method == 'POST':
            status, body = mock.start(route.request.post_data_json)
            return await fulfil(route, body, status)
        if url.endswith('/cancel'):
            return await fulfil(route, mock.cancel())
        if url.endswith('/resume'):
            return await fulfil(route, mock.resume())
        if '/statistics' in url:
            status, body = mock.analysis('statistics')
            return await fulfil(route, body, status)
        if url.endswith('/comparison'):
            status, body = mock.analysis('comparison')
            return await fulfil(route, body, status)
        return await fulfil(route, mock.poll())

    await page.route('**/api/compute/**', compute)
    await page.route('**/api/bootstrap', lambda r: fulfil(r, {'token': 'stats-token', 'testMode': True, 'jobs': [],
        'connections': [{'id': 'c1', 'accountId': 'acc-stats', 'nickname': '검증용', 'status': 'ready',
                         'choices': [{'area': 1, 'label': 'synthetic'}]}]}))
    await page.route('**/api/accounts/*/snapshot', lambda r: fulfil(r, {'id': 'snap-synthetic', 'accountId': 'acc-stats',
        'synchroLevel': 137, 'observedAt': '2026-09-15T00:00:00Z',
        'characters': [{'characterId': i, 'name': n, 'level': 137, 'limitBreak': 3, 'core': 0} for i, n in zip(IDS, NAMES)]}))
    await page.route('**/api/presentation', lambda r: fulfil(r, {'characters': [
        {'characterUid': i, 'displayName': n, 'burstStep': s} for i, n, s in zip(IDS, NAMES, [1, 2, 3, 3, 3])]}))
    await page.route('**/api/presentation/status', lambda r: fulfil(r, {'status': 'idle', 'revision': 1, 'message': 'ready'}))
    await page.route('**/api/accounts/*/formation', lambda r: fulfil(r, {'accountId': 'acc-stats', 'slots': IDS}))
    await page.route('**/api/accounts/*/burst-tactic', lambda r: fulfil(r, {'saved': None, 'stale': False, 'executionStatus': 'legacy'}))
    await page.route('**/api/snapshots/*/combat-powers', lambda r: fulfil(r, {i: 1 for i in IDS}))
    await page.route('**/api/runtime/skill-replays**', lambda r: fulfil(r, {'id': 'replay-none', 'result': {}}))


async def open_stats(page, base):
    await page.goto(base + '/editor/')
    await page.wait_for_function("document.body.dataset.ready==='true'", timeout=60000)
    await page.locator('[data-tab="stats"]').click()
    await page.wait_for_selector('#compute-start', timeout=15000)


async def panel_text(page):
    return await page.locator('#stats-content').inner_text()


async def device_options(page):
    return await page.evaluate(
        "() => [...document.querySelectorAll('#compute-device option')].map(o => o.textContent.trim())")


async def run():
    output = ROOT / 'artifacts/ui/single-deck-stats' / f'run-{uuid.uuid4().hex[:12]}'
    output.mkdir(parents=True)
    server, base = serve(ROOT / 'apps/desktop-ui')
    summary = {'kind': 'single_deck_stats_browser', 'evidenceKind': 'synthetic_http_fixture',
               'contract': 'backend-v1-f2327e5',
               'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain', 'apps/desktop-ui', 'tests/ui'], cwd=ROOT, text=True).strip()),
               'states': {}}
    problems, errors, asset_warnings = [], [], []
    mock = ComputeMock()
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(channel='msedge', headless=True)
            try:
                page = await browser.new_page(viewport={'width': 1500, 'height': 1000})
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('console', lambda m: (asset_warnings if 'Failed to load resource' in m.text else errors)
                        .append('console: ' + m.text) if m.type == 'error' and 'favicon' not in m.text else None)
                await route_api(page, mock)
                await open_stats(page, base)

                # 1. GPUs exist but none is eligible: no GPU option, reasons shown.
                options = await device_options(page)
                summary['states']['deviceOptions'] = options
                if any(o.startswith('GPU') for o in options):
                    problems.append(f'ineligible GPU offered: {options}')
                text = await panel_text(page)
                for needle in ['사용 불가', 'full battle GPU provider가 아직 구현되지 않았습니다.', 'FP64 미지원']:
                    if needle not in text:
                        problems.append(f'device panel missing {needle!r}')

                # 2. Forced GPU is rejected before execution (409 gpu_unavailable).
                await page.evaluate("""() => {
                    const select = document.querySelector('#compute-device');
                    const option = document.createElement('option');
                    option.value = 'gpu-forced'; option.textContent = 'GPU · forced';
                    select.appendChild(option); select.value = 'gpu-forced';
                    select.dispatchEvent(new Event('change'));
                }""")
                await page.locator('#compute-start').click()
                await page.wait_for_function(
                    "() => document.querySelector('#stats-content')?.textContent.includes('gpu_unavailable')", timeout=15000)
                summary['states']['forcedGpuRejected'] = True
                await page.evaluate("""() => {
                    const select = document.querySelector('#compute-device');
                    select.value = 'auto'; select.dispatchEvent(new Event('change'));
                }""")

                # 3. Run -> running -> completed with statistics and comparison.
                await page.locator('#compute-runs').fill('1000')
                await page.locator('#compute-start').click()
                await page.wait_for_function(
                    "() => document.querySelector('#compute-batch-state')?.textContent.includes('완료')", timeout=20000)
                await page.wait_for_function(
                    "() => document.querySelector('#stats-content')?.textContent.includes('152,083,461.2')", timeout=20000)
                completed = await panel_text(page)
                summary['states']['completed'] = [l for l in completed.splitlines() if '표본' in l or '평균' in l][:6]
                for needle in ['1,000', '152,083,461.2 ~ 152,681,125.6', '68.3%', '앨리스', '개선']:
                    if needle not in completed:
                        problems.append(f'completed view missing {needle!r}')
                shots = {}
                for width in WIDTHS:
                    await page.set_viewport_size({'width': width, 'height': 1000})
                    await page.wait_for_timeout(150)
                    overflow = await page.evaluate("""() => {
                        const panel = document.querySelector('#stats-content');
                        const shells = [...panel.querySelectorAll('.table-scroll')];
                        const outside = [...panel.querySelectorAll('*')]
                          .filter(e => !shells.some(s => s.contains(e)))
                          .filter(e => e.getBoundingClientRect().right > panel.getBoundingClientRect().right + 1).length;
                        return { document: document.documentElement.scrollWidth - window.innerWidth,
                                 panel: panel.scrollWidth - panel.clientWidth, outsideElements: outside };
                    }""")
                    path = output / f'stats-{width}.png'
                    await page.locator('#stats-content').screenshot(path=str(path))
                    shots[width] = {'screenshot': str(path.relative_to(ROOT)), 'overflow': overflow}
                    if overflow['document'] > 0 or overflow['panel'] > 0 or overflow['outsideElements'] > 0:
                        problems.append(f'overflow at {width}px: {overflow}')
                summary['states']['responsive'] = shots
                await page.set_viewport_size({'width': 1500, 'height': 1000})

                # 3b. The accepted start request must carry the real combat conditions in contract shape.
                accepted = [r for r in mock.requests if (r.get('execution') or {}).get('requested') != 'gpu']
                if not accepted:
                    problems.append('no accepted start request captured')
                else:
                    combat = (accepted[-1].get('conditions') or {}).get('combat') or {}
                    summary['states']['startCombat'] = combat
                    if combat.get('enemyDefense') not in (30925, 31784):
                        problems.append(f"start request enemyDefense={combat.get('enemyDefense')!r}")
                    if combat.get('durationFrames') != 10800:
                        problems.append(f"start request durationFrames={combat.get('durationFrames')!r}")
                    if 'targetDefense' in combat:
                        problems.append('start request used the documented targetDefense typo')
                    if not (accepted[-1].get('conditions') or {}).get('roundingPolicy'):
                        problems.append('start request lost roundingPolicy')
                    if accepted[-1].get('recordLevel') != 'summary' or accepted[-1].get('runs') != 1000:
                        problems.append(f"start request recordLevel/runs: {accepted[-1].get('recordLevel')!r}/{accepted[-1].get('runs')!r}")

                # 4. Cancel -> partial result, unsupported member metrics, undetermined comparison.
                await page.locator('#compute-start').click()
                await page.wait_for_selector('#compute-cancel:not([disabled])', timeout=15000)
                await page.locator('#compute-cancel').click()
                await page.wait_for_function(
                    "() => document.querySelector('#compute-batch-state')?.textContent.includes('취소')", timeout=20000)
                await page.wait_for_function(
                    "() => document.querySelector('#stats-content')?.textContent.includes('우열 미확정')", timeout=20000)
                cancelled = await panel_text(page)
                for needle in ['부분 결과', '미지원', '우열 미확정', '신뢰구간과 맞지 않아']:
                    if needle not in cancelled:
                        problems.append(f'cancelled view missing {needle!r}')
                summary['states']['cancelled'] = [l for l in cancelled.splitlines() if '취소' in l or '부분' in l][:4]

                # 5. Resume -> attempt 2.
                await page.locator('#compute-resume').click()
                await page.wait_for_function(
                    "() => document.querySelector('#stats-content')?.textContent.includes('attempt 2')", timeout=20000)
                summary['states']['resumedAttempt'] = True

                # 6. Restart recovery from the stored experiment id.
                stored = await page.evaluate("() => localStorage.getItem('nikke-single-deck-experiment')")
                summary['states']['storedExperimentId'] = stored
                if not stored:
                    problems.append('experiment id not stored for restart recovery')
                await page.reload()
                await page.wait_for_function("document.body.dataset.ready==='true'", timeout=60000)
                await page.locator('[data-tab="stats"]').click()
                await page.wait_for_selector('#compute-start', timeout=15000)
                await page.wait_for_function(
                    "() => document.querySelector('#stats-content')?.textContent.includes('재시작 복구')", timeout=15000)
                summary['states']['recovered'] = True

                # 7. Analysis not integrated -> explicit 409 state instead of empty numbers.
                mock.analysis_integrated = False
                mock.state = 'completed'
                await page.evaluate("() => document.querySelector('#compute-remeasure').click()")
                await page.locator('#compute-start').click()
                await page.wait_for_function(
                    "() => document.querySelector('#stats-content')?.textContent.includes('Analysis) 미연결')", timeout=25000)
                analysis_text = await panel_text(page)
                if '평균 CI는 평균의 불확실성' in analysis_text:
                    problems.append('statistics claimed while analysis is not integrated')
                await page.locator('#stats-content').screenshot(path=str(output / 'stats-analysis-not-integrated.png'))
                summary['states']['analysisNotIntegrated'] = True

                # 8. Probe failure state keeps CPU-only options.
                mock.profile_key = 'probeFailed'
                await page.evaluate("() => document.querySelector('#compute-remeasure').click()")
                await page.wait_for_function(
                    "() => document.querySelector('#stats-content')?.textContent.includes('탐지 일부 실패')", timeout=15000)
                failed_text = await panel_text(page)
                if 'probe timeout' not in failed_text:
                    problems.append('probe failure reason missing')
                options_after = await device_options(page)
                if any(o.startswith('GPU') for o in options_after):
                    problems.append(f'GPU offered after probe failure: {options_after}')
                summary['states']['probeFailedOptions'] = options_after

                # 9. Existing screens still work (solo raid level 400).
                await page.locator('[data-tab="raid"]').click()
                await page.wait_for_selector('#replay-form', timeout=15000)
                level_fields = await page.locator('#replay-form [name="level"]').count()
                if level_fields:
                    problems.append('solo raid level field reappeared')
                summary['states']['raidLevelFields'] = level_fields
                await page.close()
            finally:
                await browser.close()
    finally:
        server.shutdown()
    summary['startRequests'] = mock.requests
    summary['errors'] = errors
    summary['assetWarnings'] = asset_warnings
    summary['problems'] = problems + [f'JS {e}' for e in errors]
    summary['passed'] = not summary['problems']
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output)
    print(json.dumps({'passed': summary['passed'], 'problems': summary['problems']}, ensure_ascii=False, indent=2))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(run()))

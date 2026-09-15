"""Browser check for the single-deck statistics screen (apps/desktop-ui/single-deck-stats.js).

Synthetic HTTP only: the compute routes are mocked from tests/ui/fixtures/single-deck-compute because
Backend has not published docs/single-deck-compute-contract.ko.md yet. A mock pass is NOT an end-to-end
API pass; the summary records evidenceKind=synthetic_http_fixture for exactly that reason.

States covered: detection failed, CPU-only, multi-GPU with unusable devices, run -> running -> completed,
cancel -> partial, resume -> second attempt, restart recovery from stored batch id, statistics with
unsupported metrics, OL comparison verdicts, and the responsive widths 1500/850/500.

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
    """Scripted compute endpoints; each poll advances the batch exactly like a real lifecycle would."""

    def __init__(self):
        self.hardware = load('hardware-profiles.json')
        self.selections = load('execution-selections.json')
        self.batches = load('batches.json')
        self.statistics = load('statistics.json')
        self.ol = load('ol-comparison.json')
        self.profile_key = 'multiGpu'
        self.selection_key = 'autoCpu'
        self.state = None
        self.poll_count = 0
        self.requests = []

    def hardware_payload(self):
        return {'hardware': self.hardware[self.profile_key], 'selection': self.selections[self.selection_key]}

    def start(self, body):
        self.requests.append(body)
        self.state = 'queued'
        self.poll_count = 0
        return {'batch': self.batches['queued'], 'selection': self.selections[self.selection_key],
                'experiment': {'snapshotId': body.get('snapshotId'), 'synchroLevel': body.get('synchroLevel'),
                               'durationSeconds': body.get('durationSeconds'), 'requestedRuns': body.get('requestedRuns'),
                               'rulesVersion': 'p04.team.2', 'fingerprint': 'fp-synthetic',
                               'members': [{'characterId': i, 'displayName': n, 'burstStep': s}
                                           for i, n, s in zip(IDS, NAMES, [1, 2, 3, 3, 3])]}}

    def poll(self):
        self.poll_count += 1
        if self.state in ('cancelled', 'failed'):
            return {'batch': self.batches['cancelledPartial' if self.state == 'cancelled' else 'failed']}
        if self.state == 'resumed':
            return {'batch': self.batches['resumedAttempt']}
        if self.poll_count >= 2:
            self.state = 'completed'
            return {'batch': self.batches['completed'], 'statistics': self.statistics['normal'],
                    'olComparison': self.ol['mixedVerdicts']}
        self.state = 'running'
        return {'batch': self.batches['running']}

    def cancel(self):
        self.state = 'cancelled'
        return {'batch': self.batches['cancelledPartial'], 'statistics': self.statistics['partialUnsupported']}

    def resume(self):
        self.state = 'resumed'
        self.poll_count = 0
        return {'batch': self.batches['resumedAttempt']}

    def results(self):
        if self.state == 'cancelled':
            return {'statistics': self.statistics['partialUnsupported'], 'olComparison': self.ol['empty']}
        return {'statistics': self.statistics['normal'], 'olComparison': self.ol['mixedVerdicts']}


async def route_api(page, mock):
    async def fulfil(route, body):
        await route.fulfill(json=body)

    async def compute(route):
        url = route.request.url
        method = route.request.method
        if url.endswith('/api/compute/hardware'):
            return await fulfil(route, mock.hardware_payload())
        if url.endswith('/api/compute/batches') and method == 'POST':
            return await fulfil(route, mock.start(route.request.post_data_json))
        if url.endswith('/cancel'):
            return await fulfil(route, mock.cancel())
        if url.endswith('/resume'):
            return await fulfil(route, mock.resume())
        if url.endswith('/results'):
            return await fulfil(route, mock.results())
        if url.endswith('/overload-comparison'):
            return await fulfil(route, {'olComparison': mock.results()['olComparison']})
        return await fulfil(route, mock.poll())

    await page.route('**/api/compute/**', compute)
    await page.route('**/api/bootstrap', lambda r: fulfil(r, {'token': 'stats-token', 'testMode': True, 'jobs': [],
        'connections': [{'id': 'c1', 'accountId': 'acc-stats', 'nickname': '검증용', 'status': 'ready',
                         'choices': [{'area': 1, 'label': 'synthetic'}]}]}))
    await page.route('**/api/accounts/*/snapshot', lambda r: fulfil(r, {'id': 'snap-stats', 'accountId': 'acc-stats',
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


async def run():
    output = ROOT / 'artifacts/ui/single-deck-stats' / f'run-{uuid.uuid4().hex[:12]}'
    output.mkdir(parents=True)
    server, base = serve(ROOT / 'apps/desktop-ui')
    summary = {'kind': 'single_deck_stats_browser', 'evidenceKind': 'synthetic_http_fixture',
               'contract': 'provisional_pending_backend_contract',
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

                # 1. Detected hardware: only the verified GPU may be offered.
                text = await panel_text(page)
                # The advanced controls sit in a collapsed <details>; read them without relying on visibility.
                options = await page.evaluate(
                    "() => [...document.querySelectorAll('#compute-device option')].map(o => o.textContent.trim())")
                summary['states']['deviceOptions'] = options
                if any('이름만' in o or '정확성 실패' in o for o in options):
                    problems.append(f'unusable GPU offered: {options}')
                if '사용 불가' not in text:
                    problems.append('unusable device not marked')
                if 'CPU' not in text:
                    problems.append('effective backend missing')

                # 2. Run -> running -> completed with statistics and OL comparison.
                await page.locator('#compute-runs').fill('1000')
                await page.locator('#compute-start').click()
                await page.wait_for_function(
                    "() => document.querySelector('#compute-batch-state')?.textContent.includes('완료')", timeout=20000)
                completed = await panel_text(page)
                summary['states']['completed'] = [l for l in completed.splitlines() if '표본' in l or '평균' in l][:6]
                for needle in ['1,000', '152,083,461.2 ~ 152,681,125.6', '68.3%', '우열 미확정', '앨리스']:
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

                # 3. Cancel -> partial result with unsupported metrics stated.
                await page.locator('#compute-start').click()
                await page.wait_for_selector('#compute-cancel:not([disabled])', timeout=15000)
                await page.locator('#compute-cancel').click()
                await page.wait_for_function(
                    "() => document.querySelector('#compute-batch-state')?.textContent.includes('취소')", timeout=20000)
                cancelled = await panel_text(page)
                if '부분 결과' not in cancelled or '미지원' not in cancelled:
                    problems.append('cancelled state missing partial/unsupported markers')
                if '표본에서 제외' not in cancelled:
                    problems.append('incomplete runs not excluded explicitly')
                summary['states']['cancelled'] = [l for l in cancelled.splitlines() if '취소' in l or '부분' in l][:4]

                # 4. Resume -> a new attempt, no duplicate aggregation claim.
                await page.locator('#compute-resume').click()
                await page.wait_for_function(
                    "() => document.querySelector('#compute-batch-state')?.textContent.includes('실행 중')", timeout=20000)
                resumed = await panel_text(page)
                if '중복 집계하지 않습니다' not in resumed:
                    problems.append('resume message missing')
                summary['states']['resumed'] = True

                # 5. Restart recovery: reload keeps the stored batch id and re-reads its real state.
                stored = await page.evaluate("() => localStorage.getItem('nikke-single-deck-batch')")
                summary['states']['storedBatchId'] = stored
                if not stored:
                    problems.append('batch id not stored for restart recovery')
                await page.reload()
                await page.wait_for_function("document.body.dataset.ready==='true'", timeout=60000)
                await page.locator('[data-tab="stats"]').click()
                await page.wait_for_selector('#compute-start', timeout=15000)
                await page.wait_for_function(
                    "() => document.querySelector('#stats-content')?.textContent.includes('재시작 복구')", timeout=15000)
                summary['states']['recovered'] = True

                # 6. Detection failure state.
                mock.profile_key = 'detectionFailed'
                mock.selection_key = 'gpuFallback'
                await page.evaluate("() => document.querySelector('#compute-remeasure').click()")
                await page.wait_for_function(
                    "() => document.querySelector('#stats-content')?.textContent.includes('탐지 실패')", timeout=15000)
                failed_text = await panel_text(page)
                if 'probe timeout' not in failed_text:
                    problems.append('detection failure reason missing')
                if 'GPU 성공으로 표시하지 않습니다' not in failed_text:
                    problems.append('gpu fallback not distinguished')
                options_after = await page.evaluate(
                    "() => [...document.querySelectorAll('#compute-device option')].map(o => o.textContent.trim())")
                if any(o.startswith('GPU') for o in options_after):
                    problems.append(f'GPU offered after detection failure: {options_after}')
                await page.locator('#stats-content').screenshot(path=str(output / 'stats-detection-failed.png'))
                summary['states']['detectionFailed'] = options_after

                # 7. Existing screens still work (level 400 raid form).
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

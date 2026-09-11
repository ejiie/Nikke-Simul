"""
UI Integration Verification Test for U2 (Damage Log & Burst Tactics).
Uses Playwright with Edge/Chromium against a local static web server with mock API routes.

Verifies:
1. Backend (B1) & Engine (E1) BurstTacticSettings Contract Alignment:
   - Server GET/PUT /api/accounts/{id}/burst-tactic persistence and restoration
   - schemaVersion: 1, allowedCharacterIds, stage priorities, burst3Rotation, firstBurst3CharacterId, unavailablePolicy
   - Stale status detection and executionStatus validation
2. Save -> Reload/Restore -> Execution -> Timeline & Log Cross-Comparison Flow
3. Solo Raid tab load & 180-second engine limit enforcement
4. Detailed Damage Log Viewer:
   - Real server log vs uncollected status vs explicit mock preview separation
   - Distinguishes Shot Count (발사 수) vs Hit Count (명중 수)
   - Alice (5004) default target and Modernia (5044) target switching
   - SVG timeline graph with distinct Self Burst Active & Team Full Burst bands
   - Calculation audit inspection panel
   - Interactive filters (burst state, hit type)
   - CSV and JSON export
5. Responsive layouts (1500px, 850px, 500px) with zero horizontal overflow
6. Zero JavaScript / Page errors
"""

import asyncio
import http.server
import json
import os
from pathlib import Path
import socketserver
import threading
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / 'artifacts/ui/verification'
PORT = 5199
BASE_URL = f'http://127.0.0.1:{PORT}'


class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def translate_path(self, path):
        if path.startswith('/editor/'):
            rel = path[len('/editor/'):]
            return str(ROOT / 'apps/desktop-ui' / rel)
        return super().translate_path(path)


def start_server():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), CustomHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


async def run_verification():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    server = start_server()
    errors = []
    summary = {}
    server_saved_tactic = None
    captured_replay_requests = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(channel='msedge', headless=True)
            page = await browser.new_page(viewport={'width': 1500, 'height': 1000})
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda msg: print(f'[BROWSER CONSOLE] {msg.type}: {msg.text}'))

            # Mock API Routes
            async def handle_bootstrap(route):
                await route.fulfill(json={
                    'token': 'ui-test-token-2026',
                    'testMode': True,
                    'connections': [{
                        'id': 'conn-mock-1',
                        'accountId': 'acc-test-1',
                        'nickname': '지휘관 (검증용)',
                        'status': 'ready',
                        'choices': [{'area': 1, 'label': '한국 서버'}]
                    }],
                    'jobs': []
                })

            async def handle_snapshot(route):
                await route.fulfill(json={
                    'id': 'snap-mock-1',
                    'accountId': 'acc-test-1',
                    'synchroLevel': 400,
                    'observedAt': '2026-09-11T10:00:00Z',
                    'characters': [
                        {'characterId': '5011', 'name': '리타', 'level': 400, 'limitBreak': 3, 'core': 2},
                        {'characterId': '5008', 'name': '블랑', 'level': 400, 'limitBreak': 3, 'core': 1},
                        {'characterId': '5009', 'name': '누아르', 'level': 400, 'limitBreak': 3, 'core': 0},
                        {'characterId': '5004', 'name': '앨리스', 'level': 400, 'limitBreak': 3, 'core': 7},
                        {'characterId': '5044', 'name': '모더니아', 'level': 400, 'limitBreak': 3, 'core': 5}
                    ]
                })

            async def handle_presentation(route):
                await route.fulfill(json={
                    'characters': [
                        {'characterUid': '5011', 'displayName': '리타', 'burstStep': 1, 'weaponCode': 'submachine_gun'},
                        {'characterUid': '5008', 'displayName': '블랑', 'burstStep': 2, 'weaponCode': 'assault_rifle'},
                        {'characterUid': '5009', 'displayName': '누아르', 'burstStep': 3, 'weaponCode': 'shotgun'},
                        {'characterUid': '5004', 'displayName': '앨리스', 'burstStep': 3, 'weaponCode': 'sniper_rifle'},
                        {'characterUid': '5044', 'displayName': '모더니아', 'burstStep': 3, 'weaponCode': 'machine_gun'}
                    ]
                })

            async def handle_formation(route):
                if route.request.method == 'GET':
                    await route.fulfill(json={'accountId': 'acc-test-1', 'slots': ['5011', '5008', '5009', '5004', '5044']})
                else:
                    data = route.request.post_data_json
                    await route.fulfill(json={'accountId': 'acc-test-1', 'slots': data.get('slots', [])})

            async def handle_burst_tactic(route):
                nonlocal server_saved_tactic
                if route.request.method == 'GET':
                    if server_saved_tactic:
                        await route.fulfill(json={
                            'saved': {
                                'accountId': 'acc-test-1',
                                'snapshotId': 'snap-mock-1',
                                'formationSlots': ['5011', '5008', '5009', '5004', '5044'],
                                'tactic': server_saved_tactic,
                                'savedAt': '2026-09-11T11:00:00Z'
                            },
                            'stale': False,
                            'executionStatus': 'saved',
                            'issues': []
                        })
                    else:
                        await route.fulfill(json={'saved': None, 'stale': False, 'executionStatus': 'legacy'})
                elif route.request.method == 'PUT':
                    data = route.request.post_data_json
                    server_saved_tactic = data.get('tactic')
                    await route.fulfill(json={
                        'saved': {
                            'accountId': 'acc-test-1',
                            'snapshotId': data.get('snapshotId', 'snap-mock-1'),
                            'formationSlots': data.get('formationSlots', []),
                            'tactic': server_saved_tactic,
                            'savedAt': '2026-09-11T11:05:00Z'
                        },
                        'stale': False,
                        'executionStatus': 'saved',
                        'issues': []
                    })

            async def handle_combat_powers(route):
                await route.fulfill(json={'5011': 85000, '5008': 82000, '5009': 81000, '5004': 95000, '5044': 92000})

            async def handle_presentation_status(route):
                await route.fulfill(json={'status': 'idle', 'revision': 1, 'message': '준비 완료'})

            async def handle_skill_replays(route):
                data = route.request.post_data_json
                captured_replay_requests.append(data)
                replay_payload = {
                    'id': 'replay-mock-test-01',
                    'createdAt': '2026-09-11T10:15:00Z',
                    'inputs': [
                        {'weapon': {'characterId': '5011'}, 'skills': {'slots': {}}},
                        {'weapon': {'characterId': '5008'}, 'skills': {'slots': {}}},
                        {'weapon': {'characterId': '5009'}, 'skills': {'slots': {}}},
                        {'weapon': {'characterId': '5004'}, 'skills': {'slots': {'burst': {'skillId': 50043, 'functionIds': []}}}},
                        {'weapon': {'characterId': '5044'}, 'skills': {'slots': {'burst': {'skillId': 50443, 'functionIds': []}}}}
                    ],
                    'conditions': {
                        'roundingPolicy': 'final_round_even',
                        'combat': {'durationFrames': 10800, 'enemyDefense': 30925}
                    },
                    'result': {
                        'totalDamage': 356000000,
                        'members': [
                            {'characterId': '5011', 'damage': 15000000, 'effects': {'normal_attack': 15000000}},
                            {'characterId': '5008', 'damage': 18000000, 'effects': {'normal_attack': 18000000}},
                            {'characterId': '5009', 'damage': 25000000, 'effects': {'normal_attack': 25000000}},
                            {'characterId': '5004', 'damage': 185000000, 'effects': {'normal_attack': 65000000, 'skill:50043:weapon': 120000000}},
                            {'characterId': '5044', 'damage': 113000000, 'effects': {'normal_attack': 43000000, 'skill:50443:weapon': 70000000}}
                        ],
                        'teamBurst': {
                            'fullBursts': [
                                {'cycle': 1, 'caster': '5004', 'startFrame': 650, 'endFrame': 1250, 'memberDamage': {'5004': 25000000}},
                                {'cycle': 2, 'caster': '5044', 'startFrame': 1850, 'endFrame': 2750, 'memberDamage': {'5044': 20000000}},
                                {'cycle': 3, 'caster': '5004', 'startFrame': 3350, 'endFrame': 3950, 'memberDamage': {'5004': 28000000}},
                                {'cycle': 4, 'caster': '5044', 'startFrame': 4550, 'endFrame': 5450, 'memberDamage': {'5044': 21000000}},
                                {'cycle': 5, 'caster': '5004', 'startFrame': 6050, 'endFrame': 6650, 'memberDamage': {'5004': 30000000}}
                            ],
                            'fullBurstFrames': 4200,
                            'timeline': [
                                {'frame': 600, 'step': 1, 'kind': 'burst_cast', 'characterId': '5011'},
                                {'frame': 620, 'step': 2, 'kind': 'burst_cast', 'characterId': '5008'},
                                {'frame': 650, 'step': 3, 'kind': 'burst_cast', 'characterId': '5004'},
                                {'frame': 1800, 'step': 1, 'kind': 'burst_cast', 'characterId': '5011'},
                                {'frame': 1820, 'step': 2, 'kind': 'burst_cast', 'characterId': '5008'},
                                {'frame': 1850, 'step': 3, 'kind': 'burst_cast', 'characterId': '5044'}
                            ],
                            'acceptedGaugeByMember': {'5011': 120000, '5008': 80000, '5009': 150000, '5004': 450000, '5044': 200000},
                            'sourceConstants': {'capacityRaw': 1000000}
                        }
                    }
                }
                await route.fulfill(json=replay_payload)

            await page.route('**/api/bootstrap', handle_bootstrap)
            await page.route('**/api/accounts/*/snapshot', handle_snapshot)
            await page.route('**/api/presentation', handle_presentation)
            await page.route('**/api/presentation/status', handle_presentation_status)
            await page.route('**/api/accounts/*/formation', handle_formation)
            await page.route('**/api/accounts/*/burst-tactic', handle_burst_tactic)
            await page.route('**/api/snapshots/*/combat-powers', handle_combat_powers)
            await page.route('**/api/runtime/skill-replays', handle_skill_replays)

            # Navigate to editor
            await page.goto(f'{BASE_URL}/editor/')
            await page.wait_for_function("document.body.dataset.ready==='true'")

            # 1. Enter Solo Raid Tab
            await page.locator('[data-tab="raid"]').click()
            assert await page.locator('#burst-tactics-section').is_visible()

            # 2. Check 180-second limit
            seconds_input = page.locator('[name="seconds"]')
            assert await seconds_input.get_attribute('max') == '180'
            assert await seconds_input.input_value() == '180'

            # 3. Burst Tactics Controls & Server Persistence Flow (PUT /api/accounts/{id}/burst-tactic)
            await page.locator('#preset-alice-first').click()
            # Click [서버에 저장]
            await page.locator('#btn-force-save-server').click()
            await page.wait_for_timeout(300)
            assert server_saved_tactic is not None, "Server must have received PUT tactic"
            assert server_saved_tactic.get('schemaVersion') == 1, "DTO must be schemaVersion: 1"
            assert '5004' in server_saved_tactic.get('allowedCharacterIds', [])
            assert server_saved_tactic.get('firstBurst3CharacterId') == '5004'
            assert server_saved_tactic.get('unavailablePolicy') == 'next_ready'

            # Verify badge says server saved
            assert await page.locator('.status-pill.green:has-text("서버 저장 완료")').is_visible()

            # 4. Reload / Restore from Server (GET /api/accounts/{id}/burst-tactic)
            await page.locator('[data-tab="home"]').click()
            await page.locator('[data-tab="raid"]').click()
            await page.wait_for_timeout(300)
            assert await page.locator('[data-tactic-allow="5004"]').is_checked()
            assert await page.locator('#tactic-first-caster').input_value() == '5004'
            assert await page.locator('#tactic-stage3-mode').input_value() == 'alternate'

            # 5. Run Damage Simulation with Tactic Attached
            await page.locator('#run-replay').click()
            await page.wait_for_selector('#burst-timeline-comparison table')

            # Verify captured request has tactic adhering to Backend/Engine schemaVersion 1
            assert len(captured_replay_requests) > 0
            sent_req = captured_replay_requests[-1]
            tactic_payload = sent_req.get('conditions', {}).get('autoBurst', {}).get('tactic')
            assert tactic_payload is not None, "Request must include tactic DTO"
            assert tactic_payload.get('schemaVersion') == 1
            assert tactic_payload.get('allowedCharacterIds') == ['5011', '5008', '5009', '5004', '5044']
            assert tactic_payload.get('stage3Priority') == ['5004', '5009', '5044']
            assert tactic_payload.get('burst3Rotation') == ['5004', '5009', '5044']
            assert tactic_payload.get('firstBurst3CharacterId') == '5004'
            assert tactic_payload.get('unavailablePolicy') == 'next_ready'
            summary['tacticPayloadVerified'] = True

            # 6. Verify Timeline Comparison View
            comparison_rows = await page.locator('#burst-timeline-comparison tbody tr').count()
            assert comparison_rows >= 5
            summary['comparisonRows'] = comparison_rows

            # 7. Verify Uncollected Log State & Explicit Mock Preview Boundary
            # Without server log and without allowMock, UI cleanly reports uncollected
            assert await page.locator('.status-pill.warning:has-text("로그 미수집 상태")').is_visible()
            assert await page.locator('#btn-load-mock-preview').is_visible()
            summary['uncollectedNoticeVerified'] = True

            # Click explicit mock preview button
            await page.locator('#btn-load-mock-preview').click()
            await page.wait_for_selector('.damage-graph-svg')
            assert await page.locator('.status-pill.neutral:has-text("합성 Mock Fixture")').is_visible()

            # Check Alice default and hits count
            target_select = page.locator('#log-character-select')
            assert await target_select.input_value() == '5004'
            dots_count = await page.locator('.graph-hit-dot').count()
            assert dots_count > 20
            summary['aliceHitCount'] = dots_count

            # Check Shot Count vs Hit Count distinction in metric card
            shot_metric_text = await page.locator('.metric-card:has(span:has-text("발사 / 명중 횟수")) strong').inner_text()
            assert '발사' in shot_metric_text and '명중' in shot_metric_text
            summary['shotHitDistinctionVerified'] = True

            # Check burst bands
            self_bands = await page.locator('.band-self-burst').count()
            team_bands = await page.locator('.band-team-burst').count()
            assert self_bands > 0, "Self burst bands must be rendered"
            assert team_bands > 0, "Team full burst bands must be rendered"

            # 8. Check Calculation Audit Inspection Panel
            first_audit_btn = page.locator('[data-view-audit]').first
            await first_audit_btn.click()
            assert await page.locator('.damage-audit-panel').is_visible()
            assert '기초 공격력' in await page.locator('.damage-audit-panel').inner_text()
            assert '버프 적용 공격력' in await page.locator('.damage-audit-panel').inner_text()
            assert '공방차' in await page.locator('.damage-audit-panel').inner_text()
            await page.locator('#btn-close-audit').click()
            assert not await page.locator('.damage-audit-panel').is_visible()

            # 9. Check Interactive Filters
            await page.locator('[data-filter-burst="self_only"]').click()
            assert await page.locator('.log-table-shell tbody tr').count() > 0
            await page.locator('[data-filter-hit="crit"]').click()
            assert await page.locator('.log-table-shell tbody tr').count() > 0
            await page.locator('[data-filter-burst="all"]').click()
            await page.locator('[data-filter-hit="all"]').click()

            # 10. Switch Nikke to Modernia (5044)
            await target_select.select_option('5044')
            await page.wait_for_timeout(300)
            modernia_dots = await page.locator('.graph-hit-dot').count()
            assert modernia_dots > 50

            # Switch back to Alice
            await target_select.select_option('5004')
            await page.wait_for_timeout(300)

            # 11. Check Export Handlers
            await page.locator('#btn-export-json').click()
            await page.locator('#btn-export-csv').click()

            # 12. Check Stale ID detection & Clean button
            await page.evaluate("""() => {
                const raw = localStorage.getItem('nikke-burst-tactics-acc-test-1');
                if (raw) {
                    const t = JSON.parse(raw);
                    t.allowlist['9999_stale'] = true;
                    t.priority.stage3.push('9999_stale');
                    localStorage.setItem('nikke-burst-tactics-acc-test-1', JSON.stringify(t));
                }
            }""")
            await page.locator('[data-tab="home"]').click()
            await page.locator('[data-tab="raid"]').click()
            assert await page.locator('#btn-clean-stale').is_visible()
            await page.locator('#btn-clean-stale').click()
            assert not await page.locator('#btn-clean-stale').is_visible()

            # 13. Responsive Layouts: 1500px, 850px, 500px
            for width in [1500, 850, 500]:
                await page.set_viewport_size({'width': width, 'height': 1000})
                await page.wait_for_timeout(200)
                await page.screenshot(path=str(OUTPUT / f'ui-damage-log-{width}px.png'))
                is_overflow = await page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                assert not is_overflow, f'Horizontal overflow detected at {width}px'

            # 14. Check zero page errors
            assert not errors, f'JavaScript errors encountered: {errors}'

            await browser.close()

        summary.update({
            'success': True,
            'widthsChecked': [1500, 850, 500],
            'jsErrorsCount': len(errors),
            'serverTacticContractVerified': True,
            'uncollectedVsMockSeparated': True,
            'maxSecondsLimit': 180
        })

        (OUTPUT / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps(summary, indent=2, ensure_ascii=False))

    finally:
        server.shutdown()


if __name__ == '__main__':
    asyncio.run(run_verification())

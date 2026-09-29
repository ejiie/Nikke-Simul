"""U-FIX-4 (F2-Q-2): damage audit source labels on a REAL saved replay, without recomputation.

Evidence type: synthetic HTTP + real saved replay (read only, hash-checked), like check_damage_audit_browser.py.
The saved replay (--saved-replay, e.g. the Director's isolated live response) carries overload/skill source keys in
hit attack inputs (cube/collection keys only elsewhere; their labels are unit-tested). For hits using them, the audit panel's "최종 공격력 입력" must show Korean labels (character · slot n번 줄 ·
option, 큐브 · …, 소장품 · …) and no raw key, character code or option id, at 1500/850/500px. The replay JSON is served
as stored; nothing is recalculated. Output: artifacts/ui/source-labels/run-<id>/. Exit 1 = NOT accepted.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import uuid

from playwright.async_api import async_playwright

from check_damage_audit_browser import ROOT, WIDTHS, capture, serve

RAW = re.compile(r'overload:|cube:|collection:|equipment:|skill:\d|function:|StatAtk|StatAmmo|StatCritical|native_|basis |\b50\d\d\b|#50')
NAMES = {'5011': '리타', '5008': '블랑', '5009': '누아르', '5004': '앨리스', '5044': '모더니아'}
SLOTS = {'head': '머리', 'torso': '몸통', 'arm': '팔', 'leg': '다리'}
OPTIONS = {'StatAtk': '공격력', 'StatAmmoLoad': '최대 장탄 수', 'StatCritical': '크리티컬 확률', 'StatCriticalDamage': '크리티컬 대미지',
           'StatChargeDamage': '차지 대미지', 'StatChargeTime': '차지 속도', 'IncElementDmg': '우월코드 대미지', 'StatAccuracyCircle': '명중률'}


def expected_label(source):
    parts = source.split(':')
    if parts[0] == 'overload':
        return f"{NAMES.get(parts[1], '이름 미확인')} · {SLOTS.get(parts[2], '장비')} {parts[3]}번 줄 · {OPTIONS.get(parts[4], '오버로드 옵션')}"
    if parts[0] == 'cube':
        return f"큐브 · {OPTIONS[parts[2]]}" if parts[2] in OPTIONS else '큐브 효과'
    if parts[0] == 'collection':
        return f"소장품 · {OPTIONS[parts[2]]}" if parts[2] in OPTIONS else '소장품 효과'
    return None


async def run(args):
    out = ROOT / 'artifacts/ui/source-labels' / f'run-{uuid.uuid4().hex[:12]}'
    out.mkdir(parents=True)
    path = Path(args.saved_replay)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    saved = json.loads(path.read_text(encoding='utf-8'))
    replay = saved.get('replay', saved)
    entries = replay['result']['damageLog']['entries']
    kinds = {}
    for e in entries:
        for b in (e.get('hit') or {}).get('attackBuffs', []) + (e.get('hit') or {}).get('runtimeAttackBuffs', []) + (e.get('hit') or {}).get('attackFlatBuffs', []):
            kind = str(b.get('source', '')).split(':')[0]
            kinds.setdefault(kind, e)
    targets = list({id(e): e for e in kinds.values()}.values())
    server, base = serve(ROOT / 'apps/desktop-ui')
    problems, results = [], []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for entry in targets:
                shots, errors = await capture(browser, f"hit{entry['hitId']}", base, replay, entry, out, WIDTHS)
                text = shots[1500]['probe']['text']
                attack = next((g for k, g in shots[1500]['probe']['groups'].items() if k == 'attack'), [])
                sources = [b['source'] for b in entry['hit'].get('attackBuffs', []) + entry['hit'].get('runtimeAttackBuffs', [])]
                want = [lbl for lbl in (expected_label(s) for s in sources) if lbl]
                missing = [w for w in want if w not in text]
                leaks = RAW.findall(text)
                results.append({'hitId': entry['hitId'], 'sources': sources, 'attackLines': attack, 'expected': want, 'missing': missing,
                                'leaks': leaks, 'overflow': {w: shots[w]['overflow'] for w in WIDTHS}, 'errors': errors})
                if missing or leaks or errors:
                    problems.append(f"hit {entry['hitId']}: missing {missing} leaks {leaks[:5]} errors {errors[:2]}")
                for w in WIDTHS:
                    o = shots[w]['overflow']
                    if o['document'] > 0 or o['outsideElements']:
                        problems.append(f"hit {entry['hitId']} overflow @{w}: {o}")
            await browser.close()
    finally:
        server.shutdown()
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    if before != after:
        problems.append('saved replay changed')
    kinds_seen = sorted(kinds)
    # In this saved replay cube/collection keys appear outside hit attack inputs; overload + skill are what the panel shows.
    if 'overload' not in kinds_seen:
        problems.append(f'saved replay lacks expected source kinds: {kinds_seen}')
    summary = {'evidence': 'synthetic_http_real_saved_replay', 'savedReplay': str(path), 'sha256': before, 'unchanged': before == after,
               'sourceKinds': kinds_seen, 'results': results, 'problems': problems, 'accepted': not problems}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(out), 'accepted': not problems, 'problems': problems, 'sourceKinds': kinds_seen}, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--saved-replay', required=True)
    raise SystemExit(asyncio.run(run(parser.parse_args())))

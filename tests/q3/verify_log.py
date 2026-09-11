"""Independent Q3 structural/invariant audit; never a game damage oracle."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import uuid


def verify(payload):
    if 'replay' in payload:
        assert payload.get('exportSchemaVersion') == 1, 'unsupported export schema'
        result = payload['replay']['result']
        log = result.get('damageLog')
        assert payload.get('collectionStatus') == (log['status'] if log is not None else 'not_collected'), 'collectionStatus mismatch'
    else:
        result = payload.get('result', payload)
        log = result.get('damageLog')
    if log is None:
        return {'status': 'not_collected', 'damage': None, 'hits': None, 'shots': None}
    if log.get('schemaVersion') != 1:
        return {'status': 'unsupported_schema', 'damage': None, 'hits': None, 'shots': None}
    if log.get('truncated') or log.get('status') != 'complete':
        return {'status': 'incomplete', 'damage': None, 'hits': None, 'shots': None}
    assert log.get('truncationReason') is None, 'complete log has truncation reason'
    rows = log['entries']
    assert len(rows) == log['eventCount'], 'event count mismatch'
    duration = result['conditions']['combat']['durationFrames']
    assert 1 <= duration <= 10800, 'duration outside 180-second bound'
    total, previous = 0, 0
    hits, shots = set(), set()
    states = set()
    for row in rows:
        assert row['hitId'] not in hits, 'duplicate hit ID'
        hits.add(row['hitId'])
        assert row['source'] == log['characterId'], 'wrong character'
        assert previous <= row['frame'] <= duration and row['frame'] >= 1, 'frame/order outside battle'
        previous = row['frame']
        assert math.isclose(row['seconds'], row['frame'] / 60, abs_tol=1e-12), 'seconds mismatch'
        assert math.isfinite(row['damage']) and row['damage'] >= 0, 'invalid damage'
        total += row['damage']
        assert math.isclose(total, row['cumulativeDamage'], rel_tol=1e-12, abs_tol=1e-6), 'cumulative mismatch'
        assert row['kind'] in (2, 3, 4), 'unsupported damage kind'
        if row['shotId'] is not None:
            shots.add(row['shotId'])
        if row['kind'] == 3:
            assert row['shotId'] is None, 'direct skill must not create a shot'
        if row['kind'] != 2:
            assert all(row.get(k) is None for k in ('fullCharge', 'chargeRatioRaw', 'actualChargeFrames', 'effectiveChargeFrames')), 'skill/extra charge must be null'
        ratio = row.get('chargeRatioRaw')
        if ratio is not None:
            assert 0 <= ratio <= 10000, 'invalid charge ratio'
        assert row['calculation']['damage'] == row['damage'], 'resolved calculation mismatch'
        assert row['calculation']['policy'] == result['conditions']['roundingPolicy'], 'policy mismatch'
        assert isinstance(row['calculation']['terms'], list), 'missing calculation terms'
        assert isinstance(row['buffs'], list), 'missing buffs'
        for flag in ('crit', 'core', 'fullBurst'):
            assert type(row['hit'][flag]) is bool, 'missing hit flag'
        assert type(row['ownBurstEffectActive']) is bool, 'missing own burst flag'
        states.add((row['ownBurstEffectActive'], row['hit']['fullBurst']))
    member = next(m for m in result['members'] if m['characterId'] == log['characterId'])
    assert math.isclose(total, log['totalDamage'], rel_tol=1e-12, abs_tol=1e-6), 'summary total mismatch'
    assert math.isclose(total, member['damage'], rel_tol=1e-12, abs_tol=1e-6), 'member total mismatch'
    # This is damage-associated distinct shots, not all fired shots or hit accuracy.
    assert len(shots) <= member['shots'], 'more damage-associated shots than fired shots'
    return {'status': 'complete_zero' if not rows and total == 0 else 'complete', 'damage': total,
            'hits': len(hits), 'shots': len(shots), 'firedShots': member['shots'],
            'durationFrames': duration, 'lastHitFrame': previous if rows else None,
            'ownTeamStates': [list(s) for s in sorted(states)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Native result, SavedSkillReplay, or damage-log export envelope')
    parser.add_argument('--output-root', type=Path, default=Path(__file__).resolve().parents[2] / 'artifacts/q3')
    args = parser.parse_args()
    output = args.output_root / ('log-' + uuid.uuid4().hex)
    output.mkdir(parents=True)
    raw = args.input.read_bytes()
    report = {'input': str(args.input.resolve()), 'sha256': hashlib.sha256(raw).hexdigest(), 'gameVerified': False}
    try:
        report['result'] = verify(json.loads(raw.decode('utf-8-sig')))
        report['acceptedComplete'] = report['result']['status'] in ('complete', 'complete_zero')
    except (AssertionError, KeyError, TypeError, ValueError, StopIteration) as error:
        report.update(acceptedComplete=False, error=f'{type(error).__name__}: {error}')
    (output / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(output), **report}, ensure_ascii=False, indent=2))
    return 0 if report['acceptedComplete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

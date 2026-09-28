"""Generates tests/ui/fixtures/client-f32-mock.json for UI stage A (mock only).

The client_f32 terms are computed here with Python struct binary32 arithmetic in the order written in
the engine report (5ced15a docs/hit-damage-client-f32.ko.md). This file is a UI rendering fixture: it is
NOT engine output, NOT an API response and NOT a game observation. The request/response wrapper shapes
(schema 3, v2 conversion, errors) are provisional until the Backend (I-BE) publishes the wire contract.
Legacy candidates are copied unchanged from hit-calculator-cases.json (real HitCalculator p02.3 output).
"""
import json
import math
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'hit-calculator-cases.json'
TARGET = HERE / 'client-f32-mock.json'


def f32(value):
    result = struct.unpack('<f', struct.pack('<f', value))[0]
    if not math.isfinite(result):
        raise ValueError('non-finite float32')
    return result


def add(a, b):
    return f32(a + b)


def mul(a, b):
    return f32(a * b)


def raw10000(rate):
    raw = round(rate * 10000)
    if raw / 10000 != rate:
        raise ValueError(f'rate {rate} is finer than 1/10000')
    return raw


def attack_long(hit):
    native = int(hit['statAttack'])
    groups = {}
    for buff in hit.get('attackBuffs', []) + hit.get('runtimeAttackBuffs', []):
        key = raw10000(buff['rate'])
        groups[key] = groups.get(key, 0) + buff.get('stacks', 1)
    total = native
    for raw, count in groups.items():
        numerator = native * raw * count
        quotient, remainder = divmod(abs(numerator), 10000)
        delta = quotient + (1 if remainder * 2 >= 10000 else 0)
        total += delta if numerator >= 0 else -delta
    for flat in hit.get('attackFlatBuffs', []):
        total += int(flat['amount'])
    return total


def client_terms(hit):
    attack = attack_long(hit)
    defence = 0 if hit['damageType'] == 'true' else int(hit['defense'])
    difference = attack - defence
    charge = 1.0
    if hit['fullCharge']:
        charge = mul(f32(hit['chargeBase']), add(1.0, f32(hit['chargeMultiplierBonus'])))
        charge = add(charge, f32(hit['chargeAdd']))
    kind = hit['damageType']
    addition = add(1.0, f32(hit['attackDamage']))
    addition = add(addition, f32(hit['pierceDamage']) if hit['pierce'] else 0.0)
    addition = add(addition, f32(hit['dotDamage']) if kind == 'dot' else 0.0)
    addition = add(addition, f32(hit['sequentialDamage']) if kind == 'sequential' else 0.0)
    addition = add(addition, f32(hit['trueDamage']) if kind == 'true' else 0.0)
    rate = lambda active, bonus: add(1.0, f32(bonus)) if active else 1.0
    crit, core = rate(hit['crit'], hit['critBonus']), rate(hit['core'], hit['coreBonus'])
    burst, distance = rate(hit['fullBurst'], hit['burstBonus']), rate(hit['properDistance'], hit['distanceBonus'])
    brk = rate(hit['parts'], hit['partsDamage'])
    reduction_rate = -add(f32(hit['damageTaken']), f32(hit['distributionDamage']) if kind == 'distribution' else 0.0)
    element = add(add(1.0, f32(hit['elementBase'])), f32(hit['elementBonus'])) if hit['elementAdvantage'] else 1.0
    base = f32(float(difference))
    base = mul(base, f32(hit['coefficient']))
    base = mul(base, f32(hit['statDamageRatio']))
    base = mul(base, charge)
    bonus = 1.0
    for value in (crit, core, burst, distance):
        bonus = add(bonus, f32(value - 1.0))
    extra = f32(add(brk, addition) - 1.0)
    reduction = f32(1.0 - reduction_rate)
    defence_factor = f32(1.0 - f32(hit['defenceRatioRate']))
    product = mul(base, bonus)
    for factor in (extra, reduction, defence_factor, element):
        product = mul(product, factor)
    damage = max(1, math.floor(product + 0.5))
    return attack, [
        {'name': 'effectiveAttack', 'before': hit['statAttack'], 'after': attack, 'operation': 'checked int64 grouped rate/10000, then flat grants'},
        {'name': 'effectiveDefense', 'before': hit['defense'], 'after': defence, 'operation': 'true damage: 0; otherwise integer defence'},
        {'name': 'difference', 'before': attack, 'after': difference, 'operation': 'checked int64 attack - defence; then cast float32'},
        {'name': 'base', 'before': difference, 'after': base, 'operation': 'float32 left-to-right damageRatio * statDamageRatio * chargeDamageRate'},
        {'name': 'B', 'before': 1, 'after': bonus, 'operation': 'float32 critical -> core -> burst -> range, each rate - 1 then add'},
        {'name': 'extra', 'before': 0, 'after': extra, 'operation': 'float32 breakRate + addDamageRate - 1; provisional mapping'},
        {'name': 'reduction', 'before': 0, 'after': reduction, 'operation': 'float32 1 - damageReductionRate; provisional mapping'},
        {'name': 'defenceRatio', 'before': hit['defenceRatioRate'], 'after': defence_factor, 'operation': 'float32 1 - defenceRatioRate'},
        {'name': 'product', 'before': base, 'after': product, 'operation': 'float32 left-to-right base * B * extra * reduction * defenceRatio * element'},
        {'name': 'final', 'before': product, 'after': damage, 'operation': 'MathF.Round AwayFromZero; max(1); checked int64'},
    ], damage


def main():
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    cases = {}
    variants = {'': (1, 0), '__defence_ratio_quarter': (1, 0.25), '__stat_damage_ratio_two': (2, 0)}
    for name, case in source['cases'].items():
        for suffix, (stat_ratio, defence_ratio) in variants.items():
            if suffix and name != 'crit_core_fullburst_distance':
                continue
            hit = dict(case['hit'], statDamageRatio=stat_ratio, defenceRatioRate=defence_ratio)
            attack, terms, damage = client_terms(hit)
            client = {'policy': 'client_f32', 'damage': damage, 'residual': None, 'relativeError': None, 'terms': terms}
            # Engine Compare order: 3 legacy candidates first, client_f32 appended fourth. Legacy candidates do
            # not consume the new ratios, so they are kept only for the neutral variant.
            legacy = case['candidates'] if not suffix else []
            cases[name + suffix] = {'hit': hit, 'comparison': {
                'rulesVersion': 'p02.4-client-f32', 'status': 'provisional_rounding', 'input': hit,
                'effectiveAttack': attack, 'observedDamage': None, 'candidates': legacy + [client]}}
    out = {
        'kind': 'ui_mock_not_engine_output',
        'generator': 'tests/ui/fixtures/make_client_f32_mock.py (Python struct binary32, engine 5ced15a order)',
        'wireStatus': 'provisional_until_backend_contract',
        'legacySource': 'hit-calculator-cases.json (HitCalculator.Compare p02.3)',
        'cases': cases,
        'provisionalErrors': {
            'fractionalAttack': {'status': 400, 'body': {'error': 'invalid_hit_input', 'message': 'client_f32 requires integer native attack; 144863.5 was not truncated.'}},
            'finerRate': {'status': 400, 'body': {'error': 'invalid_hit_input', 'message': 'attack rate 0.01401 is finer than 1/10000.'}},
        },
    }
    TARGET.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for name, case in cases.items():
        print(name, case['comparison']['candidates'][-1]['damage'])


if __name__ == '__main__':
    main()

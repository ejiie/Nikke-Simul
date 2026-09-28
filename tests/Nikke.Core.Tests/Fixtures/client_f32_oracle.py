"""Independent synthetic oracle; Python stdlib IEEE binary32 pack/unpack at each operation.
No product code, account input, game process, or numpy dependency. Run to regenerate golden JSON.
"""
import json
import math
import struct
from pathlib import Path


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def evaluate(name, attack, defence, rates):
    r = [f32(x) for x in rates]
    base = f32(attack - defence)
    for factor in r[:3]:
        base = f32(base * factor)
    bonus = f32(1)
    for rate in r[3:7]:
        bonus = f32(bonus + f32(rate - f32(1)))
    extra = f32(f32(r[7] + r[8]) - f32(1))
    reduction = f32(f32(1) - r[9])
    defence_factor = f32(f32(1) - r[10])
    result = base
    for factor in [bonus, extra, reduction, defence_factor, r[11]]:
        result = f32(result * factor)
    magnitude = abs(result)
    whole = math.floor(magnitude)
    rounded = math.copysign(whole + (magnitude - whole >= .5), result)
    return dict(name=name, attack=attack, defence=defence, rates=rates,
                baseBits=bits(base), bonusBits=bits(bonus), extraBits=bits(extra),
                productBits=bits(result), damage=int(max(1, rounded)))


neutral = [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1]
cases = [evaluate('neutral', 100, 30, neutral),
         evaluate('resolution_2p24', 16777217, 0, neutral),
         evaluate('long_subtract_before_float', 16777217, 16777216, [100] + neutral[1:]),
         evaluate('large_long_difference', 9223372036854775807, 9223372036854775782, neutral),
         evaluate('B_3p3', 100000000, 0, [1, 1, 1, 1.5, 2, 1.5, 1.3, 1, 1, 0, 0, 1]),
         evaluate('B_3p67', 100000000, 0, [1, 1, 1, 1.87, 2, 1.5, 1.3, 1, 1, 0, 0, 1]),
         evaluate('half_away', 1, 0, [2.5] + neutral[1:]),
         evaluate('minimum', 10, 20, neutral),
         evaluate('sequential_full_formula', 100000, 30925,
                  [1.014, 1.25, 3.7, 1.87, 2, 1.5, 1.3, 1.3, 1.121, -.15, .2, 1.1]),
         evaluate('zero_defence_factor', 100000, 0, neutral[:10] + [1, 1])]
path = Path(__file__).with_name('client-f32-golden.json')
path.write_text(json.dumps(dict(evidence='synthetic_python_struct_binary32', cases=cases), indent=2) + '\n', encoding='utf-8')
print(path)

"""P02 API audit with pinned historical observations and normalized Python round oracle.

Read-only account access. Individual account results go only to ignored artifacts/.
"""
import json
import math
from pathlib import Path
import urllib.request
import urllib.error
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
BASE = 'http://127.0.0.1:5180/api'

def request(path, payload=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token: headers['X-Nikke-Token'] = token
    if path == '/calculations/hit' and payload is not None:
        payload = {'inputSchemaVersion': 2, **payload}
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def main():
    sys.path.insert(0, str(ROOT / '.reference/nikke-calc'))
    from calculator.damage import calc_damage, default_hit_type
    boot = request('/bootstrap'); token = boot['token']
    connections = [c for c in boot['connections'] if c.get('accountId')]
    account_results = []; shared_buff_checks = 0
    def attack_oracle(native, buffs):
        rates = Counter()
        for buff in buffs: rates[buff['rate']] += buff.get('stacks',1)
        result = native
        for rate,count in rates.items():
            value = native * (rate * count)
            result += math.floor(value + .5) if value >= 0 else math.ceil(value - .5)
        return result
    for connection in connections:
        snapshot = request('/accounts/' + connection['accountId'] + '/snapshot')
        for char in snapshot['characters']:
            r = request('/snapshots/' + snapshot['id'] + '/characters/' + char['characterId'] + '/stats?scenarioLevel=400')
            if r['nativeStats']:
                for key in ('hp', 'atk', 'def'):
                    assert math.isclose(sum(s['value'][key] for s in r['steps']), r['nativeStats'][key], abs_tol=1e-7), (char['characterId'], key)
                assert not any(s['name'] in ('overload','accessoryRates') for s in r['steps'])
                source_rates = [float(line['normalizedValue']) for gear in char['equipment'] for line in gear['lines']
                                if line['presence']=='present' and line['optionType']=='StatAtk']
                assert source_rates == [b['rate'] for b in r['permanentBuffs']['attack']]
                if r['basicHit']:
                    assert r['basicHit']['statAttack']==r['nativeStats']['atk']
                    for skill_rates in ([], [.5], [.5,.3], source_rates[:1]):
                        skill_buffs=[{'source':f'audit:skill:{i}', 'rate':rate, 'stacks':1} for i,rate in enumerate(skill_rates)]
                        hit = {**r['basicHit'], 'runtimeAttackBuffs':skill_buffs}
                        comparison = request('/calculations/hit', {'input':hit}, token)
                        assert comparison['status'] == 'provisional_rounding'
                        assert comparison['effectiveAttack'] == attack_oracle(hit['statAttack'], hit['attackBuffs']+skill_buffs)
                        assert comparison['input']['statAttack']==r['nativeStats']['atk']
                        shared_buff_checks += 1
            account_results.append(r)
    # These are copied observations from the pinned C# golden fixture, not new game measurements.
    points = [
        (False,False,False,False,0,0,0,45024780), (True,False,False,False,0,0,0,58532212),
        (True,True,False,False,0,0,0,81044602), (False,False,True,False,0,0,0,101999134),
        (False,False,False,True,0,0,0,97721778), (False,True,True,False,0,0,0,124511524),
        (True,True,False,True,0,0,0,133741600), (False,False,True,True,0,0,0,154696132),
        (False,True,False,True,0,0,0,120234168), (False,True,True,True,0,0,0,177208522),
        (True,False,False,False,0,0,1.4293,142192292), (False,False,True,False,0,0,1.4293,247786478),
        (True,False,True,False,0,0,1.4293,280600080), (True,False,False,True,0,0,1.4293,270209101),
        (True,True,True,True,0,0,1.4293,463306234), (True,False,False,False,.484,0,0,86861800),
        (True,False,False,False,.484,0,1.4293,211013357), (True,False,False,False,.484,.042,1.4293,219875918)]
    observations = []
    for dist, burst, crit, core, b3, b4, b5, measured in points:
        context = dict(statAttack=901497, defense=100, coefficient=4.995, chargeApplicable=True, fullCharge=True,
                       chargeBase=10, critBonus=1.2654, coreBonus=1.1704, properDistance=dist,
                       fullBurst=burst, crit=crit, core=core, attackDamage=b3, damageTaken=b4,
                       elementAdvantage=b5 != 0, elementBase=0, elementBonus=b5)
        r = request('/calculations/hit', {'input': context, 'observedDamage': measured}, token)
        # Same semantic factors, fixed binary64 operation order: isolate quantization only.
        p = (901497 - 100) * 4.995 * 10
        expected = max(round(p * (1 + .3*dist + .5*burst + 1.2654*crit + 1.1704*core) * (1+b3) * (1+b4) * (1+b5)), 1)
        assert r['candidates'][1]['damage'] == expected
        original = calc_damage(901497, {
            'crit_rate': float(crit), 'crit_dmg': 76.54, 'core_dmg_pct': 17.04,
            'atk_dmg_pct': b3*100, 'received_dmg': b4*100,
            'is_element_match': b5 != 0, 'element_bonus_pct': (b5-.1)*100 if b5 else 0,
        }, {'damage_coeff':499.5,'full_charge_mult':1000,'core_dmg_mult':200},
            default_hit_type(is_normal_atk=True,is_full_charge=True,is_optimal_range=dist,is_full_burst=burst,is_core=core),
            enemy_def=100, expected=True)
        r['upstreamOriginalDamage'] = original['damage']
        assert original['damage'] == expected, ('upstream arithmetic difference', original['damage'], expected)
        observations.append(r)
    boundary = []
    for attack in (1, 3, 17, 99, 1001):
        for coefficient in (.015, .125, .5, 1.9, 2.5, 3.5):
            c = dict(statAttack=attack, coefficient=coefficient, crit=True, critBonus=.5, attackDamage=.15, damageTaken=.15)
            r = request('/calculations/hit', {'input': c}, token)
            assert r['candidates'][1]['damage'] == max(round((attack*coefficient)*(1+.5)*1.15*1.15),1)
            boundary.append(r)
    for invalid in ({'input':{'attack':100}}, {'inputSchemaVersion':2,'input':{'statAttack':100,'attack':100}},
                    {'inputSchemaVersion':2,'input':{'statAttack':100,'attackBuffs':None}}):
        raw=urllib.request.Request(BASE+'/calculations/hit',data=json.dumps(invalid).encode(),
            headers={'Content-Type':'application/json','X-Nikke-Token':token})
        try: urllib.request.urlopen(raw); raise AssertionError('Invalid/obsolete hit input accepted')
        except urllib.error.HTTPError as error: assert error.code==400
    output = ROOT / 'artifacts/p02-buff-fix'; output.mkdir(parents=True, exist_ok=True)
    (output/'account-stats.json').write_text(json.dumps(account_results, ensure_ascii=False, indent=2),encoding='utf-8')
    (output/'rounding-comparison.json').write_text(json.dumps({'observations':observations,'synthetic':boundary},indent=2),encoding='utf-8')
    counts = {s:sum(r['status']==s for r in account_results) for s in sorted({r['status'] for r in account_results})}
    codes = {}
    for r in account_results:
        for issue in r['issues']: codes[issue['code']] = codes.get(issue['code'],0)+1
    report = {'accountResults':len(account_results),'statusCounts':counts,'issueCounts':codes,
              'sharedBuffChecks':shared_buff_checks,'invalidRequestChecks':3,
              'historicalPoints':len(points),'pythonRoundingChecks':len(points)+len(boundary),
              'residualRanges':{policy: [min(r['candidates'][i]['residual'] for r in observations),max(r['candidates'][i]['residual'] for r in observations)]
                                for i,policy in enumerate(['legacy_term_floor','final_round_even','nested_floor'])}}
    (output/'audit-summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__ == '__main__': main()

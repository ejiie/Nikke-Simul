"""Pin the selected characters' official graphs without flattening skill phases.

Game data stays in ignored data/local/runtime. This exports evidence; it does not
claim that importing a function means the combat interpreter supports it.
"""
import hashlib
import json
import re
from pathlib import Path
from prepare_combat_conditions import assemble_profiles

ROOT = Path(__file__).resolve().parents[2]
# Original five, then SSR batch 1 in 묑카엘-account combat-power order (S-SKILL-1; Director replaced the 5th slot with #5101 레드 후드). #5175 신데렐라 : 크리스탈 웨이브
# is absent from every pinned source (skill_chains/roledata_clean/blabla_roledata) and is NOT assembled.
TARGETS = ('리타', '블랑', '누아르', '앨리스', '모더니아',
           '스노우 화이트', '라피 : 레드 후드', '맥스웰', '홍련 : 흑영', '레드 후드')
PHASES = ('before_use', 'before_hurt', 'after_use', 'after_hurt')


def gauge_constants(table, config):
    """Verify the derived table against its pinned ConfigBattle KV source; no fill formula inferred."""
    fields = {'per_sec': 'sec', 'use_skill': 'use_skill', 'skill_hit': 'skill_hit',
              'shot_hit': 'shot_hit', 'hurt': 'hurt', 'cover_hurt': 'cover_hurt', 'empty_ammo': 'empty_ammo'}
    pairs = [('burst_energy_max', table['burst_energy_max'])]
    pairs += [('ulti_gauge_' + suffix, table['ally'][key]) for key, suffix in fields.items()]
    pairs += [('ulti_gauge_kill_' + suffix, table['ally']['kill'][key])
              for key, suffix in [('minion', 'm'), ('elite', 'e'), ('centurion', 'c'), ('boss', 'b')]]
    for key, value in pairs:
        if type(value) is not int or value < 0 or value != int(config[key]):
            raise ValueError('Gauge source mismatch: ' + key)
    if table['burst_energy_max'] <= 0:
        raise ValueError('Gauge capacity must be positive')
    return {'capacityRaw': table['burst_energy_max'], 'allyRaw': dict(pairs[1:]),
            'formulaStatus': 'unverified', 'unit': 'raw'}


def burst_connection(character, weapon, role):
    # Stage labels map to the numerals the official chain itself stores (verified below against both sources).
    # AllStep/NextStep (#5101 only) are numerals 5/6 in the source; the team-burst controller does not support
    # them (I->II->III only), so no AllStep chain semantics are invented here.
    steps = {'Step1': 1, 'Step2': 2, 'Step3': 3, 'StepFull': 4, 'AllStep': 5, 'NextStep': 6}
    burst = weapon['burst']
    for key, normalized in [('use_burst_skill', 'useBurstSkill'), ('change_burst_step', 'changeBurstStep')]:
        if steps[role[key]] != character[key] or role[key] != burst[normalized]:
            raise ValueError('Burst stage source mismatch: ' + key)
    for key, normalized in [('burst_apply_delay', 'applyDelaySec'), ('burst_duration', 'durationSec')]:
        if role[key] != character[key] or role[key] != round(burst[normalized] * 100):
            raise ValueError('Burst time source mismatch: ' + key)
    for key, normalized in [('burst_energy_pershot', 'energyPerShot'),
                            ('target_burst_energy_pershot', 'targetEnergyPerShot'),
                            ('full_charge_burst_energy', 'fullChargeEnergy')]:
        if role['shot'][key] != burst[normalized]:
            raise ValueError('Weapon gauge source mismatch: ' + key)
    replacements = set()
    for slot in character['skills'].values():
        for definition in slot['levels'].values():
            body = definition.get('skill') or {}
            if body.get('skill_type') == 7:
                replacements.add(body['skill_value_data'][2]['skill_value'])
    return {'step': character['use_burst_skill'], 'nextStep': character['change_burst_step'],
            'applyDelayCs': character['burst_apply_delay'], 'fullBurstDurationCs': character['burst_duration'],
            'shotId': character['shot_id'], 'energyPerShotRaw': burst['energyPerShot'],
            'targetEnergyPerShotRaw': burst['targetEnergyPerShot'], 'fullChargeEnergyRaw': burst['fullChargeEnergy'],
            'unresolvedReplacementShotIds': sorted(replacements)}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def skill_roots(level):
    # Passive function_ids and active function_phases are distinct, ordered sources.
    roots = list(level.get('function_ids', []))
    phases = level.get('function_phases', {})
    unknown = set(phases) - set(PHASES)
    if unknown:
        raise ValueError(f'Unreviewed skill phase: {sorted(unknown)}')
    for phase in PHASES:
        roots.extend(phases.get(phase, []))
    return roots


def graph_closure(chains, roots):
    functions, skills, missing = {}, {}, set()
    pending = list(roots)
    while pending:
        key = str(pending.pop())
        if key == '0' or key in functions:
            continue
        function = chains.get('functions', {}).get(key)
        if function is None:
            missing.add('function:' + key)
            continue
        functions[key] = function
        pending.extend(function.get('connected_function', []))
        if function.get('function_type') == 72:  # official UseCharacterSkillId
            skill_id = str(function['function_value'])
            if skill_id in skills:
                continue
            skill = chains.get('character_skills', {}).get(skill_id)
            if skill is None:
                missing.add('character_skill:' + skill_id)
            else:
                skills[skill_id] = skill
                pending.extend(skill_roots(skill))
    return functions, skills, sorted(missing)


def weapon_change_profile(role, slot_name, level):
    """Replacement-weapon facts that exist only as game description text (no shot table is pinned).

    Parsed from the pinned public roster description: charge time, full-charge multiplier, magazine and pierce.
    Only the ChangeWeapon bodies measured in shots (Snow White, Maxwell) are profiled; every other ChangeWeapon
    keeps the base-weapon fallback documented in docs/p03-skill-runtime.ko.md.
    """
    skill = role['skills'][slot_name]
    text = re.sub(r'<[^>]+>', '', skill['description'])
    charge = re.search(r'Charge Time:\s*([0-9.]+)\s*sec', text)
    full = re.search(r'Full Charge Damage:\s*([0-9.]+)%', text)
    ammo = re.search(r'Max Ammunition Capacity:\s*\{description_value_(\d+)\}', text)
    if not (charge and full and ammo):
        raise ValueError('Weapon-change description is missing charge/full-charge/ammo: ' + role['name'])
    values = skill['description_value_list'][int(ammo.group(1)) - 1]['description_value']
    if len(values) != 10 or any(v != values[0] for v in values):
        raise ValueError('Magazine is not level-invariant: ' + role['name'])
    return {'charge_time_sec': float(charge.group(1)), 'full_charge_rate': float(full.group(1)) / 100,
            'max_ammo': int(values[0]), 'pierce': 'Additional Effect: Pierce' in text,
            'source': 'blabla_roledata.json roster/%s/skills/%s/description' % (role['name_code'] if 'name_code' in role else role['name'], slot_name)}


def assemble(chains, roles, names, upstream_skills, upstream_characters, source_roles=None):
    selected, functions, character_skills, missing = {}, {}, {}, []
    for name in TARGETS:
        ids = [key for key, value in names.items() if value == name]
        if len(ids) != 1:
            raise ValueError('Ambiguous character: ' + name)
        key = ids[0]
        character = chains.get('characters', {}).get(key)
        weapon = roles.get(key, {}).get('weaponData')
        if not character or not weapon:
            raise ValueError('Missing official character or weapon: ' + name)
        roots = []
        for slot in character['skills'].values():
            for level in slot['levels'].values():
                roots.extend(skill_roots(level))
        fs, cs, ms = graph_closure(chains, roots)
        functions.update(fs); character_skills.update(cs); missing.extend(ms)
        selected[key] = {'name': name, 'weapon': weapon, 'official': character,
                         'upstreamSkills': upstream_skills[name], 'upstreamCharacter': upstream_characters[name],
                         'functionIds': sorted(fs, key=int), 'missing': ms,
                         'skillExecutionStatus': 'not_connected'}
        if source_roles is not None:
            role = source_roles['roster'][key]
            for level in character['skills']['burst']['levels'].values():
                body = level.get('skill') or {}
                if body.get('skill_type') == 7 and body.get('duration_type') == 2:
                    body['weapon_change'] = weapon_change_profile(role, 'burst', level)
            selected[key]['sourceRole'] = {'squad': role['squad'], 'skills': role['skills'],
                                           'burstDurationCs': role['burst_duration']}
            selected[key]['burstConnection'] = burst_connection(character, weapon, role)
    return {'schemaVersion': 1, 'characters': selected, 'functions': functions,
            'characterSkills': character_skills, 'missing': sorted(set(missing)),
            'skillExecutionStatus': 'not_connected'}


def main():
    sources = json.loads((ROOT / 'docs/p03-source-manifest.json').read_text(encoding='utf-8-sig'))
    inputs = {}
    hashes = {}
    for source in sources:
        if 'inputKey' not in source:
            continue
        path = ROOT / source['sourceRoot'] / source['path']
        content = path.read_bytes()
        if digest(content) != source['sha256']:
            raise ValueError('P03 source changed; review before repinning: ' + source['path'])
        inputs[source['inputKey']] = json.loads(content)
        hashes[source['inputKey']] = source['sha256']
    catalog = assemble(inputs['chains'], inputs['roles'], inputs['names'], inputs['skills'], inputs['characters'], inputs['sourceRoles'])
    catalog['gaugeConstants'] = gauge_constants(inputs['gaugeTable'], inputs['gaugeConfig'])
    catalog['connectionSchemaVersion'] = 1
    catalog['sourceHashes'] = hashes
    catalog['combatProfiles'] = assemble_profiles(inputs['sourceRoles'], hashes['sourceRoles'])
    content = json.dumps(catalog, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    version = digest(content)
    folder = ROOT / 'data/local/runtime' / version
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / 'catalog.json'
    if target.exists() and target.read_bytes() != content:
        raise ValueError('Immutable runtime catalog conflict')
    target.write_bytes(content)
    pointer = folder.parent / 'current.json'
    pending = pointer.with_suffix('.tmp')
    pending.write_text(json.dumps({'id': version, 'file': 'catalog.json', 'schemaVersion': 1}), encoding='utf-8')
    pending.replace(pointer)
    print(json.dumps({'runtimeDataId': version, 'characters': len(catalog['characters']),
                      'functions': len(catalog['functions']), 'characterSkills': len(catalog['characterSkills']),
                      'missing': catalog['missing'], 'skillExecutionStatus': 'not_connected'}))


if __name__ == '__main__':
    main()

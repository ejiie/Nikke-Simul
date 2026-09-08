"""Pin the five selected characters' official graphs without flattening skill phases.

Game data stays in ignored data/local/runtime. This exports evidence; it does not
claim that importing a function means the combat interpreter supports it.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = ('리타', '블랑', '누아르', '앨리스', '모더니아')
PHASES = ('before_use', 'before_hurt', 'after_use', 'after_hurt')


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
            selected[key]['sourceRole'] = {'squad': role['squad'], 'skills': role['skills'],
                                           'burstDurationCs': role['burst_duration']}
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
    catalog['sourceHashes'] = hashes
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

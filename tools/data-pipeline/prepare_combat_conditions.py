"""Enrich an existing immutable runtime catalog using the pinned PUBLIC roster.

No collection/network/account access. Explicit runtime output directory required.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ELEMENTS = ('Fire', 'Water', 'Wind', 'Iron', 'Electronic')
WEAPONS = ('AR', 'SMG', 'SG', 'SR', 'MG', 'RL')


def source_record():
    manifest = json.loads((ROOT / 'docs/p03-source-manifest.json').read_text(encoding='utf-8-sig'))
    return next(row for row in manifest if row.get('inputKey') == 'sourceRoles')


def assemble_profiles(roster, sha256):
    characters = {}
    for id, role in sorted(roster['roster'].items()):
        low, high = role.get('bonusrange_min'), role.get('bonusrange_max')
        element, weapon = role.get('element'), role.get('shot', {}).get('weapon_type')
        if type(low) is not int or type(high) is not int or not 0 <= low <= high <= 100:
            raise ValueError('Missing/invalid character range: ' + id)
        if element not in ELEMENTS or weapon not in WEAPONS:
            raise ValueError('Missing/invalid character element/weapon: ' + id)
        characters[id] = {'characterId': id, 'name': role['name'], 'weaponType': weapon,
                          'bonusRangeMin': low, 'bonusRangeMax': high, 'element': element}
    return {'schemaVersion': 1, 'source': {'path': 'Database/raw/blabla_roledata.json',
        'sha256': sha256, 'version': 'sha256:' + sha256, 'origin': roster['_source'], 'locale': roster['locale']},
        'characters': characters}


def load_profiles(path=None):
    record = source_record()
    path = Path(path) if path else Path(record['sourceRoot']) / record['path']
    content = path.read_bytes()
    sha = hashlib.sha256(content).hexdigest()
    if sha != record['sha256']:
        raise ValueError('Public roster changed; explicit source review/repin required')
    return assemble_profiles(json.loads(content), sha)


def enrich_runtime(runtime_root, profiles):
    runtime_root = Path(runtime_root)
    pointer = runtime_root / 'current.json'
    old = json.loads(pointer.read_text(encoding='utf-8-sig'))
    version = old['id']
    if len(version) != 64 or any(c not in '0123456789abcdef' for c in version):
        raise ValueError('Invalid runtime ID')
    content = (runtime_root / version / 'catalog.json').read_bytes()
    if hashlib.sha256(content).hexdigest() != version:
        raise ValueError('Runtime catalog hash mismatch')
    catalog = json.loads(content)
    if catalog.get('schemaVersion') != 1:
        raise ValueError('Unsupported runtime schema')
    catalog['combatProfiles'] = profiles
    return write_runtime(runtime_root, catalog)


def write_runtime(runtime_root, catalog):
    content = json.dumps(catalog, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    version = hashlib.sha256(content).hexdigest()
    folder = Path(runtime_root) / version
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / 'catalog.json'
    if target.exists() and target.read_bytes() != content:
        raise ValueError('Immutable runtime conflict')
    target.write_bytes(content)
    pointer = folder.parent / 'current.json'
    pending = pointer.with_suffix('.tmp')
    pending.write_text(json.dumps({'id': version, 'file': 'catalog.json', 'schemaVersion': 1}), encoding='utf-8')
    pending.replace(pointer)
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--source-roster', type=Path)
    args = parser.parse_args()
    profiles = load_profiles(args.source_roster)
    print(json.dumps({'runtimeDataId': enrich_runtime(args.runtime_root, profiles),
                      'characters': len(profiles['characters']), 'source': profiles['source']}))


if __name__ == '__main__':
    main()

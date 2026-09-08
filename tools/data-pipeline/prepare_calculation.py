"""Build immutable P02 static inputs from pinned local references, never personal builds."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = ['stat_table.csv', 'equip_stat_table.json', 'cube_base_table.json', 'cube_effect_table.json', 'roledata_clean.json']

def main():
    provenance = json.loads((ROOT / 'docs/p02-source-manifest.json').read_text(encoding='utf-8-sig'))
    for entry in provenance:
        source = ROOT / entry['sourceRoot'] / entry['path']
        if hashlib.sha256(source.read_bytes()).hexdigest() != entry['sha256']:
            raise RuntimeError('P02 pinned source changed: ' + entry['path'])
    legacy = ROOT / '.reference/legacy-simulator/Database/processed'
    upstream = ROOT / '.reference/nikke-calc'
    files = {name: (legacy / name).read_bytes() for name in FILES}
    for name, rel in [('collection.json', 'data/base_stat_tables/collection.json'), ('name_codes.json', 'data/name_codes.json'), ('parsed_nikke.json', 'data/parsed_nikke.json')]:
        files[name] = (upstream / rel).read_bytes()
    hashes = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
    version = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    output = ROOT / 'data/local/calculation' / version
    output.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        target = output / name
        if target.exists() and target.read_bytes() != content:
            raise RuntimeError('Immutable calculation data conflict')
        target.write_bytes(content)
    manifest = {'id': version, 'fileHashes': hashes,
                'sources': {'legacy': 'P00 pinned legacy snapshot', 'collection.json': 'P00 pinned nikke-calc collection grade/level table'}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    pointer = ROOT / 'data/local/calculation/current.json'
    pending = pointer.with_suffix('.tmp')
    pending.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    pending.replace(pointer)
    print(f'P02 calculation tables prepared: {len(files)} files; {version}')

if __name__ == '__main__':
    main()

"""Q-IMG acceptance assertions for captured CLI/API output, independent of producers.

This validates evidence; it never refreshes caches or starts/stops a server.
The legacy diagnose.py remains an explicit failing-baseline reproduction.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

CATALOGS = ('account-presentation.json', 'spec-presentation.json')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def capture(directory):
    """Capture public mapping and bytes for a before/after comparison, without writes."""
    directory = Path(directory).resolve()
    hashes, mappings = {}, {}
    for name in ('presentation.json', *CATALOGS):
        path = directory / name
        if not path.exists():
            continue
        manifest = read(path)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        fields = {'presentation.json': ('characters',), 'account-presentation.json': ('consoles', 'cubes'),
                  'spec-presentation.json': ('supportDefinitions', 'overloadOptions')}[name]
        for field in fields:
            mappings[field] = manifest.get(field, [])
        for asset in manifest.get('assets', []):
            target = (directory / asset['path']).resolve()
            assert target.is_relative_to(directory), 'asset path escaped cache'
            assert target.is_file(), f'missing asset: {asset["path"]}'
            raw = target.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            assert digest == asset['sha256'], f'asset checksum mismatch: {asset["path"]}'
            if asset['path'].startswith('assets/'):
                assert raw.startswith(b'\x89PNG\r\n\x1a\n') or (raw[:4] == b'RIFF' and raw[8:12] == b'WEBP'), 'not PNG/WEBP'
            hashes[asset['path']] = digest
    return {'hashes': hashes, 'mappings': mappings}


def assert_success(presentation, status, snapshot, before=None):
    assert presentation.get('unresolved') == [], 'unresolved errors remained or were omitted'
    assert status.get('status') == 'succeeded', 'API did not transition to succeeded'
    assert set(CATALOGS).issubset(snapshot['hashes']), 'catalog was never generated'
    for field in ('characters', 'consoles', 'cubes', 'supportDefinitions', 'overloadOptions'):
        assert snapshot['mappings'].get(field), f'missing/empty mapping: {field}'
    if before:
        for field, rows in before['mappings'].items():
            assert snapshot['mappings'].get(field) == rows, f'mapping changed: {field}'
        for path, digest in before['hashes'].items():
            if path.startswith('assets/'):
                assert snapshot['hashes'].get(path) == digest, f'image bytes changed: {path}'


def assert_failure(presentation, status, expected, snapshot, before=None):
    """Expected records use the existing path/error/cached contract; check fixed wire later."""
    unresolved = presentation.get('unresolved')
    assert isinstance(unresolved, list), 'missing failure records'
    assert len(unresolved) == len(expected), 'failure count changed'
    paths = [row.get('path') for row in unresolved]
    assert len(paths) == len(set(paths)), 'duplicate failure records'
    assert set(paths) == {row['path'] for row in expected}, 'wrong failed resources'
    assert status.get('status') in ('partial', 'failed'), 'failure was reported as success/idle'
    for wanted in expected:
        actual = next(row for row in unresolved if row['path'] == wanted['path'])
        assert actual.get('error'), 'safe cause code missing'
        assert bool(actual.get('cached', False)) == wanted['cached'], 'cache availability misreported'
        if wanted['cached']:
            assert before is not None, 'cached claim requires before evidence'
            path = wanted['path']
            assert path in before['hashes'], 'cached claim without old file'
            assert snapshot['hashes'].get(path) == before['hashes'][path], f'old cache lost: {path}'
    message = status.get('message') or ''
    assert message.strip(), 'failure message missing'
    catalog_count = sum(row['path'] in CATALOGS for row in expected)
    image_count = len(expected) - catalog_count
    if catalog_count:
        assert '카탈로그' in message, 'catalog errors presented only as image failures'
        number = re.search(r'카탈로그[^0-9]{0,30}([0-9]+)', message)
        assert number and int(number[1]) == catalog_count, 'catalog count in message is wrong or absent'
    if image_count:
        assert '이미지' in message, 'image errors missing from message'
        number = re.search(r'이미지(?!\s*카탈로그)[^0-9]{0,30}([0-9]+)', message)
        assert number and int(number[1]) == image_count, 'image count in message is wrong or absent'
    if catalog_count and not image_count:
        assert not re.search(r'이미지\s*' + str(catalog_count) + r'\s*개', message), 'catalog count mislabeled as image count'
    if not any(row['cached'] for row in expected):
        assert not re.search(r'기존 이미지(?:는|를)?\s*유지', message), 'no-cache result claims preserved images'


def assert_recovery(failed_presentation, failed_status, presentation, status, snapshot, before):
    assert failed_presentation.get('unresolved'), 'recovery lacks a preceding failure'
    assert failed_status.get('status') in ('partial', 'failed'), 'recovery did not start from an error'
    assert_success(presentation, status, snapshot, before)
    if 'revision' in status and 'revision' in failed_status:
        assert status['revision'] > failed_status['revision'], 'recovery did not advance revision'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--presentation-dir', type=Path, required=True)
    parser.add_argument('--status-json', type=Path, required=True, help='Captured actual API status JSON')
    parser.add_argument('--expected-failures', type=Path, help='Explicit path/cached list; omitted means fixed success')
    parser.add_argument('--before-json', type=Path, help='Earlier capture() output from the same isolated case')
    args = parser.parse_args()
    snapshot = capture(args.presentation_dir)
    presentation = read(args.presentation_dir / 'presentation.json')
    before = read(args.before_json) if args.before_json else None
    if args.expected_failures:
        assert_failure(presentation, read(args.status_json), read(args.expected_failures), snapshot, before)
    else:
        assert_success(presentation, read(args.status_json), snapshot, before)
    print(json.dumps({'acceptedEvidence': True, 'kind': 'captured_output_assertions_not_execution',
                      'expected': 'failure' if args.expected_failures else 'fixed_success'}))


if __name__ == '__main__':
    main()

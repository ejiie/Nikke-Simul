"""Read-only source audit and offline replay of presentation preparation in a UUID sandbox.

No account DB, cookies, source writes, server POST, or public network requests.
Dependency restoration below is a test control, not a product patch.
"""
import argparse
import contextlib
import hashlib
import importlib
import io
import json
from pathlib import Path
import shutil
import sys
import urllib.request
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/data-pipeline'))
import presentation_assets as presentation
import account_presentation_assets as account
import spec_presentation_assets as spec


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def safe(root, relative):
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('Path outside requested root')
    return target


def signature(raw):
    if raw.startswith(presentation.PNG):
        return 'PNG'
    if raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':
        return 'WEBP'
    return 'not_image'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-data', type=Path, required=True)
    parser.add_argument('--deployed-root', type=Path, required=True)
    args = parser.parse_args()
    run = ROOT / 'artifacts/image-collection-qa' / uuid.uuid4().hex
    run.mkdir(parents=True)
    source = args.source_data.resolve() / 'presentation'
    destination = run / 'isolated/presentation'
    destination.mkdir(parents=True)
    manifests = {name: read(source / name) for name in ('presentation.json', 'account-presentation.json', 'spec-presentation.json')}
    report = {'evidence': 'current_source_cache_read_and_offline_actual_product_functions',
              'run': str(run), 'sourceData': str(args.source_data.resolve()),
              'deployedRoot': str(args.deployed_root.resolve()), 'originalUnresolved': manifests['presentation.json']['unresolved'],
              'originalWrites': False, 'serverPosts': 0, 'publicRequests': 0}
    tracked = {}
    def copy(relative):
        src = safe(source, relative)
        target = safe(destination, relative)
        tracked[relative] = sha(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
    audits = []
    for name, manifest in manifests.items():
        copy(name)
        rows = []
        for entry in manifest['assets']:
            src = safe(source, entry['path'])
            raw = src.read_bytes()
            kind = signature(raw)
            row = dict(path=entry['path'], sha256=sha(src), hashMatches=sha(src) == entry['sha256'],
                       bytes=len(raw), signature=kind)
            if entry['path'].startswith('assets/'):
                assert kind in ('PNG', 'WEBP'), f'Invalid image: {entry["path"]}'
                # Decode/verify if Pillow is available; explicitly record when it is not.
                try:
                    from PIL import Image
                except ImportError:
                    row['decode'] = 'not_available'
                else:
                    with Image.open(io.BytesIO(raw)) as image:
                        row['dimensions'] = list(image.size)
                        image.verify()
                    row['decode'] = 'verified'
            assert row['hashMatches'], f'Cache checksum mismatch: {entry["path"]}'
            copy(entry['path'])
            rows.append(row)
        audits.append(dict(manifest=name, assets=rows))
    copy('blablalink-index.json')
    imported = read(source / 'import-manifest.private.json')
    tracked['import-manifest.private.json'] = sha(source / 'import-manifest.private.json')
    # Preserve only public image mapping fields required by the product; no ZIP path/private metadata.
    imported = dict(characters=[{k: c[k] for k in ('displayName', 'portraitPath', 'characterUid')} for c in imported['characters']],
                    files=[{k: f[k] for k in ('path', 'sha256', 'byteLength')} for f in imported['files']], zipSha256=imported.get('zipSha256'))
    (destination / 'import-manifest.private.json').write_text(json.dumps(imported), encoding='utf-8')
    report['cacheAudits'] = audits
    report['deployedMissingDependencies'] = {rel: not (args.deployed_root / rel).exists() for rel in
                                           ('data/local/calculation/current.json', 'data/local/game-catalog.json')}
    # Emulate the deployed split layout: code-local data missing, presentation under external data.
    isolated_code = run / 'isolated/code'
    isolated_code.mkdir()
    presentation.ROOT = account.ROOT = spec.ROOT = isolated_code
    attempts = []
    def forbidden_network(*a, **k):
        attempts.append('blocked')
        raise AssertionError('Unexpected network request in offline reproduction')
    with patch.object(urllib.request, 'urlopen', forbidden_network):
        failures = []
        for name, module in [('account-presentation.json', account), ('spec-presentation.json', spec)]:
            before = sha(destination / name)
            try:
                module.prepare(destination)
            except FileNotFoundError as error:
                failures.append(dict(manifest=name, error=type(error).__name__, missingFile=str(error.filename),
                                     previousManifestPreserved=sha(destination / name) == before))
            else:
                raise AssertionError('Expected missing code-local dependency')
        report['isolatedDirectFailures'] = failures
        with contextlib.redirect_stdout(io.StringIO()) as receipt:
            failed = presentation.build(destination, include_account_assets=True)
        report['isolatedBuildBefore'] = json.loads(receipt.getvalue())
        assert failed['unresolved'] == report['originalUnresolved'], 'Did not reproduce exact two current failures'
        # Read only public calculation catalog/table; never account DB/session.
        calculation = read(args.source_data / 'calculation/current.json')
        public_files = ['calculation/current.json', 'calculation/' + calculation['id'] + '/cube_effect_table.json', 'game-catalog.json']
        public_before = {}
        for rel in public_files:
            src = safe(args.source_data, rel)
            target = safe(isolated_code / 'data/local', rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            public_before[rel] = sha(src)
            shutil.copyfile(src, target)
        with contextlib.redirect_stdout(io.StringIO()) as receipt:
            recovered = presentation.build(destination, include_account_assets=True)
        report['isolatedBuildAfterDependencyControl'] = json.loads(receipt.getvalue())
        assert recovered['unresolved'] == [], 'Dependency restoration did not recover'
        report['controlCopiedPublicFiles'] = public_before
        report['publicDependenciesUnchanged'] = all(sha(safe(args.source_data, rel)) == value for rel, value in public_before.items())
    assert not attempts, 'An unexpected network attempt occurred'
    report['offlineNetworkAttempts'] = len(attempts)
    report['sourceCacheUnchanged'] = all(sha(safe(source, rel)) == value for rel, value in tracked.items())
    report['sourceFileCountChecked'] = len(tracked)
    assert report['sourceCacheUnchanged'] and report['publicDependenciesUnchanged']
    (run / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (run / 'source-hashes.json').write_text(json.dumps(tracked, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'cacheAudits'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

"""GET-only public presentation/status and four cached image probes on localhost.

Stores metadata/hashes only, with no account APIs or image refresh calls.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[2]


def get(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        raw = response.read(8 * 1024 * 1024)
        return raw, dict(url=url, status=response.status, contentType=response.headers.get('Content-Type'),
                         bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    run = ROOT / 'artifacts/image-collection-qa' / ('http-' + uuid.uuid4().hex)
    run.mkdir(parents=True)
    result = {'requests': [], 'serverPosts': 0, 'publicRequests': 0}
    for port in (5180, 5181):
        url = f'http://127.0.0.1:{port}/api/presentation/status'
        try:
            raw, receipt = get(url)
            receipt['body'] = json.loads(raw)
        except (OSError, ValueError) as error:
            receipt = dict(url=url, error=type(error).__name__)
        result['requests'].append(receipt)
    raw, receipt = get('http://127.0.0.1:5180/api/presentation')
    catalog = json.loads(raw)
    receipt['counts'] = {k: len(catalog.get(k, [])) for k in ('characters', 'unresolved', 'consoles', 'cubes', 'supportDefinitions', 'overloadOptions')}
    receipt['unresolved'] = catalog['unresolved']
    result['requests'].append(receipt)
    samples = [('console', catalog['consoles'][0]), ('cube', catalog['cubes'][0]),
               ('equipment', next(s for s in catalog['supportDefinitions'] if s['kindCode'] == 'equipment')),
               ('collection', next(s for s in catalog['supportDefinitions'] if s['kindCode'] == 'collection'))]
    for kind, sample in samples:
        relative = sample['imagePath']
        assert relative.startswith('/editor/assets/') and '..' not in relative
        raw, receipt = get('http://127.0.0.1:5180' + relative)
        receipt.update(kind=kind, resourceId=sample.get('id', sample.get('definitionUid')), displayName=sample['displayName'], imagePath=relative)
        receipt['signature'] = raw[:12].hex()
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as image:
            receipt['format'] = image.format
            receipt['dimensions'] = list(image.size)
            image.verify()
        receipt['imageVerified'] = True
        result['requests'].append(receipt)
    (run / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(run), **result}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

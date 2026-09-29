"""Prepare public display-only bosses into an explicit, isolated presentation root.

Korean names are extracted from Korean sources, never translated from English.
Unresolved names remain diagnostics; English names and source IDs/URLs stay internal.
"""
import argparse
import hashlib
import html
import json
import re
import urllib.request
import uuid
from pathlib import Path

ENIKK = 'https://enikk.app'
QUERY = 'query { soloRaidSummaries { wave_name monster_image raid_number } }'
# Korean reporting of the first solo raid; Korean official announcement reproduced by the event archive.
NAME_SOURCES = [
    {'seasons': [1, 29], 'url': 'https://www.inven.co.kr/webzine/news/?news=284716&site=nikke',
     'pattern': r"솔로 레이드\s*['‘]([^'’<>]+)['’]"},
    {'seasons': [41], 'url': 'https://dal.wiki/t/3mfSf1w8xI4j/e/TUCfdar5Gl0J',
     'pattern': r'「([^」]+)」'},
]
# Reviewed identity mapping to existing Korean catalog records (no translated strings).
KOREAN_BOSS_IDS = {
    'f2cc3de5-b918-424d-aa2b-1ac9ae2928e0': [35],
    '7fb2b973-bf5b-4b54-9bb5-2d109c6dfbcd': [36],
    '87072f50-0aee-4040-9cb5-f6aabf4a9d57': [37],
    '2f3ad99d-e6fd-4bd7-b5e5-25348bdd0cba': [38],
    '8461f50c-ee62-43bb-a289-f4a19b564e16': [39],
    '8337b763-38bc-4dab-89eb-952b34e0c3dc': [40],
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def download(url, body=None):
    request = urllib.request.Request(url, data=body, headers={
        'User-Agent': 'Nikke-Simul-Boss-Catalog/1.0', 'Content-Type': 'application/json', 'Accept-Language': 'ko-KR,ko;q=0.9'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read(8 * 1024 * 1024 + 1)


def korean_catalog():
    # Read the same public anonymous catalog used by the Korean page; no login or user records.
    origin = 'https://www.nikkesolo.com'
    page = download(origin + '/').decode('utf-8')
    for chunk in re.findall(r'<script[^>]+src="([^"]+)"', page):
        if not chunk.startswith('/_next/static/chunks/'):
            continue
        script = download(origin + html.unescape(chunk)).decode('utf-8')
        if 'boss_default' not in script:
            continue
        hosts = set(re.findall(r'https://[a-z0-9]+\.supabase\.co', script))
        keys = re.findall(r'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+', script)
        if len(hosts) != 1 or not keys:
            break
        url = next(iter(hosts)) + '/rest/v1/bosses?select=id,title,image_path,starts_at,ends_at'
        with urllib.request.urlopen(urllib.request.Request(url, headers={'apikey': keys[0]}), timeout=30) as response:
            return response.read(), url
    raise ValueError('korean_public_catalog_not_located')


def assemble(rows, korean, image_loader):
    bosses = [{'id': 'dummy', 'name': '더미 보스', 'imageUrl': None, 'season': None}]
    diagnostics, internal, images = [], [], {}
    seen = set()
    for row in sorted(rows, key=lambda r: r['raid_number'], reverse=True):
        season = row['raid_number']
        if type(season) is not int or season < 1 or season in seen:
            raise ValueError('invalid_or_duplicate_raid_number')
        seen.add(season)
        resource = row['monster_image']
        if not re.fullmatch(r'[a-zA-Z0-9_]+', resource):
            raise ValueError('invalid_boss_image_resource')
        boss_id = f'solo-raid-{season}'
        item = {'id': boss_id, 'sourceName': row['wave_name'], 'sourceId': resource,
                'sourceUrl': ENIKK + '/bosses/' + resource + '.png', 'season': season}
        name = korean.get(season)
        code = 'korean_name_unavailable'
        if name and re.search('[가-힣]', name['name']):
            item['koreanSource'] = name
            try:
                raw = image_loader(item['sourceUrl'])
                if len(raw) > 8 * 1024 * 1024 or not raw.startswith(b'\x89PNG\r\n\x1a\n'):
                    raise ValueError('invalid_boss_png')
                sha = digest(raw)
                asset_key = uuid.uuid4().hex + '.png'
                images[asset_key] = raw
                item['sha256'] = sha
                item['localFile'] = asset_key
                bosses.append({'id': boss_id, 'name': name['name'], 'imageUrl': '/editor/assets/bosses/' + asset_key, 'season': season})
                item['displayable'] = True
                internal.append(item)
                continue
            except (OSError, ValueError) as error:
                code = 'boss_image_unavailable'
                item['error'] = str(error)
        item.update(displayable=False, reason=code)
        internal.append(item)
        diagnostics.append({'id': boss_id, 'season': season, 'code': code, 'displayable': False,
                            'message': '한국어 이름 원천 미확인' if code == 'korean_name_unavailable' else '보스 이미지 준비 실패'})
    return {'schemaVersion': 1, 'defaultBossId': 'dummy', 'bosses': bosses,
            'diagnostics': diagnostics, 'complete': not diagnostics}, internal, images


def prepare(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Manifest/source snapshots are OUTSIDE the static assets directory.
    sources = output / 'boss-sources'
    sources.mkdir(exist_ok=True)
    raw = download(ENIKK + '/api/graphql', json.dumps({'query': QUERY}).encode())
    data = json.loads(raw)
    if data.get('errors') or not data.get('data', {}).get('soloRaidSummaries'):
        raise ValueError('boss_source_query_failed')
    (sources / (digest(raw) + '.json')).write_bytes(raw)
    names, name_receipts = {}, []
    try:
        content, url = korean_catalog()
        sha = digest(content)
        (sources / (sha + '.json')).write_bytes(content)
        for row in json.loads(content):
            for season in KOREAN_BOSS_IDS.get(row['id'], []):
                if not re.search('[가-힣]', row['title']):
                    continue
                names[season] = {'name': row['title'], 'url': url, 'sha256': sha, 'recordId': row['id']}
        name_receipts.append({'page': 'https://www.nikkesolo.com/', 'url': url, 'sha256': sha})
    except (OSError, ValueError) as error:
        name_receipts.append({'page': 'https://www.nikkesolo.com/', 'error': str(error)})
    for spec in NAME_SOURCES:
        receipt = dict(spec)
        try:
            content = download(spec['url'])
            sha = digest(content)
            (sources / (sha + '.html')).write_bytes(content)
            text = html.unescape(content.decode('utf-8'))
            matches = re.findall(spec['pattern'], text)
            matches = sorted(set(x.strip() for x in matches if re.search('[가-힣]', x)))
            if len(matches) != 1:
                raise ValueError('korean_name_not_unique')
            receipt.update(sha256=sha, name=matches[0])
            for season in spec['seasons']:
                names[season] = {'name': matches[0], 'url': spec['url'], 'sha256': sha}
        except (OSError, ValueError) as error:
            receipt['error'] = str(error)
        name_receipts.append(receipt)
    catalog, rows, images = assemble(data['data']['soloRaidSummaries'], names, download)
    assets = output / 'assets/bosses'
    assets.mkdir(parents=True, exist_ok=True)
    for name, image in images.items():
        (assets / name).write_bytes(image)
    manifest = {'schemaVersion': 1, 'page': ENIKK + '/soloraid', 'queryUrl': ENIKK + '/api/graphql',
                'querySha256': digest(raw), 'koreanSources': name_receipts, 'bosses': rows}
    (output / 'solo-raid-bosses.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    pending = output / 'solo-raid-bosses.pending.json'
    pending.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
    pending.replace(output / 'solo-raid-bosses.json')
    return catalog


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--presentation-root', required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.presentation_root)
    print(json.dumps({'displayed': len(result['bosses']), 'excluded': len(result['diagnostics']), 'complete': result['complete']}))

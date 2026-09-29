"""Prepare public display-only bosses into an explicit, isolated presentation root.

Korean names use reviewed Korean sources, never translations from English.
Unresolved names remain diagnostics; English names and source IDs/URLs stay internal.
"""
import argparse
import hashlib
from datetime import datetime, timezone
import json
import re
import urllib.request
import uuid
from pathlib import Path

ENIKK = 'https://enikk.app'
QUERY = 'query { soloRaidSummaries { wave_name monster_image raid_number } }'
REVIEWED_NAMES = Path(__file__).with_name('manifests') / 'solo-raid-korean-names.manifest.json'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def download(url, body=None):
    request = urllib.request.Request(url, data=body, headers={
        'User-Agent': 'Nikke-Simul-Boss-Catalog/1.0', 'Content-Type': 'application/json', 'Accept-Language': 'ko-KR,ko;q=0.9'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read(8 * 1024 * 1024 + 1)


def reviewed_names(rows, manifest):
    """Use pinned, reviewed facts; unknown/changed upstream identities stay unresolved."""
    if manifest.get('schemaVersion') != 1 or manifest.get('visibility') != 'internal_only':
        raise ValueError('invalid_korean_name_manifest')
    sources, indexed = manifest['sources'], {}
    for record in manifest['records']:
        season = record['season']
        if type(season) is not int or season < 1 or season in indexed:
            raise ValueError('invalid_reviewed_season')
        if not re.search('[가-힣]', record['name']) or not record.get('decision'):
            raise ValueError('invalid_reviewed_korean_name')
        if not any(e['source'] == record['adoptedSource'] and e['name'] == record['name'] for e in record['evidence']):
            raise ValueError('reviewed_name_not_in_adopted_source')
        refs = [record['adoptedSource']] + [e['source'] for e in record['evidence']]
        for ref in refs:
            source = sources[ref]
            if datetime.fromisoformat(source['verifiedAt']).tzinfo is None:
                raise ValueError('missing_source_verification_timezone')
            if not source['kind'].startswith('user_') and not source.get('url', '').startswith('https://'):
                raise ValueError('missing_korean_source_url')
        indexed[season] = record
    names, issues = {}, {}
    for row in rows:
        season = row['raid_number']
        record = indexed.get(season)
        if record is None:
            issues[season] = '한국어 시즌 대응 미확인'
        elif (row['wave_name'], row['monster_image']) != (record['expectedSourceName'], record['expectedSourceId']):
            issues[season] = '원천 보스 식별 변경으로 한국어 시즌 대응 재확인 필요'
        else:
            names[season] = record
    return names, issues


def assemble(rows, korean, image_loader, name_issues=None):
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
        message = (name_issues or {}).get(season, '한국어 이름 원천 미확인') if code == 'korean_name_unavailable' else '보스 이미지 준비 실패'
        item.update(displayable=False, reason=code, detail=message)
        internal.append(item)
        diagnostics.append({'id': boss_id, 'season': season, 'code': code, 'displayable': False,
                            'message': message})
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
    reviewed_raw = REVIEWED_NAMES.read_bytes()
    reviewed = json.loads(reviewed_raw)
    names, issues = reviewed_names(data['data']['soloRaidSummaries'], reviewed)
    catalog, rows, images = assemble(data['data']['soloRaidSummaries'], names, download, issues)
    assets = output / 'assets/bosses'
    assets.mkdir(parents=True, exist_ok=True)
    for name, image in images.items():
        (assets / name).write_bytes(image)
    manifest = {'schemaVersion': 1, 'page': ENIKK + '/soloraid', 'queryUrl': ENIKK + '/api/graphql',
                'querySha256': digest(raw), 'preparedAt': datetime.now(timezone.utc).isoformat(),
                'reviewedNamesSha256': digest(reviewed_raw), 'koreanSources': reviewed, 'bosses': rows}
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

"""Local Lab UI assets: verified user ZIP + public Blablalink CDN cache.

Resource URL algorithm and icon names adapted from Nikke-Local-Lab
c05fc1c392a523b9e17ebe0cbd4811bed9c19adb, materialize-nll-phase-d-presentation-assets.ps1.
No account credentials are needed or read. Art/image bytes remain Git-external.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import time
import unicodedata
import urllib.request
import urllib.error
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PNG = b'\x89PNG\r\n\x1a\n'
WEB = 'https://www.blablalink.com/assets/nikke/version/default/'
ICONS = {**{f'code-{v}.png': f'shiftysassets/images/icon-code-{r}.png' for v,r in
    [('fire','fire'),('water','water'),('wind','wind'),('electric','electronic'),('iron','iron')]},
    **{f'job-{v}.png': f'shiftysassets/images/nikkes/nikke-job-{v}--yellow.png' for v in ['attacker','defender','supporter']},
    **{f'burst-{v}.png': f'shiftysassets/images/icon-burst-{v}.png' for v in ['1','2','3','p']},
    **{f'weapon-{v}.png': f'shiftysassets/images/icon-weapon-{r}.png' for v,r in
    [('assault_rifle','assault_rifle'),('machine_gun','machine_gun'),('rocket_launcher','rocket_launcher'),
     ('shotgun','shot_gun'),('sniper_rifle','sniper_rifle'),('submachine_gun','sub_machine_gun')]},
    'star-empty.png':'assets/icon-nikke-star-Bv0b_V3C.png',
    'star-filled.png':'assets/icon-nikke-star-gold-BnTupWrm.png',
    'evolve.png':'assets/icon-evolve-z8366Dwx.png',
    'card-bottom.png':'assets/nikkes-item-btmbg-UZMV6c4h.png',
    'equipment-background.png':'shiftysassets/images/nikkes/nikke-equip-bg.png',
    'overload.png':'shiftysassets/images/icon-overload.png',
    'tab-mask.png':'assets/mask-tab-IdeLJVuW.png'}

def digest(data): return hashlib.sha256(data).hexdigest()

def normal_resource_uri(logical):
    path = logical.lstrip('/')
    parts = path.split('/')
    primes = [224737,1000639,2654435761,2654435769,1000621,4294967291]
    if not 2 <= len(parts) <= len(primes)+1 or any(p in ('','..','.') for p in parts):
        raise ValueError('Invalid resource path')
    output = []
    for seed in primes[:len(parts)-1]:
        value = seed
        for ch in path:
            value = (value * 33 + ord(ch)) & 0xffffffff
            if value >= 0x80000000: value -= 0x100000000
        rem = value % seed
        output.append(f'{chr(97+(rem//26)%26)}{chr(97+rem%26)}-{rem%99:02}')
    output.append(hashlib.md5(path.encode()).hexdigest()+'.'+parts[-1].split('.',1)[1])
    return 'https://sg-tools-cdn.blablalink.com/'+'/'.join(output)

def download(url):
    from urllib.parse import urlsplit
    if urlsplit(url).scheme != 'https' or urlsplit(url).hostname not in ('www.blablalink.com','sg-tools-cdn.blablalink.com'):
        raise ValueError('Unexpected asset host')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Nikke-Simul-Assets/1.0'}),timeout=25) as response:
                data = response.read(16*1024*1024+1)
                if len(data)>16*1024*1024: raise ValueError('Asset too large')
                return data
        except Exception:
            if attempt == 2: raise
            time.sleep(attempt+1)

def atomic(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary = path.with_name(path.name+'.tmp-'+uuid.uuid4().hex)
    temporary.write_bytes(data); temporary.replace(path)

def json_write(path, obj): atomic(path,json.dumps(obj,ensure_ascii=False,indent=2).encode())

def resolve_data_root(data_root=None, output=None):
    """Explicit input > environment > output sibling convention > legacy default."""
    return Path(data_root or os.environ.get('NIKKE_DATA_ROOT') or
                (Path(output).parent if output is not None else ROOT/'data/local')).resolve()

def failure(path, error, cached=False):
    return dict(path=path, kind='image' if path.startswith('assets/') else 'catalog',
                error=type(error).__name__, code='http_error' if isinstance(error, urllib.error.HTTPError) else
                'missing_metadata' if isinstance(error, FileNotFoundError) else
                'invalid_content' if isinstance(error, (ValueError, KeyError, TypeError)) else 'io_error',
                cached=bool(cached), **({'httpStatus':error.code} if isinstance(error, urllib.error.HTTPError) else {}))

class PreparationError(Exception):
    def __init__(self, issues):
        self.issues=issues
        super().__init__('Asset or catalog preparation failed')

class CatalogCache:
    """Stage replacements until the complete catalog is valid; failed refreshes retain verified cache."""
    def __init__(self, output, manifest, refresh=False):
        self.output=Path(output); self.refresh=refresh; self.assets=[]; self.pending={}; self.issues=[]
        try:self.previous={a['path']:a for a in json.loads((self.output/manifest).read_bytes())['assets']}
        except (OSError, ValueError, KeyError):self.previous={}

    def get(self, relative, url, fetch=None, image=False):
        fetch=fetch or download; path=safe_path(self.output,relative)
        existing=path.read_bytes() if path.exists() else None
        def validate(data):
            if image and not (data.startswith(PNG) or data[:4]==b'RIFF' and data[8:12]==b'WEBP'):
                raise ValueError('Not an image')
            if relative.endswith('.json'):json.loads(data)
        valid=False
        if existing is not None:
            try:
                validate(existing)
                prior=self.previous.get(relative)
                valid=prior is None or digest(existing)==prior['sha256']
            except (ValueError, KeyError):pass
        try:
            data=existing if valid and not self.refresh else fetch(url)
            validate(data)
        except Exception as error:
            issue=failure(relative,error,valid); self.issues.append(issue)
            if not valid:raise PreparationError(self.issues) from error
            data=existing
        self.pending[relative]=data
        self.assets.append(dict(path=relative,url=url,sha256=digest(data)))
        return data

    def commit(self):
        for relative,data in self.pending.items():atomic(safe_path(self.output,relative),data)

def receipt(presentation, output):
    issues=presentation['unresolved']; image_paths=set()
    for name in ('presentation.json','account-presentation.json','spec-presentation.json'):
        try:
            manifest=presentation if name=='presentation.json' else json.loads((output/name).read_bytes())
            for asset in manifest.get('assets',[]):
                if not asset['path'].startswith('assets/'):continue
                path=safe_path(output,asset['path'])
                if path.exists() and digest(path.read_bytes())==asset['sha256']:image_paths.add(asset['path'])
        except (OSError, ValueError, KeyError):continue
    return dict(characters=len(presentation.get('characters',[])),zipPortraits=presentation.get('importedPortraits',0),
                assets=len(presentation.get('assets',[])),unresolved=issues,
                status='succeeded' if not issues else 'partial' if image_paths else 'failed',
                failureSummary=dict(imageFailures=sum(i['kind']=='image' for i in issues),
                    catalogFailures=sum(i['kind']=='catalog' for i in issues),cachedFailures=sum(i.get('cached',False) for i in issues),
                    availableImages=len(image_paths)))

def safe_path(root, relative):
    def canonical(path):
        text=str(path.resolve())
        # Windows GetFinalPathNameByHandle can preserve the extended prefix during concurrent mkdir.
        if text.startswith('\\\\?\\UNC\\'): text='\\\\'+text[8:]
        elif text.startswith('\\\\?\\'): text=text[4:]
        return Path(text)
    root = canonical(root)
    rel = PurePosixPath(relative)
    if rel.is_absolute() or '\\' in relative or ':' in relative or any(p in ('..','.') for p in rel.parts):
        raise ValueError('Invalid asset path')
    target = canonical(root/relative)
    if not target.is_relative_to(root): raise ValueError(f'Asset outside destination: {target} vs {root}')
    return target

def import_zip(path, output):
    with zipfile.ZipFile(path) as z:
        if len(z.namelist()) != len(set(z.namelist())): raise ValueError('Duplicate ZIP entry')
        manifest = json.loads(z.read('manifest.private.json'))
        if manifest.get('contractId') != 'nll/local-ui-reuse-assets/v1': raise ValueError('Unknown ZIP contract')
        verified = []
        for entry in manifest['files']:
            target = safe_path(output,entry['path'])
            info = z.getinfo(entry['path'])
            if info.file_size > 8*1024*1024: raise ValueError('Oversized image')
            data = z.read(info)
            if not data.startswith(PNG) or len(data)!=entry['byteLength'] or digest(data)!=entry['sha256']:
                raise ValueError('ZIP asset checksum mismatch: '+entry['path'])
            verified.append((target,data))
        if len({str(p) for p,_ in verified}) != len(verified): raise ValueError('Duplicate manifest entry')
        for target,data in verified: atomic(target,data)
        manifest['zipSha256'] = digest(Path(path).read_bytes())
        json_write(output/'import-manifest.private.json',manifest)
        return manifest

def normalize(name):
    return ''.join(c for c in unicodedata.normalize('NFKC',name).casefold() if c.isalnum())

def main():
    args = argparse.ArgumentParser()
    args.add_argument('--zip',type=Path)
    args.add_argument('--output',type=Path)
    args.add_argument('--data-root',type=Path)
    args.add_argument('--refresh',action='store_true')
    args.add_argument('--update-index',action='store_true')
    opts = args.parse_args()
    data_root=resolve_data_root(opts.data_root,opts.output); output=opts.output or data_root/'presentation'
    try:
        built=build(output,opts.zip,opts.refresh,opts.update_index,include_account_assets=True,data_root=data_root)
        if receipt(built,output)['status']=='failed':raise SystemExit(1)
    except Exception as error:
        try:previous=json.loads((output/'presentation.json').read_bytes())
        except (OSError, ValueError):previous={}
        previous['unresolved']=error.issues if isinstance(error,PreparationError) else [failure('presentation.json',error,bool(previous))]
        print(json.dumps(receipt(previous,output),ensure_ascii=False),flush=True)
        raise SystemExit(1)

def growth_metadata(output):
    source=ROOT.parent/'Nikke-Dmg-Simulator/Database/raw/staticdata/mpk/CharacterTable.json'
    cache=output/'catalog/character-growth.json'
    if source.exists():
        raw=source.read_bytes()
        records={str(r['name_code']):r.get('corporation_sub_type') for r in json.loads(raw)}
        json_write(cache,dict(source=str(source),sha256=digest(raw),corporationSubtypes=records))
    return json.loads(cache.read_bytes())['corporationSubtypes'] if cache.exists() else {}

def maximum_bond(manufacturer,subtype):
    if manufacturer=='pilgrim' or subtype==1:return 40
    return 30 if subtype==0 else None  # Missing source data is not proof of a normal subtype.

def build(output,zip_path=None,refresh=False,update_index=False,include_account_assets=False,data_root=None):
    output=Path(output); data_root=resolve_data_root(data_root,output)
    output.mkdir(parents=True,exist_ok=True)
    imported_path = output/'import-manifest.private.json'
    imported = import_zip(zip_path,output) if zip_path else (json.loads(imported_path.read_text(encoding='utf-8')) if imported_path.exists() else {'characters':[],'files':[]})
    try:
        previous=json.loads((output/'presentation.json').read_text(encoding='utf-8'))
        previous_by_path={entry['path']:entry for entry in previous['assets']}
    except (FileNotFoundError,json.JSONDecodeError,KeyError): previous_by_path={}
    index_path = output/'blablalink-index.json'
    index_url = normal_resource_uri('character/ko/nikke_list_v2.json')
    index_issues=[]
    def read_index(raw):
        index=json.loads(raw)
        if not isinstance(index,list) or len(index)<100:raise ValueError('Invalid public character index')
        return index
    try:
        raw = download(index_url) if refresh or update_index or not index_path.exists() else index_path.read_bytes()
        index=read_index(raw)
    except Exception as error:
        try:raw=index_path.read_bytes(); index=read_index(raw)
        except Exception:raise PreparationError([failure('blablalink-index.json',error)]) from error
        index_issues.append(failure('blablalink-index.json',error,True))
    # The public index has canonical numeric name_code IDs; Lab UUIDs are image IDs only.
    by_name = {}
    for c in imported['characters']: by_name.setdefault(normalize(c['displayName']),[]).append(c)
    assets = {}
    for f in imported['files']:
        target=safe_path(output,f['path'])
        if target.exists() and digest(target.read_bytes())==f['sha256']:
            assets[f['path']]={**f,'source':'user_zip','sourceArchiveSha256':imported.get('zipSha256')}
    characters=[]; pending=[]; unresolved=index_issues
    growth=growth_metadata(output)
    weapons=dict(AR='assault_rifle',MG='machine_gun',RL='rocket_launcher',SG='shotgun',SR='sniper_rifle',SMG='submachine_gun')
    for row in index:
        name=row['name_localkey']['name']; cid=str(row['name_code'])
        matches=by_name.get(normalize(name),[])
        # Ambiguous duplicate names must be downloaded by official resource ID.
        public_matches=[r for r in index if normalize(r['name_localkey']['name'])==normalize(name)]
        reuse=matches[0] if len(matches)==1 and len(public_matches)==1 and matches[0]['portraitPath'] in assets else None
        relative=reuse['portraitPath'] if reuse else f'assets/characters/{cid}.png'
        url=normal_resource_uri(f'character/mi/mi_c{int(row["resource_id"]):03}_00_s.png')
        if not reuse: pending.append((relative,url))
        characters.append(dict(characterUid=cid,displayName=name,portraitPath='/editor/'+relative,
            labCharacterUid=reuse['characterUid'] if reuse else None,
            combatClassCode=row.get('class','').lower(),manufacturerCode=row.get('corporation','').lower(),
            corporationSubtype=growth.get(cid),maximumBondLevel=maximum_bond(row.get('corporation','').lower(),growth.get(cid)),
            rarityCode=row.get('original_rare','').lower(),elementCode={'Electronic':'electric','Electric':'electric','Fire':'fire','Water':'water','Wind':'wind','Iron':'iron'}.get(row.get('element_id',{}).get('element',{}).get('element'),''),
            burstStep={'Step1':1,'Step2':2,'Step3':3,'AllStep':5}.get(row.get('use_burst_skill')),
            weaponCode=weapons.get(row.get('shot_id',{}).get('element',{}).get('weapon_type'),'')))
    for leaf,logical in ICONS.items():
        relative='assets/ui/'+leaf
        if relative not in assets: pending.append((relative,WEB+logical))
    def fetch(item):
        relative,url=item; target=safe_path(output,relative)
        cached=previous_by_path.get(relative)
        existing=target.read_bytes() if target.exists() else None
        cache_valid=bool(cached and existing and existing.startswith(PNG) and digest(existing)==cached['sha256'])
        try:
            data=download(url) if refresh or not cache_valid else existing
            if not data.startswith(PNG): raise ValueError('Not PNG')
            atomic(target,data)
            return relative,dict(path=relative,byteLength=len(data),sha256=digest(data),source='blablalink',url=url)
        except Exception as error:
            # Keep a previously verified cache entry on refresh failure, but report the failure separately.
            if cache_valid:
                return relative,{**cached,'refreshIssue':failure(relative,error,True)}
            return relative,{**failure(relative,error), 'url':url}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for relative,result in pool.map(fetch,pending):
            if 'error' in result: unresolved.append(result)
            else:
                if 'refreshIssue' in result: unresolved.append(result.pop('refreshIssue'))
                assets[relative]=result
    # Never publish a broken URL for a failed download; UI shows an explicit fallback.
    for c in characters:
        if c['portraitPath'].removeprefix('/editor/') not in assets: c['portraitPath']=None
    presentation=dict(schemaVersion=1,source='Blablalink',indexUrl=index_url,indexSha256=digest(raw),
        characters=characters,assets=list(assets.values()),unresolved=unresolved,
        importedPortraits=sum(c['labCharacterUid'] is not None for c in characters))
    if include_account_assets:
        from account_presentation_assets import prepare as prepare_account
        from spec_presentation_assets import prepare as prepare_specs
        for manifest,prepare in [('account-presentation.json',prepare_account),('spec-presentation.json',prepare_specs)]:
            try:
                prepared=prepare(output,data_root=data_root,refresh=refresh)
                unresolved.extend(prepared.get('unresolved',[]))
            except Exception as error:
                # Each catalog keeps its previous manifest if its refresh fails.
                unresolved.extend(error.issues if isinstance(error,PreparationError) else [failure(manifest,error,(output/manifest).exists())])
    atomic(index_path,raw)
    json_write(output/'presentation.json',presentation)
    print(json.dumps(receipt(presentation,output),ensure_ascii=False),flush=True)
    return presentation

if __name__=='__main__': main()

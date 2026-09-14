"""Backend CLI/API regression with copied public assets and synthetic HTTP responses.

Never reads/copies source accounts.db or sessions, never calls user ports or live CDN.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[2]

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-data',type=Path,required=True);parser.add_argument('--dotnet',required=True)
    args=parser.parse_args()
    run=ROOT/'artifacts/image-catalog-fix'/uuid.uuid4().hex;run.mkdir(parents=True)
    origin=run/'origin';data=run/'external-data';source=args.source_data.resolve()
    hashes={};urls={};checks=[]
    def copy_public(relative):
        src=(source/relative).resolve();assert src.is_relative_to(source)
        hashes[relative]=sha(src);dst=origin/relative;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    report={'kind':'actual_product_cli_api_with_synthetic_network','status':'failed','checks':checks}
    try:
        for name in ('presentation.json','account-presentation.json','spec-presentation.json'):
            copy_public('presentation/'+name)
            for asset in read(source/'presentation'/name)['assets']:
                relative='presentation/'+asset['path'];copy_public(relative)
                if asset.get('url'):urls[asset['url']]=str(origin/relative)
        for name in ('blablalink-index.json','import-manifest.private.json','catalog/character-growth.json'):
            if (source/'presentation'/name).exists():copy_public('presentation/'+name)
        copy_public('calculation/current.json')
        version=read(source/'calculation/current.json')['id']
        copy_public('calculation/'+version+'/cube_effect_table.json');copy_public('game-catalog.json')
        urls[read(source/'presentation/presentation.json')['indexUrl']]=str(origin/'presentation/blablalink-index.json')
        shutil.copytree(origin,data)
        hooks=run/'hooks';hooks.mkdir();control=run/'control.json';control.write_text('{}')
        mapping=run/'mock-network.json';mapping.write_text(json.dumps(urls))
        (hooks/'sitecustomize.py').write_text('''import io,json,os,urllib.request,urllib.error,time
from pathlib import Path
mapping=json.loads(Path(os.environ['IMAGE_TEST_MAP']).read_text())
def open_mock(request,*args,**kwargs):
    url=request.full_url if hasattr(request,'full_url') else request
    control=json.loads(Path(os.environ['IMAGE_TEST_CONTROL']).read_text())
    if control.get('all') or url==control.get('url'):
        if control.get('invalid'):return io.BytesIO(b'<html>not an image</html>')
        raise urllib.error.HTTPError(url,503,'synthetic unavailable',{},None)
    if url not in mapping:raise AssertionError('Unmapped public request: '+url)
    return io.BytesIO(Path(mapping[url]).read_bytes())
urllib.request.urlopen=open_mock
time.sleep=lambda seconds:None
''',encoding='utf-8')
        env=dict(os.environ,PYTHONPATH=str(hooks),IMAGE_TEST_MAP=str(mapping),IMAGE_TEST_CONTROL=str(control),PYTHONIOENCODING='utf-8')
        env.pop('NIKKE_DATA_ROOT',None)
        def cli(*flags):
            result=subprocess.run([sys.executable,str(ROOT/'tools/data-pipeline/presentation_assets.py'),*flags],cwd=ROOT,env=env,text=True,capture_output=True)
            receipt=json.loads(result.stdout)
            assert result.returncode==(1 if receipt['status']=='failed' else 0),(result.returncode,result.stderr)
            (run/f'cli-{len(checks)}.json').write_text(json.dumps(receipt,ensure_ascii=False))
            return receipt
        assert not (ROOT/'data/local/calculation/current.json').exists(), 'Use checkout without code-root data for this case'
        for flags in ([],['--update-index'],['--refresh']):
            result=cli('--output',str(data/'presentation'),*flags)
            assert result['status']=='succeeded' and not result['unresolved'],result
            checks.append('CLI output-only external root '+str(flags))
        # Public mappings and image bytes must be identical to copied originals.
        for name,fields in (('account-presentation.json',('consoles','cubes')),('spec-presentation.json',('supportDefinitions','overloadOptions'))):
            expected=read(origin/'presentation'/name);actual=read(data/'presentation'/name)
            for field in fields:assert actual[field]==expected[field],field
            for asset in expected['assets']:
                if asset['path'].startswith('assets/'):assert sha(data/'presentation'/asset['path'])==asset['sha256']
        checks.append('all account/spec mappings and artwork hashes preserved')
        # Direct helper CLI uses explicit input independently of output location.
        for helper in ('account_presentation_assets.py','spec_presentation_assets.py'):
            subprocess.run([sys.executable,str(ROOT/'tools/data-pipeline'/helper),'--data-root',str(data),'--output',str(data/'presentation')],cwd=ROOT,env=env,check=True,capture_output=True)
        checks.append('direct helper CLIs')
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        assert port not in (5180,5181)
        api_env=dict(env,NIKKE_PROJECT_ROOT=str(ROOT),NIKKE_DATA_ROOT=str(data),NIKKE_GAME_CATALOG=str(data/'game-catalog.json'),NIKKE_PYTHON=sys.executable,NIKKE_PORT=str(port),NIKKE_TEST_FIXTURE='1')
        token=''
        def call(path,post=False):
            req=urllib.request.Request(f'http://127.0.0.1:{port}/api/'+path,data=b'{}' if post else None,headers={'Content-Type':'application/json','X-Nikke-Token':token})
            with urllib.request.urlopen(req,timeout=10) as response:return json.load(response)
        def refresh():
            call('presentation/refresh',True)
            for _ in range(300):
                state=call('presentation/status')
                if state['status']!='running':return state
                time.sleep(.1)
            raise AssertionError('Refresh timed out')
        with (run/'api.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen([args.dotnet,str(ROOT/'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],cwd=ROOT,env=api_env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:
                for _ in range(100):
                    try:token=call('bootstrap')['token'];break
                    except (OSError,urllib.error.URLError):time.sleep(.1)
                else:raise AssertionError('API startup failed')
                assert refresh()['status']=='succeeded';checks.append('API refresh success')
                old_manifests={name:sha(data/'presentation'/name) for name in ('account-presentation.json','spec-presentation.json')}
                (data/'calculation/current.json').rename(data/'calculation/current.saved')
                (data/'game-catalog.json').rename(data/'game.saved')
                state=refresh();assert state['status']=='partial' and state['failureSummary']['catalogFailures']==2 and state['failureSummary']['imageFailures']==0,state
                assert '카탈로그 준비 2건' in state['message'] and '이미지 2개' not in state['message']
                assert state['failureSummary']['cachedFailures']==2
                assert all(sha(data/'presentation'/name)==value for name,value in old_manifests.items())
                checks.append('API two missing metadata catalogs with cache')
                target=next(a for a in read(origin/'presentation/presentation.json')['assets'] if a.get('url') and a['path'].startswith('assets/'))
                control.write_text(json.dumps({'url':target['url'],'invalid':True}))
                state=refresh();assert state['failureSummary']['imageFailures']>=1 and state['failureSummary']['catalogFailures']==2,state
                assert sha(data/'presentation'/target['path'])==target['sha256'];checks.append('API mixed non-image and metadata failures preserve cache')
                (data/'calculation/current.saved').rename(data/'calculation/current.json');(data/'game.saved').rename(data/'game-catalog.json')
                control.write_text('{}');state=refresh();assert state['status']=='succeeded' and state['unresolved']==[],state
                checks.append('API recovery clears status and unresolved')
                (data/'presentation'/target['path']).unlink();control.write_text(json.dumps({'url':target['url']}))
                state=refresh();assert state['failureSummary']['imageFailures']>=1 and any(i['kind']=='image' and not i['cached'] and i['code']=='http_error' for i in state['unresolved'])
                assert '기존 이미지는 유지' not in state['message'];checks.append('API uncached HTTP image failure')
                control.write_text('{}');assert refresh()['status']=='succeeded';checks.append('API final recovery')
                # Same isolated server, explicitly empty cache: no blanket cache-preserved claim.
                (data/'presentation').rename(data/'presentation.saved')
                (data/'presentation').mkdir()
                control.write_text(json.dumps({'all':True}))
                state=refresh();assert state['status']=='failed' and state['failureSummary']['availableImages']==0,state
                assert '실패 항목에 사용할 캐시가 없습니다' in state['message'] and state['failureSummary']['cachedFailures']==0
                (data/'presentation').rename(data/'presentation.failed-empty')
                (data/'presentation.saved').rename(data/'presentation')
                control.write_text('{}');assert refresh()['status']=='succeeded'
                checks.append('API total failure with empty cache and subsequent recovery')
                report['apiFinal']=call('presentation/status')
            finally:process.terminate();process.wait(timeout=15)
        empty=run/'empty/presentation';control.write_text(json.dumps({'all':True}))
        result=cli('--data-root',str(run/'empty'),'--output',str(empty),'--refresh')
        assert result['status']=='failed' and result['failureSummary']['availableImages']==0 and not result['unresolved'][0]['cached']
        checks.append('CLI total failure without cache')
        report['status']='passed'
    finally:
        changed=[relative for relative,value in hashes.items() if sha(source/relative)!=value]
        report['sourceFilesChecked']=len(hashes);report['sourceChanges']=changed
        (run/'source-hashes.json').write_text(json.dumps(hashes,indent=2));(run/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(run)
        assert not changed, 'Original public files changed'

if __name__=='__main__':main()

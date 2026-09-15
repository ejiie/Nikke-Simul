"""Q-IMG independent CLI/API/browser execution; public copies + synthetic URL responses.
Only writes to a new workspace artifact directory. Never contacts 5180/5181 or live CDN.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import uuid
import urllib.request
from acceptance import capture, assert_success, assert_failure, assert_recovery

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/data-pipeline'))
import presentation_assets as product


def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


HOOK = '''import io,json,os,urllib.request,urllib.error,time
from pathlib import Path
mapping=json.loads(Path(os.environ['QIMG_MAP']).read_text(encoding='utf-8'))
def mocked(request,*args,**kwargs):
    url=request.full_url if hasattr(request,'full_url') else request
    control=json.loads(Path(os.environ['QIMG_CONTROL']).read_text(encoding='utf-8'))
    if control.get('all') or url==control.get('url'):
        if control.get('mode')=='invalid':return io.BytesIO(b'<html>Q-IMG synthetic non-image</html>')
        raise urllib.error.HTTPError(url,404,'Q-IMG synthetic missing',{},None)
    if url not in mapping:raise AssertionError('Unmapped network denied: '+url)
    return io.BytesIO(Path(mapping[url]).read_bytes())
urllib.request.urlopen=mocked
time.sleep=lambda n:None
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-data', type=Path, required=True)
    parser.add_argument('--dotnet', required=True)
    args = parser.parse_args()
    # Short UUID/case names avoid the Windows MAX_PATH limit for asset .tmp-UUID names.
    run = ROOT / 'artifacts/image-collection-qa' / ('f-' + uuid.uuid4().hex[:12])
    run.mkdir(parents=True)
    source = args.source_data.resolve()
    origin = run / 'origin'
    original_hashes, urls, checks = {}, {}, []
    report = {'commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'productCommit': '104646006318f252f01b8d39b3424316e0a262ba', 'evidence':'actual_CLI_API_browser_with_synthetic_network',
              'status':'failed','checks':checks,'liveCDNRequests':0,'userServerRequests':0}
    def check(name, function):
        try:
            value = function()
            checks.append({'name':name,'passed':True,'detail':value})
        except Exception as error:
            checks.append({'name':name,'passed':False,'error':str(error)})
        write(run/'summary.json',report)
        print(name + ': ' + ('PASS' if checks[-1]['passed'] else 'FAIL ' + checks[-1]['error']), flush=True)
    def copy_public(relative):
        src = (source / relative).resolve()
        assert src.is_relative_to(source)
        original_hashes[relative] = sha(src)
        dst = origin / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src,dst)
    def seed(data, warm):
        data.mkdir(parents=True,exist_ok=True)
        shutil.copytree(origin/'calculation',data/'calculation')
        shutil.copyfile(origin/'game-catalog.json',data/'game-catalog.json')
        if warm: shutil.copytree(origin/'presentation',data/'presentation')
        else:
            (data/'presentation/catalog').mkdir(parents=True)
            growth=origin/'presentation/catalog/character-growth.json'
            if growth.exists():shutil.copyfile(growth,data/'presentation/catalog/character-growth.json')
    try:
        for name in ('presentation.json','account-presentation.json','spec-presentation.json'):
            copy_public('presentation/'+name)
            for asset in read(source/'presentation'/name)['assets']:
                copy_public('presentation/'+asset['path'])
                if asset.get('url'):urls[asset['url']]=str(origin/'presentation'/asset['path'])
        for name in ('blablalink-index.json','import-manifest.private.json','catalog/character-growth.json'):
            if (source/'presentation'/name).exists():copy_public('presentation/'+name)
        copy_public('calculation/current.json')
        version=read(source/'calculation/current.json')['id']
        copy_public('calculation/'+version+'/cube_effect_table.json');copy_public('game-catalog.json')
        catalog=read(origin/'presentation/presentation.json')
        urls[catalog['indexUrl']]=str(origin/'presentation/blablalink-index.json')
        # Cold-cache fixture uses the same public portrait bytes at official logical URLs.
        portraits={c['characterUid']:c['portraitPath'].removeprefix('/editor/') for c in catalog['characters']}
        for row in read(origin/'presentation/blablalink-index.json'):
            url=product.normal_resource_uri(f'character/mi/mi_c{int(row["resource_id"]):03}_00_s.png')
            urls[url]=str(origin/'presentation'/portraits[str(row['name_code'])])
        for leaf,logical in product.ICONS.items():urls[product.WEB+logical]=str(origin/'presentation/assets/ui'/leaf)
        hooks=run/'hooks';hooks.mkdir();(hooks/'sitecustomize.py').write_text(HOOK,encoding='utf-8')
        control=run/'control.json';write(control,{})
        write(run/'network-map.json',urls)
        env=dict(os.environ,PYTHONPATH=str(hooks),QIMG_MAP=str(run/'network-map.json'),QIMG_CONTROL=str(control),PYTHONIOENCODING='utf-8')
        env.pop('NIKKE_DATA_ROOT',None)
        expected=capture(origin/'presentation')
        from PIL import Image
        image_count=0
        for path in expected['hashes']:
            if path.startswith('assets/'):
                with Image.open(origin/'presentation'/path) as image:image.verify()
                image_count+=1
        report['verifiedOriginalImages']=image_count
        assert not (ROOT/'data/local').exists(), 'external case must have no code-local data'
        def cli_matrix(layout,mode,warm):
            case=run/'cli'/str(len(checks))
            code=case/'code'
            (code/'tools/data-pipeline').mkdir(parents=True)
            for name in ('presentation_assets.py','account_presentation_assets.py','spec_presentation_assets.py'):
                src=ROOT/'tools/data-pipeline'/name;dst=code/'tools/data-pipeline'/name
                shutil.copyfile(src,dst);assert sha(src)==sha(dst)
            data=code/'data/local' if layout=='default' else case/'external'
            seed(data,warm)
            script=code/'tools/data-pipeline/presentation_assets.py'
            flags=[] if layout=='default' else ['--data-root',str(data)]
            if mode!='initial':flags.append('--'+mode)
            prior=None
            for repeat in range(2):
                proc=subprocess.run([sys.executable,str(script),*flags],cwd=code,env=env,capture_output=True,text=True,timeout=120)
                (case/f'cli-{repeat}.stderr').write_text(proc.stderr,encoding='utf-8')
                receipt=json.loads(proc.stdout);write(case/f'cli-{repeat}.json',receipt)
                assert proc.returncode==0 and receipt['status']=='succeeded',receipt
                snap=capture(data/'presentation')
                assert_success(read(data/'presentation/presentation.json'),receipt,snap,prior)
                for field in ('consoles','cubes','supportDefinitions','overloadOptions'):
                    assert snap['mappings'][field]==expected['mappings'][field],field
                if warm:
                    for path,digest in expected['hashes'].items():
                        if path.startswith('assets/'):assert snap['hashes'][path]==digest,path
                prior=snap
            return {'repeats':2,'exit':0}
        for layout in ('default','external'):
            for mode in ('initial','update-index','refresh'):
                for warm in (False,True):check(f'CLI {layout} {mode} cache={warm}',lambda:cli_matrix(layout,mode,warm))
        data=run/'api-data';seed(data,True)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        assert port not in (5180,5181)
        report['isolatedPort']=port
        api_env=dict(env,NIKKE_PROJECT_ROOT=str(ROOT),NIKKE_DATA_ROOT=str(data),NIKKE_GAME_CATALOG=str(data/'game-catalog.json'),
                     NIKKE_PYTHON=sys.executable,NIKKE_PORT=str(port),NIKKE_TEST_FIXTURE='1')
        token=''
        def call(path,post=False):
            request=urllib.request.Request(f'http://127.0.0.1:{port}/api/{path}',data=b'{}' if post else None,
                                          headers={'Content-Type':'application/json','X-Nikke-Token':token})
            with urllib.request.urlopen(request,timeout=15) as response:return json.load(response)
        def refresh():
            call('presentation/refresh',True)
            for _ in range(600):
                state=call('presentation/status')
                if state['status']!='running':return state
                time.sleep(.1)
            raise AssertionError('isolated refresh timeout')
        target=next(a for a in catalog['assets'] if a.get('url') and a['path'].startswith('assets/'))
        api_log=(run/'api.log').open('w',encoding='utf-8')
        process=subprocess.Popen([args.dotnet,str(ROOT/'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],cwd=ROOT,env=api_env,
                                 stdout=api_log,stderr=api_log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            for _ in range(150):
                try:token=call('bootstrap')['token'];break
                except OSError:time.sleep(.1)
            else:raise AssertionError('isolated API startup failed')
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(channel='msedge',headless=True)
                page=browser.new_page(viewport={'width':1400,'height':1000})
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{port}/editor/');page.wait_for_selector('body[data-ready="true"]')
                def screen(state,label):
                    # Product refresh loop must display the actual API message; no mocked status route.
                    page.wait_for_function('(m)=>document.getElementById("status").textContent===m',arg=state['message'],timeout=20000)
                    page.screenshot(path=str(run/f'browser-{label}.png'))
                    return {'message':page.locator('#status').inner_text(),'jsErrors':list(errors)}
                def image_screen():
                    # Actual account renderer with synthetic empty account; actual presentation API.
                    return page.evaluate('''async()=>{
                      const p=await (await fetch('/api/presentation')).json();
                      const host=document.createElement('section');host.id='qimg-renderer';document.body.append(host);
                      const {mountAccountCards}=await import('/editor/local-lab-account.js');
                      mountAccountCards(host,{characters:[],consoles:{},cubeLevels:{}},p);
                      const extra=p.supportDefinitions.filter(x=>['equipment','collection'].includes(x.kindCode));
                      for(const kind of ['equipment','collection']){const img=document.createElement('img');img.dataset.qimg=kind;img.src=extra.find(x=>x.kindCode===kind).imagePath;host.append(img);}
                      const imgs=[...host.querySelectorAll('img')];for(const img of imgs){img.loading='eager';await img.decode();}
                      const result={rendered:imgs.length,console:host.querySelectorAll('.console-image').length,cube:host.querySelectorAll('.cube-image').length,
                        equipment:host.querySelector('[data-qimg=equipment]').naturalWidth,collection:host.querySelector('[data-qimg=collection]').naturalWidth};
                      host.remove();return result;
                    }''')
                def success_api():
                    state=refresh();assert_success(call('presentation'),state,capture(data/'presentation'))
                    write(run/'api-success.json',state);return screen(state,'initial-success')
                check('API actual success + browser message',success_api)
                cases=['current','cube_table','game','both','http','invalid','mixed']
                for warm in (True,False):
                    for kind in cases:
                        def failure_case():
                            case=run/'api-cases'/f'{kind}-{warm}';case.mkdir(parents=True)
                            # Rename only this run's presentation folder, never source or user caches.
                            old=(data/'presentation').resolve();assert old.is_relative_to(run.resolve())
                            old.rename(case/'previous-presentation')
                            if warm:shutil.copytree(origin/'presentation',data/'presentation')
                            else:(data/'presentation').mkdir()
                            before=capture(data/'presentation')
                            write(case/'before.json',before)
                            missing=[]
                            if kind in ('current','both','mixed'):missing.append('calculation/current.json')
                            if kind=='cube_table':missing.append('calculation/'+version+'/cube_effect_table.json')
                            if kind in ('game','both','mixed'):missing.append('game-catalog.json')
                            wanted=[]
                            if any(p.startswith('calculation/') for p in missing):wanted.append({'path':'account-presentation.json','cached':warm})
                            if 'game-catalog.json' in missing:wanted.append({'path':'spec-presentation.json','cached':warm})
                            if kind in ('http','invalid','mixed'):wanted.append({'path':target['path'],'cached':warm})
                            for relative in missing:(data/relative).rename(data/(relative+'.qimg-held'))
                            write(control,{'url':target['url'],'mode':'invalid' if kind=='invalid' else 'http'} if kind in ('http','invalid','mixed') else {})
                            try:
                                state=refresh();write(case/'failure-status.json',state)
                                assert_failure(state,state,wanted,capture(data/'presentation'),before)
                                summary=state['failureSummary']
                                assert summary['imageFailures']==sum(w['path'].startswith('assets/') for w in wanted)
                                assert summary['catalogFailures']==sum(not w['path'].startswith('assets/') for w in wanted)
                                assert summary['cachedFailures']==sum(w['cached'] for w in wanted)
                                for issue in state['unresolved']:
                                    assert issue['kind']==('image' if issue['path'].startswith('assets/') else 'catalog')
                                    assert issue['code']==('invalid_content' if kind=='invalid' else 'http_error' if issue['kind']=='image' else 'missing_metadata')
                                shot=screen(state,f'{kind}-{warm}')
                                if warm and kind=='both':shot['images']=image_screen()
                            finally:
                                for relative in missing:
                                    held=data/(relative+'.qimg-held')
                                    if held.exists():held.rename(data/relative)
                                write(control,{})
                            recovered=refresh();write(case/'recovered-status.json',recovered)
                            assert_recovery(state,state,call('presentation'),recovered,capture(data/'presentation'),before if warm else None)
                            screen(recovered,f'recovery-{kind}-{warm}')
                            return {'failure':state,'recovered':recovered,'browser':shot}
                        check(f'API {kind} cache={warm} + recovery + browser',failure_case)
                # Entire cold index fetch fails; API must not confuse preserved old manifest with this run.
                def total_failure():
                    (data/'presentation').rename(run/'api-total-before');(data/'presentation').mkdir()
                    write(control,{'all':True})
                    state=refresh();write(run/'api-total-failure.json',state)
                    assert state['status']=='failed' and state['failureSummary']['availableImages']==0
                    assert state['failureSummary']['cachedFailures']==0
                    assert '캐시가 없습니다' in state['message']
                    screen(state,'total-failure')
                    write(control,{})
                    recovered=refresh();assert_success(call('presentation'),recovered,capture(data/'presentation'))
                    screen(recovered,'total-recovery')
                    return {'failed':state,'recovered':recovered}
                check('API cold total failure and recovery',total_failure)
                report['browserErrors']=errors
                browser.close()
        finally:
            process.terminate();process.wait(timeout=20);api_log.close()
        report['status']='passed' if all(c['passed'] for c in checks) else 'failed'
    finally:
        changed=[rel for rel,digest in original_hashes.items() if sha(source/rel)!=digest]
        report['originalFilesChecked']=len(original_hashes);report['originalChanges']=changed
        write(run/'source-hashes.json',original_hashes);write(run/'summary.json',report)
        print('EVIDENCE '+str(run),flush=True)
        assert not changed,'original public inputs changed'
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())

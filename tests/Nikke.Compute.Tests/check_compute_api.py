"""Portable, isolated CPU/API smoke. Public tables + synthetic account; no source DB/session reads."""
import argparse, hashlib, json, os, shutil, socket, sqlite3, subprocess, time, urllib.request, urllib.error, uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-data',type=Path,required=True);parser.add_argument('--dotnet',required=True)
    args=parser.parse_args();source=args.source_data.resolve();run=ROOT/'artifacts/single-deck-backend'/uuid.uuid4().hex;data=run/'data';data.mkdir(parents=True)
    hashes={};checks=[];report={'kind':'actual_cpu_api_public_tables_synthetic_account','checks':checks,'status':'failed'}
    def copy(relative):
        src=source/relative;hashes[str(relative)]=digest(src);dest=data/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
    process=None;log=None
    try:
        copy(Path('game-catalog.json'))
        for folder in ('calculation','runtime'):
            copy(Path(folder)/'current.json');manifest=read(data/folder/'current.json');version=manifest['id'];assert len(version)==64 and all(c in '0123456789abcdef' for c in version)
            names=list(manifest['fileHashes']) if folder=='calculation' else ['catalog.json']
            for name in names:assert Path(name).name==name;copy(Path(folder)/version/name)
        game=read(data/'game-catalog.json');runtime=read(data/'runtime'/read(data/'runtime/current.json')['id']/'catalog.json')
        ids=[]
        for name in ('리타','블랑','앨리스','누아르','모더니아'):
            found=[key for key in runtime['characters'] if game['names'].get(key)==name or runtime['characters'][key].get('name')==name]
            assert len(found)==1,(name,found);ids.append(found[0])
        snapshot={'id':'synthetic-compute','accountId':'synthetic-account','gameSnapshotId':game['id'],'synchroLevel':400,'savedAt':'2026-09-15T00:00:00+00:00','observedAt':'2026-09-15T00:00:00+00:00',
            'consoles':{key:0 for key in ('1001','1101','1102','1103','1201','1202','1203','1204','1205')},'characters':[
                {'characterId':id,'name':game['names'][id],'level':400,'nativeLevel':400,'limitBreak':0,'core':0,'bond':0,
                 'skills':{'1':10,'2':10,'3':10},'cubeId':'0','cubeLevel':0,'collectionId':'0','collectionGrade':'none','collectionLevel':0,
                 'equipment':[{'slot':slot,'tier':0,'level':0,'manufacturer':0,'lines':[{'lineIndex':i,'presence':'absent'} for i in range(1,4)]} for slot in ('head','torso','arm','leg')]} for id in ids]}
        # This is a NEW database with explicitly synthetic rows; source accounts.db is never opened.
        with sqlite3.connect(data/'accounts.db') as db:
            db.execute('CREATE TABLE snapshots(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL)')
            db.execute('CREATE TABLE accounts(id TEXT PRIMARY KEY,current_id TEXT NOT NULL REFERENCES snapshots(id))')
            db.execute('INSERT INTO snapshots VALUES(?,?,?,?)',(snapshot['id'],snapshot['accountId'],1,json.dumps(snapshot)))
            db.execute('INSERT INTO accounts VALUES(?,?)',(snapshot['accountId'],snapshot['id']))
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        assert port not in (5180,5181)
        env=dict(os.environ,NIKKE_DATA_ROOT=str(data),NIKKE_PROJECT_ROOT=str(ROOT),NIKKE_GAME_CATALOG=str(data/'game-catalog.json'),NIKKE_PORT=str(port),NIKKE_TEST_FIXTURE='1')
        token=''
        def call(path,payload=None,method=None):
            request=urllib.request.Request(f'http://127.0.0.1:{port}/api/'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Nikke-Token':token},method=method)
            with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)
        def start():
            nonlocal process,log,token
            log=(run/('api-'+str(time.time_ns())+'.log')).open('w',encoding='utf-8')
            process=subprocess.Popen([args.dotnet,str(ROOT/'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            for _ in range(200):
                try:token=call('bootstrap')['token'];return
                except (OSError,urllib.error.URLError):time.sleep(.1)
            raise AssertionError('API startup failed')
        def stop():
            nonlocal process,log
            if process is not None:process.terminate();process.wait(timeout=30);process=None
            if log:log.close();log=None
        def wait(id):
            for _ in range(1800):
                state=call('compute/experiments/'+id)
                if state['state'] in ('completed','failed','cancelled'):return state
                time.sleep(.1)
            raise AssertionError('batch timeout')
        start();initial_snapshot=call('snapshots/'+snapshot['id']);hw=call('compute/hardware');report['hardware']=hw;assert all(not g['eligible'] for g in hw['gpus']);checks.append('hardware inventory with honest GPU unavailability')
        call('accounts/synthetic-account/formation',{'slots':ids},'PUT')
        tactic={'schemaVersion':1,'allowedCharacterIds':ids,'stage1Priority':[ids[0]],'stage2Priority':[ids[1]],'stage3Priority':[ids[2],ids[3],ids[4]],'burst3Rotation':[ids[2],ids[4]],'unavailablePolicy':'next_ready'}
        call('accounts/synthetic-account/burst-tactic',{'snapshotId':snapshot['id'],'formationSlots':ids,'tactic':tactic},'PUT')
        request={'snapshotId':snapshot['id'],'characterIds':ids,'runs':4,'phase':'final','conditions':{'roundingPolicy':'final_round_even','combat':{'durationFrames':10800,'enemyDefense':30925,'critMode':'sample','core':True,'pelletCoefficientPolicy':'per_trigger','manualCharacterId':ids[2]}},'execution':{'requested':'auto','maxWorkers':2}}
        started=time.perf_counter();batch=call('compute/experiments',request);end=wait(batch['id']);assert end['state']=='completed',end
        report['batch']=end;report['wallSeconds']=time.perf_counter()-started
        rows=call('compute/experiments/'+batch['id']+'/results?limit=100')['runs'];assert len(rows)==4 and len({r['runId'] for r in rows})==4
        assert all(r['backend']=='cpu' and len(r['members'])==5 and r['fullBursts']>0 and r['teamDamage']>0 for r in rows)
        assert end['input']['synchroLevel']==400 and end['input']['defPolicy']=='fixed:30925';checks.append('actual ordered five-member 180s CPU batch and persisted tactic')
        report['runs']=rows
        try:call('compute/experiments',dict(request,execution={'requested':'gpu'}));raise AssertionError('GPU accepted')
        except urllib.error.HTTPError as error:assert error.code==409 and 'gpu_unavailable' in error.read().decode()
        checks.append('forced GPU rejected before batch execution')
        retry=call('compute/experiments',request);call('compute/experiments/'+retry['id']+'/cancel',{});cancelled=wait(retry['id']);assert cancelled['state']=='cancelled'
        stop();start();restored=call('compute/experiments/'+retry['id']);assert restored['state']=='cancelled'
        resumed=call('compute/experiments/'+retry['id']+'/resume',{});assert resumed['attempt']==2
        final=wait(retry['id']);assert final['state']=='completed' and final['valid']==4,final
        rows=call('compute/experiments/'+retry['id']+'/results')['runs'];assert len({r['runId'] for r in rows})==4;checks.append('cancel restart resume without duplicate normal samples')
        assert call('snapshots/'+snapshot['id'])==initial_snapshot;checks.append('synthetic snapshot remains unchanged')
        report['status']='passed'
    finally:
        if process is not None:process.terminate();process.wait(timeout=30)
        if log:log.close()
        report['sourceFilesChecked']=len(hashes);report['sourceChanges']=[name for name,value in hashes.items() if digest(source/name)!=value]
        (run/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');(run/'source-hashes.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
        print(run);assert not report['sourceChanges'],'public source changed'

if __name__=='__main__':main()

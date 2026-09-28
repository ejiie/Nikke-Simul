"""Independent Q-F32 B1 API acceptance. Never imports Backend's acceptance script.
Only own prior public fixtures and synthetic compute history; new external dataRoot.
"""
import argparse,json,os,shutil,socket,sqlite3,subprocess,time,urllib.request,urllib.error,uuid
from copy import deepcopy
from pathlib import Path
from public_fixture import create,read,digest
from check_client_f32 import context
from actual_stats import metric

ROOT=Path(__file__).resolve().parents[2]
POLICIES=['client_f32','legacy_term_floor','final_round_even','nested_floor']

def normalized(c):
    c=deepcopy(c)
    for key in ['attackBuffs','runtimeAttackBuffs','attackFlatBuffs']:
        for b in c.get(key,[]):
            if 'rawRate10000' in b:
                b['rawRate10000']=int(b['rawRate10000']);b.setdefault('rate',b['rawRate10000']/10000)
            if 'exactAmount' in b:
                b['exactAmount']=int(b['exactAmount']);b.setdefault('amount',float(b['exactAmount']))
    return c

def main():
    p=argparse.ArgumentParser();p.add_argument('--dotnet',required=True);a=p.parse_args()
    source=ROOT/'artifacts/single-deck-qa/load1000-3db71912a601/data'
    assert source.is_dir()
    run=ROOT/'artifacts/single-deck-qa'/('f32-b1-'+uuid.uuid4().hex[:12]);data=run/'data';data.mkdir(parents=True)
    hashes,game,snapshot,ids=create(source,data)
    report=dict(scope='Q-F32 B1 synthetic independent API only',product='74ca24fc9b242b6268856f82a4c722f2e57f9b9c',checks=[],status='running',performanceComparison=False)
    save=lambda name,value:(run/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    def check(name,ok,detail=None):
        report['checks'].append(dict(name=name,passed=bool(ok),detail=detail));save('summary',report)
        print(name+(': PASS' if ok else ': FAIL'),flush=True)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    assert port not in (5180,5181);report['port']=port
    env=dict(os.environ,NIKKE_DATA_ROOT=str(data),NIKKE_PROJECT_ROOT=str(ROOT),NIKKE_PORT=str(port),NIKKE_TEST_FIXTURE='1');env.pop('NIKKE_GAME_CATALOG',None)
    process=None;log=None;token='';http=[]
    def call(path,payload=None,method=None,raw=None,code=200):
        req=urllib.request.Request(f'http://127.0.0.1:{port}/api/'+path,data=raw.encode() if raw is not None else None if payload is None else json.dumps(payload).encode(),method=method,headers={'Content-Type':'application/json','X-Nikke-Token':token})
        try:
            with urllib.request.urlopen(req,timeout=60) as res:status=res.status;body=res.read().decode()
        except urllib.error.HTTPError as e:status=e.code;body=e.read().decode()
        value=json.loads(body) if body else None
        http.append(dict(path=path,method=req.get_method(),request=payload,raw=raw,status=status,response=value))
        save('http',http)
        assert status==code,(path,status,code,value)
        return value
    def start():
        nonlocal process,log,token
        log=(run/f'api-{time.time_ns()}.log').open('w',encoding='utf-8')
        process=subprocess.Popen([a.dotnet,str(ROOT/'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        report.setdefault('ownedPids',[]).append(process.pid)
        for _ in range(300):
            try:token=call('bootstrap')['token'];return
            except OSError:time.sleep(.1)
        raise AssertionError('own API startup failed')
    def stop():
        nonlocal process,log
        if process:
            process.terminate();process.wait(timeout=30);process=None
        if log:log.close();log=None
    def hit(c,schema=3,policy=None):
        payload=dict(inputSchemaVersion=schema,input=c)
        if policy:payload['roundingPolicy']=policy
        r=call('calculations/hit',payload);expected=context(normalized(c))
        check('hit independent '+r['id'],r['candidates'][0]['exactDamage']==str(expected['damage']) and r['exactEffectiveAttack']==str(expected['attack']) and [x['policy'] for x in r['candidates']]==POLICIES and r['selectedPolicy']==(policy or 'client_f32') and r['originalInput']==c)
        check('hit persistence '+r['id'],call('calculations/hit/'+r['id'])==r==read(data/'hit-calculations'/(r['id']+'.json')))
        return r
    def error(name,payload=None,raw=None,fragment=None,path='calculations/hit',code=400):
        before=len(list((data/'hit-calculations').glob('*.json')))
        r=call(path,payload,raw=raw,code=code)
        check(name,isinstance(r.get('message'),str) and (fragment is None or fragment in r['message']) and before==len(list((data/'hit-calculations').glob('*.json'))),r)
    def wait(id):
        for _ in range(600):
            r=call('compute/experiments/'+id)
            if r['state'] in ['completed','failed','cancelled']:return r
            time.sleep(.1)
        raise AssertionError('small batch timeout')
    def stats(id):
        page=call(f'compute/experiments/{id}/results?limit=1000');rows=page['runs'];st=call(f'compute/experiments/{id}/statistics?cut=0')
        metric(st['team'],[r['teamDamage'] for r in rows],0)
        for member in ids:metric(st['members'][member],[next(m['damage'] for m in r['members'] if m['characterId']==member) for r in rows])
        check('statistics separate '+id,st['team']['n']==len(rows) and all(r['inputFingerprint']==page['batch']['input']['fingerprint'] and sum(m['damage'] for m in r['members'])==r['teamDamage'] for r in rows))
        return rows,st
    try:
        start();original=call('snapshots/'+snapshot['id']);save('hardware',call('compute/hardware'))
        base=dict(statAttack=100,defense=0,coefficient=1,statDamageRatio=2,defenceRatioRate=.25)
        sample=hit(base)
        check('v3 default rates audit',sample['conversion']['converted'] is False and [x['name'] for x in sample['selectedCandidate']['terms']]==['effectiveAttack','effectiveDefense','difference','base','B','extra','reduction','defenceRatio','product','final'] and [x['damage'] for x in sample['candidates']]==[150,100,100,100])
        for policy in POLICIES[1:]:hit(base,policy=policy)
        r=hit({'statAttack':100,'attackBuffs':[{'source':'boundary','rawRate10000':'1450'}],'attackFlatBuffs':[{'source':'after','exactAmount':17}]})
        check('exact output strings',r['input']['attackBuffs'][0]['rawRate10000']=='1450' and r['input']['attackFlatBuffs'][0]['exactAmount']=='17' and r['exactEffectiveAttack']=='132')
        r=hit({'statAttack':0,'attackFlatBuffs':[{'source':'large','exactAmount':'9007199254740993'}]})
        check('unavailable is null not zero',all(x['status']=='unavailable' and x['damage'] is None and x['residual'] is None and x['relativeError'] is None and x['terms']==[] and x['errorCode'] for x in r['candidates'][1:]))
        error('select unavailable rejected',dict(inputSchemaVersion=3,input=r['originalInput'],roundingPolicy='legacy_term_floor'),fragment='selected_policy_unavailable')
        v2input={'statAttack':100,'defense':7,'coefficient':1.5};v2=hit(v2input,schema=2)
        check('v2 original explicit conversion',v2['inputSchemaVersion']==3 and v2['input']['statDamageRatio']==1 and v2['input']['defenceRatioRate']==0 and v2['conversion']==dict(originalSchemaVersion=2,targetSchemaVersion=3,converted=True,method='v2_to_v3_neutral_rates',appliedDefaults=dict(statDamageRatio=1,defenceRatioRate=0)))
        artifact=dict(inputSchemaVersion=2,comparison=dict(input=v2input,observedDamage=140,selectedPolicy='nested_floor',candidates=[{'historicalOnly':'retain'}]),notes='QA synthetic old artifact')
        imported=call('calculations/hit/import',artifact)
        check('old import preserves source and conversion',imported['sourceArtifact']==artifact and imported['originalInput']==v2input and imported['conversion']['converted'] and imported['selectedPolicy']=='nested_floor' and imported['id']!=v2['id'] and call('calculations/hit/'+imported['id'])==imported)
        imported3=call('calculations/hit/import',sample)
        check('new import new ID original record intact',imported3['sourceArtifact']==sample and imported3['id']!=sample['id'] and call('calculations/hit/'+sample['id'])==sample)
        hit({'statAttack':16777217,'defense':16777216,'coefficient':100})
        for label,patch in [('fractional attack',{'statAttack':100.5}),('fractional defense',{'defense':.25}),('fractional flat',{'attackFlatBuffs':[{'source':'x','amount':.1}]}),('precise rate',{'attackBuffs':[{'source':'x','rate':.01401}]}),('raw mismatch',{'attackBuffs':[{'source':'x','rate':.145,'rawRate10000':'1400'}]}),('unsafe numeric exact',{'attackFlatBuffs':[{'source':'x','exactAmount':9007199254740993}]}),('overflow',{'attackFlatBuffs':[{'source':'x','exactAmount':'9223372036854775807'}]}),('unknown field',{'invented':1})]:error(label,dict(inputSchemaVersion=3,input={'statAttack':100}|patch))
        for name,text in [('tiny integer','100.000000000000000001'),('underflow','1e-400')]:error(name,raw='{"inputSchemaVersion":3,"input":{"statAttack":'+text+'}}',fragment='must_be_integer')
        error('lexeme precise rate',raw='{"inputSchemaVersion":3,"input":{"statAttack":100,"attackBuffs":[{"source":"x","rate":0.01400000000000000001}]}}',fragment='exact_1_per_10000')
        for value in ['1e3','1.0',' 100','100 ','9223372036854775808']:
            error('invalid exact string '+repr(value),dict(inputSchemaVersion=3,input=dict(statAttack=100,attackFlatBuffs=[dict(source='x',exactAmount=value)])))
        error('v2 cannot carry v3',dict(inputSchemaVersion=2,input=base),fragment='schema2_cannot_contain_schema3_rates')
        error('missing schema',dict(input={'statAttack':100}),fragment='unsupported_hit_schema')
        error('unknown policy',dict(inputSchemaVersion=3,input={'statAttack':100},roundingPolicy='invented'),fragment='unknown_rounding_policy')
        call('calculations/hit/'+'0'*32,code=404)
        call('accounts/synthetic-account/formation',dict(slots=ids),'PUT')
        tactic=dict(schemaVersion=1,allowedCharacterIds=ids,stage1Priority=[ids[0]],stage2Priority=[ids[1]],stage3Priority=ids[2:],burst3Rotation=[ids[2],ids[4]],unavailablePolicy='next_ready')
        call('accounts/synthetic-account/burst-tactic',dict(snapshotId=snapshot['id'],formationSlots=ids,tactic=tactic),'PUT')
        req=dict(snapshotId=snapshot['id'],characterIds=ids,runs=1,phase='pilot',conditions=dict(combat=dict(durationFrames=600,enemyDefense=30925,critMode='off',core=True,pelletCoefficientPolicy='per_trigger')),execution=dict(requested='cpu',maxWorkers=1,memoryLimitBytes=268435456))
        requests=[('default',req),('legacy',dict(req,conditions=dict(req['conditions'],roundingPolicy='legacy_term_floor')))]
        for label,override in [('stat',{'statDamageRatio':2}),('defence',{'defenceRatioRate':.25}),('raw',{'runtimeAttackBuffs':[{'source':'qa','rawRate10000':'1450'}]}),('rate',{'runtimeAttackBuffs':[{'source':'qa','rate':.145}]}),('flat',{'attackFlatBuffs':[{'source':'qa','exactAmount':'100'}]})]:requests.append((label,dict(req,hitOverrides={ids[2]:override})))
        batches={};prepareds={}
        for label,request in requests:
            b=call('compute/experiments',request,code=202);end=wait(b['id']);save(label+'-batch',end);batches[label]=end
            check('completed '+label,end['state']=='completed' and end['valid']==1 and end['input']['inputSchemaVersion']==3 and end['input']['summaryVersion']=='cpu-summary.2-client-f32')
            stats(b['id'])
            with sqlite3.connect(data/'compute/batches.db') as db:prepared,storedreq=db.execute('SELECT prepared,request FROM experiments WHERE id=?',(b['id'],)).fetchone()
            prepareds[label]=json.loads(prepared);save(label+'-prepared',prepareds[label])
            check('saved tactic and versions '+label,json.loads(storedreq)['conditions']['autoBurst']['tactic']['allowedCharacterIds']==ids and end['input']['defPolicy']=='fixed:30925' and end['input']['synchroLevel']==400)
        check('all inputs and tuning keys separated',len({b['input']['fingerprint'] for b in batches.values()})==7 and len({b['execution']['fingerprint'] for b in batches.values()})==7)
        check('raw presence fingerprint despite equal rate',prepareds['raw']['members'][2]['weapon']['hit']['runtimeAttackBuffs'][0]['rawRate10000']=='1450' and prepareds['rate']['members'][2]['weapon']['hit']['runtimeAttackBuffs'][0]['rawRate10000'] is None)
        repeat=wait(call('compute/experiments',req,code=202)['id']);save('repeat-batch',repeat)
        check('same input cache reuse',repeat['input']['fingerprint']==batches['default']['input']['fingerprint'] and repeat['execution']['fingerprint']==batches['default']['execution']['fingerprint'] and repeat['execution']['tuning']['cacheSource']=='validated_policy_cache')
        for label,request in [('mismatched baseline',dict(requests[2][1],baselineExperimentId=batches['default']['id'])),('unsupported override',dict(req,hitOverrides={ids[2]:{'coefficient':2}})),('foreign ID',dict(req,hitOverrides={'missing':{'statDamageRatio':2}}))]:error(label,request,path='compute/experiments')
        check('synthetic snapshot unchanged',call('snapshots/'+snapshot['id'])==original)
        stop()
        # Genuine pre-transition results produced by our earlier synthetic QA; no account DB copied.
        oldpath=source/'compute/batches.db';oldhash=digest(oldpath)
        with sqlite3.connect(oldpath.as_uri()+'?mode=ro',uri=True) as olddb:
            oldexp=olddb.execute("SELECT * FROM experiments WHERE state='completed' ORDER BY json_extract(request,'$.runs') LIMIT 1").fetchone()
            oldrows=olddb.execute('SELECT * FROM batch_runs WHERE batch=? ORDER BY idx',(oldexp[0],)).fetchall()
        oldid=oldexp[0];oldinput=json.loads(oldexp[3]);oldrun=json.loads(oldrows[0][3]);save('old-run',oldrun)
        save('old-history-source',dict(path=str(oldpath),sha256=oldhash,id=oldid,input=oldinput,rows=len(oldrows),provenance='own Q-LOAD-1000 pre-client synthetic calibration results; read-only'))
        with sqlite3.connect(data/'compute/batches.db') as db:
            db.execute('INSERT INTO experiments VALUES(?,?,?,?,?,?,?,?)',oldexp)
            db.executemany('INSERT INTO batch_runs VALUES(?,?,?,?,?)',oldrows)
        save('prepared',prepareds['default']);save('compute-request',req)
        subprocess.run([a.dotnet,str(ROOT/'tests/single_deck_compute_qa/F32Boundary/bin/Release/net10.0/F32Boundary.dll'),str(run)],check=True,cwd=ROOT)
        boundary=read(run/'boundary.json');check('same hardware old keys and write rejection',boundary['keysDistinct'] and boundary['rejected'] and boundary['countAfterRejected']==0 and boundary['validCount']==1,boundary)
        (run/'cache-probe').mkdir()
        for path in (source/'compute/tuning').glob('*.json'):shutil.copyfile(path,run/'cache-probe'/path.name)
        subprocess.run([a.dotnet,str(ROOT/'tests/single_deck_compute_qa/F32Boundary/bin/Release/net10.0/F32Boundary.dll'),str(run),'--cache'],check=True,cwd=ROOT)
        start()
        oldresult=call(f'compute/experiments/{oldid}/results?limit=1000')
        check('genuine old results unchanged readable',oldresult['runs']==[json.loads(r[3]) for r in oldrows] and oldresult['batch']['input']['inputSchemaVersion']==2 and oldresult['batch']['input']['summaryVersion'] is None)
        error('old resume rejected by version',{},path=f'compute/experiments/{oldid}/resume',code=409,fragment='engine_or_rules_version_changed')
        stats(oldid);rows,_=stats(boundary['batchId']);check('new statistics excludes old rejected row',len(rows)==1 and rows[0]['inputFingerprint']!=oldinput['fingerprint'])
        for b in batches.values():stats(b['id'])
        check('hit archive survives API restart',call('calculations/hit/'+v2['id'])==v2 and call('calculations/hit/'+imported['id'])==imported)
        check('source old DB immutable',digest(oldpath)==oldhash)
        supplemental(run)
        report['status']='passed' if all(c['passed'] for c in report['checks']) else 'failed'
    except Exception as ex:
        report['status']='aborted';report['error']=repr(ex);raise
    finally:
        stop();report['ownApiStopped']=process is None
        report['publicSourceChanges']=[name for name,h in hashes.items() if digest(source/name)!=h]
        save('source-hashes',hashes);save('summary',report);print('EVIDENCE '+str(run),flush=True)
    return 0 if report['status']=='passed' and not report['publicSourceChanges'] else 1

def supplemental(run):
    """Read-only audit also callable after the bounded cache probe; no API rerun."""
    checks=[]
    def check(name,ok):checks.append(dict(name=name,passed=bool(ok)))
    data=read(run/'cache-probe-result.json')
    check('old caches present but new workload miss',data['first']['tuning']['cacheSource']=='miss' and data['first']['tuning']['status']=='measured')
    check('new complete cache validated reuse',data['second']['tuning']['cacheSource']=='validated_policy_cache' and data['first']['fingerprint']==data['second']['fingerprint'])
    check('tampered restored payload rejected',data['tamper']=='prepared_input_fingerprint_mismatch')
    source=ROOT/'artifacts/single-deck-qa/load1000-3db71912a601/data/compute/tuning'
    hashes={p.name:digest(p) for p in source.glob('*.json')}
    check('genuine old cache files unchanged and different key',bool(hashes) and all(digest(run/'cache-probe'/name)==value for name,value in hashes.items()) and data['first']['fingerprint']+'.json' not in hashes)
    for label,field,want in [('stat','statDamageRatio',2),('defence','defenceRatioRate',.25)]:
        frozen=read(run/(label+'-prepared.json'));check('override persisted '+label,frozen['members'][2]['weapon']['hit'][field]==want)
    frozen=read(run/'flat-prepared.json');check('flat exact persisted',frozen['members'][2]['weapon']['hit']['attackFlatBuffs'][0]['exactAmount']=='100')
    actual=read(run/'http.json');results={x['response']['batch']['id']:x['response']['runs'] for x in actual if '/results?' in x['path'] and x['status']==200}
    summary=[]
    for label in ['default','legacy','stat','defence','raw','rate','flat']:
        b=read(run/(label+'-batch.json'));row=results[b['id']][0]
        summary.append(dict(label=label,experimentId=b['id'],teamDamage=row['teamDamage'],members=row['members'],fingerprint=b['input']['fingerprint'],tuningKey=b['execution']['fingerprint'],tuningCache=b['execution']['tuning']['cacheSource'],n=b['valid']))
    check('all new variant API caches miss',all(row['tuningCache']=='miss' for row in summary))
    check('all variant API normal n1 tuning excluded',all(row['n']==1 for row in summary))
    report=dict(checks=checks,passed=sum(c['passed'] for c in checks),failures=[c for c in checks if not c['passed']],oldCacheHashes=hashes,batches=summary,performanceComparison=False)
    (run/'supplemental-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Supplemental',report['passed'],'/',len(checks),flush=True)
    assert not report['failures'],report['failures']

if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='--audit-existing':supplemental(Path(sys.argv[2]))
    else:raise SystemExit(main())

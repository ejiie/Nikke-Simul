"""Actual small isolated API checks. Public allowlist + NEW synthetic account.
No production account, presentation cache, EXE or user-server access; no benchmark comparison.
"""
import argparse,json,os,socket,sqlite3,subprocess,time,urllib.request,urllib.error,uuid
from pathlib import Path
from copy import deepcopy
from public_fixture import create,read,digest
from backend_v1 import results
from actual_stats import metric,comparison

ROOT=Path(__file__).resolve().parents[2]

def main():
    p=argparse.ArgumentParser();p.add_argument('--source-data',type=Path,required=True);p.add_argument('--dotnet',required=True);a=p.parse_args()
    run=ROOT/'artifacts/single-deck-qa'/('small-'+uuid.uuid4().hex[:12]);data=run/'data';data.mkdir(parents=True)
    hashes,game,snapshot,ids=create(a.source_data,data)
    report=dict(evidence='actual_API_CPU_Analysis_public_tables_synthetic_account',checks=[],productCommit='48c11d8654fc7a9be32cfd2ae1f5f2bc66475887',status='running',performanceComparison=False)
    def save(name,obj):(run/(name+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    def check(name,f):
        try: detail=f();report['checks'].append(dict(name=name,passed=True,detail=detail));print(name+': PASS',flush=True)
        except Exception as e:report['checks'].append(dict(name=name,passed=False,error=str(e)));print(name+': FAIL '+str(e),flush=True)
        save('summary',report)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    assert port not in (5180,5181);report['port']=port
    env=dict(os.environ,NIKKE_DATA_ROOT=str(data),NIKKE_PROJECT_ROOT=str(ROOT),NIKKE_PORT=str(port),NIKKE_TEST_FIXTURE='1');env.pop('NIKKE_GAME_CATALOG',None)
    process=log=None;token='';latencies=[]
    def call(path,payload=None,method=None):
        started=time.perf_counter()
        request=urllib.request.Request(f'http://127.0.0.1:{port}/api/'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Nikke-Token':token},method=method)
        with urllib.request.urlopen(request,timeout=45) as res:value=json.load(res)
        latencies.append(dict(path=path,ms=1000*(time.perf_counter()-started)))
        return value
    def start():
        nonlocal process,log,token
        log=(run/f'api-{time.time_ns()}.log').open('w',encoding='utf-8')
        process=subprocess.Popen([a.dotnet,str(ROOT/'src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll')],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for _ in range(300):
            try:token=call('bootstrap')['token'];return
            except OSError:time.sleep(.1)
        raise AssertionError('startup_timeout')
    def stop():
        nonlocal process,log
        if process:process.terminate();process.wait(timeout=30);process=None
        if log:log.close();log=None
    def status(id):return call('compute/experiments/'+id)
    def wait(id):
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            state=status(id)
            if state['state'] in ('completed','failed','cancelled'):return state
            time.sleep(.15)
        raise AssertionError('small_batch_timeout')
    def allpages(id,label):
        pages=[];offset=0
        while True:
            page=call(f'compute/experiments/{id}/results?offset={offset}&limit=1');pages.append(page)
            offset+=len(page['runs'])
            if offset>=page['batch']['valid']:break
        save(label+'-pages',pages);results(pages)
        return [r for p in pages for r in p['runs']]
    def expect_error(request,code,fragment):
        try:call('compute/experiments',request)
        except urllib.error.HTTPError as e:
            body=e.read().decode();assert e.code==code and fragment in body,(e.code,body);return dict(code=e.code,reason=fragment)
        raise AssertionError('invalid_request_accepted')
    try:
        start();original=call('snapshots/'+snapshot['id'])
        hw=call('compute/hardware');save('hardware',hw)
        check('inventory_is_not_GPU_execution',lambda: all(g['eligible'] is False and g['runtimeStatus']=='not_implemented' for g in hw['gpus']) or (_ for _ in ()).throw(AssertionError(hw)))
        call('accounts/synthetic-account/formation',{'slots':ids},'PUT')
        tactic=dict(schemaVersion=1,allowedCharacterIds=ids,stage1Priority=[ids[0]],stage2Priority=[ids[1]],stage3Priority=[ids[2],ids[3],ids[4]],burst3Rotation=[ids[2],ids[4]],firstBurst3CharacterId=None,unavailablePolicy='next_ready')
        call('accounts/synthetic-account/burst-tactic',dict(snapshotId=snapshot['id'],formationSlots=ids,tactic=tactic),'PUT')
        request=dict(snapshotId=snapshot['id'],characterIds=ids,runs=3,phase='final',conditions=dict(roundingPolicy='final_round_even',combat=dict(durationFrames=10800,enemyDefense=30925,critMode='sample',core=True,pelletCoefficientPolicy='per_trigger',manualCharacterId=ids[2])),execution=dict(requested='auto',maxWorkers=2))
        save('request',request)
        batch=call('compute/experiments',request);id=batch['id'];end=wait(id);save('baseline-status',end)
        rows=allpages(id,'baseline');save('baseline-rows',rows)
        def baseline():
            assert end['state']=='completed' and end['valid']==3
            assert end['input']['engineVersion']=='cpu-summary.1' and end['input']['synchroLevel']==400 and end['input']['defPolicy']=='fixed:30925'
            assert end['input']['characterIds']==ids and all(r['teamDamage']>0 and r['backend']=='cpu' for r in rows)
            with sqlite3.connect(data/'compute/batches.db') as db: frozen,stored_request=db.execute('SELECT prepared,request FROM experiments WHERE id=?',(id,)).fetchone()
            obj=json.loads(frozen);req=json.loads(stored_request)
            assert req['conditions']['autoBurst']['tactic']==tactic
            assert obj['conditions']['combat']['enemyDefense']==30925
            assert obj['input']['fingerprint']==end['input']['fingerprint']
            save('prepared-synthetic',obj)
            return dict(selection=end['execution'],fingerprint=end['input']['fingerprint'],valid=len(rows))
        check('summary1_400_order_tactic_fixedDEF_fingerprint',baseline)
        cut=rows[0]['teamDamage']
        def statistics():
            st=call(f'compute/experiments/{id}/statistics?cut={cut}');save('baseline-statistics',st)
            metric(st['team'],[r['teamDamage'] for r in rows],cut)
            for member in ids:metric(st['members'][member],[next(m['damage'] for m in r['members'] if m['characterId']==member) for r in rows])
            assert st['partial'] is False and st['gameVerified'] is False
            assert call(f'compute/experiments/{id}/statistics?cut={cut}')==st
            return dict(n=st['team']['n'],cut=cut,strictSuccess=st['team']['cutSuccess'])
        check('all_pages_independent_Student_type7_Wilson_strict_cut_cache',statistics)
        check('forced_GPU_409',lambda:expect_error(dict(request,execution={'requested':'gpu'}),409,'gpu_unavailable'))
        catalog=call(f'compute/experiments/{id}/ol-candidates');save('catalog',catalog)
        def candidate_catalog():
            assert catalog['catalogVersion']==game['id'] and catalog['gameVerified'] is False
            for c in catalog['candidates']:
                after=c['after'];assert (after['characterId'],after['slot'],after['lineIndex'])==(ids[2],'head',1)
                assert after!=c['before'] and after['optionId'] not in ('StatDef','StatAccuracyCircle','IncHurtDef','IncElementDmg')
            for op,key,sign in [('StatAtk','atk_pct',1),('StatChargeTime','charge_speed_pct',-1)]:
                found={c['after']['value'] for c in catalog['candidates'] if c['after']['optionId']==op}
                expected={sign*v for v in game['optionSteps'][key]}
                if op=='StatAtk':expected.discard(game['optionSteps'][key][0])
                assert found==expected,(op,found,expected)
            return len(catalog['candidates'])
        check('OL_signed_tiers_slot_line_noop_effect_exclusions',candidate_catalog)
        for op in ('StatAtk','StatChargeTime'):
            def ol():
                change=next(c['after'] for c in catalog['candidates'] if c['after']['optionId']==op)
                cr=dict(request,runs=2,baselineExperimentId=id,olChanges=[change]);b=call('compute/experiments',cr);s=wait(b['id']);assert s['state']=='completed'
                rr=allpages(b['id'],op);cc=call(f"compute/experiments/{b['id']}/comparison");save(op+'-comparison',cc)
                comparison(cc,[r['teamDamage'] for r in rows],[r['teamDamage'] for r in rr])
                assert cc['verdict']=='unverified_design_or_input_difference' and cc['gameVerified'] is False
                assert s['input']['fingerprint']!=end['input']['fingerprint'] and not ({r['runId'] for r in rows}&{r['runId'] for r in rr})
                assert call('snapshots/'+snapshot['id'])==original
                return dict(change=change,valid=s['valid'],verdict=cc['verdict'])
            check(op+'_actual_full_rerun_Welch_original_immutable',ol)
        change=next(c['after'] for c in catalog['candidates'] if c['after']['optionId']=='StatChargeTime')
        for label,changes,fragment in [('positive_charge',[dict(change,value=abs(change['value']))],'invalid_ol_value'),('duplicate_line',[change,change],'duplicate_or_excessive_ol_changes'),('absent_line',[dict(change,lineIndex=2)],'ol_line_missing')]:
            check('reject_'+label,lambda:expect_error(dict(request,olChanges=changes),400,fragment))
        def cancel_recover():
            retry=call('compute/experiments',dict(request,runs=6));rid=retry['id'];deadline=time.monotonic()+120
            while time.monotonic()<deadline:
                s=status(rid)
                if s['valid']>=1:break
                assert s['state'] not in ('failed','completed');time.sleep(.1)
            assert 1<=s['valid']<6,s
            before=call(f'compute/experiments/{rid}/results?limit=100')['runs']
            cached=call(f'compute/experiments/{rid}/statistics?cut=0');save('partial-statistics',cached)
            assert cached['partial'] and 1<=cached['team']['n']<6
            started=time.perf_counter();call(f'compute/experiments/{rid}/cancel',{});cancelled=wait(rid);cancel_ms=1000*(time.perf_counter()-started)
            assert cancelled['state']=='cancelled' and cancelled['partial']
            kept=allpages(rid,'cancelled');stop();start()
            assert status(rid)['state']=='cancelled'
            resumed=call(f'compute/experiments/{rid}/resume',{});assert resumed['attempt']==2
            final=wait(rid);assert final['state']=='completed' and final['valid']==6
            rr=allpages(rid,'resumed');byid={r['runId']:r for r in rr}
            assert all(byid[r['runId']]==r for r in kept)
            st=call(f'compute/experiments/{rid}/statistics?cut=0');metric(st['team'],[r['teamDamage'] for r in rr],0);assert not st['partial'] and st['team']['n']==6
            save('resumed-statistics',st)
            return dict(cancelMilliseconds=cancel_ms,preservedValid=len(kept),attempts=[r['attempt'] for r in rr],finalN=6)
        check('cancel_partial_cache_restart_resume_keeps_old_valid_indexes',cancel_recover)
        def crash():
            b=call('compute/experiments',dict(request,runs=2));rid=b['id'];stop();start();s=status(rid)
            assert s['state']=='cancelled' and s['errorCode']=='process_interrupted',s
            call(f'compute/experiments/{rid}/resume',{});final=wait(rid);assert final['valid']==2 and final['attempt']==2
            return dict(recovered=s,final=final)
        check('abrupt_process_death_recovery_and_resume',crash)
        check('synthetic_account_unchanged',lambda:call('snapshots/'+snapshot['id'])==original or (_ for _ in ()).throw(AssertionError('snapshot changed')))
        report['status']='passed' if all(c['passed'] for c in report['checks']) else 'failed'
    except Exception as error:
        report['status']='aborted';report['errorType']=type(error).__name__
        raise
    finally:
        stop();report['sourceFilesChecked']=len(hashes);report['sourceChanges']=[r for r,h in hashes.items() if digest(a.source_data/r)!=h]
        save('latencies',latencies);save('source-hashes',hashes);save('summary',report);print('EVIDENCE '+str(run),flush=True)
        assert not report['sourceChanges']
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())

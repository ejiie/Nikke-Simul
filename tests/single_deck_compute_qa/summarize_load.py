"""Offline complete stored/API audit and bounded-window metric summary; never runs battles."""
import argparse,json,sqlite3,math,hashlib
from pathlib import Path
from public_fixture import read,digest
from backend_v1 import results
from actual_stats import metric
from datetime import datetime

p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();run=a.run
s=read(run/'summary.json');pid=s['apiPid'];telemetry=[json.loads(x) for x in (run/'telemetry.jsonl').read_text(encoding='utf-8').splitlines()];telemetry.append(s['finalHost'])
out=dict(kind='offline_independent_audit_and_observed_battery_window',product=s['product'],distributionAcceptance='not_evaluated',performanceOptimality='not_evaluated',checks={})
with sqlite3.connect(f"file:{(run/'data/compute/batches.db').as_posix()}?mode=ro",uri=True) as db:
    assert db.execute('PRAGMA integrity_check').fetchone()==('ok',)
    out['checks']['sqliteIntegrity']=True
    assert db.execute('SELECT count(*) FROM experiments').fetchone()[0]==2
    assert db.execute('SELECT count(*) FROM batch_runs').fetchone()[0]==1020
    populations=[]
    for name,expected,phase in [('calibration',20,'exploration'),('pilot',1000,'pilot')]:
        pages=read(run/(name+'-pages.json'));results(pages);rows=[r for page in pages for r in page['runs']];final=read(run/(name+'-final.json'));stats=read(run/(name+'-statistics.json'))
        assert len(rows)==expected and [r['index'] for r in rows]==list(range(expected))
        assert final['state']=='completed' and final['valid']==expected and final['failed']==final['cancelled']==0
        assert all(r['phase']==phase and r['attempt']==1 and r['experimentId']==final['id'] for r in rows)
        stored=db.execute('SELECT idx,attempt,payload,error FROM batch_runs WHERE batch=? ORDER BY idx',(final['id'],)).fetchall()
        assert len(stored)==expected
        for i,(index,attempt,payload,error) in enumerate(stored):assert index==i and attempt==1 and error is None and json.loads(payload)==rows[i]
        metric(stats['team'],[r['teamDamage'] for r in rows],stats['team']['cut'])
        for member in final['input']['characterIds']:metric(stats['members'][member],[next(m['damage'] for m in r['members'] if m['characterId']==member) for r in rows])
        timing=read(run/(name+'-timing.json'));normalUpper=timing['endEpoch']-(timing['lastQueuedEpoch'] or timing['startEpoch'])
        # Completion is observed at polling time, so no exact compute-only timing claim.
        before=[t for t in telemetry if t['epoch']<=timing['startEpoch']];after=[t for t in telemetry if t['epoch']>=timing['endEpoch']]
        def cpu(t):return next(x['cpuSeconds'] for x in t['processes'] if x['pid']==pid)
        cpuBracket=None
        if before and after:
            left,right=before[-1],after[0];cpuBracket=dict(seconds=cpu(right)-cpu(left),sampleStartEpoch=left['epoch'],sampleEndEpoch=right['epoch'],includesBoundaryOverhead=True)
        out[name]=dict(id=final['id'],n=expected,phase=phase,normalZero=sum(r['teamDamage']==0 for r in rows),attempt=1,failed=0,cancelled=0,
            startKst=datetime.fromtimestamp(timing['startEpoch']).astimezone().isoformat(),endKst=datetime.fromtimestamp(timing['endEpoch']).astimezone().isoformat(),
            fullWallSeconds=timing['wallSeconds'],fullWallRunsPerSecond=expected/timing['wallSeconds'],normalBatchUpperSeconds=normalUpper,normalFirstRunningObservedSeconds=timing['normalObservedSeconds'],
            preparationMs=timing['preparationMs'],tuningStatus=timing['tuning']['status'],tuningElapsedIsOriginalCacheEvidence=name=='pilot',selectedWorkers=final['execution']['workers'],memoryLimitBytes=final['execution']['memoryLimitBytes'],processCpuBracket=cpuBracket)
        populations.append(set(r['runId'] for r in rows));out['checks'][name+'AllStoredRowsEqualApi']=True
    assert not populations[0]&populations[1]
    out['checks']['calibrationPilotDisjoint']=True
cal=read(run/'calibration-final.json');pilot=read(run/'pilot-final.json')
assert cal['execution']['tuning']['cacheSource']=='miss' and cal['execution']['tuning']['status']=='measured'
assert pilot['execution']['tuning']['cacheSource']=='validated_policy_cache' and pilot['execution']['tuning']['status']=='cache_reused'
assert cal['input']['fingerprint']==pilot['input']['fingerprint']
out['checks']['freshCalibrationCacheThenSameInputReuse']=True
def canonical_hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()
with sqlite3.connect(f"file:{(run/'data/accounts.db').as_posix()}?mode=ro",uri=True) as db:
    snapshot=json.loads(db.execute('SELECT payload FROM snapshots WHERE id=?',('synthetic-compute',)).fetchone()[0])
provenance=read(run/'fixed-provenance.json')
out['fixedFingerprints']=dict(input=pilot['input'],syntheticSnapshotCanonicalSha256=canonical_hash(snapshot),tacticCanonicalSha256=canonical_hash(provenance['tactic']),buildDllHashes=read(run/'build-hashes.json'))
out['projectionOnly']={str(n):dict(seconds=out['pilot']['fullWallSeconds']*n/1000,minutes=out['pilot']['fullWallSeconds']*n/60000,planningSecondsWith50PercentAnd180s=out['pilot']['fullWallSeconds']*n/1000*1.5+180) for n in (10000,50000)}
own=[next(x for x in t['processes'] if x['pid']==pid) for t in telemetry]
out['telemetry']=dict(sampleCount=len(telemetry),batteryStart=read(run/'power-before.json')['batteryPercent'],batteryEnd=read(run/'power-after.json')['batteryPercent'],
    powerStable=all(t['ac']==0 and t['powerScheme']=='ab6534a3-bc02-4c44-94d1-a8535b2eb070' and t['desktop']=='Default' for t in telemetry),
    peakWorkingSet=max(x.get('peakWorkingSet',0) for x in own),sampledPeakPrivateBytes=max(x.get('privateBytes',0) for x in own),finalProcessCpuSeconds=own[-1]['cpuSeconds'],
    minimumAvailablePhysical=min(t['availablePhysical'] for t in telemetry),minimumDiskFree=min(t['diskFreeBytes'] for t in telemetry),finalStorageBytes=telemetry[-1]['storageBytes'],
    maximumSystemCpuPercent=max(t['systemCpuPercent'] or 0 for t in telemetry),maximumExternalSystemCpuPercent=max(t.get('externalSystemCpuPercent',0) for t in telemetry),
    externalComputeObservations=sum(bool(t.get('externalCompute')) for t in telemetry),maxIntervalSeconds=max(t['intervalSeconds'] or 0 for t in telemetry),
    unreadableProcessesRange=[min(t['unreadableProcesses'] for t in telemetry),max(t['unreadableProcesses'] for t in telemetry)],
    statusApiP95Ms=s['statusApiP95Ms'],statusApiSamples=s['statusApiSamples'],unavailableMetrics={k:dict(value=None,reason=v) for k,v in s['unavailableMetrics'].items()})
out['checks']['sourceAndLockPreserved']=not s['sourceChanges'] and s['packageLockUnchanged'];assert out['checks']['sourceAndLockPreserved']
out['checks']['noSafetyStop']=s['stopReason'] is None;assert out['checks']['noSafetyStop']
out['artifactHashes']={f.name:digest(f) for f in sorted(run.glob('*.json')) if f.name!='final-audit.json'}
(run/'final-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='artifactHashes'},ensure_ascii=False,indent=2))

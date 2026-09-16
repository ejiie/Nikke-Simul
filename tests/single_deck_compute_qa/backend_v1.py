"""Read-only adapter for committed Backend 48c11d8 Compute.cs camelCase DTOs.

Consumes a COMPLETE frozen set of BatchResults pages. It does not reconstruct
failed attempts that the results API does not expose. No product code imports.
"""
from fractions import Fraction
from oracle import count, number, require

CONTRACT_COMMIT='48c11d8654fc7a9be32cfd2ae1f5f2bc66475887'
ROUTES={
    'hardware':'/api/compute/hardware',
    'create':'/api/compute/experiments',
    'status':'/api/compute/experiments/{id}',
    'cancel':'/api/compute/experiments/{id}/cancel',
    'resume':'/api/compute/experiments/{id}/resume',
    'results':'/api/compute/experiments/{id}/results?offset={offset}&limit={limit}',
    'statistics':'/api/compute/experiments/{id}/statistics',
    'comparison':'/api/compute/experiments/{id}/comparison',
}


def results(pages):
    require(isinstance(pages,list) and pages, 'missing_result_pages')
    status=pages[0]['batch']
    require(status['state'] in ('completed','cancelled','failed'), 'freeze_terminal_results_before_audit')
    requested,valid,failed,cancelled=(count(status[k]) for k in ('requested','valid','failed','cancelled'))
    require(count(status['attempt']) >= 1, 'invalid_batch_attempt')
    require(valid+failed+cancelled <= requested, 'terminal_counts_exceed_request')
    require(status['partial'] is (valid < requested), 'incorrect_partial')
    if status['state']=='completed':
        require(valid+failed == requested and cancelled==0, 'unfinished_completed_batch')
    experiment=status['input']; execution=status['execution']
    require(experiment['synchroLevel']==400 and count(experiment['durationFrames']) > 0, 'invalid_battle_parameters')
    require(experiment['recordLevel']=='summary' and experiment['gameVerified'] is False, 'invalid_model_claim')
    require(all(experiment[k] for k in ('fingerprint','snapshotId','dataVersion','engineVersion','rulesVersion','defPolicy')), 'missing_input_versions')
    members=experiment['characterIds']
    require(len(members)==5 and len(set(members))==5, 'invalid_five_person_order')
    require(experiment['phase'] in ('warmup','pilot','exploration','final'), 'unknown_sampling_phase')
    require(execution['requested'] in ('auto','cpu','gpu') and execution['backend'], 'unknown_execution')
    require(all(execution[k] for k in ('deviceId','reason','validationVersion','benchmarkVersion','fingerprint')), 'missing_execution_provenance')
    require(count(execution['workers'])>0 and count(execution['chunkSize'])>0 and number(execution['memoryLimitBytes'])>0, 'invalid_execution_budget')
    rows=[]
    for page in sorted(pages,key=lambda p:p['offset']):
        require(page['batch']==status, 'batch_changed_during_pagination')
        require(count(page['offset'])==len(rows), 'missing_or_overlapping_page')
        require(1 <= count(page['limit']) <= 1000 and len(page['runs'])<=page['limit'], 'invalid_page_limit')
        rows.extend(page['runs'])
    require(len(rows)==valid, 'partial_page_set_is_not_complete_results')
    indexes=set()
    for row in rows:
        index=count(row['index'])
        require(index < requested and index not in indexes, 'duplicate_or_invalid_index')
        indexes.add(index)
        require(row['experimentId']==status['id'] and row['runId']==f"{status['id']}:{index}", 'run_identity_mismatch')
        # Earlier successful indexes survive resume; require <= current generation, not ==.
        require(1 <= count(row['attempt']) <= status['attempt'], 'future_or_invalid_attempt')
        require(row['inputFingerprint']==experiment['fingerprint'] and row['phase']==experiment['phase'], 'mixed_input_or_phase')
        require(row['backend']==execution['backend'], 'mixed_backend_population')
        require([m['characterId'] for m in row['members']]==members, 'member_order_changed')
        require(number(row['teamDamage'])>=0, 'invalid_team_damage')
        for member in row['members']:
            require(number(member['damage'])>=0, 'invalid_member_damage')
            for field in ('shots','hits','criticalHits','reloads','burstCasts'): count(member[field])
            # Hits counts normal hits, CriticalHits includes skill damage; no ordering constraint.
        require(Fraction(row['teamDamage'])==sum(Fraction(m['damage']) for m in row['members']), 'team_member_damage_disagrees')
        count(row['fullBursts']);require(number(row['elapsedMilliseconds'])>=0, 'invalid_elapsed_time')
    return dict(contractCommit=CONTRACT_COMMIT, validRuns=len(rows), phase=experiment['phase'],
                scope='frozen_BatchResults_consistency_only', productAcceptance='not_evaluated',
                attemptHistory='not_exposed_by_results_endpoint')

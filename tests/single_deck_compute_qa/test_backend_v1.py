"""Synthetic wire fixtures tied to f2327e5, not actual API execution."""
from copy import deepcopy
import unittest
from backend_v1 import results


def pages():
    ids=['liter','blanc','alice','noir','modernia']
    status=dict(id='fixture-experiment',state='completed',attempt=2,requested=2,valid=2,failed=0,cancelled=0,partial=False,errorCode=None,
                input=dict(fingerprint='input-fixed',snapshotId='synthetic-no-account',dataVersion='fixture',engineVersion='fixture',rulesVersion='fixture',
                           characterIds=ids,synchroLevel=400,durationFrames=10800,phase='final',recordLevel='summary',defPolicy='fixed:30925',gameVerified=False),
                execution=dict(requested='auto',backend='cpu',deviceId='cpu',workers=2,chunkSize=8,memoryLimitBytes=1024**2,reason='fixture',
                               validationVersion='fixture',benchmarkVersion='fixture',fingerprint='fixture',fallbackReason='gpu_not_implemented'))
    rows=[]
    for i in range(2):
        rows.append(dict(runId=f'fixture-experiment:{i}',attempt=i+1,index=i,experimentId='fixture-experiment',inputFingerprint='input-fixed',backend='cpu',phase='final',teamDamage=0,
                         members=[dict(characterId=k,damage=0,shots=0,hits=0,criticalHits=0,reloads=0,burstCasts=0) for k in ids],fullBursts=0,elapsedMilliseconds=1))
    return [dict(batch=status,offset=i,limit=1,runs=[row]) for i,row in enumerate(rows)]


class BackendV1Tests(unittest.TestCase):
    def test_resume_retains_earlier_valid_index(self):
        self.assertEqual(results(pages())['validRuns'],2)

    def test_partial_pagination_not_full_acceptance(self):
        with self.assertRaises(ValueError): results(pages()[:1])

    def test_duplicate_and_future_attempt(self):
        x=pages();x[1]['runs'][0]=deepcopy(x[0]['runs'][0])
        with self.assertRaises(ValueError): results(x)
        x=pages();x[0]['runs'][0]['attempt']=3
        with self.assertRaises(ValueError): results(x)

    def test_torn_pagination_and_wrong_offset(self):
        x=deepcopy(pages()); x[1]['batch']=deepcopy(x[1]['batch']);x[1]['batch']['attempt']=3
        with self.assertRaises(ValueError): results(x)
        x=pages();x[1]['offset']=0
        with self.assertRaises(ValueError): results(x)

    def test_failed_index_not_normal_zero(self):
        x=pages()[:1];s=x[0]['batch'];s.update(valid=1,failed=1,partial=True)
        self.assertEqual(results(x)['validRuns'],1)
        s['valid']=2
        with self.assertRaises(ValueError): results(x)

    def test_wire_member_order_backend_phase_and_sum(self):
        for key,value in [('backend','gpu'),('phase','pilot'),('teamDamage',1),('inputFingerprint','other')]:
            x=pages();x[0]['runs'][0][key]=value
            with self.assertRaises(ValueError): results(x)
        x=pages();x[0]['runs'][0]['members'].reverse()
        with self.assertRaises(ValueError): results(x)

    def test_empty_cancelled_batch_is_partial(self):
        x=pages()[:1];x[0]['runs']=[];x[0]['batch'].update(state='cancelled',valid=0,cancelled=2,partial=True)
        self.assertEqual(results(x)['validRuns'],0)


if __name__=='__main__': unittest.main()

"""Synthetic mutation tests of Q3 audit assertions, not engine/game evidence."""
import copy
import unittest
from verify_log import verify


def fixture():
    rows = []
    for i, (kind, shot) in enumerate([(2, 10), (2, 10), (4, 10), (3, None)]):
        rows.append(dict(hitId=i + 1, shotId=shot, kind=kind, source='5004', frame=60,
                         seconds=1, damage=25, cumulativeDamage=(i + 1) * 25,
                         fullCharge=None, chargeRatioRaw=None, actualChargeFrames=None,
                         effectiveChargeFrames=None, buffs=[], ownBurstEffectActive=bool(i % 2),
                         hit=dict(crit=False, core=True, fullBurst=i >= 2),
                         calculation=dict(damage=25, policy='legacy_term_floor', terms=[])))
    return dict(conditions=dict(combat=dict(durationFrames=10800), roundingPolicy='legacy_term_floor'),
                members=[dict(characterId='5004', damage=100, shots=1)],
                damageLog=dict(schemaVersion=1, status='complete', truncated=False, truncationReason=None,
                               characterId='5004', eventCount=4, totalDamage=100, entries=rows))


class IndependentAuditTests(unittest.TestCase):
    def test_native_saved_envelope_and_multiple_hits_one_shot(self):
        native = fixture()
        expected = verify(native)
        self.assertEqual((expected['hits'], expected['shots']), (4, 1))
        self.assertEqual(len(expected['ownTeamStates']), 4)
        saved = dict(result=native)
        self.assertEqual(expected, verify(saved))
        self.assertEqual(expected, verify(dict(exportSchemaVersion=1, collectionStatus='complete', replay=saved)))

    def test_missing_null_and_zero_are_distinct(self):
        for absent in [False, True]:
            payload = fixture()
            if absent:
                del payload['damageLog']
            else:
                payload['damageLog'] = None
            self.assertIsNone(verify(payload)['damage'])
            self.assertEqual(verify(payload)['status'], 'not_collected')
        payload = fixture()
        payload['damageLog'].update(entries=[], eventCount=0, totalDamage=0)
        payload['members'][0].update(damage=0, shots=0)
        self.assertEqual(verify(payload)['status'], 'complete_zero')
        self.assertEqual(verify(payload)['damage'], 0)

    def test_unknown_and_truncated_are_not_complete(self):
        for changes, expected in [({'schemaVersion': 2}, 'unsupported_schema'),
                                  ({'truncated': True}, 'incomplete'), ({'status': 'truncated'}, 'incomplete')]:
            payload = fixture(); payload['damageLog'].update(changes)
            self.assertEqual(verify(payload)['status'], expected)
            self.assertIsNone(verify(payload)['damage'])

    def test_corruptions_are_rejected(self):
        changes = [
            ('duplicate_hit', lambda p: p['damageLog']['entries'][1].update(hitId=1)),
            ('wrong_source', lambda p: p['damageLog']['entries'][0].update(source='other')),
            ('missing_hit', lambda p: p['damageLog']['entries'].pop()),
            ('wrong_seconds', lambda p: p['damageLog']['entries'][0].update(seconds=2)),
            ('out_of_range', lambda p: p['damageLog']['entries'][-1].update(frame=10801)),
            ('cumulative', lambda p: p['damageLog']['entries'][0].update(cumulativeDamage=0)),
            ('total', lambda p: p['damageLog'].update(totalDamage=0)),
            ('member', lambda p: p['members'][0].update(damage=0)),
            ('additional_new_shot', lambda p: p['damageLog']['entries'][2].update(shotId=99)),
            ('direct_shot', lambda p: p['damageLog']['entries'][3].update(shotId=10)),
            ('null_coerced_false', lambda p: p['damageLog']['entries'][3].update(fullCharge=False)),
            ('calculation', lambda p: p['damageLog']['entries'][0]['calculation'].update(damage=24)),
            ('version_string_kind', lambda p: p['damageLog']['entries'][0].update(kind='NormalHit')),
            ('nan', lambda p: p['damageLog']['entries'][0].update(damage=float('nan'))),
        ]
        for name, change in changes:
            with self.subTest(name=name):
                payload = copy.deepcopy(fixture()); change(payload)
                with self.assertRaises(AssertionError):
                    verify(payload)

    def test_envelope_status_mismatch_rejected(self):
        with self.assertRaises(AssertionError):
            verify(dict(exportSchemaVersion=1, collectionStatus='not_collected', replay=dict(result=fixture())))


if __name__ == '__main__':
    unittest.main(verbosity=2)

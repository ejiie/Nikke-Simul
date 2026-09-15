"""Synthetic mutation tests of the Q-IMG oracle. These are not fixed-product results."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
import uuid
from acceptance import assert_failure, assert_recovery, assert_success, capture

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'artifacts/image-collection-qa' / ('oracle-' + uuid.uuid4().hex)


def snapshot():
    return {'hashes': {'account-presentation.json': 'account', 'spec-presentation.json': 'spec', 'assets/test.png': 'png'},
            'mappings': {k: [{'id': 'synthetic', 'displayName': k}] for k in
                         ('characters', 'consoles', 'cubes', 'supportDefinitions', 'overloadOptions')}}


def failure(cached=True, image=False):
    wanted = [{'path': path, 'cached': cached} for path in ('account-presentation.json', 'spec-presentation.json')]
    if image:
        wanted.append({'path': 'assets/test.png', 'cached': cached})
    presentation = {'unresolved': [{**row, 'error': 'FileNotFoundError' if row['path'].endswith('.json') else 'HTTPError'} for row in wanted]}
    status = {'status': 'partial', 'revision': 1, 'message': '카탈로그 2종 갱신 실패' + (' / 이미지 1개 실패' if image else '')}
    return presentation, status, wanted


class AcceptanceOracleTests(unittest.TestCase):
    def test_complete_success_requires_both_catalogs_and_mappings(self):
        before = snapshot()
        assert_success({'unresolved': []}, {'status': 'succeeded'}, before, copy.deepcopy(before))
        for mutate in (lambda s: s['hashes'].pop('account-presentation.json'), lambda s: s['mappings'].update(cubes=[])):
            changed = snapshot(); mutate(changed)
            with self.assertRaises(AssertionError):
                assert_success({'unresolved': []}, {'status': 'succeeded'}, changed)

    def test_old_baseline_message_is_rejected_by_fixed_oracle(self):
        p, status, expected = failure()
        status['message'] = '이미지 2개를 수집하지 못했습니다. 다시 시도하세요.'
        with self.assertRaisesRegex(AssertionError, 'catalog'):
            assert_failure(p, status, expected, snapshot(), snapshot())

    def test_cached_and_uncached_catalog_failures(self):
        for cached in (True, False):
            p, status, expected = failure(cached)
            assert_failure(p, status, expected, snapshot(), snapshot() if cached else None)

    def test_mixed_failure_has_both_categories(self):
        p, status, expected = failure(image=True)
        assert_failure(p, status, expected, snapshot(), snapshot())
        status['message'] = '카탈로그 3종 실패'
        with self.assertRaises(AssertionError):
            assert_failure(p, status, expected, snapshot(), snapshot())

    def test_no_cache_cannot_claim_old_images_preserved(self):
        p, status, expected = failure(False)
        status['message'] += '. 기존 이미지는 유지됩니다.'
        with self.assertRaises(AssertionError):
            assert_failure(p, status, expected, snapshot())

    def test_message_counts_must_match_actual_failure_categories(self):
        p, status, expected = failure(image=True)
        for message in ('카탈로그 99종 / 이미지 1개 실패', '카탈로그 2종 / 이미지 3개 실패'):
            status['message'] = message
            with self.assertRaises(AssertionError):
                assert_failure(p, status, expected, snapshot(), snapshot())

    def test_hidden_error_duplicate_missing_cause_and_false_cached_rejected(self):
        p, status, expected = failure()
        mutations = [lambda p: p.update(unresolved=[]), lambda p: p['unresolved'].append(p['unresolved'][0]),
                     lambda p: p['unresolved'][0].pop('error'), lambda p: p['unresolved'][0].update(cached=False)]
        for mutate in mutations:
            changed = copy.deepcopy(p); mutate(changed)
            with self.assertRaises(AssertionError):
                assert_failure(changed, status, expected, snapshot(), snapshot())

    def test_cache_loss_mapping_loss_and_image_change_rejected(self):
        p, status, expected = failure()
        changed = snapshot(); changed['hashes']['account-presentation.json'] = 'overwritten'
        with self.assertRaises(AssertionError):
            assert_failure(p, status, expected, changed, snapshot())
        for mutate in (lambda s: s['hashes'].update({'assets/test.png': 'changed'}), lambda s: s['mappings']['cubes'][0].update(displayName='wrong')):
            changed = snapshot(); mutate(changed)
            with self.assertRaises(AssertionError):
                assert_success({'unresolved': []}, {'status': 'succeeded'}, changed, snapshot())

    def test_recovery_requires_clean_status_and_new_revision(self):
        p, status, _ = failure()
        assert_recovery(p, status, {'unresolved': []}, {'status': 'succeeded', 'revision': 2}, snapshot(), snapshot())
        for after_p, after_status in [(p, {'status': 'succeeded', 'revision': 2}),
                                      ({'unresolved': []}, status), ({'unresolved': []}, {'status': 'succeeded', 'revision': 1})]:
            with self.assertRaises(AssertionError):
                assert_recovery(p, status, after_p, after_status, snapshot(), snapshot())

    def test_capture_rejects_corrupt_hash_and_path_escape(self):
        directory = RUN / 'capture'
        directory.mkdir(parents=True)
        (directory / 'assets').mkdir()
        # Signature fixture only; full decoding remains a separate real-image acceptance check.
        image = b'\x89PNG\r\n\x1a\nsynthetic-signature-fixture'
        (directory / 'assets/test.png').write_bytes(image)
        manifest = {'characters': [], 'assets': [{'path': 'assets/test.png', 'sha256': hashlib.sha256(image).hexdigest()}]}
        path = directory / 'presentation.json'
        path.write_text(json.dumps(manifest), encoding='utf-8')
        self.assertIn('assets/test.png', capture(directory)['hashes'])
        manifest['assets'][0]['sha256'] = 'bad'
        path.write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaisesRegex(AssertionError, 'checksum'):
            capture(directory)
        manifest['assets'][0]['path'] = '../outside.png'
        path.write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaisesRegex(AssertionError, 'escaped'):
            capture(directory)


if __name__ == '__main__':
    RUN.mkdir(parents=True)
    with (RUN / 'tests.log').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AcceptanceOracleTests))
    summary = {'evidence': 'synthetic_acceptance_oracle_tests_only', 'productAcceptance': 'not_evaluated_by_this_self_test',
               'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'output': str(RUN)}
    (RUN / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary))
    raise SystemExit(0 if result.wasSuccessful() else 1)

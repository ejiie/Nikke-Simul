import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_combat_conditions import assemble_profiles, enrich_runtime, load_profiles


class CombatCatalogTests(unittest.TestCase):
    def roster(self):
        def role(weapon, low, high, element):
            return dict(name='fixture', shot={'weapon_type': weapon}, bonusrange_min=low, bonusrange_max=high, element=element)
        return {'_source': 'synthetic', 'locale': 'en', 'roster': {
            'rl': role('RL', 0, 0, 'Fire'), 'sr': role('SR', 45, 100, 'Water'),
            'exception': role('SR', 25, 45, 'Electronic')}}

    def test_source_ranges_and_exception_are_preserved_without_weapon_defaults(self):
        source = self.roster()
        result = assemble_profiles(source, 'a' * 64)
        self.assertEqual(result['characters']['rl']['bonusRangeMax'], 0)
        self.assertEqual(result['characters']['exception']['bonusRangeMin'], 25)
        self.assertEqual(result['source']['version'], 'sha256:' + 'a' * 64)
        self.assertEqual(source, self.roster())

    def test_missing_fractional_unknown_source_values_fail(self):
        for key, value in [('bonusrange_min', None), ('bonusrange_max', 1.5), ('bonusrange_min', -1),
                           ('bonusrange_max', 101), ('element', 'electric')]:
            source = self.roster()
            source['roster']['sr'][key] = value
            with self.assertRaises(ValueError):
                assemble_profiles(source, 'a' * 64)

    def test_changed_source_cannot_repin_itself(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'public.json'
            path.write_text(json.dumps(self.roster()), encoding='utf-8')
            with self.assertRaises(ValueError):
                load_profiles(path)

    def test_enrichment_is_immutable_idempotent_and_keeps_graph(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            content = json.dumps({'schemaVersion': 1, 'functions': {'9': {'value': 3}}}).encode()
            old = hashlib.sha256(content).hexdigest()
            (root / old).mkdir()
            (root / old / 'catalog.json').write_bytes(content)
            (root / 'current.json').write_text(json.dumps({'id': old}), encoding='utf-8')
            profiles = assemble_profiles(self.roster(), 'a' * 64)
            new = enrich_runtime(root, profiles)
            self.assertNotEqual(new, old)
            self.assertEqual((root / old / 'catalog.json').read_bytes(), content)
            self.assertEqual(json.loads((root / new / 'catalog.json').read_bytes())['functions'], {'9': {'value': 3}})
            self.assertEqual(enrich_runtime(root, profiles), new)

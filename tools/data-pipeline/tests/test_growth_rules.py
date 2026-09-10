import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from presentation_assets import maximum_bond

class GrowthRulesTests(unittest.TestCase):
    def test_overspec_keeps_40_regardless_of_manufacturer(self):
        for manufacturer in ['elysion','missilis','tetra','pilgrim']:
            self.assertEqual(40,maximum_bond(manufacturer,1))
    def test_pilgrim_and_normal_caps(self):
        self.assertEqual(40,maximum_bond('pilgrim',None))
        self.assertEqual(30,maximum_bond('elysion',0))
        self.assertIsNone(maximum_bond('elysion',None))

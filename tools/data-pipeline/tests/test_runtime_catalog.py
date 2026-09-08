import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_runtime import skill_roots, graph_closure


class RuntimeCatalogTests(unittest.TestCase):
    def test_phases_are_not_lost_or_reordered(self):
        level = {'function_ids': [1], 'function_phases': {'after_hurt': [5], 'before_use': [2], 'after_use': [4], 'before_hurt': [3]}}
        self.assertEqual(skill_roots(level), [1,2,3,4,5])
        self.assertEqual(level['function_phases']['after_hurt'], [5])

    def test_nested_character_skill_and_cycles_preserve_closure(self):
        chains = {'functions': {'1': {'function_type':72,'function_value':9,'connected_function':[2]},
                               '2': {'function_type':1,'connected_function':[1]}, '3': {'function_type':1}},
                  'character_skills': {'9': {'function_phases': {'after_hurt':[3]}}}}
        functions, skills, missing = graph_closure(chains, [1])
        self.assertEqual(set(functions), {'1','2','3'})
        self.assertEqual(set(skills), {'9'})
        self.assertEqual(missing, [])

    def test_missing_edges_are_reported(self):
        chains = {'functions': {'1': {'function_type':72,'function_value':9,'connected_function':[2]}}}
        self.assertEqual(graph_closure(chains, [1])[2], ['character_skill:9','function:2'])

    def test_unreviewed_phase_cannot_silently_disappear(self):
        with self.assertRaises(ValueError):
            skill_roots({'function_phases': {'new_phase': [1]}})

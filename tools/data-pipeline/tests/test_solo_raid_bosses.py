import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prepare_solo_raid_bosses import assemble,digest


class BossPreparationTests(unittest.TestCase):
    rows=[{'raid_number':1,'wave_name':'English source','monster_image':'full_fixture'},
          {'raid_number':2,'wave_name':'Unresolved English','monster_image':'full_other'}]
    def test_only_korean_source_names_are_displayed_and_provenance_is_internal(self):
        raw=b'\x89PNG\r\n\x1a\nsynthetic'
        catalog,internal,images=assemble(self.rows,{1:{'name':'합성 한국어 원천','url':'synthetic-source'}},lambda _:raw)
        self.assertEqual(['dummy','solo-raid-1'],[b['id'] for b in catalog['bosses']])
        self.assertEqual('합성 한국어 원천',catalog['bosses'][1]['name'])
        self.assertEqual('korean_name_unavailable',catalog['diagnostics'][0]['code'])
        self.assertFalse(catalog['complete'])
        self.assertEqual([raw],list(images.values()))
        self.assertNotIn(digest(raw),str(catalog))
        self.assertIn('sourceName',internal[0])
        self.assertNotIn('sourceName',catalog['bosses'][1])
    def test_english_only_name_does_not_fall_back(self):
        catalog,_,images=assemble(self.rows,{1:{'name':'English only'}},lambda _:self.fail('must not download unresolved image'))
        self.assertEqual(1,len(catalog['bosses']));self.assertEqual(2,len(catalog['diagnostics']));self.assertFalse(images)
    def test_invalid_image_becomes_an_explicit_exclusion(self):
        catalog,_,_=assemble(self.rows[:1],{1:{'name':'한국어 이름'}},lambda _:b'<html>error</html>')
        self.assertEqual('boss_image_unavailable',catalog['diagnostics'][0]['code'])
        self.assertEqual(1,len(catalog['bosses']))
    def test_duplicate_season_and_image_path_traversal_are_rejected(self):
        with self.assertRaises(ValueError):assemble(self.rows[:1]*2,{},lambda _:b'')
        with self.assertRaises(ValueError):assemble([dict(self.rows[0],monster_image='../bad')],{},lambda _:b'')


if __name__=='__main__':unittest.main()

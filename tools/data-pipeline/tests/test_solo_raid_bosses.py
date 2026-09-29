import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prepare_solo_raid_bosses import assemble,digest,reviewed_names,REVIEWED_NAMES


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

    def test_changed_identity_and_unknown_season_never_inherit_a_known_name(self):
        manifest=json.loads(REVIEWED_NAMES.read_text(encoding='utf-8'))
        record=manifest['records'][0]
        original={'raid_number':record['season'],'wave_name':record['expectedSourceName'],'monster_image':record['expectedSourceId']}
        rows=[dict(original,monster_image='changed'),dict(original,raid_number=1000)]
        names,issues=reviewed_names(rows,manifest)
        catalog,internal,_=assemble(rows,names,lambda _:self.fail('unverified identity must not download'),issues)
        self.assertFalse(catalog['complete'])
        self.assertEqual(2,len(catalog['diagnostics']))
        self.assertTrue(all(d['code']=='korean_name_unavailable' for d in catalog['diagnostics']))
        self.assertEqual(issues[record['season']],internal[1]['detail'])

    def test_reviewed_source_trace_is_required_and_not_public(self):
        manifest=json.loads(REVIEWED_NAMES.read_text(encoding='utf-8'))
        rows=[{'raid_number':r['season'],'wave_name':r['expectedSourceName'],'monster_image':r['expectedSourceId']} for r in manifest['records']]
        names,issues=reviewed_names(rows,manifest)
        self.assertFalse(issues)
        self.assertEqual('울트라',names[37]['name'])
        self.assertEqual('앨트루이아',names[42]['name'])
        catalog,_,_=assemble(rows,names,lambda _:b'\x89PNG\r\n\x1a\nfixture')
        self.assertEqual(43,len(catalog['bosses']))
        self.assertTrue(catalog['complete'])
        for boss in catalog['bosses']:
            self.assertEqual({'id','name','season','imageUrl'},set(boss))
        broken=copy.deepcopy(manifest)
        broken['records'][0]['name']='추측한 이름'
        with self.assertRaisesRegex(ValueError,'reviewed_name_not_in_adopted_source'):
            reviewed_names(rows,broken)


if __name__=='__main__':unittest.main()

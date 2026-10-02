import copy
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_solo_raid_boss_attributes as prep
from prepare_solo_raid_boss_attributes import SCHEMAS, StaticDataError, build_attributes


def enc_string(value):
    raw = value.encode('utf-8')
    return struct.pack('<i', ~len(raw)) + struct.pack('<i', len(value)) + raw if value else struct.pack('<i', 0)


def enc_value(kind, value):
    if kind.endswith('[]'):
        return struct.pack('<i', len(value)) + b''.join(enc_value(kind[:-2], v) for v in value)
    if kind.startswith('@'):
        return enc_object(SCHEMAS[kind[1:]], value)
    return {'int': lambda: struct.pack('<i', value), 'enum': lambda: struct.pack('<i', value),
            'uint': lambda: struct.pack('<I', value), 'long': lambda: struct.pack('<q', value),
            'float': lambda: struct.pack('<f', value), 'bool': lambda: bytes([int(value)]),
            'string': lambda: enc_string(value)}[kind]()


def enc_object(schema, row):
    return bytes([len(schema)]) + b''.join(enc_value(kind, row[name]) for name, kind in schema)


def enc_table(schema_name, rows):
    return struct.pack('<i', len(rows)) + b''.join(enc_object(SCHEMAS[schema_name], r) for r in rows)


def fill(schema_name, **values):
    row = {}
    for name, kind in SCHEMAS[schema_name]:
        row[name] = values.get(name, [] if kind.endswith('[]') else '' if kind == 'string' else False if kind == 'bool' else 0)
    return row


ELEMENTS = [(100001, 'icn_element_fire', 200001), (200001, 'icn_element_water', 400001), (300001, 'icn_element_wind', 100001),
            (400001, 'icn_element_elect', 500001), (500001, 'icn_element_iron', 300001)]


def archive_entries(seasons=(1, 2)):
    managers, presets, waves, monsters, parts = [], [], [], [], []
    groups = ['stage_id, group_id']
    for i, season in enumerate(seasons):
        group, wave, boss, model = 10000 + season, 6700000 + season * 100 + 2, 1000 + season, 500 + season
        managers.append(fill('SoloRaidManagerData', Id=1000000 + season, Monster_preset=group, Ranking_group_id=season))
        for level in (45, 85):
            presets.append(fill('SoloRaidPresetData', Id=group * 1000 + level, Preset_group_id=group, Difficulty_type=1,
                Monster_stage_lv=level, Wave=wave - 1, Monster_image=f'full_boss{season}'))
        presets.append(fill('SoloRaidPresetData', Id=group * 1000 + 999, Preset_group_id=group, Difficulty_type=2, Character_lv=400,
            Monster_stage_lv=390, Monster_stage_lv_change_group=904, Wave=wave, Monster_image=f'full_boss{season}'))
        groups.append(f'{wave}, wave_x')
        path = fill('WavePathData', wave_path='p', wave_monster_list=[fill('WaveMonster', wave_monster_id=boss), fill('WaveMonster', wave_monster_id=77)])
        waves.append(fill('WaveData', stage_id=wave, group_id='wave_x', target_list=[boss, 0], wave_data=[path]))
        monsters.append(fill('MonsterData', id=boss, element_id=[ELEMENTS[i][0]], monster_model_id=model, hp_ratio=10000,
            defence_ratio=10000, defence_ratio_ratio=0, statenhance_id=230000))
        parts.append(fill('MonsterPartData', id=model * 100 + 1, monster_model_id=model, is_main_part=True, hp_ratio=10000, defence_ratio=10000))
        if season == 1:
            parts.append(fill('MonsterPartData', id=model * 100 + 2, monster_model_id=model, hp_ratio=0, parts_object=['core_col_01'], weapon_object=['gun']))
    stats = [fill('MonsterStatEnhanceData', id=230000 + lv, group_id=230000, lv=lv, level_hp=lv * 1000, level_attack=lv, level_defence=lv * 10)
             for lv in (45, 85, 390, 400)]
    changes = [fill('StageLvChangeData', id=90401, group_id=904, step=1, flag=1, range_from=0, range_to=2000000000, level=390),
               fill('StageLvChangeData', id=90402, group_id=904, step=2, flag=1, range_from=2000000001, range_to=0, level=400)]
    elements = [fill('ElementData', id=i, element=4, group_id=5, weak_element_id=w, icon=icon) for i, icon, w in ELEMENTS]
    models = [fill('MonsterModelData', id=500 + s, mon_prefab=f'boss{s}') for s in seasons]
    return {'SoloRaidManagerTable.mpk': enc_table('SoloRaidManagerData', managers), 'SoloRaidPresetTable.mpk': enc_table('SoloRaidPresetData', presets),
            'MonsterTable.mpk': enc_table('MonsterData', monsters), 'MonsterStatEnhanceTable.mpk': enc_table('MonsterStatEnhanceData', stats),
            'MonsterPartsTable.mpk': enc_table('MonsterPartData', parts), 'MonsterModelTable.mpk': enc_table('MonsterModelData', models),
            'ElementTable.mpk': enc_table('ElementData', elements), 'MonsterStageLvChangeTable.mpk': enc_table('StageLvChangeData', changes),
            'WaveData.GroupDict.csv': '\n'.join(groups).encode(), 'WaveDataTable.wave_x.mpk': enc_table('WaveData', waves)}


def build(entries, expected=2, images=None):
    return build_attributes(entries.get, expected, images)


class BossAttributeTests(unittest.TestCase):
    def test_exact_join_levels_element_defence_and_parts(self):
        catalog = build(archive_entries())
        one, two = catalog['bosses']
        self.assertEqual((1, 'available'), (one['season'], one['status']))
        self.assertEqual({'id': 100001, 'key': 'Fire', 'weakId': 200001, 'weakKey': 'Water'}, one['element'])
        self.assertEqual({'id': 200001, 'key': 'Water', 'weakId': 400001, 'weakKey': 'Electronic'}, two['element'])
        self.assertEqual((390, 400), (one['challenge']['level'], one['challenge']['characterLevel']))
        self.assertEqual(3900, one['challenge']['stats']['defence'])
        self.assertEqual([45, 85], [x['level'] for x in one['ladder']])
        self.assertEqual((10000, 0, 1001), (one['defenceRatio'], one['defenceRatioRate'], one['monsterId']))
        steps = one['challenge']['levelChange']['steps']
        self.assertEqual([(0, 2000000000, 390), (2000000001, None, 400)], [(s['rangeFrom'], s['rangeTo'], s['level']) for s in steps])
        self.assertEqual(4000, steps[1]['stats']['defence'])
        self.assertEqual(2, len(one['parts']))
        self.assertEqual({'kind': 'separate_part', 'partIds': [50102], 'evidence': 'collider_name_contains_core'}, one['core'])

    def test_missing_core_marker_is_unconfirmed_not_guessed(self):
        two = build(archive_entries())['bosses'][1]
        self.assertEqual('unconfirmed', two['core']['kind'])
        self.assertEqual([], two['core']['partIds'])
        self.assertIn('core_position', two['unconfirmed'])

    def test_absent_season_is_an_explicit_diagnostic(self):
        catalog = build(archive_entries(), expected=3)
        missing = catalog['bosses'][2]
        self.assertEqual({'id': 'solo-raid-3', 'season': 3, 'status': 'unavailable', 'reason': 'static_data_season_missing'}, missing)
        self.assertFalse(catalog['complete'])
        self.assertEqual('static_data_season_missing', catalog['diagnostics'][0]['code'])
        self.assertEqual({'id', 'season', 'code', 'displayable', 'message'}, set(catalog['diagnostics'][0]))
        self.assertFalse(catalog['diagnostics'][0]['displayable'])

    def test_missing_level_row_is_unconfirmed_not_zero(self):
        entries = archive_entries()
        stats = [fill('MonsterStatEnhanceData', id=230000 + lv, group_id=230000, lv=lv, level_defence=lv) for lv in (45, 85, 390)]
        entries['MonsterStatEnhanceTable.mpk'] = enc_table('MonsterStatEnhanceData', stats)
        one = build(entries)['bosses'][0]
        self.assertIsNone(one['challenge']['levelChange']['steps'][1]['stats'])
        self.assertIn('level_change_step_2_stats', one['unconfirmed'])

    def test_missing_challenge_level_row_is_null_and_declared_unconfirmed(self):
        entries = archive_entries()
        stats = [fill('MonsterStatEnhanceData', id=230000 + lv, group_id=230000, lv=lv, level_defence=lv) for lv in (45, 85, 400)]
        entries['MonsterStatEnhanceTable.mpk'] = enc_table('MonsterStatEnhanceData', stats)
        one = build(entries)['bosses'][0]
        self.assertIsNone(one['challenge']['stats'])
        self.assertIn('challenge_level_stats', one['unconfirmed'])
        self.assertEqual(100001, one['element']['id'])
        self.assertIn('level_change_step_1_stats', one['unconfirmed'])

    def test_defence_ratio_rate_is_a_raw_value_never_defaulted(self):
        entries = archive_entries()
        rows = [fill('MonsterData', id=1001, element_id=[100001], monster_model_id=501, hp_ratio=10000, defence_ratio=10000,
                     defence_ratio_ratio=6000, statenhance_id=230000),
                fill('MonsterData', id=1002, element_id=[200001], monster_model_id=502, hp_ratio=10000, defence_ratio=10000, statenhance_id=230000)]
        entries['MonsterTable.mpk'] = enc_table('MonsterData', rows)
        self.assertEqual([6000, 0], [b['defenceRatioRate'] for b in build(entries)['bosses']])

    def test_multi_element_boss_has_no_element(self):
        entries = archive_entries()
        rows = [fill('MonsterData', id=1001, element_id=[100001, 200001], monster_model_id=501, statenhance_id=230000),
                fill('MonsterData', id=1002, element_id=[200001], monster_model_id=502, statenhance_id=230000)]
        entries['MonsterTable.mpk'] = enc_table('MonsterData', rows)
        one = build(entries)['bosses'][0]
        self.assertIsNone(one['element'])
        self.assertIn('element', one['unconfirmed'])

    def test_drift_and_ambiguity_fail_instead_of_guessing(self):
        entries = archive_entries()
        truncated = dict(entries, **{'MonsterTable.mpk': entries['MonsterTable.mpk'] + b'\x00'})
        with self.assertRaises(StaticDataError):
            build(truncated)
        member_drift = bytearray(entries['ElementTable.mpk'])
        member_drift[4] = 9
        with self.assertRaises(StaticDataError):
            build(dict(entries, **{'ElementTable.mpk': bytes(member_drift)}))
        with self.assertRaises(StaticDataError):
            build({k: v for k, v in entries.items() if k != 'WaveDataTable.wave_x.mpk'})
        waves = enc_table('WaveData', [fill('WaveData', stage_id=6700102, group_id='wave_x', target_list=[1001, 1002],
            wave_data=[fill('WavePathData', wave_monster_list=[fill('WaveMonster', wave_monster_id=1001), fill('WaveMonster', wave_monster_id=1002)])]),
            fill('WaveData', stage_id=6700202, group_id='wave_x', target_list=[1002],
            wave_data=[fill('WavePathData', wave_monster_list=[fill('WaveMonster', wave_monster_id=1002)])])])
        with self.assertRaises(StaticDataError):
            build(dict(entries, **{'WaveDataTable.wave_x.mpk': waves}))

    def test_duplicate_season_relation_and_reviewed_image_mismatch_are_rejected(self):
        entries = archive_entries()
        managers = enc_table('SoloRaidManagerData', [fill('SoloRaidManagerData', Id=1, Monster_preset=10001, Ranking_group_id=1),
            fill('SoloRaidManagerData', Id=2, Monster_preset=10002, Ranking_group_id=1)])
        with self.assertRaises(StaticDataError):
            build(dict(entries, **{'SoloRaidManagerTable.mpk': managers}))
        with self.assertRaises(StaticDataError):
            build(entries, images={1: 'full_other'})
        self.assertEqual(2, len(build(entries, images={1: 'full_boss1', 2: 'full_boss2', 3: 'full_boss3'})['bosses']))

    def test_unknown_element_icon_is_rejected(self):
        entries = archive_entries()
        rows = [fill('ElementData', id=100001, icon='icn_element_new', weak_element_id=200001)]
        with self.assertRaises(StaticDataError):
            build(dict(entries, **{'ElementTable.mpk': enc_table('ElementData', rows)}))

    def test_source_fingerprint_changes_when_an_entry_changes(self):
        before = build(archive_entries())['source']['entries']
        entries = archive_entries()
        stats = [fill('MonsterStatEnhanceData', id=230000 + lv, group_id=230000, lv=lv, level_defence=lv + 1) for lv in (45, 85, 390, 400)]
        entries['MonsterStatEnhanceTable.mpk'] = enc_table('MonsterStatEnhanceData', stats)
        after = build(entries)['source']['entries']
        self.assertNotEqual(before['MonsterStatEnhanceTable.mpk']['sha256'], after['MonsterStatEnhanceTable.mpk']['sha256'])
        self.assertEqual(before['MonsterTable.mpk'], after['MonsterTable.mpk'])
        self.assertIn('WaveDataTable.wave_x.mpk', before)


if __name__ == '__main__':
    unittest.main()

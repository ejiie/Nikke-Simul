"""B-DATA-1: prepare a version-pinned, display-only catalog of solo raid boss static attributes.

Input is an already-downloaded StaticData.zip (MemoryPack tables). Nothing is fetched and the
archive is only read. Decoded tables are not committed or redistributed; only the derived
catalog is written, into an explicit presentation root outside the repository.

Rules:
- every table must decode exactly (member count per record, end of buffer, root count);
- boss identity is the exact join manager -> challenge preset -> GroupDict -> WaveData
  (target list intersect spawned monsters), not a name or position guess;
- a field that cannot be derived is null and listed in ``unconfirmed``; nothing is guessed;
- seasons absent from the archive are explicit diagnostics, never filled in.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import struct
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
KIND = 'solo_raid_boss_static_attributes'
OUTPUT_NAME = 'solo-raid-boss-attributes.json'
REVIEWED_NAMES = Path(__file__).with_name('manifests') / 'solo-raid-korean-names.manifest.json'
CHALLENGE = 2
LADDER = 1

# MemoryPack member order, ported from the pinned public converter models as recorded in
# docs/hit-damage-source-investigation.ko.md (S9) and the legacy decoder. Member counts are
# enforced per record, so a client/schema drift fails instead of shifting fields.
SCHEMAS = {
    'SoloRaidManagerData': [('Id', 'int'), ('Monster_preset', 'int'), ('Ranking_group_id', 'int')],
    'SoloRaidPresetData': [
        ('Id', 'int'), ('Preset_group_id', 'int'), ('Difficulty_type', 'enum'), ('Quick_battle_type', 'enum'),
        ('Character_lv', 'int'), ('Wave_open_condition', 'int'), ('Wave_order', 'int'), ('Wave', 'int'),
        ('Monster_stage_lv', 'int'), ('Monster_stage_lv_change_group', 'int'), ('Dynamic_object_stage_lv', 'int'),
        ('Cover_stage_lv', 'int'), ('Spot_autocontrol', 'bool'), ('Wave_name', 'string'),
        ('Wave_description', 'string'), ('Monster_image_si', 'string'), ('Monster_image', 'string'),
        ('First_clear_reward_id', 'int'), ('Reward_id', 'int')],
    'WaveMonster': [('wave_monster_id', 'long'), ('spawn_type', 'enum')],
    'WavePathData': [('wave_path', 'string'), ('private_monster_count', 'int'), ('wave_monster_list', '@WaveMonster[]')],
    'WaveData': [
        ('stage_id', 'int'), ('group_id', 'string'), ('spot_mod', 'enum'), ('ui_theme', 'enum'),
        ('battle_time', 'int'), ('mod_value', 'string'), ('monster_count', 'int'), ('use_intro_scene', 'bool'),
        ('wave_repeat', 'bool'), ('point_data', 'string'), ('point_data_fly', 'string'),
        ('background_name', 'string'), ('theme', 'enum'), ('theme_time', 'enum'), ('stage_info_bg', 'string'),
        ('target_list', 'long[]'), ('wave_data', '@WavePathData[]'), ('close_monster_count', 'int'),
        ('mid_monster_count', 'int'), ('far_monster_count', 'int')],
    'MonsterSkillInfoData': [('skill_id', 'int'), ('use_function_id_skill', 'int[]'), ('hurt_function_id_skill', 'int[]')],
    'MonsterData': [
        ('id', 'long'), ('element_id', 'int[]'), ('monster_model_id', 'int'), ('ui_grade', 'enum'),
        ('name_localkey', 'string'), ('appearance_localkey', 'string'), ('description_localkey', 'string'),
        ('is_irregular', 'bool'), ('hp_ratio', 'int'), ('defence_ratio', 'int'), ('attack_ratio', 'int'),
        ('defence_ratio_ratio', 'int'), ('energy_resist_ratio', 'int'), ('metal_resist_ratio', 'int'),
        ('bio_resist_ratio', 'int'), ('detector_center', 'int'), ('detector_radius', 'int'), ('nonetarget', 'enum'),
        ('functionnonetarget', 'enum'), ('spot_ai', 'string'), ('spot_ai_defense', 'string'),
        ('spot_ai_basedefense', 'string'), ('spot_move_speed', 'int'), ('spot_acceleration_time', 'int'),
        ('fixed_spawn_type', 'enum'), ('spot_rand_ratio_normal', 'int'), ('spot_rand_ratio_jump', 'int'),
        ('spot_rand_ratio_drop', 'int'), ('spot_rand_ratio_dash', 'int'), ('spot_rand_ratio_teleport', 'int'),
        ('passive_skill_id', 'int'), ('skill_data', '@MonsterSkillInfoData[]'), ('statenhance_id', 'int')],
    'MonsterStatEnhanceData': [
        ('id', 'int'), ('group_id', 'int'), ('lv', 'int'), ('level_hp', 'long'), ('level_attack', 'int'),
        ('level_defence', 'int'), ('level_statdamageratio', 'int'), ('level_energy_resist', 'int'),
        ('level_metal_resist', 'int'), ('level_bio_resist', 'int'), ('level_projectile_hp', 'int'),
        ('level_broken_hp', 'long')],
    'MonsterPartData': [
        ('id', 'int'), ('monster_model_id', 'int'), ('parts_name_localkey', 'string'), ('damage_hp_ratio', 'int'),
        ('hp_ratio', 'int'), ('defence_ratio', 'int'), ('destroy_after_anim', 'bool'),
        ('destroy_after_movable', 'bool'), ('passive_skill_id', 'int'), ('visible_hp', 'bool'),
        ('linked_parts_id', 'int'), ('weapon_object', 'string[]'), ('weapon_object_enum', 'int[]'),
        ('parts_type', 'enum'), ('parts_object', 'string[]'), ('energy_resist_ratio', 'int'),
        ('metal_resist_ratio', 'int'), ('bio_resist_ratio', 'int'), ('attack_ratio', 'int'),
        ('parts_skin', 'string'), ('monster_destroy_anim_trigger', 'enum'), ('is_main_part', 'bool'),
        ('is_parts_damage_able', 'bool')],
    'MonsterModelData': [
        ('id', 'int'), ('resource_id', 'int'), ('mon_prefab', 'string'), ('grade', 'enum'),
        ('monster_generation', 'float'), ('size', 'enum'), ('dissolve_type', 'enum'), ('attribute', 'enum'),
        ('move_type', 'enum'), ('category_type_1', 'enum'), ('category_type_2', 'enum'),
        ('category_type_3', 'enum'), ('monster_class', 'enum')],
    # Member names inferred from the exact 8-member wire layout and the string values themselves.
    'ElementData': [
        ('id', 'int'), ('element', 'enum'), ('group_id', 'int'), ('weak_element_id', 'int'),
        ('name_localkey', 'string'), ('code_name_localkey', 'string'), ('desc_localkey', 'string'),
        ('icon', 'string')],
    # Positional names: the layout was recovered from the wire (10 members, exact end of buffer);
    # the real member names are unconfirmed. range_from is unsigned (2,400,000,001 > int32).
    'StageLvChangeData': [
        ('id', 'int'), ('group_id', 'int'), ('step', 'int'), ('flag', 'int'), ('range_from', 'uint'),
        ('field_6', 'int'), ('range_to', 'long'), ('level', 'int'), ('field_9', 'int'), ('field_10', 'long')],
}
TABLES = {
    'SoloRaidManagerTable.mpk': 'SoloRaidManagerData', 'SoloRaidPresetTable.mpk': 'SoloRaidPresetData',
    'MonsterTable.mpk': 'MonsterData', 'MonsterStatEnhanceTable.mpk': 'MonsterStatEnhanceData',
    'MonsterPartsTable.mpk': 'MonsterPartData', 'MonsterModelTable.mpk': 'MonsterModelData',
    'ElementTable.mpk': 'ElementData', 'MonsterStageLvChangeTable.mpk': 'StageLvChangeData'}
GROUP_DICT = 'WaveData.GroupDict.csv'
# The app's element vocabulary (BossConditionResolver.IsElement); mapped through the table's own icon.
ICON_TO_ELEMENT = {'icn_element_fire': 'Fire', 'icn_element_water': 'Water', 'icn_element_wind': 'Wind',
                   'icn_element_elect': 'Electronic', 'icn_element_iron': 'Iron'}

FIELDS = [
    {'key': 'element', 'label': '속성', 'source': 'MonsterTable.element_id → ElementTable.icon', 'unit': '속성 ID',
     'confidence': '확인', 'note': '보스 monster 행의 element_id가 정확히 1개일 때만 채운다.'},
    {'key': 'weakElement', 'label': '약점 속성', 'source': 'ElementTable.weak_element_id(보스 속성 행)', 'unit': '속성 ID',
     'confidence': '유력', 'note': '필드 이름과 알려진 상성(불→바람→철→전기→물→불)이 일치. 계산에는 반영하지 않는다.'},
    {'key': 'challengeLevel', 'label': '챌린지 레벨', 'source': 'SoloRaidPresetTable(Difficulty_type=2).Monster_stage_lv',
     'unit': '레벨', 'confidence': '확인', 'note': 'Character_lv(싱크로 레벨)도 함께 표시. 일반 난이도 사다리는 별도 ladder.'},
    {'key': 'levelChange', 'label': '레벨 변경', 'source': 'MonsterStageLvChangeTable(group=Monster_stage_lv_change_group)',
     'unit': '누적 피해 구간 → 레벨', 'confidence': '유력',
     'note': '그룹 904: 0~20억 레벨 390, 20억 초과 레벨 400. 사용자 R4(20억 초과 시 DEF 30925→31784)와 DEF 표 값이 일치하나 열 이름은 미확인.'},
    {'key': 'levelStats', 'label': '레벨별 HP·공격·방어', 'source': 'MonsterStatEnhanceTable[group=monster.statenhance_id, lv]',
     'unit': '정수', 'confidence': '확인', 'note': '표의 원값. monster.hp_ratio·defence_ratio와의 곱 규칙은 미확인이라 곱하지 않는다.'},
    {'key': 'defence', 'label': '방어력', 'source': 'levelStats.defence, MonsterTable.defence_ratio, MonsterPartsTable.defence_ratio',
     'unit': '표 원값(비율은 /10000 후보)', 'confidence': '확인(원값) / 미확인(합성)',
     'note': '유효 방어력으로의 합성은 확정하지 않았다. 챌린지 레벨 390·400 값은 사용자 R4의 30925·31784와 일치.'},
    {'key': 'defenceRatioRate', 'label': '방어율', 'source': 'MonsterTable.defence_ratio_ratio', 'unit': '원값(단위 미확인)',
     'confidence': '확인(필드·값) / 미확인(단위)', 'note': '시즌 1~40 보스는 모두 0. 방어율 기믹의 단위·적용 조건은 미확인.'},
    {'key': 'parts', 'label': '파츠 구성', 'source': 'MonsterPartsTable[monster_model_id]', 'unit': '파츠 행', 'confidence': '확인',
     'note': 'parts_type은 원값 정수만 제공(이름 매핑 미검증). 파츠별 defence_ratio·hp_ratio는 원값.'},
    {'key': 'core', 'label': '코어 구성', 'source': 'MonsterPartsTable.weapon_object/parts_object/parts_skin 의 collider 이름', 'unit': '파츠 ID',
     'confidence': '유력', 'note': 'collider 이름에 core가 든 파츠를 코어로 본다. 없으면 코어 위치 미확인(몸통 기본 약점 추정은 하지 않는다).'},
]


class StaticDataError(RuntimeError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class Reader:
    def __init__(self, buffer):
        self.b, self.o = buffer, 0

    def take(self, fmt):
        value = struct.unpack_from(fmt, self.b, self.o)[0]
        self.o += struct.calcsize(fmt)
        return value

    def string(self):
        h = self.take('<i')
        if h == -1:
            return None
        if h == 0:
            return ''
        if h <= -2:
            size = ~h
            self.take('<i')
            value = self.b[self.o:self.o + size].decode('utf-8')
            self.o += size
            return value
        value = self.b[self.o:self.o + 2 * h].decode('utf-16-le')
        self.o += 2 * h
        return value


def read_value(r, kind):
    if kind.endswith('[]'):
        count = r.take('<i')
        if count < 0:
            return None
        return [read_value(r, kind[:-2]) for _ in range(count)]
    if kind.startswith('@'):
        return read_object(r, SCHEMAS[kind[1:]])
    if kind in ('int', 'enum'):
        return r.take('<i')
    if kind == 'uint':
        return r.take('<I')
    if kind == 'long':
        return r.take('<q')
    if kind == 'float':
        return r.take('<f')
    if kind == 'bool':
        return bool(r.take('<B'))
    if kind == 'string':
        return r.string()
    raise StaticDataError('unknown_schema_type')


def read_object(r, schema):
    members = r.take('<B')
    if members != len(schema):
        raise StaticDataError(f'member_count_drift expected={len(schema)} actual={members}')
    return {name: read_value(r, kind) for name, kind in schema}


def decode_exact(raw, entry, schema_name):
    schema = SCHEMAS[schema_name]
    try:
        r = Reader(raw)
        count = r.take('<i')
        if count <= 0:
            raise StaticDataError('empty_table')
        rows = [read_object(r, schema) for _ in range(count)]
    except (struct.error, UnicodeDecodeError, IndexError) as error:
        raise StaticDataError(f'{entry}: decode_failed') from error
    except StaticDataError as error:
        raise StaticDataError(f'{entry}: {error}') from error
    if r.o != len(raw):
        raise StaticDataError(f'{entry}: trailing_or_short_buffer')
    return rows


def unique_index(rows, key, label):
    index = {}
    for row in rows:
        value = row[key]
        if value in index:
            raise StaticDataError(f'{label}: duplicate {key}={value}')
        index[value] = row
    return index


def read_group_dict(raw):
    reader = csv.reader(io.StringIO(raw.decode('utf-8-sig')))
    header = [c.strip().lower() for c in next(reader, [])]
    if header != ['stage_id', 'group_id']:
        raise StaticDataError('group_dict_header_drift')
    stages = {}
    for row in reader:
        if len(row) != 2 or not row[0].strip().isdigit() or not re.fullmatch(r'[A-Za-z0-9_-]+', row[1].strip()):
            raise StaticDataError('group_dict_row_invalid')
        stage, group = int(row[0].strip()), row[1].strip()
        if stages.setdefault(stage, group) != group:
            raise StaticDataError(f'group_dict_stage_ambiguous {stage}')
    return stages


def is_core_collider(text):
    return isinstance(text, str) and 'core' in text.lower()


def part_markers(part):
    names = list(part['weapon_object'] or []) + list(part['parts_object'] or [])
    if part['parts_skin']:
        names.append(part['parts_skin'])
    return [name for name in names if is_core_collider(name)]


def level_stats(stats, group, level):
    row = stats.get((group, level))
    if row is None:
        return None
    return {'level': level, 'hp': row['level_hp'], 'attack': row['level_attack'], 'defence': row['level_defence']}


def classify_core(parts):
    cores = [(p, part_markers(p)) for p in parts]
    cores = [(p, m) for p, m in cores if m]
    if not cores:
        return {'kind': 'unconfirmed', 'partIds': [], 'evidence': None}
    kind = 'separate_part' if any(not p['is_main_part'] for p, _ in cores) else 'main_body_attached'
    return {'kind': kind, 'partIds': [p['id'] for p, _ in cores], 'evidence': 'collider_name_contains_core'}


def build_attributes(archive, expected_seasons, expected_images=None):
    """archive: callable(entry) -> bytes (None when absent). expected_images: {season: 'full_xxx'}."""
    raws = {}
    for entry in (*TABLES, GROUP_DICT):
        raw = archive(entry)
        if raw is None:
            raise StaticDataError(f'required_entry_missing {entry}')
        raws[entry] = raw
    tables = {entry: decode_exact(raws[entry], entry, schema) for entry, schema in TABLES.items()}
    stages_by_wave = read_group_dict(raws[GROUP_DICT])

    managers, presets = tables['SoloRaidManagerTable.mpk'], tables['SoloRaidPresetTable.mpk']
    monsters = unique_index(tables['MonsterTable.mpk'], 'id', 'MonsterTable')
    models = unique_index(tables['MonsterModelTable.mpk'], 'id', 'MonsterModelTable')
    elements = unique_index(tables['ElementTable.mpk'], 'id', 'ElementTable')
    stats = {}
    for row in tables['MonsterStatEnhanceTable.mpk']:
        key = (row['group_id'], row['lv'])
        if key in stats:
            raise StaticDataError(f'MonsterStatEnhanceTable: duplicate {key}')
        stats[key] = row
    parts_by_model = {}
    for row in tables['MonsterPartsTable.mpk']:
        parts_by_model.setdefault(row['monster_model_id'], []).append(row)
    changes = {}
    for row in tables['MonsterStageLvChangeTable.mpk']:
        changes.setdefault(row['group_id'], []).append(row)
    element_keys = {}
    for eid, row in elements.items():
        if row['icon'] not in ICON_TO_ELEMENT:
            raise StaticDataError(f'ElementTable: unknown icon {row["icon"]}')
        element_keys[eid] = ICON_TO_ELEMENT[row['icon']]

    presets_by_group = {}
    for row in presets:
        presets_by_group.setdefault(row['Preset_group_id'], []).append(row)
    relations = {}
    for row in managers:
        relations.setdefault(row['Ranking_group_id'], set()).add(row['Monster_preset'])
    season_waves = {}
    needed = {}
    for season, groups in relations.items():
        if len(groups) != 1:
            raise StaticDataError(f'season {season}: preset_group count={len(groups)}')
        group = next(iter(groups))
        challenge = [p for p in presets_by_group.get(group, []) if p['Difficulty_type'] == CHALLENGE]
        if len(challenge) != 1:
            raise StaticDataError(f'season {season}: challenge preset count={len(challenge)}')
        wave_group = stages_by_wave.get(challenge[0]['Wave'])
        if wave_group is None:
            raise StaticDataError(f'season {season}: wave {challenge[0]["Wave"]} not in GroupDict')
        season_waves[season] = (group, challenge[0], wave_group)
        needed[wave_group] = None
    wave_tables, wave_entries = {}, {}
    for wave_group in sorted(needed):
        entry = f'WaveDataTable.{wave_group}.mpk'
        raw = archive(entry)
        if raw is None:
            raise StaticDataError(f'required_entry_missing {entry}')
        wave_tables[wave_group] = unique_index(decode_exact(raw, entry, 'WaveData'), 'stage_id', entry)
        wave_entries[entry] = {'sha256': digest(raw), 'size': len(raw), 'records': len(wave_tables[wave_group])}

    bosses, diagnostics = [], []
    for season in range(1, expected_seasons + 1):
        boss_id = f'solo-raid-{season}'
        if season not in season_waves:
            bosses.append({'id': boss_id, 'season': season, 'status': 'unavailable',
                           'reason': 'static_data_season_missing'})
            diagnostics.append({'id': boss_id, 'season': season, 'code': 'static_data_season_missing', 'displayable': False,
                                'message': '사용한 StaticData 사본에 이 시즌이 없어 속성을 준비하지 못함'})
            continue
        group, challenge, wave_group = season_waves[season]
        wave = wave_tables[wave_group].get(challenge['Wave'])
        if wave is None:
            raise StaticDataError(f'season {season}: wave record missing')
        targets = {t for t in wave['target_list'] if t}
        spawned = {s['wave_monster_id'] for path in wave['wave_data'] for s in path['wave_monster_list'] if s['wave_monster_id']}
        candidates = targets & spawned
        if len(candidates) != 1:
            raise StaticDataError(f'season {season}: boss candidates={sorted(candidates)}')
        monster = monsters.get(next(iter(candidates)))
        if monster is None:
            raise StaticDataError(f'season {season}: boss monster row missing')
        images = {p['Monster_image'] for p in presets_by_group[group]}
        if len(images) != 1:
            raise StaticDataError(f'season {season}: preset images differ')
        image = next(iter(images))
        if expected_images is not None and expected_images.get(season) not in (None, image):
            raise StaticDataError(f'season {season}: boss image {image} != reviewed {expected_images[season]}')
        model = models.get(monster['monster_model_id'])
        stat_group = monster['statenhance_id']
        element = None
        if len(monster['element_id']) == 1 and monster['element_id'][0] in elements:
            eid = monster['element_id'][0]
            weak = elements[eid]['weak_element_id']
            element = {'id': eid, 'key': element_keys[eid], 'weakId': weak, 'weakKey': element_keys.get(weak)}
        ladder, unconfirmed = [], []
        for row in sorted((p for p in presets_by_group[group] if p['Difficulty_type'] == LADDER), key=lambda p: p['Monster_stage_lv']):
            stat = level_stats(stats, stat_group, row['Monster_stage_lv'])
            if stat is None:
                unconfirmed.append(f'ladder_level_{row["Monster_stage_lv"]}_stats')
            else:
                ladder.append(stat)
        challenge_stat = level_stats(stats, stat_group, challenge['Monster_stage_lv'])
        if challenge_stat is None:
            unconfirmed.append('challenge_level_stats')
        change_group = challenge['Monster_stage_lv_change_group']
        level_change = None
        if change_group:
            steps = sorted(changes.get(change_group, []), key=lambda r: r['step'])
            if not steps:
                unconfirmed.append('level_change_rows')
            else:
                level_change = {'groupId': change_group, 'steps': []}
                for step in steps:
                    stat = level_stats(stats, stat_group, step['level'])
                    if stat is None:
                        unconfirmed.append(f'level_change_step_{step["step"]}_stats')
                    # range_to 0 on the last step is read as "no upper bound"; this is labelled as likely.
                    level_change['steps'].append({'step': step['step'], 'rangeFrom': step['range_from'],
                        'rangeTo': step['range_to'] or None, 'level': step['level'], 'stats': stat})
        parts = [{'id': p['id'], 'partsType': p['parts_type'], 'isMain': p['is_main_part'],
                  'damageable': p['is_parts_damage_able'], 'hpRatio': p['hp_ratio'],
                  'damageHpRatio': p['damage_hp_ratio'], 'defenceRatio': p['defence_ratio'],
                  'passiveSkillId': p['passive_skill_id'], 'visibleHp': p['visible_hp'],
                  'coreMarkers': part_markers(p)} for p in parts_by_model.get(monster['monster_model_id'], [])]
        if model is None:
            unconfirmed.append('model_prefab')
        if element is None:
            unconfirmed.append('element')
        elif element['weakKey'] is None:
            unconfirmed.append('weak_element')
        if not parts:
            unconfirmed.append('parts')
        core = classify_core(parts_by_model.get(monster['monster_model_id'], []))
        if core['kind'] == 'unconfirmed':
            unconfirmed.append('core_position')
        bosses.append({
            'id': boss_id, 'season': season, 'status': 'available', 'reason': None,
            'imageResource': image, 'monsterId': monster['id'], 'monsterModelId': monster['monster_model_id'],
            'modelPrefab': model['mon_prefab'] if model else None, 'statEnhanceGroup': stat_group,
            'element': element, 'hpRatio': monster['hp_ratio'],
            'defenceRatio': monster['defence_ratio'], 'defenceRatioRate': monster['defence_ratio_ratio'],
            'attackRatio': monster['attack_ratio'],
            'challenge': {'presetId': challenge['Id'], 'level': challenge['Monster_stage_lv'],
                          'characterLevel': challenge['Character_lv'], 'levelChangeGroupId': change_group,
                          'stats': challenge_stat, 'levelChange': level_change},
            'ladder': ladder, 'parts': parts, 'core': core, 'unconfirmed': unconfirmed})
    source = {name: {'sha256': digest(raw), 'size': len(raw), 'records': len(tables[name]) if name in tables else None}
              for name, raw in raws.items()}
    source.update(wave_entries)
    return {'schemaVersion': SCHEMA_VERSION, 'kind': KIND, 'fields': FIELDS, 'bosses': bosses,
            'diagnostics': diagnostics, 'complete': not diagnostics,
            'source': {'entries': source,
                       'schemaFingerprint': digest(json.dumps(SCHEMAS, sort_keys=True).encode())}}


def reviewed_images():
    manifest = json.loads(REVIEWED_NAMES.read_text(encoding='utf-8'))
    return {r['season']: r['expectedSourceId'] for r in manifest['records']}


def prepare(zip_path, output):
    zip_path = Path(zip_path)
    before = digest(zip_path.read_bytes())
    images = reviewed_images()
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        catalog = build_attributes(lambda entry: archive.read(entry) if entry in names else None, max(images), images)
    catalog['source'].update({'archiveSha256': before, 'archiveBytes': zip_path.stat().st_size,
                              'preparedAt': datetime.now(timezone.utc).isoformat()})
    if digest(zip_path.read_bytes()) != before:
        raise StaticDataError('archive_changed_during_read')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    pending = output / (OUTPUT_NAME + '.pending')
    pending.write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding='utf-8')
    pending.replace(output / OUTPUT_NAME)
    return catalog


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--static-data-zip', required=True, type=Path)
    parser.add_argument('--presentation-root', required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.static_data_zip, args.presentation_root)
    available = sum(1 for b in result['bosses'] if b['status'] == 'available')
    print(json.dumps({'bosses': len(result['bosses']), 'available': available,
                      'unavailable': [d['season'] for d in result['diagnostics']],
                      'complete': result['complete'], 'archiveSha256': result['source']['archiveSha256']}))

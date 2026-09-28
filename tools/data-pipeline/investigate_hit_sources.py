"""H-SRC: inspect existing, allowlisted JSON/text sources; write only own artifacts.

No imports from collectors/decoders, network, account data, executables or processes.
Missing sources and unmatched keys are evidence limits, never default game values.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = Path('C:/Users/user/Documents/GitHub/Nikke-Simul')
LEGACY = Path('C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator')
RAW = LEGACY / 'Database/raw/staticdata'
SD = Path('C:/NIKKE/NIKKE/game/nikke_Data/StreamingAssets/sd.bin')
RUNTIME_ID = '30b3b0be42d2c6da1ea982304f38688762656e7ef82308e1024598252e4d7dc8'
TERMS = ('damageRatio', 'statDamageRatio', 'chargeDamageRate', 'breakRate',
         'addDamageRate', 'damageReductionRate', 'defenceRatioRate', 'elementRate',
         'criticalDamageRate', 'coreDamageRate', 'burstDamageRate', 'bonusRangeRate',
         'defence_ratio_ratio')
TYPES = (11, 42, 51, 64, 69, 75, 76, 80, 87, 88, 95, 96, 112, 145,
         149, 160, 162, 165, 166, 169, 178, 194, 207, 212)
FIELDS = ('id', 'function_type', 'function_type_name', 'function_value_type',
          'function_value', 'function_standard', 'function_target', 'buff',
          'description_localkey', 'duration_value', 'full_count',
          'status_trigger_type', 'status_trigger_value', 'status_trigger2_type',
          'status_trigger2_value', 'timing_trigger_type', 'timing_trigger_value')


def sha(content):
    return hashlib.sha256(content).hexdigest()


def compact(row):
    return {k: row[k] for k in FIELDS if k in row}


def main():
    report = {'scope': __doc__, 'files': [], 'tables': {}, 'terms': list(TERMS)}
    observed = {}

    def read(path, parse=True):
        content = path.read_bytes()
        observed[path] = sha(content)
        entry = {'path': path.as_posix(), 'sha256': sha(content), 'bytes': len(content)}
        report['files'].append(entry)
        text = content.decode('utf-8-sig')
        entry['literalCountsCaseInsensitive'] = {t: text.lower().count(t.lower()) for t in TERMS}
        return json.loads(text) if parse else text

    ref = ORIGINAL / '.reference/nikke-calc'
    head = subprocess.check_output(['git', '-C', str(ref), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(ref), 'diff', '--name-only', 'HEAD'], text=True).strip()
    lock = read(ROOT / 'sources.lock.json')
    if head != lock['upstream']['commit'] or dirty:
        raise ValueError('Pinned upstream mismatch or tracked changes')
    report['upstream'] = {'head': head, 'trackedDiff': dirty}
    for rel in ('calculator/damage.py', 'data/parsed_nikke.json', 'data/base_stat_tables/collection.json'):
        read(ref / rel, parse=False)
    for rel in ('src/Nikke.Core/Combat/HitCalculator.cs', 'src/Nikke.Data/CalculationService.cs',
                'src/Nikke.Engine/Skills/SkillReplay.cs', 'docs/p03-source-manifest.json', 'package-lock.json'):
        read(ROOT / rel, parse=False)
    for rel in ('SimulatorEngine/Nikke.Simulator.Engine/Skills/OfficialSkillEnums.cs',
                'DataPipeline/crawler/memorypack_decode.py', 'Docs/VERIFICATION_LOG.md'):
        read(LEGACY / rel, parse=False)

    for rel in ('mpk/FunctionTable.json', 'mpk/CharacterSkillTable.json',
                'mpk/CharacterTable.json', 'mpk/MonsterTable.json', 'mpk/MonsterPartsTable.json',
                'mpk/StateEffectTable.json', 'decoded/ElementTable.json',
                'mpk/MonsterStatEnhanceTable.json', 'decoded/MonsterStatEnhanceTable.json',
                'decoded/CharacterStatTable.json', 'decoded/CharacterStatEnhanceTable.json',
                'season40_probe/mpk/MonsterTable.json', 'season40_probe/mpk/FunctionTable.json'):
        path = RAW / rel
        if not path.exists():
            report['tables'][rel] = {'missing': True}
            continue
        rows = read(path)
        keys = sorted({key for row in rows for key in row})
        entry = {'rows': len(rows), 'keys': keys}
        if 'FunctionTable' in rel:
            entry['functionTypes'] = {str(t): {'count': len(matches),
                'examples': [compact(x) for x in matches[:2]]}
                for t in TYPES if (matches := [x for x in rows if x['function_type'] == t])}
            ids = (127131002, 127131004, 127031004, 119111003, 226011001)
            entry['selected'] = [compact(x) for x in rows if x['id'] in ids]
        elif 'CharacterSkillTable' in rel:
            entry['selected'] = [x for x in rows if x['id'] in (1271310, 1260310)]
        elif 'MonsterStatEnhanceTable' in rel:
            field = 'level_statdamageratio' if 'level_statdamageratio' in keys else 'Level_statdamageratio'
            entry['examples'] = rows[:2]
            entry['statDamageRatioValueCounts'] = Counter(str(x.get(field)) for x in rows).most_common(12)
        elif 'MonsterTable' in rel or 'MonsterPartsTable' in rel:
            entry['defenceRatioRatioPresent'] = sum('defence_ratio_ratio' in x for x in rows)
            entry['nonzeroDefenceRatioRatio'] = [{k: x.get(k) for k in
                ('id', 'name_localkey', 'defence_ratio', 'defence_ratio_ratio')}
                for x in rows if x.get('defence_ratio_ratio')]
            entry['exampleDefenceRatio'] = {k: rows[0].get(k) for k in ('id', 'defence_ratio')}
        elif 'CharacterTable' in rel:
            entry['selected'] = [{k: x.get(k) for k in ('id', 'shot_id', 'critical_damage',
                'critical_ratio', 'bonusrange_min', 'bonusrange_max', 'element_id')}
                for x in rows if x['id'] in (319111, 327011, 327111, 426011)]
        else:
            entry['examples'] = rows[:2]
        report['tables'][rel] = entry

    config = read(RAW / 'sd_bin_json/ConfigBattleTable_kv.json')
    pattern = re.compile('damage|damge|charge|critical|core|burst_damage|bonus|element|defence', re.I)
    report['config'] = {k: v for k, v in config.items() if pattern.search(k)}
    runtime_path = ORIGINAL / 'data/local/runtime' / RUNTIME_ID / 'catalog.json'
    runtime = read(runtime_path)
    if observed[runtime_path] != RUNTIME_ID:
        raise ValueError('Runtime content-address mismatch')
    report['runtime'] = {'id': RUNTIME_ID, 'sourceHashes': runtime['sourceHashes'],
        'counts': {k: len(runtime[k]) for k in ('characters', 'functions', 'characterSkills')},
        'characters': {k: {'name': v['name'], 'weapon': v['weapon'],
            'upstreamCharacter': v['upstreamCharacter'],
            'interceptBuffs': [x for x in v['upstreamSkills'] if x.get('stat') == 'intercept_dmg_pct']}
            for k, v in runtime['characters'].items()}}
    report['gameCatalog'] = {k: v for k, v in read(ORIGINAL / 'data/local/game-catalog.json').items()
                             if k in ('id', 'source', 'fileHashes', 'schemaVersion')}
    roles = read(ORIGINAL / '.reference/legacy-simulator/Database/processed/roledata_clean.json')
    report['roleExamples'] = {k: roles[k]['basicAttack'] for k in ('5004', '5008', '5009', '5044')}
    public_roles = read(LEGACY / 'Database/raw/blabla_roledata.json')['roster']
    report['publicRoleExamples'] = {k: {field: public_roles[k].get(field) for field in
        ('critical_damage', 'critical_ratio', 'bonusrange_min', 'bonusrange_max', 'shot')}
        for k in ('5004', '5008', '5009', '5044')}
    public_commit = 'c02571f68766840054b0f640a21fd9941ba35a95'
    report['publicSchemas'] = []
    for name in ('Monster.cs', 'CharacterShotTable.cs', 'Skills.cs', 'CharacterStat.cs', 'CharacterStatEnhance.cs'):
        path = ROOT / 'artifacts/hit-damage-source/public' / name
        if path.exists():
            content = read(path, parse=False)
            report['publicSchemas'].append({'file': name, 'commit': public_commit,
                'url': f'https://github.com/SharpnelXu/nikke-mpk-json-converter/blob/{public_commit}/NikkeMpkConverter/model/{name}',
                'relevantLines': [{'line': i + 1, 'text': line.strip()} for i, line in enumerate(content.splitlines())
                    if re.search('DefenceRatio|StatDamageRatio|BreakDamage|PartsDamage|AddDamage|NormalDamageRatio', line)]})

    report['installedSd'] = {'exists': SD.exists()}
    if SD.exists():
        before = sha(SD.read_bytes())
        observed[SD] = before
        with zipfile.ZipFile(SD, 'r') as archive:
            content = archive.read('ConfigBattleTable.json')
            data = json.loads(content)
            values = {r['id']: r['value'] for r in data['records']}
            report['installedSd'].update({'sha256': before, 'entries': archive.namelist(),
                'configSha256': sha(content), 'tableVersion': data.get('version'),
                'selected': {k: v for k, v in values.items() if pattern.search(k)},
                'configMatchesExistingKv': values == config})
    # Re-read to detect concurrent drift; this does not assert untouched unexamined files.
    changed = [p.as_posix() for p, digest in observed.items() if sha(p.read_bytes()) != digest]
    report['readStability'] = {'checkedFiles': len(observed), 'changed': changed}
    if changed:
        raise ValueError('Sources changed during read: ' + str(changed))
    target = ROOT / 'artifacts/hit-damage-source/evidence.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'report': str(target), 'tables': len(report['tables']),
        'readStability': report['readStability'], 'runtimeHashVerified': True,
        'upstreamHead': head, 'sdConfigMatches': report['installedSd'].get('configMatchesExistingKv')},
        ensure_ascii=False))


if __name__ == '__main__':
    main()

"""Bounded, read-only inspection of already available game tables; no executable decoding."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
LEGACY = Path(r'C:\Users\user\Documents\GitHub\Nikke-Dmg-Simulator')
SD = Path(r'C:\NIKKE\NIKKE\game\nikke_Data\StreamingAssets\sd.bin')
KEYS = re.compile(r'damage|damge|charge|critical|bonus|round|floor|ceil|trunc', re.I)
ROUND = re.compile(r'round|floor|ceil|trunc', re.I)

def main():
    report = {'scope': 'Existing ConfigBattle and decoded Function/CharacterSkill table keys, plus local sd.bin ZIP metadata. No game process access or executable analysis.', 'files': []}
    raw = LEGACY / 'Database/raw/staticdata'
    for rel in ('sd_bin_json/ConfigBattleTable_kv.json', 'mpk/FunctionTable.json', 'mpk/CharacterSkillTable.json'):
        path = raw / rel
        if not path.exists(): continue
        payload = json.loads(path.read_text(encoding='utf-8-sig'))
        keys = set()
        def collect(node):
            if isinstance(node, dict):
                keys.update(node.keys())
                for value in node.values(): collect(value)
            elif isinstance(node, list):
                for value in node: collect(value)
        collect(payload)
        report['files'].append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                'matchingKeys': sorted(k for k in keys if KEYS.search(k)),
                                'roundingKeys': sorted(k for k in keys if ROUND.search(k))})
    report['clientSdExists'] = SD.exists()
    if SD.exists():
        report['clientSdSha256'] = hashlib.sha256(SD.read_bytes()).hexdigest()
        with zipfile.ZipFile(SD) as z:
            report['clientTables'] = z.namelist()
            for name in z.namelist():
                if Path(name).name == 'ConfigBattleTable.json':
                    data = json.loads(z.read(name)); records = data.get('records', [])
                    selected = [r for r in records if KEYS.search(str(r.get('id', '')))]
                    report['clientConfigBattleVersion'] = data.get('version')
                    report['clientConstants'] = selected
                    report['clientRoundingKeys'] = [r.get('id') for r in records if ROUND.search(str(r.get('id', '')))]
    target = ROOT / 'artifacts/p02/data-probe.json'; target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'tablesExamined':len(report['files']), 'clientSdExists':SD.exists(),
                      'roundingKeyCounts':[len(f['roundingKeys']) for f in report['files']],
                      'clientRoundingKeys':report.get('clientRoundingKeys'),
                      'conclusion':'Constants/coefficients found; no quantization order established by this bounded key inspection.'}))

if __name__ == '__main__': main()

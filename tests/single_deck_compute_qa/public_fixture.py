"""Public-file allowlist and NEW synthetic account from Backend smoke 48c11d8.
No source account/session/presentation files are read. Fixture setup only; QA assertions are separate.
"""
import hashlib,json,shutil,sqlite3
from pathlib import Path

def read(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def create(source,data):
    hashes={}
    def copy(relative):
        src=(source/relative).resolve()
        assert src.is_relative_to(source.resolve())
        hashes[str(relative)]=digest(src)
        dest=data/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
    copy(Path('game-catalog.json'))
    for folder in ('calculation','runtime'):
        copy(Path(folder)/'current.json');manifest=read(data/folder/'current.json');version=manifest['id'];assert len(version)==64 and all(c in '0123456789abcdef' for c in version)
        names=list(manifest['fileHashes']) if folder=='calculation' else ['catalog.json']
        for name in names:assert Path(name).name==name;copy(Path(folder)/version/name)
    game=read(data/'game-catalog.json');runtime=read(data/'runtime'/read(data/'runtime/current.json')['id']/'catalog.json')
    ids=[]
    for name in ('리타','블랑','앨리스','누아르','모더니아'):
        found=[key for key in runtime['characters'] if game['names'].get(key)==name or runtime['characters'][key].get('name')==name]
        assert len(found)==1,(name,found);ids.append(found[0])
    snapshot={'id':'synthetic-compute','accountId':'synthetic-account','gameSnapshotId':game['id'],'synchroLevel':400,'savedAt':'2026-09-15T00:00:00+00:00','observedAt':'2026-09-15T00:00:00+00:00',
        'consoles':{key:0 for key in ('1001','1101','1102','1103','1201','1202','1203','1204','1205')},'characters':[
            {'characterId':id,'name':game['names'][id],'level':400,'nativeLevel':400,'limitBreak':0,'core':0,'bond':0,
             'skills':{'1':10,'2':10,'3':10},'cubeId':'0','cubeLevel':0,'collectionId':'0','collectionGrade':'none','collectionLevel':0,
             'equipment':[{'slot':slot,'tier':0,'level':0,'manufacturer':0,'lines':[{'lineIndex':i,'presence':'absent'} for i in range(1,4)]} for slot in ('head','torso','arm','leg')]} for id in ids]}
    alice_head=snapshot['characters'][2]['equipment'][0];alice_head['tier']=10
    alice_head['lines'][0]={'lineIndex':1,'presence':'present','optionType':'StatAtk','normalizedValue':game['optionSteps']['atk_pct'][0],'unit':'ratio'}
    # This is a NEW database with explicitly synthetic rows; source accounts.db is never opened.
    with sqlite3.connect(data/'accounts.db') as db:
        db.execute('CREATE TABLE snapshots(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL)')
        db.execute('CREATE TABLE accounts(id TEXT PRIMARY KEY,current_id TEXT NOT NULL REFERENCES snapshots(id))')
        db.execute('INSERT INTO snapshots VALUES(?,?,?,?)',(snapshot['id'],snapshot['accountId'],1,json.dumps(snapshot)))
        db.execute('INSERT INTO accounts VALUES(?,?)',(snapshot['accountId'],snapshot['id']))
    return hashes,game,snapshot,ids

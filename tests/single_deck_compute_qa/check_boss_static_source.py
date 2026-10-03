"""Independent B-DATA-1 raw-wire audit. No implementation imports or owner fixtures.

The positional layouts below describe the input format, not expected output values.
Read public archive locally; keep every derived artifact inside ignored QA storage.
"""
import hashlib,io,json,struct,subprocess,sys,zipfile,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/single-deck-qa/bdata1';OUT.mkdir(exist_ok=True)
ARCHIVE=Path('C:/Users/user/Desktop/StaticData.zip')
def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,value):(OUT/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
checks=[]
def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail))
# Each list is an object, each tuple is a collection of the enclosed wire type.
manager=['i']*3
preset=['i']*12+['B']+['s']*4+['i']*2
monster=['q',('i',),'i','i','s','s','s','B']+['i']*11+['s']*3+['i']*9+[(['i',('i',),('i',)],),'i']
stats=['i']*3+['q']+['i']*7+['q']
part=['i','i','s','i','i','i','B','B','i','B','i',('s',),('i',),'i',('s',)]+['i']*4+['s','i','B','B']
model=['i','i','s','i','f']+['i']*8
element=['i']*4+['s']*4
change=['i']*4+['I','i','q','i','i','q']
wave=['i','s','i','i','i','s','i','B','B','s','s','s','i','i','s',('q',),(['s','i',(['q','i'],)],),'i','i','i']
layouts=dict(SoloRaidManagerTable=manager,SoloRaidPresetTable=preset,MonsterTable=monster,MonsterStatEnhanceTable=stats,MonsterPartsTable=part,MonsterModelTable=model,ElementTable=element,MonsterStageLvChangeTable=change)
class Raw:
 def __init__(self,raw):self.f=io.BytesIO(raw)
 def number(self,fmt):return struct.unpack('<'+fmt,self.f.read(struct.calcsize('<'+fmt)))[0]
 def read(self,typ):
  if isinstance(typ,list):
   assert self.number('B')==len(typ)
   return [self.read(t) for t in typ]
  if isinstance(typ,tuple):
   n=self.number('i');assert n>=-1
   return None if n==-1 else [self.read(typ[0]) for _ in range(n)]
  if typ!='s':return self.number(typ)
  n=self.number('i')
  if n==-1:return None
  if n<0:
   chars=self.number('i');v=self.f.read(~n).decode('utf-8');assert len(v.encode('utf-16-le'))//2==chars;return v
  return self.f.read(n*2).decode('utf-16-le')
def decode(raw,layout):
 r=Raw(raw);rows=r.read((layout,));assert r.f.tell()==len(raw);return rows
def prepare(path,dest):
 return subprocess.run([sys.executable,str(ROOT/'tools/data-pipeline/prepare_solo_raid_boss_attributes.py'),'--static-data-zip',str(path),'--presentation-root',str(dest)],capture_output=True,text=True,encoding='utf-8')
def main():
 original=ARCHIVE.read_bytes();before=sha(original);copy=OUT/'source.zip';copy.write_bytes(original)
 p=prepare(copy,OUT/'presentation');assert p.returncode==0,p.stderr
 catalog=json.loads((OUT/'presentation/solo-raid-boss-attributes.json').read_text(encoding='utf-8'))
 with zipfile.ZipFile(io.BytesIO(original)) as z:
  tables={k:decode(z.read(k+'.mpk'),v) for k,v in layouts.items()}
  groups=dict((int(row[0]),row[1].strip()) for row in list(csv.reader(io.StringIO(z.read('WaveData.GroupDict.csv').decode('utf-8-sig'))))[1:])
  managers=tables['SoloRaidManagerTable'];presets=tables['SoloRaidPresetTable'];monsters={r[0]:r for r in tables['MonsterTable']};elements={r[0]:r for r in tables['ElementTable']};models={r[0]:r for r in tables['MonsterModelTable']};statmap={(r[1],r[2]):dict(level=r[2],hp=r[3],attack=r[4],defence=r[5]) for r in tables['MonsterStatEnhanceTable']}
  names=json.loads((ROOT/'tools/data-pipeline/manifests/solo-raid-korean-names.manifest.json').read_text(encoding='utf-8'))
  images={r['season']:r['expectedSourceId'] for r in names['records']};seen=set();partzeros=0
  for boss in catalog['bosses']:
   season=boss['season'];relations={r[1] for r in managers if r[2]==season}
   if not relations:
    check(f'season {season} unavailable from raw absence',boss==dict(id=f'solo-raid-{season}',season=season,status='unavailable',reason='static_data_season_missing'));continue
   assert len(relations)==1;pg=relations.pop();cp=[r for r in presets if r[1]==pg and r[2]==2];assert len(cp)==1;cp=cp[0]
   w=next(r for r in decode(z.read('WaveDataTable.'+groups[cp[7]]+'.mpk'),wave) if r[0]==cp[7]);candidates=set(w[15])&{s[0] for path in w[16] for s in path[2]};assert len(candidates)==1;m=monsters[candidates.pop()];seen.add(m[0])
   check(f'{season} exact identity',boss['monsterId']==m[0] and boss['monsterModelId']==m[2] and boss['modelPrefab']==models[m[2]][2] and boss['imageResource']==cp[16]==images[season])
   check(f'{season} raw ratios including real zero',all(boss[k]==m[i] for k,i in [('hpRatio',8),('defenceRatio',9),('attackRatio',10),('defenceRatioRate',11)]) and boss['statEnhanceGroup']==m[32])
   e=elements[m[1][0]];vocab={'fire':'Fire','water':'Water','wind':'Wind','iron':'Iron','elect':'Electronic'}
   check(f'{season} own element joins',boss['element']==dict(id=e[0],key=vocab[e[7].split('_')[-1]],weakId=e[3],weakKey=vocab[elements[e[3]][7].split('_')[-1]]))
   c=boss['challenge'];check(f'{season} challenge raw stats',c['presetId']==cp[0] and c['level']==cp[8] and c['characterLevel']==cp[4] and c['stats']==statmap[m[32],cp[8]])
   check(f'{season} ladder raw stats',boss['ladder']==[statmap[m[32],p[8]] for p in sorted([r for r in presets if r[1]==pg and r[2]==1],key=lambda r:r[8])])
   rawsteps=sorted([r for r in tables['MonsterStageLvChangeTable'] if r[1]==cp[9]],key=lambda r:r[2]);check(f'{season} level ranges and stats',c['levelChangeGroupId']==cp[9]==c['levelChange']['groupId'] and c['levelChange']['steps']==[dict(step=r[2],rangeFrom=r[4],rangeTo=r[6] if r[6]!=0 else None,level=r[7],stats=statmap[m[32],r[7]]) for r in rawsteps])
   rawparts=[r for r in tables['MonsterPartsTable'] if r[1]==m[2]];expected=[];cores=[]
   for r in rawparts:
    markers=[x for x in (r[11] or [])+(r[14] or [])+([r[19]] if r[19] else []) if 'core' in x.casefold()]
    expected.append(dict(id=r[0],partsType=r[13],isMain=bool(r[21]),damageable=bool(r[22]),hpRatio=r[4],damageHpRatio=r[3],defenceRatio=r[5],passiveSkillId=r[8],visibleHp=bool(r[9]),coreMarkers=markers))
    if markers:cores.append((r[0],bool(r[21])))
    partzeros+=int(r[5]==0)
   check(f'{season} every part raw value',boss['parts']==expected)
   kind=('separate_part' if any(not x[1] for x in cores) else 'main_body_attached') if cores else 'unconfirmed'
   check(f'{season} core uncertainty retained',boss['core']==dict(kind=kind,partIds=[x[0] for x in cores],evidence='collider_name_contains_core' if cores else None) and (bool(cores) or 'core_position' in boss['unconfirmed']))
  check('42 seasons and explicit missing diagnostics',len(catalog['bosses'])==42 and [d['season'] for d in catalog['diagnostics']]==[41,42] and not catalog['complete'] and all(d['displayable'] is False and d['code']=='static_data_season_missing' for d in catalog['diagnostics']))
  for name,e in catalog['source']['entries'].items():
   raw=z.read(name);layout=wave if name.startswith('WaveDataTable.') else layouts.get(name.removesuffix('.mpk'));check('source provenance '+name,e['sha256']==sha(raw) and e['size']==len(raw) and e['records']==(len(decode(raw,layout)) if layout else None))
  check('archive provenance',catalog['source']['archiveSha256']==before and catalog['source']['archiveBytes']==len(original))
  # Modify raw ZIP bytes, never an owner mock. Rejected input must not replace an existing valid output.
  corruptions=[('missing','ElementTable.mpk',None),('trailing','MonsterTable.mpk',z.read('MonsterTable.mpk')+b'X'),('truncated','SoloRaidPresetTable.mpk',z.read('SoloRaidPresetTable.mpk')[:-1]),('member','SoloRaidManagerTable.mpk',z.read('SoloRaidManagerTable.mpk')[:4]+b'\x04'+z.read('SoloRaidManagerTable.mpk')[5:]),('csv','WaveData.GroupDict.csv',b'stage,group\n1,x\n')]
  preserved=(OUT/'presentation/solo-raid-boss-attributes.json').read_bytes()
  for label,name,replacement in corruptions:
   path=OUT/(label+'.zip')
   with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as target:
    for entry in catalog['source']['entries']:
     if entry==name and replacement is None:continue
     target.writestr(entry,replacement if entry==name else z.read(entry))
   result=prepare(path,OUT/'presentation');check('reject raw '+label,result.returncode!=0 and (OUT/'presentation/solo-raid-boss-attributes.json').read_bytes()==preserved,result.stderr[-600:])
 check('source read only',sha(ARCHIVE.read_bytes())==before==sha(copy.read_bytes()))
 save('source-audit',dict(checks=checks,passed=sum(x['passed'] for x in checks),failed=[x for x in checks if not x['passed']],archiveSha256=before,distinctBossMonsters=len(seen),partsWithZeroDefenceRatio=partzeros))
 print(json.dumps(dict(passed=sum(x['passed'] for x in checks),failed=[x for x in checks if not x['passed']]),ensure_ascii=False));return int(not all(x['passed'] for x in checks))
if __name__=='__main__':raise SystemExit(main())

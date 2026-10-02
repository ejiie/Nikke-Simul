"""Independent pinned-source audit for S-SKILL-1. Calls only the production assembler.
No owner/reviewer harness, fixture or expected result is read.
"""
import sys,json,hashlib,copy
from pathlib import Path
from html.parser import HTMLParser
from fractions import Fraction
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'artifacts/single-deck-qa/ssr1';OUT.mkdir(exist_ok=True)
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'tools/data-pipeline'))
import prepare_runtime as product
def sha(b):return hashlib.sha256(b).hexdigest()
def save(n,v):(OUT/(n+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
checks=[]
def check(n,b,detail=None):checks.append(dict(name=n,passed=bool(b),detail=detail))
class Plain(HTMLParser):
 def __init__(self,text):super().__init__();self.words=[];self.feed(text)
 def handle_data(self,d):self.words.append(d)
inputs={};provenance={}
for row in json.loads((ROOT/'docs/p03-source-manifest.json').read_text(encoding='utf-8-sig')):
 if 'inputKey' not in row:continue
 p=ROOT/row['sourceRoot']/row['path']
 if not p.exists():p=Path('C:/Users/user/Documents/GitHub/Nikke-Simul')/row['sourceRoot']/row['path']
 raw=p.read_bytes();assert sha(raw)==row['sha256'];inputs[row['inputKey']]=json.loads(raw);provenance[row['inputKey']]=dict(path=str(p),before=sha(raw))
save('source-hashes',provenance)
catalog=product.assemble(copy.deepcopy(inputs['chains']),inputs['roles'],inputs['names'],inputs['skills'],inputs['characters'],inputs['sourceRoles'])
catalog.update(gaugeConstants=product.gauge_constants(inputs['gaugeTable'],inputs['gaugeConfig']),connectionSchemaVersion=1,sourceHashes={k:v['before'] for k,v in provenance.items()},combatProfiles=product.assemble_profiles(inputs['sourceRoles'],provenance['sourceRoles']['before']))
raw=json.dumps(catalog,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();version=sha(raw);folder=OUT/'runtime'/version;folder.mkdir(parents=True,exist_ok=True);(folder/'catalog.json').write_bytes(raw);(folder.parent/'current.json').write_text(json.dumps(dict(id=version,file='catalog.json',schemaVersion=1)),encoding='utf-8')
check('ten explicit IDs',set(catalog['characters'])==set(map(str,[5011,5008,5009,5004,5044,5012,5001,5129,5105,5101])))
for key,value in catalog['functions'].items():check('raw function '+key,value==inputs['chains']['functions'][key])
for key,value in catalog['characterSkills'].items():check('raw nested skill '+key,value==inputs['chains']['character_skills'][key])
oracle={}
for id in ['5012','5001','5129','5105','5101']:
 c=catalog['characters'][id];original=inputs['chains']['characters'][id];official=copy.deepcopy(c['official']);profiles=[]
 check('raw weapon '+id,c['weapon']==inputs['roles'][id]['weaponData'])
 for slot,values in official['skills'].items():
  for lv,value in values['levels'].items():
   profile=(value.get('skill') or {}).pop('weapon_change',None)
   check('all coefficient duration trigger fields '+id+'/'+slot+'/'+lv,value==original['skills'][slot]['levels'][lv])
   if profile is not None:
    role=inputs['sourceRoles']['roster'][id];sk=role['skills'][slot];text=''.join(Plain(sk['description']).words)
    field=lambda label:text.split(label+':',1)[1].split('\n',1)[0].strip()
    charge=Fraction(field('Charge Time').split()[0]);full=Fraction(field('Full Charge Damage').split('%')[0])/100
    token=field('Max Ammunition Capacity');index=int(token.split('description_value_',1)[1].split('}',1)[0])-1;ammo=sk['description_value_list'][index]['description_value'];effect=field('Additional Effect')
    check('independent replacement description '+id+'/'+lv,profile['charge_time_sec']==float(charge) and profile['full_charge_rate']==float(full) and len(ammo)==10 and all(str(x)==str(ammo[0]) for x in ammo) and profile['max_ammo']==int(ammo[0])==1 and effect=='Pierce' and profile['pierce'] is True)
    profiles.append(dict(level=int(lv),chargeSeconds=str(charge),fullChargeMultiplier=str(full),ammo=int(ammo[0]),effect=effect,body=original['skills'][slot]['levels'][lv]['skill']))
 check('whole official graph unchanged except explicit profile '+id,official==original)
 oracle[id]=dict(profiles=profiles,skills=original['skills'])
 # The strict parser is exercised with edits to the actual pinned description, not an invented owner fixture.
 if id in ['5012','5001']:
  role=copy.deepcopy(inputs['sourceRoles']['roster'][id]);text=role['skills']['burst']['description'];needle='Additional Effect:';assert needle in text
  for label,edit,expected in [('missing',text.replace(needle,'Unrecognised Effect:'),None),('unknown',text.replace('Pierce','Armor QA'),None),('partial',text.replace('Pierce','Pierce Extra'),None),('explicit_none',text.replace('Pierce','None'),False),('unchanged',text,True)]:
   role['skills']['burst']['description']=edit
   try:v=product.weapon_change_profile(role,'burst',{})['pierce'];check('strict parsing '+id+'/'+label,expected is not None and v==expected)
   except ValueError:check('strict parsing '+id+'/'+label,expected is None)
oldroot=ROOT/'artifacts/single-deck-qa/precision1/public-copy/runtime';oldid=json.loads((oldroot/'current.json').read_text())['id'];old=json.loads((oldroot/oldid/'catalog.json').read_text(encoding='utf-8'))
check('new catalog version distinct',version!=oldid)
for key,value in old['characters'].items():check('old character assembled exactly '+key,catalog['characters'][key]==value)
for kind in ['functions','characterSkills']:check('old '+kind+' retained',all(catalog[kind][k]==v for k,v in old[kind].items()))
for k,v in provenance.items():v['after']=sha(Path(v['path']).read_bytes());check('pinned source unchanged '+k,v['before']==v['after'])
save('source-hashes',provenance);save('independent-oracle',oracle);save('source-audit',dict(version=version,checks=checks,passed=sum(c['passed'] for c in checks),failed=[c for c in checks if not c['passed']]))
print(json.dumps(dict(version=version,passed=sum(c['passed'] for c in checks),failed=[c for c in checks if not c['passed']]),ensure_ascii=False));assert all(c['passed'] for c in checks)

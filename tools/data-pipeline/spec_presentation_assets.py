"""Official equipment/collection catalog projected into Local Lab renderer fields."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from presentation_assets import ROOT, normal_resource_uri, json_write, CatalogCache, resolve_data_root

WEAPONS={'AR':'assault_rifle','MG':'machine_gun','RL':'rocket_launcher','SG':'shotgun','SR':'sniper_rifle','SMG':'submachine_gun'}
SLOTS={'Module_A':('head','head'),'Module_B':('torso','torso'),'Module_C':('arms','arm'),'Module_D':('legs','leg')}
OPTIONS=[('StatAtk','atk_pct','공격력 증가'),('IncHurtDef','def_pct','방어력 증가'),('StatAmmoLoad','max_ammo_pct','최대 장탄 수 증가'),('StatCritical','crit_rate','크리티컬 확률 증가'),('StatCriticalDamage','crit_dmg','크리티컬 대미지 증가'),('StatChargeDamage','charge_dmg_pct','차지 대미지 증가'),('StatChargeTime','charge_speed_pct','차지 속도 증가'),('IncElementDmg','element_bonus','우월코드 대미지 증가'),('StatAccuracyCircle','accuracy_pct','명중률 증가')]

def prepare(output=None, data_root=None, refresh=False):
    data_root=resolve_data_root(data_root,output); output=Path(output) if output is not None else data_root/'presentation'
    cache=CatalogCache(output,'spec-presentation.json',refresh)
    def cached(relative,logical,image=False):
        return cache.get(relative,normal_resource_uri(logical),image=image)
    # Validate local metadata before staging any artwork updates.
    game=json.loads((data_root/'game-catalog.json').read_bytes())
    options=[dict(definitionUid=tid,displayName=name,unitLabel='%',sign=-1 if tid in ['StatChargeTime','StatAccuracyCircle'] else 1,
      legalValues=[dict(unscaledValue=round(v*10000),decimalScale=4) for v in game['optionSteps'][key]]) for tid,key,name in OPTIONS]
    rows=json.loads(cached('catalog/equipment-official.json','equip/ItemEquipTable-ko.json'))['records']
    rows=[r for r in rows if r['class'] in ['Attacker','Defender','Supporter'] and r['item_sub_type'] in SLOTS and r['item_rare'] in ['T'+str(i) for i in range(1,11)]]
    resources=sorted({r['resource_id'] for r in rows})
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda rid:cached('assets/equipment/'+rid+'.png','icon/equip/'+rid+'.png',True),resources))
    supports=[]
    for r in rows:
        slot,raw_slot=SLOTS[r['item_sub_type']]
        supports.append(dict(definitionUid=str(r['id']),kindCode='equipment',displayName=r['name_localkey'],slotCode=slot,rawSlot=raw_slot,
          combatClassCode=r['class'].lower(),tier=int(r['item_rare'][1:]),maximumEnhancementLevel=5,enhancementStatIncreaseBasisPointsPerLevel=1000,
          imagePath='/editor/assets/equipment/'+r['resource_id']+'.png',stats=[dict(label={'Hp':'체력','Atk':'공격력','Defence':'방어력','Def':'방어력'}[s['stat_type']],value=str(s['stat_value']),baseValue=s['stat_value']) for s in r['stat'] if s['stat_type'] in ['Hp','Atk','Defence','Def'] and s['stat_value']>0]))
    favorite_map=json.loads(cached('catalog/favorite-map.json','equip/favorite_rare_map.json'))
    def favorite(tid):
        d=json.loads(cached(f'catalog/favorite-{tid}.json',f'equip/ko/favorite_{tid}.json'))
        rid=d['icon_resource_id'];relative=f'assets/collections/{tid}.png'
        cached(relative,f'icon/favoriteitem/{rid}.png',True)
        special=d['favorite_rare']=='SSR'
        return dict(definitionUid=str(tid),kindCode='favorite' if special else 'collection',rarityCode=d['favorite_rare'].lower(),
          displayName=d['name_localkey'] if special else d['favorite_rare']+' '+d['name_localkey'],weaponCode=WEAPONS[d['weapon_type']],favoriteCharacterUid=str(d['name_code']) if special else None,
          imagePath='/editor/'+relative,levels=[dict(level=i+1 if special else i,stats=[dict(label=label,value=str(d[key][i])) for key,label in [('hp','체력'),('atk','공격력'),('def','방어력')]]) for i in range(len(d['atk']))])
    with ThreadPoolExecutor(max_workers=4) as pool:supports.extend(pool.map(favorite,[tid for ids in favorite_map.values() for tid in ids]))
    result=dict(supportDefinitions=supports,overloadOptions=options,assets=sorted(cache.assets,key=lambda x:x['path']),unresolved=cache.issues,source='official Blablalink; Local Lab UI projection; pinned P01 OL value table')
    cache.commit()
    json_write(output/'spec-presentation.json',result)
    return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);parser.add_argument('--data-root',type=Path);parser.add_argument('--refresh',action='store_true')
    args=parser.parse_args()
    r=prepare(args.output,data_root=args.data_root,refresh=args.refresh);print(json.dumps(dict(supports=len(r['supportDefinitions']),options=len(r['overloadOptions']),images=sum('/assets/' in '/'+a['path'] for a in r['assets']))))

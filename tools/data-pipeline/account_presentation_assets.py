"""Local Lab account artwork; game icons, never generated substitutes."""
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from presentation_assets import ROOT, download, normal_resource_uri, json_write, CatalogCache, resolve_data_root

CONSOLES=[('1001','common','공용 콘솔','re-energy'),('1101','attacker','화력형 콘솔','attacker-common-console'),
 ('1102','defender','방어형 콘솔','defender-common-console'),('1103','supporter','지원형 콘솔','supporter-common-console'),
 ('1201','elysion','엘리시온 콘솔','elysion-common-console'),('1202','missilis','미실리스 콘솔','missilis-common-console'),
 ('1203','tetra','테트라 콘솔','tetra-common-console'),('1204','pilgrim','필그림 콘솔','pilgrim-common-console'),
 ('1205','abnormal','어브노멀 콘솔','abnormal-common-console')]

def prepare(output=None, data_root=None, refresh=False):
    data_root=resolve_data_root(data_root,output); output=Path(output) if output is not None else data_root/'presentation'
    cache=CatalogCache(output,'account-presentation.json',refresh)
    def cached(relative,url,fetch=download,image=False):
        return cache.get(relative,url,fetch,image)
    # Same original item artwork and mirror used by Local Lab's console materializer.
    def public(url):
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Nikke-Simul-Assets/1.0'}),timeout=25) as r:return r.read(2*1024*1024)
    def console(row):
        tid,code,name,slug=row;page='https://nikke.gg/items/'+slug+'/'
        html=cached('catalog/console-'+code+'.html',page,public).decode()
        url=re.search(r'<meta property="og:image" content="([^"]+)"',html)[1]
        if not re.fullmatch(r'https://static\.dotgg\.gg/nikke/items/[\w-]+\.webp',url):raise ValueError('Unexpected console image URL')
        relative='assets/consoles/'+code+'.webp';cached(relative,url,public,True)
        return dict(id=tid,coordinateCode=code,displayName=name,imagePath='/editor/'+relative,sourcePage=page)
    manifest=json.loads((data_root/'calculation/current.json').read_text(encoding='utf-8'))
    from presentation_assets import safe_path
    effects=json.loads(safe_path(data_root/'calculation',manifest['id']+'/cube_effect_table.json').read_text(encoding='utf-8-sig'))
    def cube(tid):
        url=normal_resource_uri('equip/ko/cube_'+tid+'.json')
        data=json.loads(cached('catalog/cube-'+tid+'.json',url))
        relative='assets/cubes/'+tid+'.png'
        cached(relative,normal_resource_uri(f'icon/equip/ie_{data["resource_id"]}.png'),image=True)
        levels=[]
        skill=(data.get('harmonycube_skill_group') or [None])[0]
        for index in range(len(data['atk'])):
            text=''
            skill_level=(data.get('level1') or [])[index]
            if skill and skill_level:
                text=skill['description_localkey']
                for n,entry in enumerate(skill.get('description_value_list',[]),1):
                    choices=entry.get('description_value',[])
                    if skill_level<=len(choices):text=text.replace('{description_value_%02d}'%n,choices[skill_level-1])
                text=re.sub(r'<[^>]+>','',text).replace('\n',' ')
            levels.append(dict(level=index+1,primaryEffect=text))
        return dict(definitionUid=tid,displayName=data['name_localkey'],imagePath='/editor/'+relative,displayOrder=data['order'],levels=levels)
    with ThreadPoolExecutor(max_workers=4) as pool:
        consoles=list(pool.map(console,CONSOLES));cubes=list(pool.map(cube,effects.keys()))
    result=dict(consoles=consoles,cubes=cubes,assets=cache.assets,unresolved=cache.issues)
    cache.commit()
    json_write(output/'account-presentation.json',result)
    return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);parser.add_argument('--data-root',type=Path);parser.add_argument('--refresh',action='store_true')
    args=parser.parse_args()
    result=prepare(args.output,data_root=args.data_root,refresh=args.refresh)
    print(json.dumps({'consoles':len(result['consoles']),'cubes':len(result['cubes'])}))

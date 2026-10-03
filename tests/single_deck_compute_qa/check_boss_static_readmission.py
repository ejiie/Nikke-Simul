"""BD1-Q-1/2 reacceptance: extend own live injection cases, no owner test inputs."""
import json
from copy import deepcopy
import check_boss_static_api as api
OUT=api.ROOT/'artifacts/single-deck-qa/bdata1r2'
def extend(s,catalog,file,write,endpoint):
 results=[]
 def request(label,c,expected=409,path=None):
  write(c);r,v=s.call(endpoint);ok=r.status==expected and (expected!=409 or v.get('message')=='boss_attributes_invalid')
  results.append(dict(label=label,status=r.status,expected=expected,path=path));s.check(label,ok,dict(status=r.status,path=path))
  if not ok:s.save('extended-failure-'+str(len(results)),dict(input=c,response=v,label=label,status=r.status,path=path))
  return v
 old=api.read(api.ROOT/'artifacts/single-deck-qa/bdata1/presentation/solo-raid-boss-attributes.json')
 request('old prepared file requires regeneration',old)
 request('regenerated file accepted',catalog,200)
 # Walk representative elements of every list shape, plus every dictionary entry.
 # Lists of strings/integers and empty lists get an actual null element as well.
 def walk(x,path=()):
  if isinstance(x,dict):
   for k,v in x.items():
    if v is not None:yield path+(k,),v
    yield from walk(v,path+(k,))
  elif isinstance(x,list) and x:yield from walk(x[0],path+(0,))
 for path,value in walk(catalog):
  label='/'.join(map(str,path))
  # reason:null is a structural normal value, not an unconfirmed value.
  # source entry records is nullable for CSV; this field is intentionally declared nullable.
  if path[-1]=='records':continue
  for mode in ['null','missing']:
   if mode=='missing' and path[:2]==('source','entries') and len(path)==3:continue # map keys are source-dependent, not required DTO fields
   c=deepcopy(catalog);parent=api.get(c,path[:-1])
   if mode=='missing':del parent[path[-1]]
   else:parent[path[-1]]=None
   request('extended '+mode+' '+label,c,path=path)
  if isinstance(value,list):
   c=deepcopy(catalog);items=api.get(c,path)
   if items:items[0]=None
   else:items.append(None)
   request('null item '+label,c,path=path+(0,))
 # non-first boss core uncertainty and unconfirmed string collection.
 unconfirmed=next(i for i,b in enumerate(catalog['bosses']) if b.get('unconfirmed'))
 c=deepcopy(catalog);c['bosses'][unconfirmed]['unconfirmed'][0]=None;request('null unconfirmed string item',c,path=('bosses',unconfirmed,'unconfirmed',0))
 for name in catalog['source']['entries']:
  c=deepcopy(catalog);c['source']['entries'][name]=None;request('null source dictionary value '+name,c,path=('source','entries',name))
 # Legitimate uncertainty pairs and structural nulls must stay readable.
 declared=[(('modelPrefab',),'model_prefab'),(('element',),'element'),(('element','weakKey'),'weak_element'),(('challenge','stats'),'challenge_level_stats'),(('challenge','levelChange'),'level_change_rows'),(('challenge','levelChange','steps',0,'stats'),'level_change_step_1_stats')]
 for path,code in declared:
  c=deepcopy(catalog);boss=c['bosses'][0];api.get(boss,path[:-1])[path[-1]]=None;boss['unconfirmed'].append(code)
  v=request('declared nullable '+code,c,200,path);s.check('declared value and unaffected parts '+code,api.get(v['bosses'][0],path) is None and v['bosses'][0]['parts']==catalog['bosses'][0]['parts'])
 c=deepcopy(catalog);c['bosses'][0]['core']=dict(kind='unconfirmed',partIds=[],evidence=None);c['bosses'][0]['unconfirmed'].append('core_position');request('declared unknown core',c,200)
 c=deepcopy(catalog);c['bosses'][0]['challenge'].update(levelChangeGroupId=0,levelChange=None);request('explicit no level change group zero',c,200)
 c=deepcopy(catalog);c['bosses'][0]['challenge']['levelChange']['steps'][-1]['rangeTo']=None;request('last upper bound unbounded',c,200)
 # Required-key checks apply even when another field declares uncertainty, for nested DTOs.
 for path,code in declared:
  if len(path)==1:continue # BossAttributes has optional fields for unavailable seasons; test undeclared omission above.
  c=deepcopy(catalog);boss=c['bosses'][0];del api.get(boss,path[:-1])[path[-1]];boss['unconfirmed'].append(code);request('nested required key despite declaration '+code,c,path=path)
 s.save('expanded-null-matrix',results);s.check('zero HTTP 500 paths',all(t['status']!=500 for t in s.traffic))
 write(catalog)
if __name__=='__main__':
 api.OUT=OUT
 raise SystemExit(api.main(product='a050853',baseline=api.ROOT/'artifacts/single-deck-qa/bdata1/baseline-api',extension=extend))

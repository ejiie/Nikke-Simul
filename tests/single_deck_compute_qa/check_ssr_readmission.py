"""SS1-Q-1: own live reproduction, endpoint-by-endpoint and old-wire compatibility.

Uses only earlier independent QA inputs and our own prior product binaries.
No owner/reviewer tests, answer files, or response mocks.
"""
import json, sqlite3, hashlib
from copy import deepcopy
import check_ssr_api as prior
from public_fixture import read

OUT=prior.ROOT/'artifacts/single-deck-qa/ssr1r2'
OLD=OUT/'baseline-api'
NEW=prior.ROOT/'src/Nikke.Api/bin/Release/net10.0'
def notes(value):
 items=value.get('limitations') or []
 motion=[x for x in items if x['id'].startswith('replacement_weapon_provisional_motion:')]
 pierce=[x for x in items if x['id']=='pierce_multi_hit_not_modelled']
 return len(items)==2 and len(motion)==len(pierce)==1 and 'provisional' in motion[0]['text'].lower() and 'not game-confirmed' in motion[0]['text'].lower() and 'one hit' in pierce[0]['text'].lower() and 'not modelled' in pierce[0]['text'].lower()
def numeric(run):return {k:run[k] for k in ['teamDamage','members','fullBursts','defense']}
def payloads(s,id):
 with sqlite3.connect(s.data/'compute/batches.db') as db:
  return db.execute('select payload from batch_runs where batch=? order by idx',(id,)).fetchall()
def extension(s,ctx,plain,team,batch,rows,stats):
 original=read(prior.ROOT/'artifacts/single-deck-qa/f2-ufix6-a80d1ba039d3/new-members-compute.json')['request']
 s.check('original SS1-Q-1 conditions and formation reproduced',team['conditions']==original['conditions'] and team['characterIds']==original['characterIds'])
 s.check('original two runs actually cast both replacement weapons',len(rows['runs'])==2 and all(all(next(m for m in r['members'] if m['characterId']==id)['burstCasts']==1 for id in ['5012','5001']) for r in rows['runs']))
 for name,value in [('batch-status',batch),('results',rows),('statistics',stats)]:
  s.check('SS1-Q-1 '+name+' identifies both limitations',notes(value),value if name=='batch-status' else None)
 for i,r in enumerate(rows['runs']):s.check('stored run '+str(i)+' identifies both limitations',notes(r))
 for offset in [0,1,2]:
  response,page=s.call('compute/experiments/'+batch['id']+'/results?offset='+str(offset)+'&limit=1')
  s.check('paged notes reflect only returned runs '+str(offset),response.status==200 and (notes(page) if offset<2 else not page.get('limitations')))
 no_cast=deepcopy(team);no_cast['conditions']['casts']=[]
 quiet,qrows,qstats=s.batch(no_cast,'replacement-members-without-cast')
 s.check('replacement owners without replacement use have no notes',all('limitations' not in x for x in [quiet,qrows,qstats,*qrows['runs']]) and all(m['burstCasts']==0 for r in qrows['runs'] for m in r['members']))
 # Create honest old records with the saved pre-merge product, in this same private data root.
 s.stop();s.start_binary(ctx.request,OLD)
 old,oldrows,oldstats=s.batch(plain,'pre-fix-five');oldnew,onrows,onstats=s.batch(team,'pre-fix-replacement')
 legacy=deepcopy(plain);legacy['conditions']['damageLog']={'characterId':'5004'}
 replay=s.replay(legacy,'pre-fix-export-replay')
 paths=['compute/experiments/'+b['id']+suffix for b in [old,oldnew] for suffix in ['', '/results','/statistics']]
 paths+=['runtime/skill-replays/'+replay['id']+suffix for suffix in ['', '/export.json','/damage-log/export.json','/damage-log/export.csv']]
 wire={path:s.call(path)[0].body() for path in paths}
 stored={b['id']:payloads(s,b['id']) for b in [old,oldnew]}
 for i,(path,body) in enumerate(wire.items()):(s.run/('old-wire-'+str(i)+'.bin')).write_bytes(body)
 # Same-old-binary restart control distinguishes a regression from preexisting dictionary order.
 s.stop();s.start_binary(ctx.request,OLD)
 control=[]
 for path,body in wire.items():
  if not path.endswith('/statistics'):continue
  response,value=s.call(path);after=response.body()
  s.check('old-old statistics values preserved '+path,response.status==200 and json.loads(body)==value)
  control.append(dict(path=path,exactBytes=body==after,beforeOrder=list(json.loads(body)['members']),afterOrder=list(value['members']),sameValues=json.loads(body)==value))
 s.save('old-restart-control',control)
 s.stop();s.start_binary(ctx.request,NEW)
 comparisons=[]
 for path,body in wire.items():
  response,value=s.call(path);after=response.body();equal=response.status==200 and body==after
  s.check('old GET/export bytes preserved '+path,equal,dict(status=response.status,before=hashlib.sha256(body).hexdigest(),after=hashlib.sha256(after).hexdigest()))
  if path.endswith('/statistics'):s.check('old statistics all values retained '+path,json.loads(body)==value)
  comparisons.append(dict(path=path,equal=equal))
  if not equal:s.save('old-wire-difference-'+str(len(comparisons)),dict(before=body.decode('utf-8-sig'),after=after.decode('utf-8-sig')))
 s.save('old-wire-comparisons',comparisons)
 # A stored .6 summary must remain readable, never silently acquire the new policy assertions.
 for b in [old,oldnew]:
  r,error=s.call('compute/experiments/'+b['id']+'/resume',{},'POST')
  s.check('old summary resume rejected '+b['id'],r.status==409 and error.get('message')=='engine_or_rules_version_changed',error)
  s.check('old stored run payloads untouched '+b['id'],payloads(s,b['id'])==stored[b['id']])
 new,nrows,nstats=s.batch(plain,'post-fix-five')
 s.check('plain five numerical summaries unchanged',[numeric(r) for r in oldrows['runs']]==[numeric(r) for r in nrows['runs']])
 s.check('replacement numerical summaries unchanged',[numeric(r) for r in onrows['runs']]==[numeric(r) for r in rows['runs']])
 s.check('plain five metrics unchanged',oldstats['team']==nstats['team'] and oldstats['members']==nstats['members'])
 s.check('plain five omit new optional fields',all('limitations' not in x for x in [new,nrows,nstats,*nrows['runs']]))
 for previous,current in [(old,new),(oldnew,batch)]:
  s.check('summary and implementation version separated '+previous['id'],all(previous['input'][k]=='cpu-summary.6-precision-1' and current['input'][k]=='cpu-summary.7-run-policies' for k in ['summaryVersion','engineVersion']))
  s.check('rules data and schema unchanged '+previous['id'],all(previous['input'][k]==current['input'][k] for k in ['rulesVersion','dataVersion','inputSchemaVersion','roundingPolicy']))
  s.check('input execution fingerprints split '+previous['id'],previous['input']['fingerprint']!=current['input']['fingerprint'] and previous['execution']['fingerprint']!=current['execution']['fingerprint'])
 # New notes survive process restart and database read, including statistics rebuilt from stored runs.
 for suffix in ['/results','/statistics']:
  r,value=s.call('compute/experiments/'+batch['id']+suffix)
  s.check('new stored notes survive restart '+suffix,r.status==200 and notes(value))
 s.check('zero HTTP500',all(t['status']!=500 for t in s.traffic))

if __name__=='__main__':
 prior.OUT=OUT
 raise SystemExit(prior.main(product='849f81b',summary_changed=True,extension=extension))

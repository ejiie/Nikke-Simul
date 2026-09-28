"""Q-F32 independent rational IEEE754 binary32 model; no engine oracle imports.
Each operation rounds exact Fraction to nearest/even 24-bit significand.
Final damage uses rational half-away, distinct from float storage rounding.
"""
import json, math, random, sys
from fractions import Fraction as Q
from pathlib import Path

def nearest(x):
    a,r=divmod(x.numerator,x.denominator)
    return a+(2*r>x.denominator or (2*r==x.denominator and a%2))

def f32(x):
    x=Q(x)
    if not x:return Q(0)
    sign=-1 if x<0 else 1
    x=abs(x); e=x.numerator.bit_length()-x.denominator.bit_length()
    if x<Q(2)**e:e-=1
    step=Q(2)**max(-149,e-23)
    value=nearest(x/step)*step
    if value>=Q(2)**128:raise OverflowError('binary32 overflow')
    return sign*value

def bits(x):
    if not x:return 0
    sign=0x80000000 if x<0 else 0;x=abs(x)
    if x<Q(2)**-126:return sign+int(x/Q(2)**-149)
    e=x.numerator.bit_length()-x.denominator.bit_length()
    if x<Q(2)**e:e-=1
    return sign+((e+127)<<23)+int(x/Q(2)**(e-23))-(1<<23)

def away(x):return (-1 if x<0 else 1)*((abs(x).numerator*2+abs(x).denominator)//(2*abs(x).denominator))
def add(a,b):return f32(f32(a)+f32(b))
def mul(a,b):return f32(f32(a)*f32(b))
NAMES=['damageRatio','statDamageRatio','chargeDamageRate','criticalDamageRate','coreDamageRate','burstDamageRate','bonusRangeRate','breakRate','addDamageRate','damageReductionRate','defenceRatioRate','elementRate']
DEFAULT=dict(zip(NAMES,[1]*9+[0,0,1]))

def calc(a,d,r):
    r={k:f32(v) for k,v in r.items()}; base=f32(a-d)
    for k in NAMES[:3]:base=mul(base,r[k])
    bonus=Q(1)
    for k in NAMES[3:7]:bonus=add(bonus,add(r[k],-1))
    extra=add(add(r['breakRate'],r['addDamageRate']),-1)
    reduction=add(1,-r['damageReductionRate']); defense=add(1,-r['defenceRatioRate'])
    product=base
    for x in [bonus,extra,reduction,defense,r['elementRate']]:product=mul(product,x)
    damage=max(1,away(product))
    if damage>=2**63:raise OverflowError('long overflow')
    return dict(attack=a,defence=d,difference=a-d,damage=damage,bits=list(map(bits,[base,bonus,extra,reduction,defense,product])))

def attack(c):
    native=int(c.get('statAttack',0)); grouped={}
    for b in c.get('attackBuffs',[])+c.get('runtimeAttackBuffs',[]):
        raw=b.get('rawRate10000')
        if raw is None:raw=round(b['rate']*10000)
        grouped[raw]=grouped.get(raw,0)+b.get('stacks',1)
    return native+sum(away(Q(native*r*n,10000)) for r,n in grouped.items())+sum(b.get('exactAmount',b['amount']) for b in c.get('attackFlatBuffs',[]))

def context(c):
    get=lambda k,d=0:c.get(k,d)
    r=DEFAULT.copy(); r['damageRatio']=get('coefficient',1);r['statDamageRatio']=get('statDamageRatio',1);r['defenceRatioRate']=get('defenceRatioRate')
    if get('fullCharge'):r['chargeDamageRate']=add(mul(get('chargeBase',1),add(1,get('chargeMultiplierBonus'))),get('chargeAdd'))
    for flag,key,default in [('crit','criticalDamageRate',.5),('core','coreDamageRate',1),('fullBurst','burstDamageRate',.5),('properDistance','bonusRangeRate',.3)]:
        name={'crit':'critBonus','core':'coreBonus','fullBurst':'burstBonus','properDistance':'distanceBonus'}[flag]
        r[key]=add(1,get(name,default)) if get(flag) else 1
    r['breakRate']=add(1,get('partsDamage')) if get('parts') else 1
    extra=add(1,get('attackDamage'))
    for flag,key in [(get('pierce'),'pierceDamage'),(get('damageType')=='dot','dotDamage'),(get('damageType')=='sequential','sequentialDamage'),(get('damageType')=='true','trueDamage')]:extra=add(extra,get(key) if flag else 0)
    r['addDamageRate']=extra;r['damageReductionRate']=-add(get('damageTaken'),get('distributionDamage') if get('damageType')=='distribution' else 0)
    if get('elementAdvantage'):r['elementRate']=add(add(1,get('elementBase',.1)),get('elementBonus'))
    return calc(attack(c),0 if get('damageType')=='true' else int(get('defense')),r)

def generate(root):
    # Independently known IEEE754 encodings and ties, not engine golden files.
    assert bits(f32(1))==0x3f800000 and bits(f32(Q(3,2)))==0x3fc00000
    assert f32(2**24+1)==2**24 and f32(2**24+3)==2**24+4
    assert f32(Q(2)**-150)==0 and f32(3*Q(2)**-150)==Q(2)**-148
    assert away(Q(5,2))==3 and away(Q(-5,2))==-3
    rows=[];expected={}
    def case(kind,data,want=None,error=None):
        i=f'{kind}-{len(rows):04d}';rows.append(dict(id=i,kind=kind,**data));expected[i]={'error':error} if error else {'result':want}
    for a in [0,1,3,5,16777215,16777216,16777217,16777219,2**63-1]:
        d=0 if a<2**63-1 else a-23
        for ratio in [.5,1,1.25]:
            r=DEFAULT|{'damageRatio':ratio};case('direct',dict(attack=a,defence=d,rates=r),calc(a,d,r))
    rng=random.Random(92832)
    for _ in range(160):
        a=rng.randrange(1,10**9);d=rng.randrange(0,40000)
        r=DEFAULT|dict(damageRatio=rng.choice([.6904,.0305,1,3.5164]),statDamageRatio=rng.choice([0,.75,1,2]),chargeDamageRate=rng.choice([1,3.5]),criticalDamageRate=1.87,coreDamageRate=2,burstDamageRate=1.5,bonusRangeRate=1.3,breakRate=1.1669,addDamageRate=1.07,damageReductionRate=-.3926,defenceRatioRate=rng.choice([0,.25,1]),elementRate=1.948)
        case('direct',dict(attack=a,defence=d,rates=r),calc(a,d,r))
    for key in NAMES:
        for bad in ['NaN','Infinity','-Infinity']:
            case('direct',dict(attack=100,defence=0,rates=DEFAULT|{key:bad}),error='ArgumentException')
    for a,r in [(2**63-1,DEFAULT),(2**62,DEFAULT|{'damageRatio':1e30})]:case('direct',dict(attack=a,defence=0,rates=r),error='OverflowException' if r==DEFAULT else 'ArgumentException')
    # Largest binary32 below 2^63, below-defense clamp, negative final tie.
    for a,d in [(2**63-2**39,0),(1,4),(16777217,16777216)]:case('direct',dict(attack=a,defence=d,rates=DEFAULT),calc(a,d,DEFAULT))
    for rawlist,flat in [([1450],0),([-1450],0),([140,140],0),([140,130],0),([-50],0),([1450],17),([140,140,140],7)]:
        groups=[[dict(source=str(i),rate=r/10000,rawRate10000=r,stacks=1)] for i,r in enumerate(rawlist)]
        c=dict(statAttack=100,attackBuffs=[b for g in groups for b in g],attackFlatBuffs=[dict(source='flat',amount=flat)])
        case('attack',dict(native=100,groups=groups,flats=c['attackFlatBuffs']),attack(c))
    case('attack',dict(native=100,groups=[[dict(source='stack',rate=.014,stacks=2)]],flats=[]),103)
    case('attack',dict(native=100,groups=[[dict(source='mismatch',rate=.014,rawRate10000=145)]],flats=[]),error='ArgumentException')
    for data in [dict(native=2**63-1,groups={'2':1},flat=0),dict(native=2**63-1,groups={},flat=1),dict(native=2**63-1,groups={'1':1},flat=0),dict(native=2**62,groups={'10000':1},flat=0)]:case('raw',data,error='OverflowException')
    for value in [.01401,math.nextafter(.014,1)]:case('attack',dict(native=100,groups=[[dict(source='bad',rate=value)]],flats=[]),error='ArgumentException')
    case('attack',dict(native=0,groups=[],flats=[dict(source='exact',amount=float(2**63-1),exactAmount=2**63-1)]),2**63-1)
    for typ in ['normal','skill','dot','sequential','distribution','true']:
        for enabled in [False,True]:
            c=dict(statAttack=123457,defense=30925,coefficient=.6904,statDamageRatio=1.3,defenceRatioRate=.25,damageType=typ,crit=enabled,core=enabled,fullBurst=enabled,properDistance=enabled,fullCharge=enabled,chargeApplicable=True,chargeBase=3.5,chargeMultiplierBonus=.13,chargeAdd=.07,pierce=enabled,parts=enabled,attackDamage=.15,pierceDamage=.08,partsDamage=.1669,dotDamage=.03,sequentialDamage=.936,trueDamage=.2117,damageTaken=.3926,distributionDamage=.2246,elementAdvantage=enabled,elementBonus=.848,attackBuffs=[dict(source='raw',rate=.145,rawRate10000=1450)],attackFlatBuffs=[dict(source='flat',amount=17)])
            case('context',dict(context=c),context(c))
    for patch in [dict(statAttack=100.5),dict(defense=.5),dict(attackFlatBuffs=[dict(source='bad',amount=.5)]),dict(attackBuffs=[dict(source='bad',rate=.01401)])]:case('context',dict(context=dict(statAttack=100,**{k:v for k,v in patch.items() if k!='statAttack'})|patch),error='ArgumentException')
    for key in ['statAttack','defense','coefficient','statDamageRatio','defenceRatioRate','chargeBase','chargeMultiplierBonus','chargeAdd','distanceBonus','burstBonus','critBonus','coreBonus','attackDamage','pierceDamage','partsDamage','dotDamage','sequentialDamage','trueDamage','damageTaken','distributionDamage','elementBase','elementBonus']:
        for bad in ['NaN','Infinity','-Infinity']:case('context',dict(context={'statAttack':100,key:bad}),error='ArgumentException')
    (root/'cases.jsonl').write_text('\n'.join(json.dumps(r) for r in rows),encoding='utf-8')
    (root/'expected.json').write_text(json.dumps(expected,indent=2),encoding='utf-8')
    print(len(rows),'independent cases')

def verify(root):
    expected=json.loads((root/'expected.json').read_text());actual=[json.loads(s) for s in (root/'actual.jsonl').read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    failures=[]
    for row in actual:
        want=expected[row['id']]
        if any(row.get(k)!=v for k,v in want.items()):failures.append(dict(actual=row,expected=want))
    assert len(actual)==len(expected)
    result=dict(cases=len(actual),passed=len(actual)-len(failures),failures=failures)
    (root/'arithmetic-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result)[:3000])
    assert not failures

def replay(root):
    load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
    checks=[]; counts={}; differences={}; examples=[]
    def check(name,ok):
        checks.append(dict(name=name,passed=bool(ok)))
    current=root/'current'; previous=root/'previous'
    for policy in ['legacy_term_floor','final_round_even','nested_floor']:
        now=load(current/(policy+'.json')); old=load(previous/(policy+'.json'))
        check(policy+' exact aggregate',now==old)
        for m in now['members']:
            name=m['characterId'];a=load(current/f'{policy}-{name}-hits.json');b=load(previous/f'{policy}-{name}-hits.json')
            check(policy+' exact per-hit '+name,[(x['frame'],x['damage'],x['cumulativeDamage']) for x in a['entries']]==[(x['frame'],x['damage'],x['cumulativeDamage']) for x in b['entries']])
    now=load(current/'default.json');old=load(previous/'legacy_term_floor.json')
    check('default policy',now['policy']=='client_f32')
    check('reported team reproduction',now['totalDamage']==1346863834 and old['totalDamage']==1346859763)
    check('team member sum',sum(m['damage'] for m in now['members'])==now['totalDamage'])
    check('full bursts unchanged nine',now['fullBursts']==old['fullBursts']==9)
    for m,o in zip(now['members'],old['members']):
        name=m['characterId'];a=load(current/f'default-{name}-hits.json');b=load(previous/f'legacy_term_floor-{name}-hits.json')
        check('shots/hits/crit unchanged '+name,all(m[k]==o[k] for k in ['shots','hits','criticalHits']))
        calculated=[context(x['hit']) for x in a['entries']]
        check('independent every hit '+name,all(r['damage']==h['damage'] for r,h in zip(calculated,a['entries'])))
        check('member hit sum '+name,sum(r['damage'] for r in calculated)==m['damage']==a['totalDamage'])
        check('log complete '+name,not a['truncated'] and a['eventCount']==len(calculated))
        counts[name]=len(calculated); diff={}
        for r,h,prior in zip(calculated,a['entries'],b['entries']):
            delta=int(h['damage']-prior['damage']);diff[delta]=diff.get(delta,0)+1
            if delta and len(examples)<3:examples.append(dict(member=name,frame=h['frame'],prior=prior['damage'],current=h['damage'],context=h['hit'],independent=r))
        differences[name]=diff
    for policy in ['legacy_term_floor','final_round_even','nested_floor','default']:
        result=load(current/(policy+'.json'));p=load(current/(policy+'-parallel.json'))
        check('pre-cancel '+policy,p['cancelled'])
        check('timed cancel and reuse '+policy,p['activeCancelled'] and p['resumed']['teamDamage']==result['totalDamage'])
        check('parallel summary '+policy,all(row['teamDamage']==result['totalDamage'] and row['fullBursts']==result['fullBursts'] and [(m['characterId'],m['damage'],m['shots'],m['hits']) for m in row['members']]==[(m['characterId'],m['damage'],m['shots'],m['hits']) for m in result['members']] for row in p['rows']))
    result=dict(checks=checks,passed=sum(x['passed'] for x in checks),failed=[x for x in checks if not x['passed']],hits=counts,differences=differences,examples=examples,team=now['totalDamage'],previousTeam=old['totalDamage'])
    (root/'replay-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['examples','checks']},indent=2))
    assert not result['failed']

if __name__=='__main__':
    root=Path(sys.argv[2]);root.mkdir(parents=True,exist_ok=True)
    {'generate':generate,'verify':verify,'replay':replay}[sys.argv[1]](root)

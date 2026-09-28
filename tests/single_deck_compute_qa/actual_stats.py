"""Independent numerical integration reference for actual API Student/Welch CIs."""
import math
from oracle import stats

def tcritical(df):
    # Integrate t density after x=sqrt(df)*tan(theta), rather than product beta inversion.
    factor=math.exp(math.lgamma((df+1)/2)-math.lgamma(df/2))/math.sqrt(math.pi)
    def f(x): return factor*math.cos(x)**(df-1)
    def area(end):
        n=4096; h=end/n
        return h/3*(f(0)+f(end)+4*sum(f(i*h) for i in range(1,n,2))+2*sum(f(i*h) for i in range(2,n,2)))
    lo,hi=0,math.pi/2-1e-12
    for _ in range(40):
        mid=(lo+hi)/2
        if area(mid)<.475:lo=mid
        else:hi=mid
    return math.sqrt(df)*math.tan((lo+hi)/2)

def close(a,b):
    assert (a is None and b is None) or (a is not None and b is not None and math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-5)),(a,b)

def metric(actual, values, cutoff=None):
    expected=stats(values,0 if cutoff is None else cutoff)
    assert actual['n']==len(values)
    for field in ('mean','sampleSd','median','p5','p95'):close(actual[field],expected[field])
    assert '7' in actual['quantileMethod']
    if len(values)<2:assert actual['meanCi'] is None
    else:
        half=tcritical(len(values)-1)*expected['sampleSd']/math.sqrt(len(values))
        close(actual['meanCi']['lower'],expected['mean']-half);close(actual['meanCi']['upper'],expected['mean']+half)
        assert 'Student' in actual['meanCi']['method']
    if cutoff is not None and values:
        close(actual['cutSuccess'],expected['cutSuccess'])
        for k,v in zip(('lower','upper'),expected['cutCi']):close(actual['cutCi'][k],v)
        assert 'strict' in actual['cutCi']['method'] and '>' in actual['cutCi']['method']

def comparison(actual, before, after):
    a,b=stats(before,0),stats(after,0)
    close(actual['teamMeanDifference'],b['mean']-a['mean'])
    av,bv=a['sampleSd']**2/len(before),b['sampleSd']**2/len(after)
    if av+bv==0:assert actual['differenceCi'] is None;return
    df=(av+bv)**2/(av*av/(len(before)-1)+bv*bv/(len(after)-1))
    half=tcritical(df)*math.sqrt(av+bv)
    close(actual['differenceCi']['lower'],b['mean']-a['mean']-half)
    close(actual['differenceCi']['upper'],b['mean']-a['mean']+half)

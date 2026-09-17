using Nikke.Compute;
using Nikke.Contracts;

namespace Nikke.Compute.Tests;

public sealed class TuningTests
{
    private static string Temp(){var path=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"../../../../../artifacts/tuning-followup/unit",Guid.NewGuid().ToString("N")));Directory.CreateDirectory(path);return path;}
    private static HardwareProfile Hardware=>HardwareProbe.Normalize(new(),8,8L<<30,"unit","Windows","X64",false);
    private static readonly TuningBudget Budget=new(TimeSpan.FromMilliseconds(150),TimeSpan.FromMilliseconds(700));
    private sealed class Prepared(Action<string,int,CancellationToken>? action=null):IPreparedExperiment
    {
        public int Calls;private int candidates;
        public ExperimentInput Input{get;set;}=new("input","snapshot","data","engine","rules",["a","b","c","d","e"],400,10800,"final","summary","fixed:30925");
        public string PersistedInput=>"fixture";
        public RunSummary Run(string id,int index,int attempt,CancellationToken token){Interlocked.Increment(ref Calls);
            action?.Invoke(id,id=="warmup"?0:Interlocked.Increment(ref candidates),token);token.ThrowIfCancellationRequested();
            return new($"{id}:{index}",attempt,index,id,Input.Fingerprint,"cpu","final",0,Input.CharacterIds.Select(x=>new MemberRunSummary(x,0,0,0,0,0,0)).ToArray(),0,0);}
    }
    private static void UntilCancelled(CancellationToken ct){ct.WaitHandle.WaitOne(TimeSpan.FromSeconds(5));ct.ThrowIfCancellationRequested();}
    [Fact] public async Task Slow_warmup_cannot_consume_candidate_reservations_and_cache_reuses_no_runs()
    {
        var root=Temp();var p=new Prepared((phase,_,ct)=>{if(phase=="warmup")UntilCancelled(ct);});var policy=new ExecutionPolicy(root,Budget,()=>0);
        var result=await policy.Select(Hardware,p,new(),default,preparationMilliseconds:123);
        Assert.Equal("measured",result.Tuning!.Status);Assert.Equal(123,result.Tuning.PreparationMilliseconds);
        Assert.Equal("stage_budget_exhausted",result.Tuning.Stages[0].StopReason);Assert.Equal(0,result.Tuning.Stages[0].Completed);
        Assert.All(result.Tuning.Stages.Skip(1),s=>{Assert.Equal(2,s.Requested);Assert.Equal(2,s.Completed);Assert.Equal(0,s.Interrupted);Assert.Equal("completed",s.Status);});
        var calls=p.Calls;var cached=await policy.Select(Hardware,p,new(),default);
        Assert.Equal("cache_reused",cached.Tuning!.Status);Assert.Equal("measured_cache",cached.Reason);Assert.Equal(calls,p.Calls);
    }
    [Fact] public async Task Partial_candidate_never_contributes_rate_or_creates_cache()
    {
        var root=Temp();var p=new Prepared((phase,n,ct)=>{if(phase!="warmup" && n>=3)UntilCancelled(ct);});
        var result=await new ExecutionPolicy(root,Budget,()=>0).Select(Hardware,p,new(),default);
        Assert.Equal("partial",result.Tuning!.Status);Assert.Equal(1,result.Workers);
        Assert.Null(result.Tuning.Stages[^1].RunsPerSecond);Assert.Equal(0,result.Tuning.Stages[^1].Completed);Assert.Empty(Directory.GetFiles(root,"*.json"));
    }
    [Fact] public async Task Partly_completed_batch_is_not_a_measurement()
    {
        var root=Temp();var p=new Prepared((phase,n,ct)=>{if(phase!="warmup" && n>=2)UntilCancelled(ct);});
        var result=await new ExecutionPolicy(root,Budget,()=>0).Select(Hardware,p,new(),default);
        Assert.Equal("not_measured",result.BenchmarkVersion);Assert.Equal("not_measured",result.Tuning!.Status);
        Assert.Equal(1,result.Tuning.Stages[1].Completed);Assert.Null(result.Tuning.Stages[1].RunsPerSecond);Assert.Equal(1,result.Workers);
        Assert.Empty(Directory.GetFiles(root,"*.json"));
    }
    [Theory][InlineData("warmup")][InlineData("tuning")]
    public async Task External_cancellation_propagates_and_is_observed_without_cache(string phase)
    {
        using var cancel=new CancellationTokenSource();var root=Temp();TuningDiagnostics? last=null;
        var p=new Prepared((name,_,ct)=>{if(name==phase){cancel.Cancel();ct.ThrowIfCancellationRequested();}});
        await Assert.ThrowsAnyAsync<OperationCanceledException>(()=>new ExecutionPolicy(root,Budget,()=>0).Select(Hardware,p,new(),cancel.Token,d=>last=d));
        Assert.Equal("cancelled",last!.Status);Assert.Equal("external_cancelled",last.StopReason);Assert.Empty(Directory.GetFiles(root,"*.json"));
    }
    [Theory][InlineData(false)][InlineData(true)]
    public async Task Memory_limit_before_or_during_run_cancels_and_never_caches(bool during)
    {
        long memory=during?0:long.MaxValue;var root=Temp();var p=new Prepared((_,_,ct)=>{Interlocked.Exchange(ref memory,long.MaxValue);UntilCancelled(ct);});
        var result=await new ExecutionPolicy(root,Budget,()=>Interlocked.Read(ref memory)).Select(Hardware,p,new(),default);
        Assert.Equal("not_measured",result.Tuning!.Status);Assert.Equal("memory_limit",result.Tuning.StopReason);Assert.Equal(1,result.Workers);
        Assert.Empty(Directory.GetFiles(root,"*.json"));if(!during)Assert.Equal(0,p.Calls);
    }
    [Fact] public async Task Memory_reserve_limits_the_predeclared_search()
    {
        var result=await new ExecutionPolicy(Temp(),Budget,()=>0).Select(Hardware,new Prepared(),new(MemoryLimitBytes:ExecutionPolicy.WorkerReserve),default);
        Assert.Equal(new[]{1},result.Tuning!.PlannedWorkers);Assert.Equal(1,result.Tuning.ResourceWorkerLimit);Assert.Equal(1,result.Workers);
    }
    [Theory][InlineData("old")][InlineData("partial")][InlineData("missing")][InlineData("rate")][InlineData("backend")][InlineData("json")]
    public async Task Old_partial_missing_or_corrupted_evidence_cannot_be_reused(string kind)
    {
        var root=Temp();var p=new Prepared();var policy=new ExecutionPolicy(root,Budget,()=>0);var valid=await policy.Select(Hardware,p,new(),default);
        var damaged=kind switch {
            "old"=>valid with {BenchmarkVersion="cpu-policy-2"},
            "partial"=>valid with {Tuning=valid.Tuning! with {Status="partial"}},
            "missing"=>valid with {Tuning=null},
            "backend"=>valid with {Backend="gpu"},
            "rate"=>valid with {Tuning=valid.Tuning! with {Stages=valid.Tuning.Stages.Select(s=>s.Name=="candidate"?s with {RunsPerSecond=999999}:s).ToArray()}},
            _=>valid};
        File.WriteAllText(Path.Combine(root,valid.Fingerprint+".json"),kind=="json"?"{":Wire.Serialize(damaged));int before=p.Calls;
        var result=await policy.Select(Hardware,p,new(),default);Assert.True(p.Calls>before);Assert.Equal("invalid",result.Tuning!.CacheSource);Assert.NotEqual("measured_cache",result.Reason);
    }
    [Fact] public async Task Retune_that_fails_cannot_leave_prior_cache_active()
    {
        var root=Temp();var policy=new ExecutionPolicy(root,Budget,()=>0);var p=new Prepared();await policy.Select(Hardware,p,new(),default);
        var fail=new Prepared((_,_,_)=>throw new Exception("fixture"));var result=await policy.Select(Hardware,fail,new(Retune:true),default);
        Assert.Equal("not_measured",result.Tuning!.Status);Assert.Equal("run_failed",result.Tuning.StopReason);Assert.Empty(Directory.GetFiles(root,"*.json"));
    }
    [Fact] public void Every_semantic_fingerprint_dimension_invalidates_cache()
    {
        var p=new Prepared();var original=ExecutionPolicy.Conservative(Hardware,p.Input,new()).Fingerprint;
        foreach(var input in new[]{p.Input with {Fingerprint="new"},p.Input with {EngineVersion="new"},p.Input with {RulesVersion="new"}})
            Assert.NotEqual(original,ExecutionPolicy.Conservative(Hardware,input,new()).Fingerprint);
        Assert.NotEqual(original,ExecutionPolicy.Conservative(Hardware with {Fingerprint="device-driver-runtime-change"},p.Input,new()).Fingerprint);
        Assert.NotEqual(original,ExecutionPolicy.Conservative(Hardware,p.Input,new(MaxWorkers:1)).Fingerprint);
    }
}

using System.Diagnostics;
using Nikke.Contracts;

namespace Nikke.Compute;

public sealed class ExecutionPolicy
{
    public const string Version="cpu-policy-3";
    public const long WorkerReserve=64L*1024*1024;
    private readonly string cacheRoot;
    private readonly TuningBudget budgets;
    private readonly Func<long> memoryUsed;
    public ExecutionPolicy(string cacheRoot):this(cacheRoot,TuningBudget.Default,()=>GC.GetTotalMemory(false)) { }
    internal ExecutionPolicy(string cacheRoot,TuningBudget budgets,Func<long> memoryUsed)
    {
        if(budgets.Warmup<=TimeSpan.Zero || budgets.Candidate<=TimeSpan.Zero || budgets.TotalMilliseconds(2)>50000)
            throw new ArgumentException("invalid_tuning_budget");
        this.cacheRoot=cacheRoot;this.budgets=budgets;this.memoryUsed=memoryUsed;
    }
    public static ExecutionSelection Conservative(HardwareProfile hw,ExperimentInput input,ComputeOptions options)
    {
        if(options.Requested is not ("auto" or "cpu" or "gpu"))throw new ArgumentException("invalid_backend");
        if(options.Requested=="gpu")throw new InvalidOperationException("gpu_unavailable");
        if(options.MaxWorkers is <1 || options.MemoryLimitBytes is <WorkerReserve)throw new ArgumentException("invalid_resource_limit");
        var memory=Math.Min(hw.MemoryLimitBytes/2,options.MemoryLimitBytes??hw.MemoryLimitBytes/4);
        if(memory<WorkerReserve)throw new InvalidOperationException("insufficient_memory");
        int cap=(int)Math.Min(Math.Min(Math.Max(1,hw.AvailableProcessors-1),options.MaxWorkers??8),memory/WorkerReserve);
        string fingerprint=Wire.Hash(Wire.Serialize(new{hardware=hw.Fingerprint,workload=input.Fingerprint,input.EngineVersion,input.RulesVersion,
            options.MaxWorkers,options.MemoryLimitBytes,policy=Version,kernel="none",memory}));
        return new(options.Requested,"cpu","cpu",Math.Max(1,cap),16,memory,"conservative_resource_limit",
            "current_engine_cpu","not_measured",fingerprint,options.Requested=="auto"?"gpu_unavailable":null);
    }
    // Restricted search, never a global-optimum assertion. Equal work: two full battles per candidate.
    private static int[] Plan(int cap)=>cap==1?[1]:[1,2];
    private static TuningStage? Best(IEnumerable<TuningStage> stages)
    {
        TuningStage? best=null;
        foreach(var stage in stages.Where(s=>s.Name=="candidate" && s.Status=="completed"))
            if(best is null || stage.RunsPerSecond>best.RunsPerSecond*1.05)best=stage;
        return best;
    }
    private static int Chunk(TuningStage stage)=>Math.Clamp((int)(100/Math.Max(1,stage.ElapsedMilliseconds/stage.Requested)),1,64);
    private bool ValidCache(ExecutionSelection cached,ExecutionSelection limit,int[] plan)
    {
        var t=cached.Tuning;
        if(cached.Fingerprint!=limit.Fingerprint || cached.Backend!="cpu" || cached.DeviceId!="cpu" || cached.BenchmarkVersion!=Version
            || cached.ValidationVersion!=limit.ValidationVersion || cached.MemoryLimitBytes!=limit.MemoryLimitBytes
            || cached.ChunkSize is <1 or >64 || t is null || t.PolicyVersion!=Version || t.Status!="measured"
            || t.PlannedWorkers is null || !t.PlannedWorkers.SequenceEqual(plan) || t.ResourceWorkerLimit!=limit.Workers
            || !double.IsFinite(t.ElapsedMilliseconds) || t.ElapsedMilliseconds<0 || t.StopReason is not null
            || t.TotalBudgetMilliseconds!=budgets.TotalMilliseconds(plan.Length) || t.Stages is null || t.Stages.Count!=plan.Length+1)return false;
        var stages=t.Stages;
        if(stages.Any(s=>s is null || s.Started<0 || s.Started>s.Requested || s.Completed<0 || s.Interrupted<0
            || s.Completed+s.Interrupted!=s.Started || !double.IsFinite(s.ElapsedMilliseconds) || s.ElapsedMilliseconds<0))return false;
        if(stages[0].Name!="warmup" || stages[0].BudgetMilliseconds!=budgets.Warmup.TotalMilliseconds
            || stages[0].Status is not ("completed" or "interrupted"))return false;
        for(int i=0;i<plan.Length;i++) {
            var s=stages[i+1];
            if(s.Name!="candidate" || s.Workers!=plan[i] || s.Requested!=2 || s.Started!=2 || s.Completed!=2 || s.Interrupted!=0
                || s.Status!="completed" || s.StopReason is not null || s.BudgetMilliseconds!=budgets.Candidate.TotalMilliseconds
                || !double.IsFinite(s.ElapsedMilliseconds) || s.ElapsedMilliseconds<=0 || s.ElapsedMilliseconds>s.BudgetMilliseconds
                || s.RunsPerSecond is not {} rate || !double.IsFinite(rate) || Math.Abs(rate-2000/s.ElapsedMilliseconds)>1e-9)return false;
        }
        var best=Best(stages);
        return best is not null && best.Workers==cached.Workers && cached.ChunkSize==Chunk(best);
    }
    public async Task<ExecutionSelection> Select(HardwareProfile hw,IPreparedExperiment prepared,ComputeOptions options,CancellationToken token,
        Action<TuningDiagnostics>? observe=null,double? preparationMilliseconds=null)
    {
        token.ThrowIfCancellationRequested();var limit=Conservative(hw,prepared.Input,options);var plan=Plan(limit.Workers);
        var stages=new List<TuningStage>();var total=Stopwatch.StartNew();string cacheSource=options.Retune?"retune":"miss";
        double totalBudget=budgets.TotalMilliseconds(plan.Length);
        TuningDiagnostics Diagnostic(string status,string? reason=null)=>new(Version,status,cacheSource,preparationMilliseconds,
            totalBudget,total.Elapsed.TotalMilliseconds,plan,limit.Workers,stages.ToArray(),reason);
        void Publish(string status,string? reason=null)=>observe?.Invoke(Diagnostic(status,reason));
        Directory.CreateDirectory(cacheRoot);string path=Path.Combine(cacheRoot,limit.Fingerprint+".json");
        if(!options.Retune && File.Exists(path)) {
            cacheSource="invalid";
            try {
                var cached=Wire.Read<ExecutionSelection>(File.ReadAllText(path));
                if(ValidCache(cached,limit,plan) && memoryUsed()<=limit.MemoryLimitBytes) {
                    token.ThrowIfCancellationRequested();var diagnostics=cached.Tuning! with {Status="cache_reused",CacheSource="validated_policy_cache",PreparationMilliseconds=preparationMilliseconds};
                    observe?.Invoke(diagnostics);
                    return cached with {Requested=options.Requested,FallbackReason=limit.FallbackReason,Reason="measured_cache",Tuning=diagnostics};
                }
            } catch(Exception ex) when(ex is IOException or System.Text.Json.JsonException or NullReferenceException or ArgumentException) { }
        }
        if(File.Exists(path))File.Delete(path); // Retune/invalid cache cannot survive a failed new measurement.
        // Preparation and cache IO are outside execution reservations. Await frame cancellation;
        // never abandon a timed-out task and overlap it with the next candidate.
        total.Restart();using var overall=CancellationTokenSource.CreateLinkedTokenSource(token);
        overall.CancelAfter(TimeSpan.FromMilliseconds(totalBudget));
        async Task<TuningStage> Measure(string name,int workers,int requested,TimeSpan allowance)
        {
            int started=0,completed=0,interrupted=0;string? reason=null;var watch=Stopwatch.StartNew();
            using var stageToken=CancellationTokenSource.CreateLinkedTokenSource(overall.Token);stageToken.CancelAfter(allowance);
            var slot=stages.Count;stages.Add(new(name,workers,requested,0,0,0,allowance.TotalMilliseconds,0,"running",null,null));Publish(name);
            using var monitorStop=new CancellationTokenSource();bool memoryExceeded=false;
            async Task MonitorMemory() {
                try {while(true) {
                    if(memoryUsed()>limit.MemoryLimitBytes){memoryExceeded=true;stageToken.Cancel();return;}
                    await Task.Delay(20,monitorStop.Token);
                }}catch(OperationCanceledException) when(monitorStop.IsCancellationRequested) { }
            }
            var monitor=MonitorMemory();
            try {
                await Parallel.ForEachAsync(Enumerable.Range(0,requested),new ParallelOptions{MaxDegreeOfParallelism=workers,CancellationToken=stageToken.Token},
                    (index,ct)=> {
                        ct.ThrowIfCancellationRequested();Interlocked.Increment(ref started);
                        try {
                            prepared.Run(name=="warmup"?"warmup":"tuning",index,0,ct);ct.ThrowIfCancellationRequested();
                            if(watch.Elapsed>allowance)throw new OperationCanceledException(ct);
                            Interlocked.Increment(ref completed);
                        }catch {Interlocked.Increment(ref interrupted);throw;}
                        return ValueTask.CompletedTask;
                    });
            }catch(OperationCanceledException) {
                reason=token.IsCancellationRequested?"external_cancelled":memoryExceeded?"memory_limit":overall.IsCancellationRequested?"total_budget_exhausted":"stage_budget_exhausted";
            }catch {reason="run_failed";}
            finally {monitorStop.Cancel();await monitor;}
            if(memoryExceeded)reason="memory_limit";
            if(reason is null && watch.Elapsed>allowance)reason="stage_budget_exhausted";
            var elapsed=watch.Elapsed.TotalMilliseconds;bool complete=reason is null && completed==requested;
            var stage=new TuningStage(name,workers,requested,started,completed,interrupted,allowance.TotalMilliseconds,elapsed,
                complete?"completed":"interrupted",reason,complete?requested*1000/Math.Max(.000001,elapsed):null);
            stages[slot]=stage;Publish(name,reason);return stage;
        }
        try {
            var warm=await Measure("warmup",1,1,budgets.Warmup);token.ThrowIfCancellationRequested();
            if(warm.StopReason is not ("memory_limit" or "run_failed")) {
                foreach(int workers in plan) {
                    token.ThrowIfCancellationRequested();if(overall.IsCancellationRequested)break;
                    var measured=await Measure("candidate",workers,2,budgets.Candidate);
                    if(measured.StopReason is "memory_limit" or "run_failed")break;
                }
            }
            token.ThrowIfCancellationRequested();
        }catch(OperationCanceledException) when(token.IsCancellationRequested) {Publish("cancelled","external_cancelled");throw;}
        var best=Best(stages);bool memoryStop=stages.Any(s=>s.StopReason=="memory_limit");if(memoryStop)best=null;
        bool all=best is not null && stages.Count(s=>s.Name=="candidate" && s.Status=="completed")==plan.Length;
        var status=all?"measured":best is null?"not_measured":"partial";
        string? stop=memoryStop?"memory_limit":all?null:stages.LastOrDefault(s=>s.StopReason is not null)?.StopReason??"candidates_not_completed";
        var result=limit with {Workers=best?.Workers??1,ChunkSize=best is null?1:Chunk(best),
            Reason=all?"bounded_workload_benchmark":best is null?"benchmark_budget_cpu_fallback":"partial_workload_benchmark",
            BenchmarkVersion=best is null?"not_measured":Version,Tuning=Diagnostic(status,stop)};
        // Partial sets never seed a measurement cache, even if one candidate is usable now.
        if(all) {
            token.ThrowIfCancellationRequested();var temp=path+"."+Guid.NewGuid().ToString("N")+".tmp";
            try {File.WriteAllText(temp,Wire.Serialize(result));token.ThrowIfCancellationRequested();File.Move(temp,path,true);}
            finally {if(File.Exists(temp))File.Delete(temp);}
        }
        observe?.Invoke(result.Tuning!);return result;
    }
}

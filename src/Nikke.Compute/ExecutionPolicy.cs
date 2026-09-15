using System.Diagnostics;
using Nikke.Contracts;

namespace Nikke.Compute;

public sealed class ExecutionPolicy(string cacheRoot)
{
    public const string Version = "cpu-policy-2";
    public const long WorkerReserve = 64L*1024*1024;
    public static ExecutionSelection Conservative(HardwareProfile hw, ExperimentInput input, ComputeOptions options)
    {
        if (options.Requested is not ("auto" or "cpu" or "gpu")) throw new ArgumentException("invalid_backend");
        if (options.Requested == "gpu") throw new InvalidOperationException("gpu_unavailable");
        if (options.MaxWorkers is < 1 || options.MemoryLimitBytes is < WorkerReserve) throw new ArgumentException("invalid_resource_limit");
        var memory = Math.Min(hw.MemoryLimitBytes / 2, options.MemoryLimitBytes ?? hw.MemoryLimitBytes / 4);
        if (memory < WorkerReserve) throw new InvalidOperationException("insufficient_memory");
        int cap = (int)Math.Min(Math.Min(Math.Max(1, hw.AvailableProcessors-1), options.MaxWorkers ?? 8), memory/WorkerReserve);
        string fingerprint=Wire.Hash(Wire.Serialize(new {hardware=hw.Fingerprint,workload=input.Fingerprint,input.EngineVersion,input.RulesVersion,
            options.MaxWorkers,options.MemoryLimitBytes,policy=Version,kernel="none",memory}));
        return new(options.Requested,"cpu","cpu",Math.Max(1,cap),16,memory,"conservative_resource_limit",
            "current_engine_cpu", "not_measured", fingerprint,options.Requested=="auto"?"gpu_unavailable":null);
    }

    public async Task<ExecutionSelection> Select(HardwareProfile hw, IPreparedExperiment prepared, ComputeOptions options, CancellationToken token)
    {
        var selection = Conservative(hw,prepared.Input,options);
        Directory.CreateDirectory(cacheRoot);
        var path=Path.Combine(cacheRoot,selection.Fingerprint+".json");
        if (!options.Retune && File.Exists(path))
            try { var cached=Wire.Read<ExecutionSelection>(File.ReadAllText(path));
                if (cached.Fingerprint==selection.Fingerprint && cached.Workers>=1 && cached.Workers<=selection.Workers &&
                    cached.MemoryLimitBytes==selection.MemoryLimitBytes && cached.BenchmarkVersion==Version &&
                    cached.Backend=="cpu" && cached.DeviceId=="cpu" && cached.ChunkSize is >=1 and <=64 &&
                    cached.ValidationVersion==selection.ValidationVersion)
                    return cached with {Requested=options.Requested,FallbackReason=selection.FallbackReason,Reason="measured_cache"}; }
            catch (Exception ex) when (ex is IOException or System.Text.Json.JsonException) { }
        int best=1; double bestRate=0, bestMs=1000; bool measured=false;
        using var budget=CancellationTokenSource.CreateLinkedTokenSource(token);
        // Includes cold JIT warmup; the initial 3-second budget could finish no measured sample.
        budget.CancelAfter(TimeSpan.FromSeconds(10));
        try {
            await Task.Run(()=>prepared.Run("warmup",0,0,budget.Token),budget.Token);
            for (int workers=1; workers<=selection.Workers; workers*=2)
            {
                if (GC.GetTotalMemory(false)>selection.MemoryLimitBytes) break;
                var watch=Stopwatch.StartNew();
                await Parallel.ForEachAsync(Enumerable.Range(0,workers*2),new ParallelOptions {
                    MaxDegreeOfParallelism=workers,CancellationToken=budget.Token },(index,ct)=> {
                        prepared.Run("tuning",index,0,ct); return ValueTask.CompletedTask; });
                double rate=workers*2 / Math.Max(.000001,watch.Elapsed.TotalSeconds);
                if (rate>bestRate*1.05) { bestRate=rate;best=workers;bestMs=watch.Elapsed.TotalMilliseconds/(workers*2); }
                measured=true;
            }
        } catch (OperationCanceledException) when (!token.IsCancellationRequested) { }
        token.ThrowIfCancellationRequested();
        selection=selection with { Workers=best,ChunkSize=Math.Clamp((int)(100/Math.Max(1,bestMs)),1,64),
            Reason=measured?"short_workload_benchmark":"benchmark_budget_cpu_fallback",BenchmarkVersion=measured?Version:"not_measured" };
        if (measured) { var temp=path+"."+Guid.NewGuid().ToString("N")+".tmp";
            File.WriteAllText(temp,Wire.Serialize(selection)); File.Move(temp,path,true); }
        return selection;
    }
}

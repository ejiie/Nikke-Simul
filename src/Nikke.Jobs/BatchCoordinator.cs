using System.Collections.Concurrent;
using System.Threading.Channels;
using Nikke.Contracts;
using Nikke.Compute;
using Nikke.Storage;

namespace Nikke.Jobs;

public sealed class BatchCoordinator(BatchStore store, HardwareProbe hardware, ExecutionPolicy policy) : IAsyncDisposable
{
    private readonly SemaphoreSlim executionSlot=new(1); // one workload benchmark/batch at a time in this API
    private readonly ConcurrentDictionary<string,(CancellationTokenSource Token,Task Task)> active=new();
    private readonly object gate=new();
    private bool stopped;
    public async Task<BatchStatus> Create(IPreparedExperiment prepared,ExperimentRequest request,CancellationToken token=default)
    {
        if(request.Runs is <1 or >50000 || request.Phase is not ("warmup" or "pilot" or "exploration" or "final") || request.RecordLevel!="summary")throw new ArgumentException("invalid_experiment_budget");
        var hw=await hardware.Detect(token);var selection=ExecutionPolicy.Conservative(hw,prepared.Input,request.Execution??new());
        lock(gate){if(stopped)throw new InvalidOperationException("compute_stopped");var batch=store.Create(prepared,request,selection);Schedule(batch,prepared);return batch;}
    }
    public BatchStatus Cancel(string id)
    {lock(gate){store.Cancel(id);if(active.TryGetValue(id,out var job))job.Token.Cancel();return store.Read(id).Status;}}
    public BatchStatus Resume(string id,IPreparedExperiment prepared)
    {lock(gate){if(stopped)throw new InvalidOperationException("compute_stopped");if(active.ContainsKey(id))throw new InvalidOperationException("attempt_still_active");
        if(store.Read(id).Status.Input.Fingerprint!=prepared.Input.Fingerprint)throw new InvalidOperationException("prepared_input_changed");
        var batch=store.Resume(id);Schedule(batch,prepared);return batch;}}
    private void Schedule(BatchStatus batch,IPreparedExperiment prepared)
    {
        var token=new CancellationTokenSource();
        // Start under gate so a very short batch cannot finish before it is registered.
        var task=Task.Run(async()=>{lock(gate){} await Execute(batch,prepared,token);});
        active[batch.Id]=(token,task);
    }
    private async Task Execute(BatchStatus batch,IPreparedExperiment prepared,CancellationTokenSource cancellation)
    {
        bool acquired=false;string? error=null;
        try {
            await executionSlot.WaitAsync(cancellation.Token);acquired=true;
            var request=store.Read(batch.Id).Request;
            var selection=await policy.Select(await hardware.Detect(cancellation.Token),prepared,request.Execution??new(),cancellation.Token);
            cancellation.Token.ThrowIfCancellationRequested();store.Running(batch.Id,batch.Attempt,selection);
            var valid=store.ValidIndices(batch.Id);
            var channel=Channel.CreateBounded<RunWrite>(new BoundedChannelOptions(Math.Max(2,selection.Workers*2)) {SingleReader=true,FullMode=BoundedChannelFullMode.Wait});
            var writer=Write();
            async Task Write()
            {
                try {await foreach(var first in channel.Reader.ReadAllAsync()) {
                    var chunk=new List<RunWrite>{first};while(chunk.Count<selection.ChunkSize && channel.Reader.TryRead(out var next))chunk.Add(next);
                    store.Write(batch.Id,batch.Attempt,chunk);}}
                catch {cancellation.Cancel();throw;}
            }
            try {
                await Parallel.ForEachAsync(Enumerable.Range(0,batch.Requested).Where(i=>!valid.Contains(i)),new ParallelOptions {
                    MaxDegreeOfParallelism=selection.Workers,CancellationToken=cancellation.Token },async(index,ct)=> {
                    ct.ThrowIfCancellationRequested();
                    // Managed memory pressure stops this attempt; never manufacture a zero sample.
                    if(GC.GetTotalMemory(false)>selection.MemoryLimitBytes)throw new InvalidOperationException("memory_budget_exceeded");
                    RunWrite row;
                    try {row=new(index,batch.Attempt,prepared.Run(batch.Id,index,batch.Attempt,ct),null);}
                    catch(OperationCanceledException){throw;}
                    catch {row=new(index,batch.Attempt,null,"run_failed");}
                    await channel.Writer.WriteAsync(row,ct);
                });
            } finally {channel.Writer.TryComplete();await writer;}
        } catch(OperationCanceledException){error="cancelled";}
        catch {error="batch_execution_failed";}
        finally {
            store.Finish(batch.Id,batch.Attempt,error=="cancelled" && cancellation.IsCancellationRequested,error);
            if(acquired)executionSlot.Release();
            lock(gate){active.TryRemove(batch.Id,out _);cancellation.Dispose();}
        }
    }
    public async ValueTask DisposeAsync()
    {
        Task[] tasks;lock(gate){stopped=true;tasks=active.Values.Select(j=>j.Task).ToArray();foreach(var (id,job) in active){store.Cancel(id);job.Token.Cancel();}}
        await Task.WhenAll(tasks);executionSlot.Dispose();
    }
}

using System.Text.Json.Nodes;
using Nikke.Compute;
using Nikke.Contracts;
using Nikke.Data;
using Nikke.Storage;
using Nikke.Jobs;

namespace Nikke.Compute.Tests;

public sealed class BatchTests
{
    private static string Temp(){var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"../../../../../artifacts/single-deck-backend",Guid.NewGuid().ToString("N")));Directory.CreateDirectory(root);return root;}
    private sealed class Inventory(JsonObject? value=null,Exception? error=null):IHardwareInventory
    {public Task<JsonObject> Read(CancellationToken token)=>error is null?Task.FromResult(value??new JsonObject()):Task.FromException<JsonObject>(error);}
    private sealed class Prepared(int delay=0,bool fail=false):IPreparedExperiment
    {
        public ExperimentInput Input {get;}=new("fixture","snapshot","data","engine","rules",["a","b","c","d","e"],400,10800,"final","summary","fixed:30925");
        public string PersistedInput=>"fixture";
        public RunSummary Run(string id,int index,int attempt,CancellationToken ct)
        {ct.ThrowIfCancellationRequested();if(delay>0 && ct.WaitHandle.WaitOne(delay))ct.ThrowIfCancellationRequested();if(fail)throw new InvalidOperationException();
            return new($"{id}:{index}",attempt,index,id,Input.Fingerprint,"cpu","final",index,Input.CharacterIds.Select((id,i)=>new MemberRunSummary(id,i==0?index:0,1,1,0,0,0)).ToArray(),0,1);}
    }
    private static HardwareProfile Hardware(string machine="machine",int processors=8,long memory=8L<<30,JsonObject? data=null)=>HardwareProbe.Normalize(data??new(),processors,memory,machine,"Windows","X64",false);
    private static ExperimentRequest Request(int runs=4)=>new("snapshot",["a","b","c","d","e"],new(),runs,Execution:new("cpu",2));
    private static (BatchStore Store,Prepared Prepared,BatchStatus Batch) NewStore()
    {var store=new BatchStore(Temp());var prepared=new Prepared();var batch=store.Create(prepared,Request(),ExecutionPolicy.Conservative(Hardware(),prepared.Input,new("cpu",2)));return(store,prepared,batch);}
    [Fact] public void Duplicate_runs_and_stale_attempts_never_double_count()
    {
        var (store,p,b)=NewStore();store.Running(b.Id,1,b.Execution);var row=new RunWrite(0,1,p.Run(b.Id,0,1,default),null);
        store.Write(b.Id,1,[row,row]);Assert.Equal(1,store.Read(b.Id).Status.Valid);
        store.Cancel(b.Id);store.Finish(b.Id,1,true);var resumed=store.Resume(b.Id);store.Running(b.Id,2,resumed.Execution);
        store.Write(b.Id,1,[new(1,1,p.Run(b.Id,1,1,default),null)]);Assert.Equal(1,store.Read(b.Id).Status.Valid);
        store.Write(b.Id,2,[new(1,2,p.Run(b.Id,1,2,default),null)]);Assert.Equal(2,store.Read(b.Id).Status.Valid);
    }
    [Fact] public void Invalid_identity_rolls_back_whole_writer_chunk()
    {
        var (store,p,b)=NewStore();store.Running(b.Id,1,b.Execution);
        Assert.Throws<ArgumentException>(()=>store.Write(b.Id,1,[new(0,1,p.Run(b.Id,0,1,default),null),new(1,1,p.Run("wrong",1,1,default),null)]));
        Assert.Equal(0,store.Read(b.Id).Status.Valid);
    }
    [Fact] public void Crash_recovery_preserves_valid_zero_and_retries_only_unfinished()
    {
        var root=Temp();var store=new BatchStore(root);var p=new Prepared();var b=store.Create(p,Request(),ExecutionPolicy.Conservative(Hardware(),p.Input,new("cpu")));
        store.Running(b.Id,1,b.Execution);store.Write(b.Id,1,[new(0,1,p.Run(b.Id,0,1,default),null),new(1,1,null,"failure")]);
        var recovered=new BatchStore(root);var state=recovered.Read(b.Id).Status;Assert.Equal("cancelled",state.State);Assert.Equal(1,state.Valid);Assert.Equal(1,state.Failed);Assert.Equal(2,state.Cancelled);
        Assert.Equal(0,recovered.Results(b.Id)[0].TeamDamage);var next=recovered.Resume(b.Id);Assert.Equal(2,next.Attempt);Assert.Equal(0,next.Failed);Assert.Single(recovered.ValidIndices(b.Id));
    }
    private static async Task<BatchStatus> Wait(BatchStore store,string id)
    {for(int i=0;i<1000;i++){var b=store.Read(id).Status;if(b.State is "completed" or "cancelled" or "failed")return b;await Task.Delay(10);}throw new TimeoutException();}
    [Fact] public async Task Coordinator_cancel_resume_and_paged_results()
    {
        var root=Temp();var store=new BatchStore(root);await using var jobs=new BatchCoordinator(store,new(new Inventory()),new(root));
        var p=new Prepared(3);var b=await jobs.Create(p,Request(30));jobs.Cancel(b.Id);Assert.Equal("cancelled",(await Wait(store,b.Id)).State);
        await Task.Delay(20);jobs.Resume(b.Id,p);var final=await Wait(store,b.Id);Assert.Equal("completed",final.State);Assert.Equal(30,final.Valid);Assert.False(final.Partial);
        Assert.Equal(Enumerable.Range(5,7),store.Results(b.Id,5,7).Select(r=>r.Index));Assert.Equal(30,store.AllResults(b.Id).Select(r=>r.RunId).Distinct().Count());
    }
    [Fact] public async Task Failed_runs_are_never_zero_samples()
    {
        var root=Temp();var store=new BatchStore(root);await using var jobs=new BatchCoordinator(store,new(new Inventory()),new(root));
        var b=await jobs.Create(new Prepared(fail:true),Request());var end=await Wait(store,b.Id);Assert.Equal("failed",end.State);Assert.Equal(0,end.Valid);Assert.Empty(store.Results(b.Id));
    }
    [Fact] public async Task Shutdown_leaves_resumable_batch()
    {
        var root=Temp();var store=new BatchStore(root);var jobs=new BatchCoordinator(store,new(new Inventory()),new(root));var b=await jobs.Create(new Prepared(10),Request(100));
        await jobs.DisposeAsync();Assert.Equal("cancelled",store.Read(b.Id).Status.State);
    }
    [Theory][InlineData("VEN_10DE","NVIDIA")][InlineData("VEN_1002","AMD")][InlineData("VEN_8086","Intel")]
    public void Inventory_is_never_promoted_to_gpu_execution(string vendorId,string vendor)
    {
        var data=JsonNode.Parse($$"""{"gpu":[{"PNPDeviceID":"PCI_{{vendorId}}","Name":"Fixture","DriverVersion":"1","ConfigManagerErrorCode":0}]}""")!.AsObject();
        var gpu=Assert.Single(Hardware(data:data).Gpus);Assert.Equal(vendor,gpu.Vendor);Assert.False(gpu.Eligible);Assert.Null(gpu.MemoryBytes);Assert.Null(gpu.SupportsFp64);Assert.Equal("not_implemented",gpu.RuntimeStatus);
    }
    [Fact] public void Disconnected_missing_driver_multigpu_and_invalid_memory()
    {
        var data=JsonNode.Parse("""{"gpu":[{"PNPDeviceID":"A","Name":"Detached","ConfigManagerErrorCode":45},{"PNPDeviceID":"B","Name":"No driver"}]}""")!.AsObject();
        var h=Hardware(memory:-1,data:data);Assert.Equal(2,h.Gpus.Count);Assert.Equal("device_unavailable",h.Gpus[0].Reason);Assert.Equal("driver_missing",h.Gpus[1].Reason);Assert.Contains("memory_unknown_conservative_limit",h.ProbeFailures);
    }
    [Fact] public async Task Probe_exception_isolated_and_cpu_fallback()
    {
        var hw=await new HardwareProbe(new Inventory(error:new UnauthorizedAccessException())).Detect();Assert.Contains("inventory_access_denied",hw.ProbeFailures);
        var selection=ExecutionPolicy.Conservative(hw,new Prepared().Input,new());Assert.Equal("cpu",selection.Backend);Assert.Equal("gpu_unavailable",selection.FallbackReason);
        Assert.Throws<InvalidOperationException>(()=>ExecutionPolicy.Conservative(hw,new Prepared().Input,new("gpu")));
    }
    private sealed class TimeoutInventory:IHardwareInventory {public Task<JsonObject> Read(CancellationToken token)=>new TaskCompletionSource<JsonObject>().Task;}
    [Fact] public async Task Probe_timeout_has_bounded_cpu_fallback()
    {var hw=await new HardwareProbe(new TimeoutInventory(),TimeSpan.FromMilliseconds(30)).Detect();Assert.Contains("inventory_timeout",hw.ProbeFailures);}
    [Fact] public async Task Tuning_cache_is_machine_workload_and_resource_specific()
    {
        var root=Temp();var policy=new ExecutionPolicy(root);var p=new Prepared();var first=await policy.Select(Hardware(),p,new(),default);
        var cached=await policy.Select(Hardware(),p,new(),default);Assert.Equal("measured_cache",cached.Reason);
        Assert.NotEqual(first.Fingerprint,ExecutionPolicy.Conservative(Hardware("other"),p.Input,new()).Fingerprint);
        Assert.NotEqual(first.Fingerprint,ExecutionPolicy.Conservative(Hardware(),p.Input with {EngineVersion="new"},new()).Fingerprint);
        var limited=await policy.Select(Hardware(),p,new(MaxWorkers:1),default);Assert.Equal(1,limited.Workers);Assert.NotEqual(first.Fingerprint,limited.Fingerprint);
    }
    [Fact] public void Virtual_ol_preserves_original_and_physical_slot_line()
    {
        var snapshot=new AccountSnapshot{Characters=[new(){CharacterId="a",Equipment=[new(){Slot="head",Tier=10,Lines=[new(){LineIndex=2,Presence="present",OptionType="StatAtk",NormalizedValue=.1m}]}]}]};
        var game=new GameSnapshot{OptionSteps=new(){["atk_pct"]=[.1m,.2m]}};var before=Wire.Serialize(snapshot);
        var copy=VirtualOverload.Apply(snapshot,game,[new("a","head",2,"StatAtk",.2m)]);Assert.Equal(before,Wire.Serialize(snapshot));Assert.Equal(.2m,copy.Characters[0].Equipment[0].Lines[0].NormalizedValue);
        Assert.Throws<ArgumentException>(()=>VirtualOverload.Apply(snapshot,game,[new("a","head",1,"StatAtk",.2m)]));
        Assert.Throws<ArgumentException>(()=>VirtualOverload.Apply(snapshot,game,[new("a","head",2,"StatAtk",.3m)]));
    }
}

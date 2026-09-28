using System.Diagnostics;
using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Compute;
using Nikke.Data;
using Nikke.Storage;
using Nikke.Analysis;

var root=Path.GetFullPath(args[0]);Directory.CreateDirectory(root);
var checks=new List<object>();
int failures=0;
void Require(bool condition,string message){if(!condition)throw new Exception(message);}
void Check(string name,Action action){try{action();checks.Add(new{name,passed=true});Console.WriteLine(name+": PASS");}catch(Exception ex){failures++;checks.Add(new{name,passed=false,error=ex.Message});Console.WriteLine(name+": FAIL "+ex.Message);}}
void Reject(Action action){try{action();}catch(ArgumentException){return;}throw new Exception("invalid record was accepted");}
var p=new Synthetic();var hw=HardwareProbe.Normalize(new(),4,8L<<30,"synthetic-machine","Windows","X64",false);
var store=new BatchStore(Path.Combine(root,"store"));
var request=new ExperimentRequest("synthetic",p.Input.CharacterIds,new JsonObject(),3,Execution:new("cpu",1));
var selection=ExecutionPolicy.Conservative(hw,p.Input,request.Execution!);
var b=store.Create(p,request,selection);store.Running(b.Id,1,selection);
RunSummary R(int index,int attempt=1)=>p.Run(b.Id,index,attempt,default);
Check("normal_zero_and_skill_crits_gt_normal_hits",()=>{
    store.Write(b.Id,1,[new(0,1,R(0),null)]);
    var s=store.AnalysisSnapshot(b.Id);var a=new ComputeAnalysis().Summarize(s.Batch,s.Runs,0);
    Require(s.Batch.Valid==1 && s.Runs[0].TeamDamage==0 && s.Runs[0].Members[0].CriticalHits>s.Runs[0].Members[0].Hits,"zero/crits lost");
    Require(a.Team.N==1 && a.Team.Mean==0 && a.Team.SampleSd is null && a.Team.CutSuccess==0,"zero/strict cut not preserved");
});
Check("negative_counters_rejected_storage_and_analysis",()=>{
    foreach(var field in Enumerable.Range(0,5)){
        var members=R(1).Members.ToArray();var m=members[0];members[0]=field switch{0=>m with{Shots=-1},1=>m with{Hits=-1},2=>m with{CriticalHits=-1},3=>m with{Reloads=-1},_=>m with{BurstCasts=-1}};
        var bad=R(1) with{Members=members};Reject(()=>store.Write(b.Id,1,[new(1,1,bad,null)]));
        var status=store.Read(b.Id).Status with{Valid=1};Reject(()=>new ComputeAnalysis().Summarize(status,[bad],null));
    }
});
Check("duplicate_conflict_is_first_write_wins",()=>{
    var old=Wire.Serialize(store.Results(b.Id)[0]);var changed=R(0) with{ElapsedMilliseconds=123};
    store.Write(b.Id,1,[new(0,1,changed,null)]);Require(store.Read(b.Id).Status.Valid==1 && Wire.Serialize(store.Results(b.Id)[0])==old,"duplicate replaced accepted row");
});
Check("atomic_writer_chunk_rollback",()=>{
    Reject(()=>store.Write(b.Id,1,[new(1,1,R(1),null),new(2,1,R(2) with{RunId="wrong"},null)]));
    Require(store.Read(b.Id).Status.Valid==1,"part of invalid chunk persisted");
});
Check("failed_null_distinct_from_zero",()=>{
    store.Write(b.Id,1,[new(1,1,null,"qa_failure")]);var s=store.Read(b.Id).Status;
    Require(s.Valid==1 && s.Failed==1 && store.Results(b.Id).Count==1,"failed row counted");
});
var oldRow=Wire.Serialize(store.Results(b.Id)[0]);
Check("actual_store_crash_restore_resume_late_writer",()=>{
    store=new BatchStore(Path.Combine(root,"store"));var s=store.Read(b.Id).Status;
    Require(s.State=="cancelled" && s.ErrorCode=="process_interrupted" && s.Valid==1 && s.Failed==1 && s.Cancelled==1,"crash recovery counts");
    var resumed=store.Resume(b.Id);Require(resumed.Attempt==2 && resumed.Failed==0,"resume failed cleanup");store.Running(b.Id,2,resumed.Execution);
    store.Write(b.Id,1,[new(2,1,R(2),null)]);Require(store.Read(b.Id).Status.Valid==1,"late writer accepted");
    store.Write(b.Id,2,[new(1,2,R(1,2),null),new(2,2,R(2,2),null)]);store.Finish(b.Id,2,false);
    var all=store.Results(b.Id);Require(all.Count==3 && Wire.Serialize(all[0])==oldRow && all[0].Attempt==1,"valid old index not preserved");
    var a=new ComputeAnalysis().Summarize(store.Read(b.Id).Status,all,0);Require(a.Team.N==3 && !a.Partial,"final analysis partial/count");
});
File.WriteAllText(Path.Combine(root,"storage-summary.json"),Wire.Serialize(checks));

// Real prepared combat observation is opt-in; never load a production account or use fixed seeds.
if(args.Length==3){
    var prepareWatch=Stopwatch.StartNew();var actual=PreparedCompute.Restore(File.ReadAllText(args[1]));var prepareMs=prepareWatch.Elapsed.TotalMilliseconds;
    var actualHardware=Wire.Read<HardwareProfile>(File.ReadAllText(args[2]));
    var observed=new Observed(actual);var policy=new ExecutionPolicy(Path.Combine(root,"actual-tuning"));
    var selections=new List<object>();
    for(int i=0;i<2;i++){
        observed.Events.Clear();var sw=Stopwatch.StartNew();var cpu=Process.GetCurrentProcess().TotalProcessorTime;
        var selected=await policy.Select(actualHardware,observed,new("auto",2,Retune:true),default);
        selections.Add(new{iteration=i,selected,elapsedMs=sw.Elapsed.TotalMilliseconds,processCpuMs=(Process.GetCurrentProcess().TotalProcessorTime-cpu).TotalMilliseconds,events=observed.Events.ToArray()});
        Console.WriteLine($"actual tuning {i}: {selected.Reason}, {observed.Events.Count} run observations");
    }
    observed.Events.Clear();var reuse=await policy.Select(actualHardware,observed,new("auto",2),default);
    File.WriteAllText(Path.Combine(root,"tuning-observation.json"),Wire.Serialize(new{kind="actual_prepared_CPU_short_diagnostic_not_performance_comparison",prepareMs,selections,reuse,reuseRunCalls=observed.Events.Count,fullBattleGpu="not_implemented",exclusiveBenchmarkWindow=false}));
}
// Cheap synthetic prepared work verifies policy cache behavior independently of real battle duration.
var syntheticPolicy=new ExecutionPolicy(Path.Combine(root,"synthetic-tuning"));
var measured=await syntheticPolicy.Select(hw,p,new("auto",2),default);var reused=await syntheticPolicy.Select(hw,p,new("auto",2),default);
Check("policy_cache_reuse_and_fingerprint_dimensions",()=>{
    Require(reused.Reason=="measured_cache","cache not reused");
    Require(ExecutionPolicy.Conservative(hw with{Fingerprint="other-machine-driver-runtime"},p.Input,new("auto",2)).Fingerprint!=measured.Fingerprint,"hardware cache stale");
    foreach(var input in new[]{p.Input with{Fingerprint="other-workload"},p.Input with{EngineVersion="new-engine"},p.Input with{RulesVersion="new-rules"}})
        Require(ExecutionPolicy.Conservative(hw,input,new("auto",2)).Fingerprint!=measured.Fingerprint,"input cache stale");
    Require(ExecutionPolicy.Conservative(hw,p.Input,new("auto",1)).Fingerprint!=measured.Fingerprint,"resource cache stale");
});
File.WriteAllText(Path.Combine(root,"storage-summary.json"),Wire.Serialize(checks));
Console.WriteLine(root);
Environment.ExitCode=failures==0?0:1;

sealed class Synthetic:IPreparedExperiment{
    public ExperimentInput Input{get;}=new("qa-fixture","synthetic","data","engine","rules",["a","b","c","d","e"],400,10800,"final","summary","fixed:30925");
    public string PersistedInput=>"synthetic";
    public RunSummary Run(string id,int index,int attempt,CancellationToken token){token.ThrowIfCancellationRequested();return new($"{id}:{index}",attempt,index,id,Input.Fingerprint,"cpu","final",index,Input.CharacterIds.Select((x,i)=>new MemberRunSummary(x,i==0?index:0,1,0,3,0,0)).ToArray(),0,1);}
}
sealed class Observed(IPreparedExperiment inner):IPreparedExperiment{
    public ExperimentInput Input=>inner.Input;public string PersistedInput=>inner.PersistedInput;
    public List<object> Events{get;}=[];
    public RunSummary Run(string id,int index,int attempt,CancellationToken token){var w=Stopwatch.StartNew();bool complete=false;string? error=null;
        try{var result=inner.Run(id,index,attempt,token);complete=true;return result;}
        catch(Exception e){error=e.GetType().Name;throw;}
        finally{lock(Events)Events.Add(new{phase=id,index,complete,error,elapsedMs=w.Elapsed.TotalMilliseconds,cancelled=token.IsCancellationRequested});}}
}

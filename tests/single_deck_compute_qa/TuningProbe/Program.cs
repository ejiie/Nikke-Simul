using System.Diagnostics;
using System.Reflection;
using System.Text.Json.Nodes;
using Nikke.Compute;
using Nikke.Contracts;
using Nikke.Data;

var root=Path.GetFullPath(args[0]);Directory.CreateDirectory(root);
var checks=new List<object>();int failures=0;
void Need(bool ok,string message){if(!ok)throw new Exception(message);}
async Task Check(string name,Func<Task> test){try{await test();checks.Add(new{name,passed=true});Console.WriteLine(name+": PASS");}catch(Exception ex){failures++;checks.Add(new{name,passed=false,error=ex.ToString()});Console.WriteLine(name+": FAIL "+ex.Message);}File.WriteAllText(Path.Combine(root,"summary.json"),Wire.Serialize(checks));}
var hw=HardwareProbe.Normalize(new(),8,8L<<30,"qa-machine","Windows","X64",false);
// Reflection only in this independent QA executable: shorten deterministic fault budgets
// and inject managed-memory readings without changing product or impersonating Backend tests.
ExecutionPolicy Policy(string name,Func<long>? memory=null){
 var type=typeof(ExecutionPolicy).Assembly.GetType("Nikke.Compute.TuningBudget")!;
 var budget=Activator.CreateInstance(type,[TimeSpan.FromMilliseconds(150),TimeSpan.FromMilliseconds(450)])!;
 return (ExecutionPolicy)Activator.CreateInstance(typeof(ExecutionPolicy),BindingFlags.Instance|BindingFlags.NonPublic,null,[Path.Combine(root,name),budget,memory??(()=>0L)],null)!;
}
async Task<ExecutionSelection> Select(string name,Work w,ComputeOptions? options=null,Func<long>? memory=null){
 var s=await Policy(name,memory).Select(hw,w,options??new("auto",2),default,d=>w.Workers=d.Stages.LastOrDefault()?.Workers??0,123);
 Need(w.Active==0,"background call survived Select");File.WriteAllText(Path.Combine(root,name+".json"),Wire.Serialize(new{s,w.Events,w.MaxActive}));return s;
}
await Check("warmup_timeout_reserves_both_candidates",async()=>{
 var w=new Work{Delay=(id,i,workers)=>id=="warmup"?11000:15};var s=await Select("reserved",w);
 Need(s.Tuning!.Status=="measured" && s.Tuning.PlannedWorkers.SequenceEqual([1,2]),"limited plan not measured");
 Need(s.Tuning.Stages[0].Completed==0 && s.Tuning.Stages[0].Interrupted==1,"slow warmup counted");
 Need(s.Tuning.Stages.Skip(1).All(x=>x.Completed==2 && x.Interrupted==0 && x.Requested==2),"unequal/incomplete candidates");
 Need(w.MaxActive<=2 && !w.Overlap,"stages overlap");
});
await Check("partial_candidate_excluded_and_no_cache",async()=>{
 var w=new Work{Delay=(id,i,n)=>id=="tuning" && n==1 && i==1?2000:10};var s=await Select("partial",w);
 var stages=s.Tuning!.Stages;Need(stages[1].Completed==1 && stages[1].RunsPerSecond is null,"partial group used");
 Need(s.Tuning.Status=="partial" && s.Workers==2 && stages[2].Completed==2,"valid group not selected");
 Need(Directory.GetFiles(Path.Combine(root,"partial"),"*.json").Length==0,"partial cached");
});
await Check("zero_complete_candidates_safe_fallback",async()=>{
 var s=await Select("none",new Work{Delay=(_,_,_)=>2000});
 Need(s.Workers==1 && s.BenchmarkVersion=="not_measured" && s.Tuning!.Status=="not_measured","false measured");
 Need(Directory.GetFiles(Path.Combine(root,"none"),"*.json").Length==0,"fallback cached");
});
foreach(var phase in new[]{"warmup","candidate"})await Check("external_cancel_"+phase,async()=>{
 var w=new Work{Delay=(id,i,n)=>phase=="warmup"||id=="tuning"?2000:5};using var stop=new CancellationTokenSource();TuningDiagnostics? last=null;
 try{await Policy("cancel-"+phase).Select(hw,w,new("auto",2),stop.Token,d=>{last=d;w.Workers=d.Stages.LastOrDefault()?.Workers??0;if(d.Status==phase)stop.CancelAfter(30);});throw new Exception("cancel swallowed");}
 catch(OperationCanceledException){Need(stop.IsCancellationRequested && last!.Status=="cancelled" && last.StopReason=="external_cancelled" && w.Active==0,"cancel not drained/observed");}
 File.WriteAllText(Path.Combine(root,"cancel-"+phase+".json"),Wire.Serialize(new{last,w.Events}));
});
foreach(var during in new[]{false,true})await Check("memory_"+(during?"during":"before"),async()=>{
 var w=new Work{Delay=(_,_,_)=>2000};var s=await Select("memory-"+during,w,memory:()=>!during||w.Active>0?long.MaxValue:0);
 Need(s.Workers==1 && s.Tuning!.Status=="not_measured" && s.Tuning.StopReason=="memory_limit" && w.Active==0,"memory guard");
});
await Check("memory_caps_plan_one",async()=>{var s=await Select("cap",new Work(),new("auto",8,ExecutionPolicy.WorkerReserve));Need(s.Tuning!.PlannedWorkers.SequenceEqual([1]) && s.Workers==1,"memory cap ignored");});
await Check("cache_reuse_zero_calls_and_invalidations",async()=>{
 var w=new Work();var policy=Policy("cache");var s=await policy.Select(hw,w,new("auto",2),default);var count=w.Events.Count;
 var r=await policy.Select(hw,w,new("auto",2),default,preparationMilliseconds:99);
 Need(r.Reason=="measured_cache" && w.Events.Count==count && r.Tuning!.PreparationMilliseconds==99,"cache reran/stale preparation");
 var path=Path.Combine(root,"cache",s.Fingerprint+".json");var good=File.ReadAllText(path);
 foreach(var mutate in new Action<JsonObject>[] {x=>x["benchmarkVersion"]="cpu-policy-2",x=>x["tuning"]!["status"]="partial",x=>x["tuning"]=null,x=>x["backend"]="gpu",x=>x["tuning"]!["stages"]![1]!["runsPerSecond"]=123456}){
  var node=JsonNode.Parse(good)!.AsObject();mutate(node);File.WriteAllText(path,node.ToJsonString());count=w.Events.Count;
  r=await policy.Select(hw,w,new("auto",2),default);Need(r.Tuning!.CacheSource=="invalid" && w.Events.Count>count,"bad cache reused");
 }
 File.WriteAllText(path,"{invalid");r=await policy.Select(hw,w,new("auto",2),default);Need(r.Tuning!.CacheSource=="invalid","corrupt cache reused");
 var dimensions=new[]{w.Input with{Fingerprint="changed"},w.Input with{EngineVersion="changed"},w.Input with{RulesVersion="changed"}};
 foreach(var input in dimensions){var next=new Work{Input=input};r=await policy.Select(hw,next,new("auto",2),default);Need(r.Fingerprint!=s.Fingerprint && r.Reason!="measured_cache" && next.Events.Count>0,"input/version reused");}
 var other=new Work();r=await policy.Select(hw with{Fingerprint="other-hardware-driver-runtime"},other,new("auto",2),default);Need(r.Fingerprint!=s.Fingerprint && other.Events.Count>0,"hardware reused");
 other=new Work();r=await policy.Select(hw,other,new("auto",1),default);Need(r.Fingerprint!=s.Fingerprint && other.Events.Count>0,"resource reused");
 w.Delay=(_,_,_)=>2000;r=await policy.Select(hw,w,new("auto",2,Retune:true),default);Need(r.Tuning!.Status=="not_measured" && !File.Exists(path),"old cache survived failed retune");
 count=w.Events.Count;r=await policy.Select(hw,w,new("auto",2),default);Need(r.Reason!="measured_cache" && w.Events.Count>count,"old cache resurrected");
});
if(args.Length==3)foreach(bool slow in new[]{false,true})await Check("actual_180_"+(slow?"injected11s":"natural"),async()=>{
 var timer=Stopwatch.StartNew();var prepared=PreparedCompute.Restore(File.ReadAllText(args[1]));double prep=timer.Elapsed.TotalMilliseconds;
 var actualHw=Wire.Read<HardwareProfile>(File.ReadAllText(args[2]));var w=new Work(prepared){Delay=(id,_,_)=>slow&&id=="warmup"?11000:0};
 var policy=new ExecutionPolicy(Path.Combine(root,"actual-"+slow));var observations=new List<TuningDiagnostics>();
 var s=await policy.Select(actualHw,w,new("auto",2),default,d=>{observations.Add(d);w.Workers=d.Stages.LastOrDefault()?.Workers??0;},prep);
 var calls=w.Events.Count;var r=await policy.Select(actualHw,w,new("auto",2),default,preparationMilliseconds:prep);
 File.WriteAllText(Path.Combine(root,"actual-"+slow+".json"),Wire.Serialize(new{injectedWarmupDelayMs=slow?11000:0,prep,s,r,reuseRunCalls=w.Events.Count-calls,w.Events,w.Overlap,w.MaxActive,observations,exclusiveBenchmark=false}));
 Need(s.Tuning!.Status=="measured" && s.Tuning.PlannedWorkers.SequenceEqual([1,2]),"real limited candidates incomplete");
 Need(s.Tuning.Stages.Skip(1).All(x=>x.Completed==2 && x.Interrupted==0 && x.Requested==2 && x.BudgetMilliseconds==24000),"real full candidates");
 Need(s.Tuning.TotalBudgetMilliseconds==50000 && s.Tuning.Scope=="bounded_candidates_not_global_optimum","scope/budget");
 Need(!w.Overlap && w.Active==0 && r.Reason=="measured_cache" && w.Events.Count==calls,"overlap or cache ran");
 if(slow)Need(s.Tuning.Stages[0].Completed==0 && s.Tuning.Stages[0].Interrupted==1,"injected warmup counted");
});
Console.WriteLine(root);Environment.ExitCode=failures==0?0:1;

sealed class Work(IPreparedExperiment? inner=null):IPreparedExperiment{
 public ExperimentInput Input{get;init;}=inner?.Input??new("qa-tune","synthetic","data","engine","rules",["a","b","c","d","e"],400,10800,"final","summary","fixed:30925");
 public string PersistedInput=>inner?.PersistedInput??"synthetic";
 public Func<string,int,int,int> Delay=(_,_,_)=>5;public int Workers,Active,MaxActive;public bool Overlap;private string? activePhase;
 public List<object> Events{get;}=[];
 public RunSummary Run(string id,int index,int attempt,CancellationToken token){var sw=Stopwatch.StartNew();bool done=false;int workers=Workers;string? error=null;
  lock(Events){if(Active>0 && activePhase!=id+workers)Overlap=true;activePhase=id+workers;Active++;MaxActive=Math.Max(MaxActive,Active);}
  try{int delay=Delay(id,index,workers);if(delay>0 && token.WaitHandle.WaitOne(delay))token.ThrowIfCancellationRequested();
   var r=inner?.Run(id,index,attempt,token)??new RunSummary($"{id}:{index}",attempt,index,id,Input.Fingerprint,"cpu","final",0,Input.CharacterIds.Select(x=>new MemberRunSummary(x,0,0,0,0,0,0)).ToArray(),0,1);done=true;return r;
  }catch(Exception ex){error=ex.GetType().Name;throw;}finally{lock(Events){Active--;Events.Add(new{id,index,workers,done,error,ms=sw.Elapsed.TotalMilliseconds});}}
 }
}

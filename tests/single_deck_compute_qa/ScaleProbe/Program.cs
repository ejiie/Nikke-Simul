using System.Diagnostics;
using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Data;
using Nikke.Analysis;

var root=Path.GetFullPath(args[0]);Directory.CreateDirectory(root);
bool tenK=args.Length==4 && args[3]=="cpu-10k";
var deadline=DateTimeOffset.Parse(tenK?"2026-09-18T11:40:00+09:00":"2026-09-18T10:58:00+09:00");
int[] order=tenK?[4,8,15]:[2,4,8,8,4,2];int measuredCount=tenK?10000:1000,warmupCount=tenK?64:32;
long memoryLimit=long.Parse(args[2]);var inputText=File.ReadAllText(args[1]);var inputHash=Wire.Hash(inputText);
var prepare=Stopwatch.StartNew();var prepared=PreparedCompute.Restore(inputText);prepare.Stop();
using var stop=new CancellationTokenSource();using var monitorStop=new CancellationTokenSource();
string? stopReason=null;int active=0;var all=new List<object>();
void Save(string name,object value)=>File.WriteAllText(Path.Combine(root,name+".json"),Wire.Serialize(value));
void Require(bool ok,string why){if(!ok)throw new InvalidOperationException(why);}
var monitor=Task.Run(async()=>{try{while(!monitorStop.IsCancellationRequested){
 if(DateTimeOffset.Now>=deadline){stopReason="window_end";stop.Cancel();}
 if(File.Exists(Path.Combine(root,"stop.json"))){stopReason="external_guard";stop.Cancel();}
 if(GC.GetTotalMemory(false)>memoryLimit){stopReason="managed_memory_limit";stop.Cancel();}
 await Task.Delay(100,monitorStop.Token);
}}catch(OperationCanceledException) when(monitorStop.IsCancellationRequested){}});
void Validate(RunSummary row,string id,int index){
 Require(row.RunId==$"{id}:{index}" && row.ExperimentId==id && row.Index==index && row.Attempt==1,"run_identity");
 Require(row.InputFingerprint==prepared.Input.Fingerprint && row.Phase=="pilot" && row.Backend=="cpu","run_provenance");
 Require(row.Members.Select(m=>m.CharacterId).SequenceEqual(prepared.Input.CharacterIds),"member_order");
 Require(double.IsFinite(row.TeamDamage) && row.TeamDamage>=0 && row.Members.All(m=>double.IsFinite(m.Damage)&&m.Damage>=0),"damage");
 Require(row.Members.Sum(m=>(decimal)m.Damage)==(decimal)row.TeamDamage,"team_sum");
 Require(row.FullBursts>=0 && row.ElapsedMilliseconds>=0 && row.Members.All(m=>m.Shots>=0&&m.Hits>=0&&m.CriticalHits>=0&&m.Reloads>=0&&m.BurstCasts>=0),"negative_counter");
}
async Task<(RunSummary?[] Rows,double Seconds,int Max,int Completed,int Cancelled,int Failed)> Measure(string id,int count,int workers,CancellationToken token){
 var allocation=Stopwatch.StartNew();var rows=new RunSummary?[count];allocation.Stop();int max=0,completed=0,cancelled=0,failed=0;var errors=new System.Collections.Concurrent.ConcurrentQueue<object>();var milestones=new System.Collections.Concurrent.ConcurrentQueue<object>();
 var started=DateTimeOffset.Now;var cpu=Process.GetCurrentProcess().TotalProcessorTime;var timer=Stopwatch.StartNew();
 try{await Parallel.ForEachAsync(Enumerable.Range(0,count),new ParallelOptions{MaxDegreeOfParallelism=workers,CancellationToken=token},(i,ct)=>{
  int n=Interlocked.Increment(ref active);int prior;do{prior=max;if(n<=prior)break;}while(Interlocked.CompareExchange(ref max,n,prior)!=prior);
  try{var r=prepared.Run(id,i,1,ct);ct.ThrowIfCancellationRequested();rows[i]=r;int nDone=Interlocked.Increment(ref completed);if(nDone%1000==0){milestones.Enqueue(new{completed=nDone,seconds=timer.Elapsed.TotalSeconds,at=DateTimeOffset.Now});Console.WriteLine($"{id} {nDone}/{count}");}}
  catch(OperationCanceledException){Interlocked.Increment(ref cancelled);throw;}
  catch(Exception ex){Interlocked.Increment(ref failed);errors.Enqueue(new{index=i,error=ex.GetType().Name,message=ex.Message});throw;}
  finally{Interlocked.Decrement(ref active);}return ValueTask.CompletedTask;
 });}catch(OperationCanceledException) when(token.IsCancellationRequested){}catch{stopReason="run_failure";stop.Cancel();}
 timer.Stop();var process=Process.GetCurrentProcess();process.Refresh();double cpuSeconds=(process.TotalProcessorTime-cpu).TotalSeconds;
 var timing=new{kind="engine_summary_QA_parallel_not_API_or_SQLite",id,requested=count,workers,maxActive=max,activeAfter=active,completed,cancelledCalls=cancelled,notCompleted=count-completed,failed,
 startedAt=started,endedAt=DateTimeOffset.Now,wallSeconds=timer.Elapsed.TotalSeconds,cpuSeconds,runsPerSecond=completed/timer.Elapsed.TotalSeconds,
 workingSet=process.WorkingSet64,privateBytes=process.PrivateMemorySize64,lifetimePeakWorkingSet=process.PeakWorkingSet64};
 var output=Stopwatch.StartNew();File.WriteAllText(Path.Combine(root,id+"-rows.json"),Wire.Serialize(rows));output.Stop();
 Save(id+"-timing",new{timing,allocationSeconds=allocation.Elapsed.TotalSeconds,outputSeconds=output.Elapsed.TotalSeconds,checksum=Wire.Hash(File.ReadAllText(Path.Combine(root,id+"-rows.json"))),errors=errors.ToArray(),milestones=milestones.ToArray()});
 Require(active==0 && max<=workers,"undrained_or_excess_concurrency");
 return(rows,timer.Elapsed.TotalSeconds,max,completed,cancelled,failed);
}
try{
 Require(DateTimeOffset.Now<deadline && Environment.ProcessorCount-1>=order.Max() && memoryLimit>=order.Max()*64L*1024*1024,"window_or_available_processors_or_memory_reserve");
 Require(prepared.Input.Phase=="pilot" && prepared.Input.SynchroLevel==400 && prepared.Input.DurationFrames==10800 && prepared.Input.DefPolicy=="fixed:30925","fixed_input");
 Save("preparation",new{milliseconds=prepare.Elapsed.TotalMilliseconds,inputHash,input=prepared.Input,memoryLimit,availableProcessors=Environment.ProcessorCount,policy="QA explicit concurrency; no ExecutionPolicy.Select/cache changes"});
 RunSummary example;string exampleId;double smokeSeconds=0;
 if(tenK){
  var calibrations=new List<object>();RunSummary? first=null;
  foreach(int workers in order){string id=$"calibration-w{workers}";var cal=await Measure(id,128,workers,stop.Token);Require(cal.Completed==128 && cal.Failed==0,"calibration_incomplete");for(int i=0;i<128;i++)Validate(cal.Rows[i]!,id,i);first??=cal.Rows[0];
   var selection=new ExecutionSelection("cpu","cpu","cpu",workers,1,memoryLimit,"qa_calibration","current_engine_cpu","not_product_tuning","qa-harness",null);
   var batch=new BatchStatus(id,"completed",1,128,128,0,0,false,prepared.Input,selection,null);Save(id+"-batch",batch);Save(id+"-statistics",new ComputeAnalysis().Summarize(batch,cal.Rows.OfType<RunSummary>(),855466067));
   calibrations.Add(new{id,workers,seconds=cal.Seconds,valid=cal.Completed,maxActive=cal.Max});Console.WriteLine(id+" complete");
  }
  Save("calibrations",calibrations);example=first!;exampleId="calibration-w4";
 }else{var smoke=await Measure("smoke",64,2,stop.Token);Require(smoke.Completed==64 && smoke.Failed==0,"smoke_incomplete");for(int i=0;i<64;i++)Validate(smoke.Rows[i]!,"smoke",i);example=smoke.Rows[0]!;exampleId="smoke";smokeSeconds=smoke.Seconds;}
 var badMembers=example.Members.ToArray();badMembers[0]=badMembers[0] with{Hits=-1};bool rejected=false;
 try{Validate(example with{Members=badMembers},exampleId,0);}catch(InvalidOperationException){rejected=true;}Require(rejected,"counter_validator_smoke");
 Save("counter-smoke",new{negativeHitsRejected=rejected});
 using(var cancel=CancellationTokenSource.CreateLinkedTokenSource(stop.Token)){
  cancel.CancelAfter(20);var cancelled=await Measure("cancel-smoke",32,2,cancel.Token);
  Require(cancel.IsCancellationRequested && cancelled.Completed<32 && cancelled.Cancelled>0 && active==0,"cooperative_cancel_smoke");
 }
 if(tenK){
  File.WriteAllText(Path.Combine(root,"calibration.ready"),"counter_and_cancel_smoke_passed");
  while(!File.Exists(Path.Combine(root,"admission.json"))){stop.Token.ThrowIfCancellationRequested();await Task.Delay(50,stop.Token);}
  if(JsonNode.Parse(File.ReadAllText(Path.Combine(root,"admission.json")))!["allowed"]!.GetValue<bool>() is false){Save("harness-summary",new{status="admission_denied",blocks=all,activeAfter=active,inputUnchanged=Wire.Hash(prepared.PersistedInput)==inputHash});return;}
 }else{double expected=smokeSeconds/64*(6000+192),remaining=(deadline-DateTimeOffset.Now).TotalSeconds;Save("admission",new{smokeSeconds,expectedSeconds=expected,conservativeSeconds=expected*1.5+180,remainingSeconds=remaining,allowed=expected*1.5+180<remaining});Require(expected*1.5+180<remaining,"insufficient_window_no_silent_reduction");}
 foreach(var (workers,ordinal) in order.Select((workers,index)=>(workers,index))){
  stop.Token.ThrowIfCancellationRequested();string id=$"block-{ordinal+1}-w{workers}";
  Console.WriteLine(id+" warmup");var warm=await Measure(id+"-warmup",warmupCount,workers,stop.Token);Require(warm.Completed==warmupCount,"warmup_incomplete");
  for(int i=0;i<warmupCount;i++)Validate(warm.Rows[i]!,id+"-warmup",i);
  stop.Token.ThrowIfCancellationRequested();Console.WriteLine(id+" measuring");var measured=await Measure(id,measuredCount,workers,stop.Token);
  // Validation, Analysis, serialization and the independent Python audit are outside measured wall.
  var auditTimer=Stopwatch.StartNew();for(int i=0;i<measuredCount;i++)if(measured.Rows[i] is {} row)Validate(row,id,i);
  Require(Wire.Hash(prepared.PersistedInput)==inputHash && Wire.Hash(File.ReadAllText(args[1]))==inputHash,"input_changed");
  var selection=new ExecutionSelection("cpu","cpu","cpu",workers,1,memoryLimit,"qa_explicit_parallel","current_engine_cpu","not_product_tuning","qa-harness",null);
  var batch=new BatchStatus(id,measured.Completed==measuredCount?"completed":"cancelled",1,measuredCount,measured.Completed,measured.Failed,measuredCount-measured.Completed-measured.Failed,measured.Completed<measuredCount,prepared.Input,selection,stopReason);
  var statistics=new ComputeAnalysis().Summarize(batch,measured.Rows.OfType<RunSummary>(),tenK?855466067:null);Save(id+"-statistics",statistics);Save(id+"-batch",batch);
  auditTimer.Stop();Save(id+"-audit-cost",new{seconds=auditTimer.Elapsed.TotalSeconds});all.Add(new{id,workers,valid=measured.Completed,seconds=measured.Seconds,maxActive=measured.Max});
  Save("progress",all);File.WriteAllText(Path.Combine(root,id+".ready"),"independent_audit_required");
  while(!File.Exists(Path.Combine(root,id+".ack"))){stop.Token.ThrowIfCancellationRequested();await Task.Delay(50,stop.Token);}
  Require(measured.Completed==measuredCount && measured.Failed==0,"partial_block_preserved");Console.WriteLine(id+" complete");
 }
 Save("harness-summary",new{status="completed",blocks=all,activeAfter=active,inputUnchanged=Wire.Hash(prepared.PersistedInput)==inputHash});
}catch(Exception ex){stop.Cancel();Save("harness-summary",new{status="incomplete",blocks=all,activeAfter=active,stopReason,error=ex.ToString()});Environment.ExitCode=1;}
finally{monitorStop.Cancel();await monitor;Require(active==0,"jobs_survived_harness");}

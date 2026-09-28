using Nikke.Contracts;
using Nikke.Compute;
using Nikke.Data;
using Nikke.Storage;

// Only a QA-created external store, while its API is stopped. No source store mutation.
var root=Path.GetFullPath(args[0]);
var prepared=PreparedCompute.Restore(File.ReadAllText(Path.Combine(root,"prepared.json")));
var request=Wire.Read<ExperimentRequest>(File.ReadAllText(Path.Combine(root,"compute-request.json"))) with {Runs=1};
var hardware=Wire.Read<HardwareProfile>(File.ReadAllText(Path.Combine(root,"hardware.json")));
var options=request.Execution!;
var current=ExecutionPolicy.Conservative(hardware,prepared.Input,options);
if(args.Contains("--cache")) {
 var policy=new ExecutionPolicy(Path.Combine(root,"cache-probe"));
 var first=await policy.Select(hardware,prepared,options,CancellationToken.None);
 var second=await policy.Select(hardware,prepared,options,CancellationToken.None);
 var node=System.Text.Json.Nodes.JsonNode.Parse(prepared.PersistedInput)!;
 node["members"]![2]!["weapon"]!["hit"]!["statDamageRatio"]=2;
 string tamper="";
 try {PreparedCompute.Restore(node.ToJsonString());}catch(InvalidOperationException ex){tamper=ex.Message;}
 File.WriteAllText(Path.Combine(root,"cache-probe-result.json"),Wire.Serialize(new{first,second,tamper}));
 if(first.Tuning?.CacheSource!="miss" || second.Tuning?.CacheSource!="validated_policy_cache" || tamper!="prepared_input_fingerprint_mismatch")Environment.ExitCode=1;
 return;
}
var keys=new Dictionary<string,string> { ["current"]=current.Fingerprint };
keys["old_engine_only"]=ExecutionPolicy.Conservative(hardware,prepared.Input with {EngineVersion="cpu-summary.1"},options).Fingerprint;
keys["old_rules_only"]=ExecutionPolicy.Conservative(hardware,prepared.Input with {RulesVersion="p03.skills.2:p04.team.2:p02.3:final_round_even"},options).Fingerprint;
keys["old_workload_only"]=ExecutionPolicy.Conservative(hardware,prepared.Input with {Fingerprint=new string('a',64)},options).Fingerprint;
var store=new BatchStore(Path.Combine(root,"data","compute"));
var batch=store.Create(prepared,request,current);store.Running(batch.Id,1,current);
var historical=Wire.Read<RunSummary>(File.ReadAllText(Path.Combine(root,"old-run.json")));
var stale=historical with {RunId=batch.Id+":0",ExperimentId=batch.Id,Index=0,Attempt=1,Phase=prepared.Input.Phase};
bool rejected=false;string error="";
try {store.Write(batch.Id,1,[new(0,1,stale,null)]);}catch(ArgumentException ex){rejected=true;error=ex.Message;}
var countAfterRejected=store.Results(batch.Id).Count;
var valid=prepared.Run(batch.Id,0,1,CancellationToken.None);
store.Write(batch.Id,1,[new(0,1,valid,null)]);store.Finish(batch.Id,1,false);
var result=new{keys,keysDistinct=keys.Values.Distinct().Count()==keys.Count,rejected,error,countAfterRejected,batchId=batch.Id,validCount=store.Results(batch.Id).Count,valid};
File.WriteAllText(Path.Combine(root,"boundary.json"),Wire.Serialize(result));
if(!rejected || countAfterRejected!=0 || result.validCount!=1 || !result.keysDistinct)Environment.ExitCode=1;

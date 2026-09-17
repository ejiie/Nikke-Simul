using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json.Nodes;
using Nikke.Compute;
using Nikke.Contracts;
using Nikke.Data;

// Only public tables are read from source. No account DB, session or production cache is opened.
var source=Path.GetFullPath(args[0]);var root=Path.GetFullPath(args[1]);Directory.CreateDirectory(root);
var hashes=new Dictionary<string,string>();var data=Path.Combine(root,"public");
string Hash(string path)=>Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(path)));
void Copy(string path){var src=Path.Combine(source,path);hashes[path]=Hash(src);var target=Path.Combine(data,path);Directory.CreateDirectory(Path.GetDirectoryName(target)!);File.Copy(src,target,false);}
Copy("game-catalog.json");
foreach(var folder in new[]{"calculation","runtime"}) {
    Copy(folder+"/current.json");var m=JsonNode.Parse(File.ReadAllText(Path.Combine(data,folder,"current.json")))!;var id=m["id"]!.GetValue<string>();
    if(id.Length!=64 || id.Any(c=>!Uri.IsHexDigit(c)))throw new Exception("bad public manifest");
    var names=folder=="runtime"?new[]{"catalog.json"}:m["fileHashes"]!.AsObject().Select(p=>p.Key);
    foreach(var name in names){if(Path.GetFileName(name)!=name)throw new Exception("bad public filename");Copy(folder+"/"+id+"/"+name);}
}
var game=Wire.Read<GameSnapshot>(File.ReadAllText(Path.Combine(data,"game-catalog.json")));
var ids=new[]{"리타","블랑","앨리스","누아르","모더니아"}.Select(name=>game.Names.Single(p=>p.Value==name).Key).ToArray();
var snapshot=new AccountSnapshot {Id="synthetic-tuning",AccountId="synthetic",GameSnapshotId=game.Id,SynchroLevel=400,
    Consoles=new[]{"1001","1101","1102","1103","1201","1202","1203","1204","1205"}.ToDictionary(k=>k,k=>0),
    Characters=ids.Select(id=>new CharacterBuild {CharacterId=id,Name=game.Names[id],Level=400,NativeLevel=400,LimitBreak=0,Core=0,Bond=0,
        Skills=new(){["1"]=10,["2"]=10,["3"]=10},CubeId="0",CubeLevel=0,CollectionId="0",CollectionGrade="none",CollectionLevel=0,
        Equipment=SnapshotNormalizer.Parts.Select(slot=>new Equipment {Slot=slot,Tier=0,Level=0,Manufacturer=0,
            Lines=Enumerable.Range(1,3).Select(i=>new EquipmentLine {LineIndex=i,Presence="absent"}).ToList()}).ToList()}).ToList()};
var conditions=new JsonObject { ["roundingPolicy"]="final_round_even",["combat"]=new JsonObject {
    ["durationFrames"]=10800,["enemyDefense"]=30925,["critMode"]="sample",["core"]=true,["pelletCoefficientPolicy"]="per_trigger",["manualCharacterId"]=ids[2]},
    ["autoBurst"]=new JsonObject { ["tactic"]=new JsonObject { ["schemaVersion"]=1,
        ["allowedCharacterIds"]=new JsonArray(ids.Select(x=>JsonValue.Create(x)).ToArray()),
        ["stage1Priority"]=new JsonArray(ids[0]),["stage2Priority"]=new JsonArray(ids[1]),
        ["stage3Priority"]=new JsonArray(ids[2],ids[3],ids[4]),["burst3Rotation"]=new JsonArray(ids[2],ids[4]),["unavailablePolicy"]="next_ready"}}};
// Match the previous public smoke's present Alice head/1 without reading its synthetic DB.
snapshot.Characters[2].Equipment[0]=new(){Slot="head",Tier=10,Level=0,Manufacturer=0,Lines=[new(){LineIndex=1,Presence="present",OptionType="StatAtk",NormalizedValue=game.OptionSteps["atk_pct"][0],Unit="ratio"},new(){LineIndex=2,Presence="absent"},new(){LineIndex=3,Presence="absent"}]};
var prepare=Stopwatch.StartNew();var runtime=new RuntimeReplayService(Path.Combine(data,"runtime"),Path.Combine(root,"unused-replays"));
var prepared=runtime.PrepareCompute(snapshot,game,new(snapshot.Id,ids,conditions,2),new CalculationService(Path.Combine(data,"calculation")));prepare.Stop();
var hardware=await new HardwareProbe().Detect();var observed=new Observed(prepared,args.Contains("--slow-warmup"));
File.WriteAllText(Path.Combine(root,"prepared-synthetic.json"),prepared.PersistedInput);
File.WriteAllText(Path.Combine(root,"hardware.json"),Wire.Serialize(hardware));
File.WriteAllText(Path.Combine(root,"snapshot-synthetic.json"),Wire.Serialize(snapshot));
File.WriteAllText(Path.Combine(root,"request-synthetic.json"),Wire.Serialize(new ExperimentRequest(snapshot.Id,ids,conditions,2,Execution:new("auto",2))));
var events=new List<object>();var policy=new ExecutionPolicy(Path.Combine(root,"tuning"));
try {
    var stages=new List<TuningDiagnostics>();
    var watch=Stopwatch.StartNew();var selected=await policy.Select(hardware,observed,new("auto",2,Retune:true),default,d=>stages.Add(d),prepare.Elapsed.TotalMilliseconds);
    events.Add(new {selected,wallMs=watch.Elapsed.TotalMilliseconds,calls=observed.Calls.ToArray()});observed.Calls.Clear();
    // Baseline runs once: do not silently turn a failed cold diagnostic into a successful warm retry.
    ExecutionSelection? cached=null;
    if(!args.Contains("--baseline"))cached=await policy.Select(hardware,observed,new("auto",2),default);
    File.WriteAllText(Path.Combine(root,"observation.json"),Wire.Serialize(new{kind="actual_public_five_synthetic_account_functional_diagnostic",policy=ExecutionPolicy.Version,
        prepareMs=prepare.Elapsed.TotalMilliseconds,prepared.Input,events,stages,cached,cacheRunCalls=observed.Calls.Count,
        controlledWarmupDelay=args.Contains("--slow-warmup"),exclusiveBenchmarkWindow=false,performanceRankingAccepted=false}));
    if(!args.Contains("--baseline") && (cached?.Reason!="measured_cache" || observed.Calls.Count!=0))throw new Exception("completed measurement/cache evidence missing");
}
finally {
    var changed=hashes.Where(p=>Hash(Path.Combine(source,p.Key))!=p.Value).Select(p=>p.Key).ToArray();
    File.WriteAllText(Path.Combine(root,"source-hashes.json"),Wire.Serialize(new{hashes,changed}));
    if(changed.Length>0)throw new Exception("public source changed");
    Console.WriteLine(root);
}
sealed class Observed(IPreparedExperiment inner,bool slow):IPreparedExperiment {
    public ExperimentInput Input=>inner.Input;public string PersistedInput=>inner.PersistedInput;
    public List<object> Calls{get;}=[];
    public RunSummary Run(string id,int index,int attempt,CancellationToken token){var watch=Stopwatch.StartNew();bool complete=false;string? error=null;
        try {if(slow && id=="warmup" && token.WaitHandle.WaitOne(TimeSpan.FromSeconds(11)))token.ThrowIfCancellationRequested();
            var result=inner.Run(id,index,attempt,token);complete=true;return result;}
        catch(Exception e){error=e.GetType().Name;throw;}
        finally{lock(Calls)Calls.Add(new{id,index,complete,error,wallMs=watch.Elapsed.TotalMilliseconds});}}
}

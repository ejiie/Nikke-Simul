// QA-only runtime variations from actual API-prepared public members; no owner fixture.
using System.Text.Json;
using System.Text.Json.Nodes;
using Nikke.Engine;
using Nikke.Engine.Skills;
using Nikke.Core.Stats;
using Nikke.Data;
using Nikke.Simulator.Core.Stats;
var json=new JsonSerializerOptions(JsonSerializerDefaults.Web);
var snake=new JsonSerializerOptions{PropertyNamingPolicy=JsonNamingPolicy.SnakeCaseLower};
var catalog=JsonNode.Parse(File.ReadAllText(args[1]));
var graph=new SkillGraph(catalog["functions"].AsObject().ToDictionary(p=>int.Parse(p.Key),p=>p.Value.Deserialize<SkillFunction>(snake)),catalog["characterSkills"].AsObject().ToDictionary(p=>int.Parse(p.Key),p=>p.Value.Deserialize<SkillDefinition>(snake))){GaugeConstants=catalog["gaugeConstants"].Deserialize<GaugeSourceConstants>(json)};
using var output=new StreamWriter(args[2]);
foreach(var id in new[]{"5012","5001"}) {
 var saved=JsonNode.Parse(File.ReadAllText(Path.Combine(args[0],$"input-{id}-10-auto.json")));
 var members=saved["inputs"].Deserialize<SkillReplayMember[]>(json);var original=members[0];
 var c=saved["result"]["conditions"].Deserialize<SkillReplayConditions>(json);
 foreach(var speed in new[]{0,.25})foreach(var window in new[]{false,true}) {
  var copy=JsonSerializer.Deserialize<SkillReplayMember>(JsonSerializer.Serialize(original,json),json);
  copy.Weapon.Weapon.maxAmmo=100;
  var buffs=copy.Weapon.Buffs with {Ammo=[StatRateBuff.FromRaw("qa-ammo",1450)],ChargeSpeed=speed==0?[]:[StatRateBuff.FromRaw("qa-speed",2500)]};
  copy=copy with{Weapon=copy.Weapon with{Buffs=buffs}};
  var input=c with{Combat=c.Combat with{DurationFrames=1800,CritMode="sample",FullBurstWindows=window?[new(1,1800)]:[],TraceLimit=20000}};
  var result=SkillReplay.Run([copy],graph,input,new Fixed());
  output.WriteLine(JsonSerializer.Serialize(new{kind="run",id,speed,window,member=copy,result},json));
 }
}
var five=JsonNode.Parse(File.ReadAllText(args[3]));var team=five["inputs"].Deserialize<SkillReplayMember[]>(json);var conditions=five["result"]["conditions"].Deserialize<SkillReplayConditions>(json);
var sw=JsonNode.Parse(File.ReadAllText(Path.Combine(args[0],"input-5012-10-auto.json")))["inputs"][0].Deserialize<SkillReplayMember>(json);
var mw=JsonNode.Parse(File.ReadAllText(Path.Combine(args[0],"input-5001-10-auto.json")))["inputs"][0].Deserialize<SkillReplayMember>(json);
SkillReplayMember[] targets=[team[0],team[1],team[3],sw,mw];
targets=targets.Select((m,i)=>m with{Weapon=m.Weapon with{Hit=m.Weapon.Hit with{StatAttack=100*(i+1)}}}).ToArray();
var targetResult=SkillReplay.Run(targets,graph,conditions with{AutoBurst=null,Casts=[],DamageLog=null,Combat=conditions.Combat with{ManualCharacterId="",DurationFrames=10,FullBurstWindows=[new(1,10)],Trace=true,TraceLimit=2000}},new Fixed());
output.WriteLine(JsonSerializer.Serialize(new{kind="targets",members=targets,result=targetResult},json));
var baseline=PreparedCompute.Create(team,graph,conditions,"qa","data-one","pilot");
var changed=graph.Functions.ToDictionary(p=>p.Key,p=>p.Value);int key=changed.Keys.First();changed[key]=changed[key] with{FunctionValue=changed[key].FunctionValue+1};
var dataChange=PreparedCompute.Create(team,graph,conditions,"qa","data-two","pilot");
var graphChange=PreparedCompute.Create(team,graph with{Functions=changed},conditions,"qa","data-one","pilot");
var conditionChange=PreparedCompute.Create(team,graph,conditions with{Combat=conditions.Combat with{Core=!conditions.Combat.Core}},"qa","data-one","pilot");
var mutations=new Dictionary<string,bool>();
foreach(var field in new[]{"dataVersion","graph","conditions"}) {
 var p=JsonNode.Parse(baseline.PersistedInput);
 if(field=="dataVersion")p["input"]["dataVersion"]="data-two";
 else if(field=="graph")p["graph"]["functions"][key.ToString()]["functionValue"]=changed[key].FunctionValue;
 else p["conditions"]["combat"]["core"]=!conditions.Combat.Core;
 try{PreparedCompute.Restore(p.ToJsonString());mutations[field]=false;}catch(InvalidOperationException e){mutations[field]=e.Message=="prepared_input_fingerprint_mismatch";}
}
output.WriteLine(JsonSerializer.Serialize(new{kind="fingerprint",baseline=baseline.Input,dataChange=dataChange.Input,graphChange=graphChange.Input,conditionChange=conditionChange.Input,mutations},json));
sealed class Fixed:IRandomSource {public double NextDouble()=>.27;}

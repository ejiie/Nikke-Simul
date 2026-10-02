// Independent QA inputs; no owner/reviewer tests, fixtures or expected outputs.
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using Nikke.Core.Combat;
using Nikke.Core.Stats;
using Nikke.Engine;
using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Data.Dto;
using Nikke.Simulator.Core.Stats;
var j=new JsonSerializerOptions(JsonSerializerDefaults.Web){NumberHandling=JsonNumberHandling.AllowNamedFloatingPointLiterals};
if(args[0]=="arithmetic") {
 using var output=new StreamWriter(args[2]);
 foreach(string line in File.ReadLines(args[1])) {
  var n=JsonNode.Parse(line);string kind=n["kind"].GetValue<string>(),id=n["id"].GetValue<string>();object value;
  try {
   if(kind=="direct") {
    var rates=n["rates"].Deserialize<ClientDamageRates>(j);long a=n["attack"].GetValue<long>(),d=n["defence"].GetValue<long>();
    string policy=n["policy"].GetValue<string>();
    value=policy=="client_f32"?ClientFloatDamage.Calculate(a,d,rates):typeof(ClientFloatDamage).GetMethod("CalculateDoubleProduct").Invoke(null,[a,d,rates]);
   } else if(kind=="context") {
    var c=n["context"].Deserialize<HitContext>(j);var policy=n["policy"].GetValue<string>();value=new{damage=HitCalculator.Calculate(c,policy),audit=HitCalculator.Evaluate(c,policy)};
   } else if(kind=="ammo") {
    var groups=n["groups"].Deserialize<StatRateBuff[][]>(j);long native=n["native"].GetValue<long>();var method=typeof(StatBuffCalculator).GetMethod("ApplyAmmo");
    value=method is null?StatBuffCalculator.Apply(native,groups):method.Invoke(null,[native,groups]);
   } else {
    var weapon=new WeaponDto{weaponType="AR",fireType="Instant",inputType="DOWN",maxAmmo=100,fireRate=60,endFireRate=60,reloadTimeSec=1,reloadBulletRate=1,shotCount=1,muzzleCount=1};
    var functions=n["functions"].Deserialize<SkillFunction[]>(j);
    var member=new SkillReplayMember(new("qa",weapon,new(){StatAttack=100,AttackDamage=.2,Parts=true,PartsDamage=.3},new()),1000,new("QA",new Dictionary<string,int>{{"skill1",1},{"skill2",1},{"burst",1}},new Dictionary<string,SkillDefinition>{{"skill1",new(){SkillId=9001,FunctionIds=functions.Select(f=>f.Id).ToArray()}},{"skill2",new(){SkillId=9002}},{"burst",new(){SkillId=9003}}}));
    var c=new SkillReplayConditions{RoundingPolicy=n["policy"].GetValue<string>(),InterruptionTarget=n["target"].GetValue<bool>(),Combat=new(){DurationFrames=3,EnemyDefense=0,CritMode="off",Trace=true,PelletCoefficientPolicy="per_trigger"},DamageLog=new(){CharacterId="qa"}};
    value=SkillReplay.Run([member],new(functions.ToDictionary(f=>f.Id),new Dictionary<int,SkillDefinition>()),c,new QaRandom(17));
   }
   output.WriteLine(JsonSerializer.Serialize(new{id,result=value},j));
  } catch(Exception ex){while(ex.InnerException is not null)ex=ex.InnerException;output.WriteLine(JsonSerializer.Serialize(new{id,error=ex.GetType().Name,message=ex.Message},j));}
 }return;
}
var catalog=JsonNode.Parse(File.ReadAllText(args[2]));var snake=new JsonSerializerOptions{PropertyNamingPolicy=JsonNamingPolicy.SnakeCaseLower};
var graph=new SkillGraph(catalog["functions"].AsObject().ToDictionary(p=>int.Parse(p.Key),p=>p.Value.Deserialize<SkillFunction>(snake)),catalog["characterSkills"].AsObject().ToDictionary(p=>int.Parse(p.Key),p=>p.Value.Deserialize<SkillDefinition>(snake))){GaugeConstants=catalog["gaugeConstants"].Deserialize<GaugeSourceConstants>(j)};
using var teamOutput=new StreamWriter(args[3]);
foreach(var file in Directory.GetFiles(args[1],"team-input-*.json").Order()) {
 var saved=JsonNode.Parse(File.ReadAllText(file));var members=saved["inputs"].Deserialize<SkillReplayMember[]>(j);var c=saved["result"]["conditions"].Deserialize<SkillReplayConditions>(j);
 foreach(var policy in (args.Length>4?new[]{"client_f32","legacy_term_floor","client_f32_dprod"}:new[]{"client_f32","legacy_term_floor"}))foreach(int seed in Enumerable.Range(1,5)) {
  var input=c with{RoundingPolicy=policy,DamageLog=null,Combat=c.Combat with{Trace=false}};
  var r=SkillReplay.Run(members,graph,input,new QaRandom(seed));
  teamOutput.WriteLine(JsonSerializer.Serialize(new{scenario=Path.GetFileNameWithoutExtension(file),policy,seed,r.TotalDamage,r.Members,r.TeamBurst,r.EventCount},j));teamOutput.Flush();Console.WriteLine(Path.GetFileName(file)+" "+policy+" "+seed);
 }
}
sealed class QaRandom(int seed):IRandomSource {readonly Random r=new(seed);public double NextDouble()=>r.NextDouble();}

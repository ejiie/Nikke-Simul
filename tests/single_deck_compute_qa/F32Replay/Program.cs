using System.Text.Json;
using Nikke.Engine.Skills;
var j=new JsonSerializerOptions(JsonSerializerDefaults.Web);
var input=JsonSerializer.Deserialize<Input>(File.ReadAllText(args[0]),j);
var members=input.Members.Select(m=>m with {Weapon=m.Weapon with {Hit=m.Weapon.Hit with {StatAttack=100000}}}).ToArray();
var conditions=input.Conditions with {DamageLog=null,Combat=input.Conditions.Combat with {CritMode="off",ManualCharacterId="",Trace=false,EnemyDefense=30925},AutoBurst=input.Conditions.AutoBurst with {TimelineLimit=0,StageDelayMinFrames=1,StageDelayMaxFrames=1}};
Directory.CreateDirectory(args[1]);
foreach(var policy in args.Skip(2)) {
 var c=conditions with {RoundingPolicy=policy=="default"?new SkillReplayConditions().RoundingPolicy:policy};
 var result=SkillReplay.Run(members,input.Graph,c);
 File.WriteAllText(Path.Combine(args[1],policy+".json"),JsonSerializer.Serialize(new {result.TotalDamage,result.Members,fullBursts=result.Connection.FullBurst.Cycle,policy=c.RoundingPolicy},j));
 foreach(var m in members) {
  var logged=SkillReplay.Run(members,input.Graph,c with {DamageLog=new(){CharacterId=m.Weapon.CharacterId}});
  File.WriteAllText(Path.Combine(args[1],policy+"-"+m.Weapon.CharacterId+"-hits.json"),JsonSerializer.Serialize(logged.DamageLog,j));
 }
 var p=PreparedSkillReplay.Create(members,input.Graph,c);
 var rows=await Task.WhenAll(Enumerable.Range(0,2).Select(_=>Task.Run(()=>p.Run())));
 using var stop=new CancellationTokenSource(); stop.Cancel(); bool cancelled=false;
 try {p.Run(stop.Token);} catch(OperationCanceledException){cancelled=true;}
 using var activeStop=new CancellationTokenSource();
 activeStop.CancelAfter(1); bool activeCancelled=false;
 try {p.Run(activeStop.Token);} catch(OperationCanceledException){activeCancelled=true;}
 var resumed=p.Run();
 File.WriteAllText(Path.Combine(args[1],policy+"-parallel.json"),JsonSerializer.Serialize(new{rows,cancelled,activeCancelled,resumed},j));
}
record Input(SkillReplayMember[] Members,SkillGraph Graph,SkillReplayConditions Conditions);

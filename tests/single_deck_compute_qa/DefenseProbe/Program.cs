using System.Text.Json;
using Nikke.Core.Combat;
using Nikke.Core.Stats;
using Nikke.Engine;
using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Data.Dto;
// QA-authored synthetic cases. No owner tests/golden/oracle data are loaded.
var j=new JsonSerializerOptions(JsonSerializerDefaults.Web);
var outputs=new List<object>();
SkillReplayMember Member(string id,double attack,int pellets=1,int timing=-1) {
 var skill=new SkillDefinition {SkillId=990,FunctionIds=timing<0?[]:[991]};
 return new(new(id,new WeaponDto {weaponType=pellets==1?"AR":"SG",fireType="Instant",inputType="DOWN",fireRate=60,endFireRate=60,maxAmmo=20,reloadTimeSec=1,reloadBulletRate=1,shotCount=pellets,muzzleCount=1},new HitContext {StatAttack=attack,Coefficient=pellets},new StatBuffSet()),1000,new("QA",new Dictionary<string,int>{{"skill1",1},{"skill2",1},{"burst",1}},new Dictionary<string,SkillDefinition>{{"skill1",skill},{"skill2",new(){SkillId=992}},{"burst",new(){SkillId=993}}}));
}
void Run(string label,SkillReplayMember[] members,int frames=1,int timing=-1,bool fixedMode=false,string policy="client_f32") {
 var functions=new Dictionary<int,SkillFunction>();
 if(timing>=0) functions[991]=new(){Id=991,FunctionType=75,FunctionTarget=1,FunctionValue=10000,FunctionValueType=2,TimingTriggerType=timing,TimingTriggerValue=1};
 var graph=new SkillGraph(functions,new Dictionary<int,SkillDefinition>());
 var c=new SkillReplayConditions {Combat=new(){DurationFrames=frames,PelletCoefficientPolicy="per_trigger",CritMode="off",EnemyDefense=30925,DefenseMode=fixedMode?"fixed":"team_damage_threshold",Trace=true,TraceLimit=20000},RoundingPolicy=policy};
 var result=SkillReplay.Run(members,graph,c);
 var summary=PreparedSkillReplay.Create(members,graph,c).Run();
 outputs.Add(new {label,members,conditions=c,result,summary});
}
Run("below",[Member("below",2000000000-128+30925)]);
Run("equal",[Member("equal",2000000000+30925)]);
Run("plus-one-same-frame",[Member("a",2000000000+30925),Member("b",30926),Member("c",31925)]);
Run("sg-six-pellets",[Member("sg",500000000+30925,6)]);
Run("extra-before-normal",[Member("extra",1000000000+30925,1,3)],2,3);
Run("frame-zero-skill",[Member("start",2000000000+128+30925,1,1)],1,1);
foreach(var policy in new[]{"client_f32","legacy_term_floor","final_round_even","nested_floor"}) Run("fixed-"+policy,[Member("fixed",2000000000+30925),Member("fixed2",31925)],3,-1,true,policy);
Directory.CreateDirectory(Path.GetDirectoryName(args[0]));
File.WriteAllText(args[0],JsonSerializer.Serialize(outputs,j));

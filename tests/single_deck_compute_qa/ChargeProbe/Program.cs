// Independent QA harness: only product APIs and QA-created public-table inputs.
using System.Text.Json;
using System.Text.Json.Nodes;
using Nikke.Core.Combat;
using Nikke.Engine;
using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Data.Dto;
using Nikke.Simulator.Core.Stats;
using Nikke.Simulator.Engine;
var json=new JsonSerializerOptions(JsonSerializerDefaults.Web);
void Save(object value)=>File.WriteAllText(args[1],JsonSerializer.Serialize(value,json));
if(args[0]=="timing") {
 var rows=new List<object>();
 void Run(string label,WeaponDto w,FiringControl c,double buff=0) {
  var a=new FiringModel(new(w),w.maxAmmo,c,new QaRandom(18),chargeSpeedBuffs:[buff]);
  var b=new SkillFiringModel(new(w),w.maxAmmo,c,new QaRandom(18),chargeSpeedBuffs:[buff]);
  var legacy=new List<FiringFrameResult>();var skill=new List<FiringFrameResult>();
  for(int f=1;f<=2400;f++){legacy.Add(a.AdvanceFrame());skill.Add(b.AdvanceFrame());}
  rows.Add(new{label,weapon=w,control=c,buff,legacy,skill});
 }
 WeaponDto Weapon(int aim,int cs,string input="UP",double maintain=0,int ammo=10000)=>new(){weaponType="SR",isChargeWeapon=true,inputType=input,fireType="Instant",fireRate=10,endFireRate=10,spotFirstDelaySec=aim/60d,spotLastDelaySec=.2,chargeTimeSec=cs/100d,maintainFireStanceSec=maintain,maxAmmo=ammo,reloadTimeSec=.9,reloadBulletRate=1,shotCount=1,muzzleCount=1};
 foreach(int aim in new[]{0,5,12}) foreach(int cs in new[]{1,10,100}) foreach(int click in new[]{1,3})
  Run($"manual-{aim}-{cs}-{click}",Weapon(aim,cs),new(){Mode=ControlMode.Manual,ReclickMinSec=click/60d,ReclickMaxSec=click/60d});
 foreach(var mode in new[]{ControlMode.Auto,ControlMode.Manual}) foreach(int cs in new[]{1,10,100}) {
  Run($"down-{mode}-{cs}",Weapon(12,cs,"DOWN_Charge",ammo:7),new(){Mode=mode});
  Run($"maintain-{mode}-{cs}",Weapon(12,cs,maintain:.23,ammo:7),new(){Mode=mode});
  if(mode==ControlMode.Auto)Run($"auto-{cs}",Weapon(12,cs,ammo:7),new(){Mode=mode});
  else Run($"tap-{cs}",Weapon(12,cs,ammo:7),new(){Mode=mode,Style=FireStyle.Tap});
 }
 Run("manual-buff-99",Weapon(12,100),new(){Mode=ControlMode.Manual,ReclickMinSec=1/60d,ReclickMaxSec=1/60d},.99);
 if(args.Length>2)foreach(var kv in JsonNode.Parse(File.ReadAllText(args[2])).AsObject())
  foreach(var mode in new[]{ControlMode.Auto,ControlMode.Manual})Run("public-"+kv.Key+"-"+mode,kv.Value.Deserialize<WeaponDto>(json),new(){Mode=mode});
 Save(new{version=SkillReplay.Version,rows});return;
}
var saved=JsonNode.Parse(File.ReadAllText(args[2]));
var members=saved["inputs"].Deserialize<SkillReplayMember[]>(json);
var catalog=JsonNode.Parse(File.ReadAllText(args[3]));
var snake=new JsonSerializerOptions{PropertyNamingPolicy=JsonNamingPolicy.SnakeCaseLower};
var graph=new SkillGraph(catalog["functions"].AsObject().ToDictionary(p=>int.Parse(p.Key),p=>p.Value.Deserialize<SkillFunction>(snake)),catalog["characterSkills"].AsObject().ToDictionary(p=>int.Parse(p.Key),p=>p.Value.Deserialize<SkillDefinition>(snake))){GaugeConstants=catalog["gaugeConstants"].Deserialize<GaugeSourceConstants>(json)};
var input=saved["result"]["conditions"].Deserialize<SkillReplayConditions>(json);
if(args.Length>4)input=input with{AutoBurst=input.AutoBurst with{Tactic=input.AutoBurst.Tactic with{Burst3Rotation=args[4].Split(',')}}};
var runs=new List<object>();
foreach(string style in new[]{"full_charge","tap","auto"}) foreach(int seed in Enumerable.Range(1,20)) {
 var c=input with {DamageLog=new(){CharacterId="5004"},Combat=input.Combat with{ManualCharacterId=style=="auto"?"":"5004",ManualStyle=style=="auto"?"full_charge":style,Trace=true,TraceLimit=20000}};
 var sink=new ShotSink();var r=SkillReplay.Run(members,graph,c,new QaRandom(seed),sink);
 var shots=sink.Shots;
 var charge=r.DamageLog.Entries.Where(e=>e.ShotId is not null).Select(e=>new{e.Frame,e.ShotId,e.EffectiveChargeFrames,e.ActualChargeFrames,e.OwnBurstEffectActive,ammo=e.Shot?.AmmoAfter}).ToArray();
 var burst=r.TeamBurst with {Timeline=seed==1?r.TeamBurst.Timeline:[]};
 runs.Add(new{style,seed,r.TotalDamage,r.Members,teamBurst=burst,shots,charge,events=seed==1?r.Events:null});
 Console.WriteLine(style+" "+seed+" "+r.TotalDamage);
 if(seed==1) {
  var quiet=SkillReplay.Run(members,graph,c with{DamageLog=null,Combat=c.Combat with{Trace=false}},new QaRandom(seed));
  var limited=SkillReplay.Run(members,graph,c with{Combat=c.Combat with{TraceLimit=7}},new QaRandom(seed));
  if(quiet.TotalDamage!=r.TotalDamage || limited.TotalDamage!=r.TotalDamage)throw new Exception("trace changed arithmetic");
 }
}
// Counterfactual: pin exactly the same prescribed casts and RNG output in both engines.
// This removes shared RNG sequence shifts and the gauge scheduling feedback.
var casts=Enumerable.Range(0,5).Select(i=>new SkillCast(250+i*2400,"5004")).ToArray();
var windows=casts.Select(c=>new FrameWindow(c.Frame,c.Frame+600)).ToArray();
var controlled=input with{AutoBurst=null,Casts=casts,DamageLog=null,Combat=input.Combat with{CritMode="off",FullBurstWindows=windows,Trace=true,TraceLimit=20000}};
var isolated=SkillReplay.Run(members,graph,controlled,new ConstantRandom());
Save(new{version=SkillReplay.Version,teamVersion=TeamBurstController.Version,summaryVersion=PreparedSkillReplay.Version,weaponVersion=WeaponReplay.Version,runs,isolated});
sealed class QaRandom(int seed):IRandomSource {readonly Random random=new(seed);public double NextDouble()=>random.NextDouble();}
sealed class ConstantRandom:IRandomSource {public double NextDouble()=>.375;}
sealed class ShotSink:ICombatEventSink {public List<object> Shots=new();public void OnEvent(CombatEvent e){if(e.Kind==CombatEventKind.Shot)Shots.Add(new{e.Frame,e.Source,e.TraceId});}}

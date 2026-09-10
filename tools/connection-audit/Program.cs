using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Data;
using Nikke.Engine;
using Nikke.Engine.Skills;

// Runs against ignored, immutable local evidence. No account mutations or network.
if (args.Length!=2) throw new ArgumentException("Usage: ConnectionAudit <project root> <p03.skills.1 baseline replays JSON>");
string root=Path.GetFullPath(args[0]), baselinePath=Path.GetFullPath(args[1]);
var pointer=JsonNode.Parse(File.ReadAllText(Path.Combine(root,"data/local/runtime/current.json")))!;
string runtimeId=pointer["id"]!.GetValue<string>();
byte[] bytes=File.ReadAllBytes(Path.Combine(root,"data/local/runtime",runtimeId,"catalog.json"));
Check(Convert.ToHexStringLower(SHA256.HashData(bytes))==runtimeId,"catalog content hash");
var catalog=JsonNode.Parse(bytes)!;
var official=new JsonSerializerOptions { PropertyNamingPolicy=JsonNamingPolicy.SnakeCaseLower };
var graph=new SkillGraph(catalog["functions"]!.AsObject().ToDictionary(p=>int.Parse(p.Key),p=>p.Value!.Deserialize<SkillFunction>(official)!),
    catalog["characterSkills"]!.AsObject().ToDictionary(p=>int.Parse(p.Key),p=>p.Value!.Deserialize<SkillDefinition>(official)!)) {
    GaugeConstants=catalog["gaugeConstants"]!.Deserialize<GaugeSourceConstants>(Wire.Json) };
var baseline=Wire.Read<List<SavedSkillReplay>>(File.ReadAllText(baselinePath));
Check(baseline.Count==3 && baseline.Select(b=>b.Result.Conditions.RoundingPolicy).Distinct().Count()==3,"three policies");
Check(baseline.All(b=>b.Result.RulesVersion=="p03.skills.1" && b.Result.Connection is null),"old record remains readable without invented connection status");
var reports=new List<object>();
foreach (var old in baseline)
{
    var members=old.Inputs.Select(m=>m with { Skills=m.Skills with {
        BurstConnection=catalog["characters"]![m.Weapon.CharacterId]!["burstConnection"]!.Deserialize<BurstConnectionProfile>(Wire.Json) } }).ToArray();
    var conditions=old.Result.Conditions;
    Check(conditions.Combat.DurationFrames==10800 && conditions.Combat.CritMode=="off" && string.IsNullOrEmpty(conditions.Combat.ManualCharacterId),"deterministic 180s fixture");
    using var prescribedSink=new DigestSink();
    var prescribed=SkillReplay.Run(members,graph,conditions,events:prescribedSink);
    Check(prescribed.TotalDamage==old.Result.TotalDamage,"baseline damage");
    Check(Wire.Serialize(prescribed.Members)==Wire.Serialize(old.Result.Members),"baseline member/effect/ammo/cooldown parity");
    Check(prescribed.EventCount==old.Result.EventCount,"legacy trace event count");
    using var drivenSink=new DigestSink();
    var driven=SkillReplay.Run(members,graph,conditions with { Casts=[],Combat=conditions.Combat with {
        FullBurstWindows=[],Trace=true,TraceLimit=3 } },events:drivenSink,driver:new ScheduleDriver(conditions));
    Check(driven.TraceTruncated && driven.Events.Count==3,"trace limit exercised");
    Check(Wire.Serialize(prescribed.Members)==Wire.Serialize(driven.Members),"driver member parity");
    Check(Wire.Serialize(prescribed.Connection)==Wire.Serialize(driven.Connection),"driver summary parity");
    Check(prescribedSink.Finish()==drivenSink.Finish(),"entire event stream parity");
    Check(drivenSink.LastFrame>10700,"delivery reaches final battle second");
    Check(!driven.Connection.TimelineTruncated,"cycle timeline complete");
    Check(driven.Connection.EventCounts[CombatEventKind.FullBurstEntered]==conditions.Combat.FullBurstWindows.Count,"every full-burst entry");
    Check(driven.Connection.EventCounts[CombatEventKind.FullBurstExited]==conditions.Combat.FullBurstWindows.Count(w=>w.EndFrame<=10800),"every full-burst exit");
    foreach (var m in driven.Members)
    {
        Check(drivenSink.Shots.GetValueOrDefault(m.CharacterId)==m.Shots,"shot delivery");
        Check(drivenSink.Ammo.GetValueOrDefault(m.CharacterId)==m.AmmoConsumed,"ammo delivery");
        Check(drivenSink.Hits.GetValueOrDefault(m.CharacterId)==m.Hits,"normal hit delivery");
        Check(drivenSink.Damage.GetValueOrDefault(m.CharacterId)==m.Damage,"all damage delivery without duplicates");
    }
    reports.Add(new { policy=conditions.RoundingPolicy,old.Result.TotalDamage,old.Result.EventCount,
        connectionEvents=driven.Connection.EventCount,lastEventFrame=drivenSink.LastFrame,
        baselineParity=true,driverParity=true,driven.Connection,appliedSkillLevels=members.ToDictionary(m=>m.Weapon.CharacterId,m=>m.Skills.Levels) });
}
// A short shifted-entry fixture captures all of Modernia's weapon transition, independently of long trace limits.
var modernia=baseline[0].Inputs.Single(m=>catalog["characters"]![m.Weapon.CharacterId]!["name"]!.GetValue<string>()=="모더니아");
modernia=modernia with { Skills=modernia.Skills with { BurstConnection=catalog["characters"]![modernia.Weapon.CharacterId]!["burstConnection"]!.Deserialize<BurstConnectionProfile>(Wire.Json) } };
var shortConditions=baseline[0].Result.Conditions with { Casts=[new(1,modernia.Weapon.CharacterId)],
    Combat=baseline[0].Result.Conditions.Combat with { DurationFrames=960,Trace=true,TraceLimit=20000,
        FullBurstWindows=[new(29,929)] } };
var shortRun=SkillReplay.Run([modernia],graph,shortConditions);
Check(!shortRun.TraceTruncated,"complete Modernia trace");
Check(shortRun.Events.Any(e=>e.Kind=="weapon_restored" && e.Frame==901),"official mode expires at 901");
Check(shortRun.Connection.Timeline.Single(e=>e.Kind==CombatEventKind.FullBurstDurationRequested).DurationRequest.DurationFrames==900,"official 15s request");
Check(shortRun.Connection.Timeline.Single(e=>e.Kind==CombatEventKind.FullBurstExited).Frame==929,"separate full burst expiry");
Check(shortRun.Members[0].Shots>shortRun.Members[0].AmmoConsumed,"unlimited ammo");
string output=Path.Combine(root,"artifacts/p03/connection-implementation");Directory.CreateDirectory(output);
File.WriteAllText(Path.Combine(output,"official-180s-audit.json"),Wire.Serialize(new { gameVerified=false,runtimeId,
    baselineSha256=Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(baselinePath))),reports }));
File.WriteAllText(Path.Combine(output,"modernia-short-trace.json"),Wire.Serialize(shortRun));
Console.WriteLine(Wire.Serialize(new { policies=3,baselineParity=true,driverParity=true,fullStreamParity=true,moderniaShortTrace=true,output }));
static void Check(bool pass,string name) { if (!pass) throw new InvalidOperationException("Audit failed: " + name); }

sealed class ScheduleDriver(SkillReplayConditions input) : ISkillBattleDriver
{
    public void OnPhase(ISkillBattleControl b,BattlePhase phase)
    {
        if (phase==BattlePhase.CastSkills)
            foreach (var c in input.Casts.Where(c=>c.Frame==b.Frame))
                if (b.TryCast(c.CharacterId,c.Slot).Status!=BattleCommandStatus.Applied) throw new InvalidOperationException("Driver cast rejected");
        if (phase==BattlePhase.FullBurstEntry)
            foreach (var w in input.Combat.FullBurstWindows.Where(w=>w.StartFrame==b.Frame))
                if (b.TryEnterFullBurst(w.EndFrame-w.StartFrame)!=BattleCommandStatus.Applied) throw new InvalidOperationException("Driver entry rejected");
    }
}
sealed class DigestSink : ICombatEventSink, IDisposable
{
    private readonly IncrementalHash hash=IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
    public Dictionary<string,int> Shots { get; }=new();
    public Dictionary<string,int> Ammo { get; }=new();
    public Dictionary<string,int> Hits { get; }=new();
    public Dictionary<string,double> Damage { get; }=new();
    public int LastFrame;
    public void OnEvent(CombatEvent e)
    {
        hash.AppendData(Encoding.UTF8.GetBytes(Wire.Serialize(e)+"\n")); LastFrame=e.Frame;
        if (e.Kind==CombatEventKind.Shot) Shots[e.Source]=Shots.GetValueOrDefault(e.Source)+1;
        if (e.Kind==CombatEventKind.AmmoConsumed) Ammo[e.Source]=Ammo.GetValueOrDefault(e.Source)+1;
        if (e.Kind==CombatEventKind.NormalHit) Hits[e.Source]=Hits.GetValueOrDefault(e.Source)+1;
        if (e.Hit is not null) Damage[e.Source]=Damage.GetValueOrDefault(e.Source)+e.Hit.Damage;
    }
    public string Finish()=>Convert.ToHexStringLower(hash.GetHashAndReset());
    public void Dispose()=>hash.Dispose();
}

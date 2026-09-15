using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Engine;
using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Data.Dto;
using Nikke.Simulator.Core.Stats;

namespace Nikke.Data;

public static class VirtualOverload
{
    public static AccountSnapshot Apply(AccountSnapshot original,GameSnapshot game,IReadOnlyList<OlChange> changes)
    {
        var copy=Wire.Read<AccountSnapshot>(Wire.Serialize(original));
        if(changes.Count>60 || changes.Select(c=>(c.CharacterId,c.Slot,c.LineIndex)).Distinct().Count()!=changes.Count)
            throw new ArgumentException("duplicate_or_excessive_ol_changes");
        foreach(var change in changes)
        {
            if(!SnapshotNormalizer.OptionKeys.TryGetValue(change.OptionId,out var key) || !game.OptionSteps.TryGetValue(key,out var values)
                || !values.Contains(Math.Abs(change.Value)) || change.Value==0
                || (change.OptionId is "StatChargeTime" or "StatAccuracyCircle")!=(change.Value<0))throw new ArgumentException("invalid_ol_value");
            var character=copy.Characters.SingleOrDefault(c=>c.CharacterId==change.CharacterId)??throw new ArgumentException("ol_character_missing");
            var eq=character.Equipment.SingleOrDefault(e=>e.Slot==change.Slot)??throw new ArgumentException("ol_slot_missing");
            if(eq.Tier!=10 || change.LineIndex is <1 or >3)throw new ArgumentException("ol_requires_overload_slot");
            int index=eq.Lines.FindIndex(l=>l.LineIndex==change.LineIndex);
            if(index<0 || eq.Lines[index].Presence!="present")throw new ArgumentException("ol_line_missing");
            if(eq.Lines.Any(l=>l.LineIndex!=change.LineIndex && l.Presence=="present" &&
                SnapshotNormalizer.OptionKeys.GetValueOrDefault(l.OptionType??"")==key))throw new ArgumentException("duplicate_ol_option");
            eq.Lines[index]=eq.Lines[index] with {OptionId=change.OptionId,OptionType=change.OptionId,NormalizedValue=change.Value,
                RawValue=null,RawUnit=null,
                Unit="ratio",ValueTier=Array.IndexOf(values,Math.Abs(change.Value))+1,Source="virtual_experiment"};
        }
        return copy;
    }
}

public sealed partial class RuntimeReplayService
{
    public IPreparedExperiment PrepareCompute(AccountSnapshot original,GameSnapshot game,ExperimentRequest request,CalculationService calculation)
    {
        if(request.SnapshotId!=original.Id || original.GameSnapshotId!=game.Id || request.CharacterIds is null || request.Conditions is null || request.CharacterIds.Count!=5 || request.CharacterIds.Distinct().Count()!=5
            || request.OlChanges?.Any(c=>!request.CharacterIds.Contains(c.CharacterId))==true)throw new ArgumentException("compute_requires_five_members");
        var snapshot=VirtualOverload.Apply(original,game,request.OlChanges??[]);
        var conditions=request.Conditions.Deserialize<SkillReplayConditions>(Wire.Json)??throw new ArgumentException("missing_conditions");
        if(conditions.Combat is null)throw new ArgumentException("missing_combat");
        conditions=conditions with {Combat=conditions.Combat with {Trace=false},DamageLog=null};
        var members=new List<SkillReplayMember>();var reports=new List<StatReport>();
        foreach(var id in request.CharacterIds)
        {
            var build=snapshot.Characters.SingleOrDefault(c=>c.CharacterId==id)??throw new ArgumentException("character_missing");
            if(build.FavoriteStage is >0)throw new ArgumentException("favorite_skill_unsupported");
            var report=calculation.Calculate(snapshot,id,400);
            if(report.Status=="incomplete" || report.BasicHit is null || report.NativeStats is null)throw new ArgumentException("incomplete_stats");
            var levels=new Dictionary<string,int>();
            foreach(var (slot,key) in new[]{("skill1","1"),("skill2","2"),("burst","3")})
                levels[slot]=build.Skills.GetValueOrDefault(key)??throw new ArgumentException("skill_level_missing");
            var weapon=catalog["characters"]?[id]?["weapon"]?.Deserialize<WeaponDto>(Wire.Json)??throw new ArgumentException("unsupported_character");
            members.Add(new(new(id,weapon,report.BasicHit,report.PermanentBuffs),report.NativeStats.HP,Loadout(id,levels)));reports.Add(report);
        }
        return PreparedCompute.Create(members,Graph(),conditions,original.Id,game.Id+":"+reports[0].CalculationDataId+":"+runtimeId,request.Phase);
    }
}

// Private frozen input; no references from mutable account/request objects escape into battles.
public sealed class PreparedCompute : IPreparedExperiment
{
    public const string ImplementationVersion="backend-current-skill-run-1";
    private sealed record Payload(ExperimentInput Input,IReadOnlyList<SkillReplayMember> Members,SkillGraph Graph,SkillReplayConditions Conditions);
    private readonly Payload payload;
    public ExperimentInput Input=>payload.Input with {CharacterIds=payload.Input.CharacterIds.ToArray()};
    public string PersistedInput {get;}
    private PreparedCompute(string persisted)
    {PersistedInput=persisted;payload=Wire.Read<Payload>(persisted);
        if(payload.Input.EngineVersion!=ImplementationVersion)throw new InvalidOperationException("engine_version_changed");}
    public static PreparedCompute Restore(string persisted)=>new(persisted);
    public static PreparedCompute Create(IReadOnlyList<SkillReplayMember> members,SkillGraph graph,SkillReplayConditions conditions,string snapshotId,string dataVersion,string phase)
    {
        if(members.Count!=5)throw new ArgumentException("compute_requires_five_members");
        conditions=conditions with {Combat=conditions.Combat with {Trace=false},DamageLog=null};
        var hash=Wire.Hash(Wire.Canonical(JsonSerializer.SerializeToNode(new {members,graph,conditions,snapshotId,dataVersion,level=400,phase,implementation=ImplementationVersion},Wire.Json)));
        var input=new ExperimentInput(hash,snapshotId,dataVersion,ImplementationVersion,
            SkillReplay.Version+":"+TeamBurstController.Version+":"+Nikke.Core.Combat.HitCalculator.Version+":"+conditions.RoundingPolicy,
            members.Select(m=>m.Weapon.CharacterId).ToArray(),400,conditions.Combat.DurationFrames,phase,"summary",
            "fixed:"+conditions.Combat.EnemyDefense.ToString("R",System.Globalization.CultureInfo.InvariantCulture));
        return new(Wire.Serialize(new Payload(input,members,graph,conditions)));
    }
    private sealed class RunRandom : IRandomSource
    {private readonly Random random=new();public double NextDouble()=>random.NextDouble();}
    private sealed class Counter(CancellationToken token) : ICombatEventSink
    {
        public Dictionary<string,long> Reloads {get;}=[];
        public Dictionary<string,long> Bursts {get;}=[];
        public int FullBursts;
        public void OnEvent(CombatEvent e)
        {token.ThrowIfCancellationRequested();if(e.Kind==CombatEventKind.ReloadCompleted)Reloads[e.Source]=Reloads.GetValueOrDefault(e.Source)+1;
            if(e.Kind==CombatEventKind.SkillCast)Bursts[e.Source]=Bursts.GetValueOrDefault(e.Source)+1;
            if(e.Kind==CombatEventKind.FullBurstEntered)FullBursts++;}
    }
    public RunSummary Run(string experimentId,int index,int attempt,CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();var watch=Stopwatch.StartNew();var events=new Counter(cancellationToken);
        var result=SkillReplay.Run(payload.Members,payload.Graph,payload.Conditions,new RunRandom(),events);
        cancellationToken.ThrowIfCancellationRequested();
        return new($"{experimentId}:{index}",attempt,index,experimentId,payload.Input.Fingerprint,"cpu",payload.Input.Phase,result.TotalDamage,
            result.Members.Select(m=>new MemberRunSummary(m.CharacterId,m.Damage,m.Shots,m.Hits,m.CriticalHits,events.Reloads.GetValueOrDefault(m.CharacterId),events.Bursts.GetValueOrDefault(m.CharacterId))).ToArray(),
            events.FullBursts,watch.Elapsed.TotalMilliseconds);
    }
}

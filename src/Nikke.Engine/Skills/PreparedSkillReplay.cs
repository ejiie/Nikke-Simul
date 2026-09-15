using System.Diagnostics;
using System.Text.Json;
using Nikke.Simulator.Core.Stats;

namespace Nikke.Engine.Skills;

public sealed record SkillRunMemberSummary(string CharacterId,double Damage,int Shots,int Hits,int CriticalHits,
    long Reloads,long BurstCasts);
public sealed record SkillRunSummary(string ImplementationVersion,string RulesVersion,double TeamDamage,
    IReadOnlyList<SkillRunMemberSummary> Members,int FullBursts,double ElapsedMilliseconds);

// Private deep copy, no mutable input exposure, no pooling, no per-run serialization.
public sealed class PreparedSkillReplay
{
    public const string Version="cpu-summary.1";
    private sealed record Input(SkillReplayMember[] Members,SkillGraph Graph,SkillReplayConditions Conditions);
    private readonly Input input;
    private PreparedSkillReplay(Input input) => this.input=input;

    public static PreparedSkillReplay Create(IReadOnlyList<SkillReplayMember> members,SkillGraph graph,SkillReplayConditions conditions)
    {
        ArgumentNullException.ThrowIfNull(members); ArgumentNullException.ThrowIfNull(graph); ArgumentNullException.ThrowIfNull(conditions);
        // Full public validation before copying also rejects unsupported source metadata.
        SkillReplay.Validate(members,graph,conditions);
        if(conditions.AutoBurst is not null)
        {
            if(conditions.Casts.Count!=0 || conditions.Combat.FullBurstWindows.Count!=0)
                throw new ArgumentException("Automatic burst cannot be mixed with prescribed casts/windows.");
            _=new TeamBurstController(members,graph,conditions,new RunRandom());
        }
        var copy=JsonSerializer.Deserialize<Input>(JsonSerializer.Serialize(new Input(members.ToArray(),graph,conditions)));
        var compact=copy.Conditions with { DamageLog=null,Combat=copy.Conditions.Combat with { Trace=false },
            AutoBurst=copy.Conditions.AutoBurst is { } auto ? auto with { TimelineLimit=0 } : null };
        return new(copy with { Conditions=compact });
    }

    public SkillRunSummary Run(CancellationToken cancellationToken=default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var watch=Stopwatch.StartNew();
        var counts=new Counts(input.Members);
        var result=SkillReplay.RunValidated(input.Members,input.Graph,input.Conditions,new RunRandom(),counts,
            cancellationToken:cancellationToken,summaryOnly:true);
        cancellationToken.ThrowIfCancellationRequested();
        var members=result.Members.Select(m=>new SkillRunMemberSummary(m.CharacterId,m.Damage,m.Shots,m.Hits,m.CriticalHits,
            counts.Reloads[m.CharacterId],counts.Casts[m.CharacterId])).ToArray();
        return new(Version,result.RulesVersion,result.TotalDamage,Array.AsReadOnly(members),
            result.Connection.FullBurst.Cycle,watch.Elapsed.TotalMilliseconds);
    }
    private sealed class RunRandom : IRandomSource
    {
        private readonly Random random=new();
        public double NextDouble() => random.NextDouble();
    }
    private sealed class Counts : ICombatEventSink
    {
        public readonly Dictionary<string,long> Reloads,Casts;
        public Counts(IEnumerable<SkillReplayMember> members)
        {
            Reloads=members.ToDictionary(m=>m.Weapon.CharacterId,_=>0L);
            Casts=members.ToDictionary(m=>m.Weapon.CharacterId,_=>0L);
        }
        public void OnEvent(CombatEvent e)
        {
            if(e.Kind==CombatEventKind.ReloadCompleted) Reloads[e.Source]++;
            // Duration requests are emitted only by the burst slot, including identical skill IDs in other slots.
            if(e.Kind==CombatEventKind.FullBurstDurationRequested) Casts[e.Source]++;
        }
    }
}

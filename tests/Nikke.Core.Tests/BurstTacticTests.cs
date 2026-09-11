using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Stats;
using static Nikke.Core.Tests.SkillReplayTests;

namespace Nikke.Core.Tests;

public class BurstTacticTests
{
    private static SkillReplayMember M(string id,int step,int cooldown=200,int delay=1)
    {
        var m=Member(id,burst:Active(cooldown:cooldown));
        return m with { Skills=m.Skills with { FullBurstDurationFrames=60,
            BurstConnection=new(step,step+1,delay,100,123,100000,200000,25000,[]) } };
    }
    private static SkillGraph G() => Graph() with { GaugeConstants=new(1000000,new Dictionary<string,long>(),"unverified","raw") };
    private static BurstTactic T() => new() { AllowedCharacterIds=["a","b","c","d"],
        Stage1Priority=["a"],Stage2Priority=["b"],Stage3Priority=["c","d"],Burst3Rotation=["c","d"] };
    private static SkillReplayConditions C(BurstTactic? tactic,int frames=1200) => Conditions(frames) with {
        AutoBurst=new() { Tactic=tactic!,StageDelayMinFrames=1,StageDelayMaxFrames=1 } };
    private static SkillReplayMember[] Members(int cooldown=200) => [M("a",1),M("b",2),M("c",3,cooldown),M("d",3)];
    private static SkillReplayResult Run(BurstTactic t,SkillReplayMember[]? ms=null,int frames=1200)
        => SkillReplay.Run(ms??Members(),G(),C(t,frames));
    [Fact]
    public void Excluded_member_never_casts_even_as_next_ready_fallback_but_still_charges()
    {
        var t=T() with { AllowedCharacterIds=["a","b","c"],Stage3Priority=["c"],Burst3Rotation=["c"] };
        var r=Run(t,Members(4000));
        Assert.DoesNotContain(r.TeamBurst.Timeline,e=>e.Kind=="burst_cast" && e.CharacterId=="d");
        Assert.Single(r.TeamBurst.FullBursts); Assert.True(r.TeamBurst.GeneratedGaugeByMember["d"]>0);
        Assert.Contains(r.TeamBurst.Timeline,e=>e.Kind=="stage_expired");
    }
    [Fact]
    public void First_caster_and_rotation_are_preserved_in_result_and_legacy_default_is_unchanged()
    {
        var t=T() with { FirstBurst3CharacterId="d" };
        var r=Run(t);
        Assert.Equal(new[]{"d","c","d"},r.TeamBurst.FullBursts.Take(3).Select(w=>w.Caster));
        Assert.Equal(t,r.TeamBurst.Options.Tactic);
        var legacy=SkillReplay.Run(Members(),G(),C(null));
        Assert.Null(legacy.TeamBurst.Options.Tactic);
        Assert.All(legacy.TeamBurst.FullBursts,w=>Assert.Equal("c",w.Caster));
        Assert.Equal("p04.team.2",legacy.RulesVersion);
    }
    [Fact]
    public void Each_stage_priority_is_obeyed_without_changing_stage_order()
    {
        var t=new BurstTactic { AllowedCharacterIds=["a","x","b","y","c"],Stage1Priority=["x","a"],
            Stage2Priority=["y","b"],Stage3Priority=["c"],Burst3Rotation=["c"] };
        var r=Run(t,[M("a",1),M("x",1),M("b",2),M("y",2),M("c",3)]);
        Assert.Equal(new[]{"x","y","c"},r.TeamBurst.Timeline.Where(e=>e.Kind=="burst_cast").Take(3).Select(e=>e.CharacterId));
    }
    [Fact]
    public void Wait_preferred_expires_without_advancing_rotation_and_next_ready_uses_fallback()
    {
        var t=T(); var ms=Members(4000);
        var wait=Run(t with { UnavailablePolicy="wait_preferred" },ms);
        Assert.Equal(new[]{"c","d"},wait.TeamBurst.FullBursts.Select(w=>w.Caster));
        Assert.Contains(wait.TeamBurst.Timeline,e=>e.Kind=="stage_expired");
        var fallback=Run(t,ms);
        Assert.True(fallback.TeamBurst.FullBursts.Count>wait.TeamBurst.FullBursts.Count);
        Assert.All(fallback.TeamBurst.FullBursts.Skip(2),w=>Assert.Equal("d",w.Caster));
    }
    [Fact]
    public void Fallback_advances_the_preferred_slot_even_when_caster_is_outside_rotation()
    {
        var t=T() with { AllowedCharacterIds=["a","b","c","d","e"],Stage3Priority=["e","c","d"] };
        var r=Run(t,[M("a",1),M("b",2),M("c",3,4000),M("d",3,0),M("e",3,0)]);
        Assert.Equal(new[]{"c","d","e","d","e","d"},r.TeamBurst.FullBursts.Take(6).Select(w=>w.Caster));
    }
    [Fact]
    public void Invalid_versions_stale_ids_duplicates_wrong_stages_and_incomplete_execution_are_rejected()
    {
        var t=T();
        BurstTactic[] bad=[t with { SchemaVersion=2 },t with { AllowedCharacterIds=["a","b","c","stale"] },
            t with { AllowedCharacterIds=["a","b","c","c"] },t with { Stage1Priority=["b"] },
            t with { Stage2Priority=[] },t with { Stage3Priority=["c"] },t with { Burst3Rotation=[] },
            t with { Burst3Rotation=["c","c"] },t with { Burst3Rotation=["a"] },
            t with { FirstBurst3CharacterId="a" },t with { UnavailablePolicy="invented" },t with { AllowedCharacterIds=null! }];
        foreach(var invalid in bad) Assert.Throws<ArgumentException>(()=>Run(invalid));
        Assert.Throws<ArgumentException>(()=>SkillReplay.Run(Members(),G(),C(t) with { AutoBurst=C(t).AutoBurst with { Burst3Rotation=["c"] } }));
        Assert.Throws<ArgumentException>(()=>SkillReplay.Run(Members(),G(),C(t) with { AutoBurst=C(t).AutoBurst with { UnavailablePolicy="wait_preferred" } }));
        var ms=Members(); ms[0]=ms[0] with { Skills=ms[0].Skills with {
            Slots=new Dictionary<string,SkillDefinition>(ms[0].Skills.Slots) { ["burst"]=Passive() } } };
        Assert.Throws<ArgumentException>(()=>Run(t,ms));
    }
    private sealed class CountingRandom : IRandomSource
    {
        public int Calls;
        public double NextDouble() => (++Calls%10)/10d;
    }
    [Fact]
    public void Logging_does_not_change_sampled_delays_rng_or_cycles_and_all_transitions_keep_max_policy()
    {
        var ms=Members(); ms[0]=M("a",1,delay:30); ms[1]=M("b",2,delay:40); ms[2]=M("c",3,delay:60);
        var c=C(T()) with { DamageLog=new() { CharacterId="c" },AutoBurst=new() { Tactic=T() } };
        c=c with { Combat=c.Combat with { CritMode="sample" } };
        var rng1=new CountingRandom(); var rng2=new CountingRandom();
        var on=SkillReplay.Run(ms,G(),c,rng1); var off=SkillReplay.Run(ms,G(),c with { DamageLog=null! },rng2);
        Assert.Equal(rng1.Calls,rng2.Calls); Assert.Equal(on.TotalDamage,off.TotalDamage);
        Assert.Equal(on.TeamBurst.Timeline,off.TeamBurst.Timeline);
        var casts=on.TeamBurst.Timeline.Where(e=>e.Kind=="burst_cast").Take(3).ToArray();
        Assert.Equal(18,casts[1].Frame-casts[0].Frame); Assert.Equal(24,casts[2].Frame-casts[1].Frame);
        Assert.Equal(36,on.TeamBurst.FullBursts[0].StartFrame-casts[2].Frame);
        Assert.True(on.TeamBurst.FullBursts.Count>1);
        Assert.Contains(on.TeamBurst.Timeline,e=>e.Kind=="gauge" && e.Frame>=on.TeamBurst.FullBursts[0].EndFrame);
        // With zero source application delay the default I->II / II->III samples remain 1..10, III->full is 28.
        ms=[M("a",1,delay:0),M("b",2,delay:0),M("c",3,delay:0),M("d",3,delay:0)];
        var sampled=SkillReplay.Run(ms,G(),c,new CountingRandom());
        foreach(var cycle in sampled.TeamBurst.Timeline.Where(e=>e.Kind=="burst_cast").Chunk(3).Where(x=>x.Length==3))
        {
            Assert.InRange(cycle[1].Frame-cycle[0].Frame,1,10); Assert.InRange(cycle[2].Frame-cycle[1].Frame,1,10);
            var window=sampled.TeamBurst.FullBursts.FirstOrDefault(w=>w.StartFrame>cycle[2].Frame);
            if(window is not null) Assert.Equal(28,window.StartFrame-cycle[2].Frame);
        }
    }
}

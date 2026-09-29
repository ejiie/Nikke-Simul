using System.Text.Json;
using Nikke.Engine;
using Nikke.Engine.Skills;
using static Nikke.Core.Tests.SkillReplayTests;

namespace Nikke.Core.Tests;

public class DefenseSwitchTests
{
    private static SkillReplayMember Billion(string id="a",int[]? roots=null) =>
        Member(id,roots,attack:1_000_030_925);
    private static SkillReplayConditions Auto(string policy="client_f32",int frames=1) => new() {
        RoundingPolicy=policy,Combat=new() { DurationFrames=frames,Trace=true,TraceLimit=20000,
            DefenseMode=DefenseMode.TeamDamageThreshold } };
    private static SkillTrace[] Hits(SkillReplayResult r) => r.Events.Where(e=>e.Kind=="damage").ToArray();
    private static void CheckSummary(SkillReplayMember[] members,SkillGraph graph,SkillReplayResult replay)
    {
        var summary=PreparedSkillReplay.Create(members,graph,replay.Conditions).Run();
        Assert.Equal(replay.TotalDamage,summary.TeamDamage);
        Assert.Equal(replay.Members.Select(m=>m.Damage),summary.Members.Select(m=>m.Damage));
        Assert.Equal(replay.Defense,summary.Defense);
        Assert.Equal(replay.Members.Sum(m=>m.Damage),replay.TotalDamage);
    }

    [Theory]
    [InlineData("client_f32",1)] [InlineData("client_f32",2)]
    [InlineData("legacy_term_floor",1)] [InlineData("legacy_term_floor",2)]
    public void Below_or_equal_threshold_does_not_switch(string policy,int count)
    {
        var members=Enumerable.Range(0,count).Select(i=>Billion(i.ToString())).ToArray();
        var result=SkillReplay.Run(members,Graph(),Auto(policy));
        Assert.Equal(count*1_000_000_000d,result.TotalDamage);
        Assert.Equal(30925,result.Defense.FinalDefense);
        Assert.Null(result.Defense.SwitchAfterHit);
        Assert.DoesNotContain(result.Events,e=>e.Kind=="defense_switch");
        Assert.All(Hits(result),h=>Assert.Equal(30925,h.Hit.Defense));
        CheckSummary(members,Graph(),result);
    }

    [Theory]
    [InlineData("client_f32",999999168d)]
    [InlineData("legacy_term_floor",999999141d)]
    [InlineData("final_round_even",999999141d)]
    [InlineData("nested_floor",999999141d)]
    public void Crossing_hit_uses_old_defense_and_next_member_same_frame_uses_new(string policy,double fourth)
    {
        var members=new[]{Billion("a"),Billion("b"),Billion("c"),Billion("d")};
        var result=SkillReplay.Run(members,Graph(),Auto(policy));
        var hits=Hits(result);
        Assert.Equal(new[]{"a","b","c","d"},hits.Select(h=>h.Source));
        Assert.All(hits,h=>Assert.Equal(1,h.Frame));
        Assert.Equal(new[]{30925d,30925,30925,31784},hits.Select(h=>h.Hit.Defense));
        Assert.Equal(new[]{1e9,1e9,1e9,fourth},hits.Select(h=>h.Value!.Value));
        var change=result.Defense.SwitchAfterHit;
        Assert.Equal(new DefenseSwitch(1,hits[2].Id,3,"c","normal_attack",3e9,30925,31784),change);
        var trace=Assert.Single(result.Events,e=>e.Kind=="defense_switch");
        Assert.Equal(change,trace.DefenseSwitch); Assert.Equal(hits[2].Id,trace.ParentId);
        Assert.True(hits[2].Id<trace.Id && trace.Id<hits[3].Id);
        CheckSummary(members,Graph(),result);
    }

    [Fact]
    public void One_point_above_threshold_switches_and_final_crossing_hit_still_records_transition()
    {
        var members=new[]{Billion("a"),Billion("b"),Member("c",attack:30926)};
        var result=SkillReplay.Run(members,Graph(),Auto());
        Assert.Equal(2_000_000_001d,result.TotalDamage);
        Assert.Equal(2_000_000_001d,result.Defense.SwitchAfterHit.CumulativeDamage);
        Assert.Equal(3,result.Defense.SwitchAfterHit.HitOrdinal);
        Assert.All(Hits(result),h=>Assert.Equal(30925,h.Hit.Defense));
        Assert.Equal(31784,result.Defense.FinalDefense);
        CheckSummary(members,Graph(),result);
    }

    [Fact]
    public void Direct_skill_normal_and_additional_hit_share_one_team_accumulator()
    {
        // Startup direct skill = 1b; normal = 1b; triggered extra = 1b crosses; member b uses new DEF.
        var members=new[]{Billion("a",[10,11]),Billion("b")};
        var graph=Graph(F(10,75,value:10000),F(11,75,31,10000) with { FunctionTarget=4,TimingTriggerValue=1 });
        var result=SkillReplay.Run(members,graph,Auto() with { DamageLog=new() { CharacterId="b" } });
        var hits=Hits(result);
        Assert.Equal(new[]{"function:10","normal_attack","function:11","normal_attack"},hits.Select(h=>h.Effect));
        Assert.Equal(0,hits[0].Frame);
        Assert.Equal(hits[2].Id,result.Defense.SwitchAfterHit.HitTraceId);
        Assert.Equal("function:11",result.Defense.SwitchAfterHit.Effect);
        Assert.Equal(new[]{30925d,30925,30925,31784},hits.Select(h=>h.Hit.Defense));
        Assert.Equal(31784,Assert.Single(result.DamageLog.Entries).Hit.Defense);
        CheckSummary(members,graph,result);
    }

    [Fact]
    public void Startup_skill_crossing_is_recorded_at_frame_zero()
    {
        var member=Billion(roots:[10,11,12]);
        var graph=Graph(F(10,75,value:10000),F(11,75,value:10000),F(12,75,value:10000));
        var result=SkillReplay.Run([member],graph,Auto());
        Assert.Equal(0,result.Defense.SwitchAfterHit.Frame);
        Assert.Equal("function:12",result.Defense.SwitchAfterHit.Effect);
        Assert.Equal(31784,Hits(result)[3].Hit.Defense);
        CheckSummary([member],graph,result);
    }

    [Fact]
    public void Shotgun_pellets_switch_in_existing_resolution_order()
    {
        var member=Billion(); member.Weapon.Weapon.weaponType="SG"; member.Weapon.Weapon.shotCount=4;
        var c=Auto() with { Combat=Auto().Combat with { PelletCoefficientPolicy="per_pellet" },
            DamageLog=new() { CharacterId="a" } };
        var result=SkillReplay.Run([member],Graph(),c);
        var hits=Hits(result);
        Assert.Equal(4,hits.Length);
        Assert.Equal(new[]{30925d,30925,30925,31784},hits.Select(h=>h.Hit.Defense));
        Assert.Equal(hits[2].Id,result.Defense.SwitchAfterHit.HitTraceId);
        Assert.Equal(4,result.DamageLog.Entries.Count);
        CheckSummary([member],Graph(),result);
    }

    [Theory]
    [InlineData(false,20000)] [InlineData(true,1)]
    public void Result_retains_transition_with_trace_disabled_or_truncated(bool trace,int limit)
    {
        var members=new[]{Billion("a"),Billion("b"),Billion("c"),Billion("d")};
        var result=SkillReplay.Run(members,Graph(),Auto() with { Combat=Auto().Combat with { Trace=trace,TraceLimit=limit } });
        Assert.NotNull(result.Defense.SwitchAfterHit);
        Assert.DoesNotContain(result.Events,e=>e.Kind=="defense_switch");
        Assert.Equal(trace,result.TraceTruncated);
        CheckSummary(members,Graph(),result);
    }

    [Theory]
    [InlineData(30925d,4000000000d)] [InlineData(31784d,3999996672d)]
    public void Old_json_without_mode_and_explicit_fixed_reproduce_saved_defense(double defense,double expected)
    {
        var json=new JsonSerializerOptions(JsonSerializerDefaults.Web);
        var combat=JsonSerializer.Deserialize<WeaponReplayConditions>($"{{\"enemyDefense\":{defense},\"durationFrames\":1,\"trace\":true}}",json)!;
        Assert.Equal(DefenseMode.Fixed,combat.DefenseMode);
        var members=new[]{Billion("a"),Billion("b"),Billion("c"),Billion("d")};
        var legacy=SkillReplay.Run(members,Graph(),new() { Combat=combat });
        var explicitFixed=SkillReplay.Run(members,Graph(),new() { Combat=combat with { DefenseMode=DefenseMode.Fixed } });
        Assert.Equal(expected,legacy.TotalDamage);
        Assert.Equal(legacy.TotalDamage,explicitFixed.TotalDamage);
        Assert.Equal(legacy.Events,explicitFixed.Events);
        Assert.Null(legacy.Defense.SwitchAfterHit);
        Assert.All(Hits(legacy),h=>Assert.Equal(defense,h.Hit.Defense));
        CheckSummary(members,Graph(),legacy);
    }

    [Fact]
    public void Prepared_parallel_and_cancelled_runs_do_not_share_threshold_state()
    {
        var members=new[]{Billion("a"),Billion("b"),Billion("c"),Billion("d")};
        var replay=SkillReplay.Run(members,Graph(),Auto(frames:30));
        var prepared=PreparedSkillReplay.Create(members,Graph(),replay.Conditions);
        using var cancel=new CancellationTokenSource(); cancel.Cancel();
        Assert.Throws<OperationCanceledException>(()=>prepared.Run(cancel.Token));
        Parallel.For(0,4,_=> {
            var result=prepared.Run(); Assert.Equal(replay.TotalDamage,result.TeamDamage);
            Assert.Equal(replay.Defense,result.Defense);
        });
        Assert.Null(SkillReplay.Run([Billion()],Graph(),Auto()).Defense.SwitchAfterHit);
    }

    [Fact]
    public void Automatic_burst_execution_and_summary_use_the_same_switch()
    {
        var members=Enumerable.Range(1,3).Select(i=> {
            var m=Billion(i.ToString());
            return m with { Skills=m.Skills with { FullBurstDurationFrames=60,
                BurstConnection=new(i,i+1,1,100,123,100000,200000,25000,[]) } };
        }).ToArray();
        var graph=Graph() with { GaugeConstants=new(1000000,new Dictionary<string,long>(),"fixture","raw") };
        var c=Auto(frames:60) with { AutoBurst=new() { StageDelayMinFrames=1,StageDelayMaxFrames=1 } };
        var replay=SkillReplay.Run(members,graph,c);
        Assert.NotNull(replay.Defense.SwitchAfterHit);
        Assert.NotEmpty(replay.TeamBurst.FullBursts);
        CheckSummary(members,graph,replay);
    }

    [Theory]
    [InlineData(null)] [InlineData("")] [InlineData("automatic")]
    public void Unknown_mode_is_rejected_before_preparing(string? mode)
    {
        var c=Auto() with { Combat=Auto().Combat with { DefenseMode=mode! } };
        Assert.Contains("defense_mode_invalid",Assert.Throws<ArgumentException>(()=>SkillReplay.Run([Billion()],Graph(),c)).Message);
        Assert.Throws<ArgumentException>(()=>PreparedSkillReplay.Create([Billion()],Graph(),c));
    }

    [Fact]
    public void Multi_policy_weapon_reference_rejects_auto_instead_of_silently_using_fixed_defense()
    {
        Assert.Contains("weapon_reference_requires_fixed_defense",Assert.Throws<ArgumentException>(()=>
            WeaponReplay.Run([Billion().Weapon],Auto().Combat)).Message);
    }
}

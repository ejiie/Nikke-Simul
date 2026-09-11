using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Stats;
using static Nikke.Core.Tests.SkillReplayTests;

namespace Nikke.Core.Tests;

// Synthetic execution fixtures. No game observations are inferred from these values.
public class DamageLogTests
{
    private sealed class CountingRandom : IRandomSource
    {
        public int Count;
        public double NextDouble() => (++Count % 13) / 13d;
    }
    private static SkillReplayMember Alice(int[]? roots = null, SkillDefinition? burst = null)
    {
        var m=Member("5004",roots,burst);
        m.Weapon.Weapon.isChargeWeapon=true; m.Weapon.Weapon.weaponType="SR";
        m.Weapon.Weapon.inputType="UP"; m.Weapon.Weapon.chargeTimeSec=1;
        return m with { Weapon=m.Weapon with { Hit=m.Weapon.Hit with { ChargeApplicable=true,ChargeBase=3.5 } } };
    }
    [Theory]
    [InlineData("legacy_term_floor")]
    [InlineData("final_round_even")]
    [InlineData("nested_floor")]
    public void Full_180_seconds_are_complete_and_logging_consumes_no_randomness(string policy)
    {
        var m=Alice(); var c=Conditions(10800) with { RoundingPolicy=policy,DamageLog=new(),
            Combat=Conditions(10800).Combat with { TraceLimit=1,CritMode="sample",ManualCharacterId="5004" } };
        var rng1=new CountingRandom(); var rng2=new CountingRandom();
        var logged=SkillReplay.Run([m],Graph(),c,rng1);
        var plain=SkillReplay.Run([m],Graph(),c with { DamageLog=null! },rng2);
        var log=logged.DamageLog;
        Assert.Null(plain.DamageLog); Assert.True(logged.TraceTruncated); Assert.False(log.Truncated);
        Assert.Equal("complete",log.Status); Assert.Null(log.TruncationReason);
        Assert.Equal(logged.Members[0].Hits,log.EventCount);
        Assert.Equal(logged.Members[0].Damage,log.Entries.Sum(e=>e.Damage));
        Assert.Equal(logged.Members[0].Damage,log.TotalDamage);
        Assert.Equal(log.TotalDamage,log.Entries[^1].CumulativeDamage);
        Assert.True(log.Entries[^1].Frame>10700);
        Assert.Equal(plain.TotalDamage,logged.TotalDamage); Assert.Equal(rng1.Count,rng2.Count);
        Assert.Equal(plain.EventCount,logged.EventCount); Assert.Equal(plain.Members[0].Shots,logged.Members[0].Shots);
        Assert.Equal(plain.Members[0].RemainingAmmo,logged.Members[0].RemainingAmmo);
        Assert.Equal(log.Entries.Count,log.Entries.Select(e=>e.HitId).Distinct().Count());
        Assert.All(log.Entries,e=> { Assert.Equal(e.Frame/60d,e.Seconds); Assert.Equal(policy,e.Calculation.Policy);
            Assert.Equal(e.Damage,e.Calculation.Damage); Assert.Equal(10000,e.ChargeRatioRaw); });
        var noTrace=SkillReplay.Run([m],Graph(),c with { Combat=c.Combat with { Trace=false } },new CountingRandom());
        Assert.Equal(log.Entries.Select(e=>(e.HitId,e.Damage,e.Frame)),noTrace.DamageLog.Entries.Select(e=>(e.HitId,e.Damage,e.Frame)));
    }
    [Theory]
    [InlineData(false,false,315d)]
    [InlineData(true,false,472d)]
    [InlineData(false,true,630d)]
    [InlineData(true,true,787d)]
    public void Resolved_hit_exposes_independent_expected_charge_crit_core_terms(bool crit,bool core,double expected)
    {
        var c=Conditions(65) with { DamageLog=new(),Combat=Conditions(65).Combat with { EnemyDefense=10,Core=core,CritMode=crit?"on":"off" } };
        var log=SkillReplay.Run([Alice()],Graph(),c).DamageLog;
        var hit=Assert.Single(log.Entries);
        Assert.Equal(expected,hit.Damage); // P=(100-10)*3.5=315; individual bonus terms floor.
        Assert.Equal(60,hit.EffectiveChargeFrames); Assert.Equal(60,hit.ActualChargeFrames);
        Assert.True(hit.FullCharge); Assert.Equal(10000,hit.ChargeRatioRaw);
        Assert.Equal(10,hit.Calculation.Terms.Single(t=>t.Name=="effectiveDefense").After);
        Assert.Equal(100,hit.Calculation.Terms.Single(t=>t.Name=="effectiveAttack").After);
    }
    [Fact]
    public void Damage_entries_can_exceed_the_general_20000_trace_limit()
    {
        var m=Member("5004"); m.Weapon.Weapon.weaponType="SG"; m.Weapon.Weapon.shotCount=10;
        m.Weapon.Weapon.maxAmmo=1000;
        var c=Conditions(10800) with { DamageLog=new(),Combat=Conditions(10800).Combat with { PelletCoefficientPolicy="per_pellet" } };
        var r=SkillReplay.Run([m],Graph(),c);
        Assert.True(r.TraceTruncated); Assert.True(r.DamageLog.EventCount>20000); Assert.False(r.DamageLog.Truncated);
        Assert.Equal(r.Members[0].Hits,r.DamageLog.Entries.Count);
        Assert.Equal(r.Members[0].Damage,r.DamageLog.TotalDamage);
    }
    [Fact]
    public void Partial_charge_records_actual_ratio_without_inventing_damage_interpolation()
    {
        var c=Conditions(120) with { DamageLog=new(),Combat=Conditions(120).Combat with { ManualCharacterId="5004",ManualStyle="tap" } };
        var log=SkillReplay.Run([Alice()],Graph(),c,new CountingRandom()).DamageLog;
        Assert.NotEmpty(log.Entries);
        Assert.All(log.Entries,e=> { Assert.False(e.FullCharge); Assert.InRange(e.ChargeRatioRaw!.Value,1,9999);
            Assert.Equal(100,e.Damage); Assert.Equal(1,e.Calculation.Terms.Single(t=>t.Name=="charge").After); });
    }
    [Fact]
    public void Own_burst_and_team_full_burst_are_independent_and_expiry_is_exclusive()
    {
        var buff=F(10,value:5000) with { DurationValue=100 };
        var m=Member("5004",burst:Active(functions:[10]));
        var c=Conditions(140) with { DamageLog=new(),Casts=[new(21,"5004")],
            Combat=Conditions(140).Combat with { FullBurstWindows=[new(61,121)] } };
        var log=SkillReplay.Run([m],Graph(buff),c).DamageLog;
        Assert.Contains(log.Entries,e=>!e.OwnBurstEffectActive && !e.Hit.FullBurst && e.Damage==100);
        Assert.Contains(log.Entries,e=>e.OwnBurstEffectActive && !e.Hit.FullBurst && e.Damage==150);
        Assert.Contains(log.Entries,e=>e.OwnBurstEffectActive && e.Hit.FullBurst && e.Damage==225);
        Assert.Contains(log.Entries,e=>!e.OwnBurstEffectActive && e.Hit.FullBurst && e.Damage==150);
        var before=log.Entries.Single(e=>e.Frame==76); var after=log.Entries.Single(e=>e.Frame==81);
        var snapshot=Assert.Single(before.Buffs); Assert.Equal(21,snapshot.AppliedAtFrame); Assert.Equal(81,snapshot.Effect.ExpiresAt);
        Assert.Equal(before.OwnBurstCastId,snapshot.BurstCastId); Assert.Empty(after.Buffs);
    }
    [Fact]
    public void Pellet_and_additional_hits_share_shot_but_never_become_extra_shots()
    {
        var extra=F(9,75,31,1000) with { TimingTriggerValue=1,FunctionTarget=4 };
        var m=Member("5004",[9]); m.Weapon.Weapon.shotCount=3; m.Weapon.Weapon.weaponType="SG";
        var c=Conditions(6) with { DamageLog=new(),Combat=Conditions(6).Combat with { PelletCoefficientPolicy="per_trigger" } };
        var r=SkillReplay.Run([m],Graph(extra),c); var log=r.DamageLog;
        Assert.Equal(2,r.Members[0].Shots); Assert.Equal(12,log.EventCount);
        Assert.Equal(2,log.Entries.Select(e=>e.ShotId).Distinct().Count());
        Assert.Equal(6,log.Entries.Count(e=>e.Kind==CombatEventKind.AdditionalHit));
        Assert.All(log.Entries,e=> { Assert.NotNull(e.Shot); Assert.Null(e.ChargeRatioRaw); });
        Assert.Equal(r.Members[0].Damage,log.TotalDamage);
    }
    [Fact]
    public void Shot_snapshots_preserve_charge_speed_changes_and_reload_spacing()
    {
        var speed=F(61,61,value:-5000) with { DurationValue=100 };
        var c=Conditions(125) with { DamageLog=new(),Casts=[new(1,"5004")] };
        var log=SkillReplay.Run([Alice(burst:Active(functions:[61]))],Graph(speed),c).DamageLog;
        Assert.Equal(new[]{30,60,120},log.Entries.Select(e=>e.Frame));
        Assert.Equal(new int?[]{30,30,60},log.Entries.Select(e=>e.EffectiveChargeFrames));
        var m=Member("5004"); m.Weapon.Weapon.maxAmmo=1; m.Weapon.Weapon.reloadTimeSec=.5;
        var reload=SkillReplay.Run([m],Graph(),Conditions(64) with { DamageLog=new() }).DamageLog;
        Assert.Equal(new[]{1,32,63},reload.Entries.Select(e=>e.Frame));
        Assert.All(reload.Entries,e=> { Assert.Equal(1,e.Shot.AmmoBefore); Assert.Equal(0,e.Shot.AmmoAfter); });
    }
    [Fact]
    public void Direct_damage_has_no_shot_and_empty_collection_differs_from_missing()
    {
        var direct=Active() with { Skill=Active().Skill with { SkillType=1,
            SkillValueData=[new(2,10000),new(0,0),new(0,0),new(0,0),new(0,0)] } };
        var r=SkillReplay.Run([Alice(burst:direct)],Graph(),Conditions(1) with { DamageLog=new(),Casts=[new(1,"5004")] });
        var hit=Assert.Single(r.DamageLog.Entries); Assert.Equal(CombatEventKind.DirectSkillHit,hit.Kind);
        Assert.Null(hit.ShotId); Assert.Null(hit.Shot); Assert.Null(hit.FullCharge); Assert.False(hit.OwnBurstEffectActive);
        var empty=SkillReplay.Run([Alice()],Graph(),Conditions(1) with { DamageLog=new() }).DamageLog;
        Assert.Empty(empty.Entries); Assert.Equal(0,empty.TotalDamage);
        Assert.Throws<ArgumentException>(()=>SkillReplay.Run([Member()],Graph(),Conditions() with { DamageLog=new() }));
        Assert.Equal("a",SkillReplay.Run([Member()],Graph(),Conditions() with { DamageLog=new() { CharacterId="a" } }).DamageLog.CharacterId);
    }
}

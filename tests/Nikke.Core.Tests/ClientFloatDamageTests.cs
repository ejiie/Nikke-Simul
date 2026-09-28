using System.Text.Json;
using Nikke.Core.Combat;
using Nikke.Core.Stats;
using Nikke.Engine;
using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Stats;
using static Nikke.Core.Tests.SkillReplayTests;

namespace Nikke.Core.Tests;

public class ClientFloatDamageTests
{
    private static readonly ClientDamageRates Neutral = new(1,1,1,1,1,1,1,1,1,0,0,1);

    [Theory]
    [InlineData(.145,1,115)] [InlineData(-.145,1,85)]
    [InlineData(.014,2,103)] [InlineData(-.025,1,97)]
    public void Long_attack_rounds_groups_away_from_zero(double rate,int stacks,long expected)
    {
        Assert.Equal(expected,StatBuffCalculator.ApplyAttack(100,new StatRateBuff[] { new("fixture",rate,stacks) }));
    }

    [Fact]
    public void Source_rates_group_across_sources_and_flat_grants_follow_all_groups()
    {
        var ol=StatRateBuff.FromRaw("OL",140);
        Assert.Equal(140,ol.RawRate10000);
        Assert.Equal(103,StatBuffCalculator.ApplyAttack(100,new[] { ol },new StatRateBuff[] { new("skill",.014) }));
        Assert.Equal(102,StatBuffCalculator.ApplyAttack(100,new[] { ol },new[] { StatRateBuff.FromRaw("skill",130) }));
        Assert.Equal(108,StatBuffCalculator.AddAttackFlat(StatBuffCalculator.ApplyAttack(100,new[] { ol },
            new[] { StatRateBuff.FromRaw("skill",140) }),new[] { StatFlatBuff.FromInteger("caster",5) }));
        // The historic binary64 comparator stays available for transition evidence.
        var c=new HitContext { StatAttack=100,AttackBuffs=[new("OL",.145)] };
        Assert.Equal(114,HitCalculator.Calculate(c,"legacy_term_floor"));
        Assert.Equal(115,HitCalculator.Calculate(c));
    }

    [Fact]
    public void Unsupported_precision_conflicting_raw_and_fractional_stats_are_not_truncated()
    {
        foreach(double rate in new[] { .01401,Math.BitIncrement(.014),double.NaN,double.PositiveInfinity })
            Assert.Throws<ArgumentException>(()=>StatBuffCalculator.ApplyAttack(100,new StatRateBuff[] { new("fixture",rate) }));
        Assert.Throws<ArgumentException>(()=>StatBuffCalculator.ApplyAttack(100,
            new[] { StatRateBuff.FromRaw("source",140) with { Rate=.015 } }));
        Assert.Throws<ArgumentException>(()=>HitCalculator.Calculate(new() { StatAttack=100.5 }));
        Assert.Throws<ArgumentException>(()=>HitCalculator.Calculate(new() { StatAttack=100,Defense=.5 }));
        Assert.Throws<ArgumentException>(()=>StatBuffCalculator.AddAttackFlat(100,new StatFlatBuff[] { new("flat",.5) }));
        Assert.Throws<ArgumentException>(()=>StatBuffCalculator.AddAttackFlat(100,
            new[] { StatFlatBuff.FromInteger("flat",10) with { Amount=11 } }));
        Assert.Throws<ArgumentException>(()=>PreparedSkillReplay.Create([Member()],Graph(),new() {
            Combat=new() { EnemyDefense=.5 } }));
        Assert.Throws<ArgumentException>(()=>PreparedSkillReplay.Create([Member()],Graph(),new() {
            Combat=new() { AttackBuffWindows=[new("a",new("fixture",.01401),1,10)] } }));
    }

    [Fact]
    public void Checked_long_multiply_group_sum_and_flat_sum_overflow_are_detected()
    {
        Assert.Throws<OverflowException>(()=>OverloadProcessor.CalculateFinalBaseStat(long.MaxValue,
            new Dictionary<long,long> { [2]=1 }));
        Assert.Throws<OverflowException>(()=>OverloadProcessor.CalculateFinalBaseStat(1,
            new Dictionary<long,long> { [long.MaxValue]=2 }));
        Assert.Throws<OverflowException>(()=>OverloadProcessor.CalculateFinalBaseStat(long.MaxValue,
            new Dictionary<long,long> { [1]=1 }));
        Assert.Throws<OverflowException>(()=>StatBuffCalculator.AddAttackFlat(long.MaxValue,
            new[] { StatFlatBuff.FromInteger("flat",1) }));
        Assert.Equal(long.MaxValue,StatBuffCalculator.AddAttackFlat(0,new[] { StatFlatBuff.FromInteger("flat",long.MaxValue) }));
    }

    [Fact]
    public void Independent_python_binary32_golden_bits_match_each_formula_stage()
    {
        using var doc=JsonDocument.Parse(File.ReadAllText(Path.Combine(AppContext.BaseDirectory,"Fixtures/client-f32-golden.json")));
        foreach(var item in doc.RootElement.GetProperty("cases").EnumerateArray())
        {
            float[] r=item.GetProperty("rates").EnumerateArray().Select(v=>v.GetSingle()).ToArray();
            var actual=ClientFloatDamage.Calculate(item.GetProperty("attack").GetInt64(),item.GetProperty("defence").GetInt64(),
                new(r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9],r[10],r[11]));
            Assert.Equal(item.GetProperty("baseBits").GetUInt32(),BitConverter.SingleToUInt32Bits(actual.Base));
            Assert.Equal(item.GetProperty("bonusBits").GetUInt32(),BitConverter.SingleToUInt32Bits(actual.Bonus));
            Assert.Equal(item.GetProperty("extraBits").GetUInt32(),BitConverter.SingleToUInt32Bits(actual.Extra));
            Assert.Equal(item.GetProperty("productBits").GetUInt32(),BitConverter.SingleToUInt32Bits(actual.BeforeRound));
            Assert.Equal(item.GetProperty("damage").GetInt64(),actual.Damage);
        }
        Assert.Equal(0x40533333u,BitConverter.SingleToUInt32Bits(ClientFloatDamage.Calculate(100,0,
            Neutral with { CriticalDamageRate=1.5f,CoreDamageRate=2f,BurstDamageRate=1.5f,BonusRangeRate=1.3f }).Bonus));
    }

    [Theory]
    [InlineData(1.5f,2)] [InlineData(2.5f,3)] [InlineData(3.5f,4)]
    [InlineData(-2.5f,1)] [InlineData(.1f,1)] [InlineData(0f,1)]
    public void Float_rounding_and_minimum_are_explicit(float value,long expected) =>
        Assert.Equal(expected,ClientFloatDamage.RoundToDamage(value));

    [Theory]
    [InlineData(0,1,100)] [InlineData(.25,1,75)] [InlineData(0,2,200)]
    [InlineData(.25,2,150)] [InlineData(1,2,1)]
    public void New_neutral_and_non_neutral_inputs_are_consumed(double defenceRatio,double statRatio,long expected)
    {
        var c=new HitContext { StatAttack=100,DefenceRatioRate=defenceRatio,StatDamageRatio=statRatio };
        Assert.Equal(expected,HitCalculator.CalculateClient(c).Damage);
        Assert.Equal(expected,HitCalculator.Evaluate(c).Damage);
    }

    [Fact]
    public void Non_finite_intermediate_and_final_long_boundaries_are_detected()
    {
        foreach(var field in typeof(HitContext).GetProperties().Where(p=>p.PropertyType==typeof(double)))
        foreach(double bad in new[] { double.NaN,double.PositiveInfinity,double.NegativeInfinity })
        {
            var c=new HitContext { StatAttack=100 }; field.SetValue(c,bad);
            Assert.Throws<ArgumentException>(()=>HitCalculator.Calculate(c));
        }
        Assert.Throws<ArgumentException>(()=>ClientFloatDamage.Calculate(1,0,Neutral with { DamageRatio=float.NaN }));
        Assert.Throws<ArgumentException>(()=>ClientFloatDamage.Calculate(1,0,Neutral with { DamageRatio=float.MaxValue,StatDamageRatio=2 }));
        Assert.Throws<OverflowException>(()=>ClientFloatDamage.Calculate(long.MaxValue,0,Neutral));
        Assert.Throws<OverflowException>(()=>ClientFloatDamage.RoundToDamage(9223372036854775808f));
        Assert.Equal(9223371487098961920L,ClientFloatDamage.RoundToDamage(MathF.BitDecrement(9223372036854775808f)));
        Assert.Throws<ArgumentException>(()=>HitCalculator.Calculate(new() { StatAttack=100,DefenceRatioRate=1.01 }));
        Assert.Throws<ArgumentException>(()=>HitCalculator.Calculate(new() { StatAttack=100,StatDamageRatio=-1 }));
    }

    [Fact]
    public void Provisional_mapping_keeps_conditional_parts_and_true_defence_zero()
    {
        var c=new HitContext { StatAttack=100,Defense=50,AttackDamage=.2,PierceDamage=.3,PartsDamage=.5 };
        Assert.Equal(60,HitCalculator.Calculate(c));
        Assert.Equal(75,HitCalculator.Calculate(c with { Pierce=true }));
        Assert.Equal(85,HitCalculator.Calculate(c with { Parts=true }));
        Assert.Equal(100,HitCalculator.Calculate(c with { Pierce=true,Parts=true }));
        Assert.Equal(120,HitCalculator.Calculate(c with { DamageType="true" }));
        Assert.Equal(72,HitCalculator.Calculate(c with { DamageType="distribution",DistributionDamage=.2 }));
    }

    [Fact]
    public void Default_replay_summary_and_damage_log_use_the_client_policy()
    {
        var member=Member() with { Weapon=Member().Weapon with { Hit=new() { StatAttack=1,Coefficient=2.5 } } };
        var c=new SkillReplayConditions { Combat=new() { DurationFrames=60 },DamageLog=new() { CharacterId="a" } };
        Assert.Equal("client_f32",c.RoundingPolicy);
        var replay=SkillReplay.Run([member],Graph(),c);
        var prepared=PreparedSkillReplay.Create([member],Graph(),c);
        var summary=prepared.Run();
        Assert.Equal(replay.Members[0].Hits*3,replay.TotalDamage);
        Assert.Equal(replay.TotalDamage,summary.TeamDamage);
        Assert.NotEmpty(replay.DamageLog.Entries);
        Assert.All(replay.DamageLog.Entries,e=>Assert.Equal("client_f32",e.Calculation.Policy));
        Parallel.For(0,8,new ParallelOptions { MaxDegreeOfParallelism=2 },_=>
            Assert.Equal(summary.TeamDamage,prepared.Run().TeamDamage));
        Assert.Equal("p03.skills.3-client-f32",summary.RulesVersion);
        var audit=HitCalculator.Compare(member.Weapon.Hit);
        Assert.Equal(4,audit.Candidates.Count);
        Assert.Equal(3,audit.Candidates.Single(r=>r.Policy=="client_f32").Damage);
        var weapon=WeaponReplay.Run([member.Weapon],c.Combat);
        Assert.Equal(weapon.Members[0].Hits*3,weapon.TotalDamage["client_f32"]);
        Assert.Equal(weapon.Members[0].Hits*2,weapon.TotalDamage["final_round_even"]);
    }

    [Fact]
    public void Caster_flat_attack_uses_long_rounding_without_reapplying_recipient_rates()
    {
        var f=F(10,value:1450) with { FunctionStandard=1,FunctionTarget=2,DurationType=3 };
        var source=Member("source",[10]); var target=Member("target");
        var replay=SkillReplay.Run([source,target],Graph(f),new() { Combat=new() { DurationFrames=1,Trace=true } });
        Assert.Equal(115,replay.Members.Single(m=>m.CharacterId=="source").Damage);
        Assert.Equal(115,replay.Members.Single(m=>m.CharacterId=="target").Damage);
        Assert.Equal(15,Assert.Single(replay.Events.First(e=>e.Kind=="damage" && e.Source=="target").Hit.AttackFlatBuffs).ExactAmount);
    }
}

using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Stats;
using static Nikke.Core.Tests.SkillReplayTests;
namespace Nikke.Core.Tests;

public class TeamBurstTests
{
    private static SkillReplayMember M(string id, int step, long energy=100000, int durationCs=100, int cooldown=200)
    {
        var m=Member(id,burst:Active(cooldown:cooldown));
        return m with { Skills=m.Skills with { FullBurstDurationFrames=SkillUnits.Frames(durationCs),
            BurstConnection=new(step,step+1,1,durationCs,123,energy,energy*2,25000,[]) } };
    }
    private static SkillGraph G(params SkillFunction[] functions) => Graph(functions) with {
        GaugeConstants=new(1000000,new Dictionary<string,long>{{"ulti_gauge_shot_hit",4}},"unverified","raw") };
    private static SkillReplayConditions C(int frames=600) => Conditions(frames) with {
        AutoBurst=new() { StageDelayMinFrames=1,StageDelayMaxFrames=1,FullBurstEntryDelayFrames=28 } };
    private static SkillReplayResult Run(SkillReplayMember[] ms, SkillReplayConditions c, SkillGraph? g=null)
        => SkillReplay.Run(ms,g??G(),c);
    [Fact]
    public void Five_members_repeat_real_gauge_cycles_and_obey_cast_order_and_cooldowns()
    {
        var r=Run([M("a",1),M("b",2),M("c",3),M("d",3),M("e",3)],C(10800));
        var t=r.TeamBurst; Assert.True(t.FullBursts.Count>20); Assert.False(t.GameVerified);
        var casts=t.Timeline.Where(e=>e.Kind=="burst_cast").ToArray();
        foreach(var cycle in casts.Chunk(3).Where(c=>c.Length==3)) Assert.Equal(new[]{1,2,3},cycle.Select(e=>e.Step));
        foreach(var group in casts.GroupBy(e=>e.CharacterId))
            foreach(var pair in group.Zip(group.Skip(1))) Assert.True(pair.Second.Frame>=pair.First.ReadyAtFrame);
        foreach(var w in t.FullBursts)
        {
            Assert.Equal(60,w.PlannedEndFrame-w.StartFrame);
            Assert.DoesNotContain(t.Timeline,e=>e.Kind=="gauge" && e.Frame>=w.StartFrame && e.Frame<(w.EndFrame??w.PlannedEndFrame));
            Assert.Equal(28,w.StartFrame-casts.Last(e=>e.Step==3 && e.Frame<w.StartFrame).Frame);
        }
        Assert.Equal(r.TotalDamage,r.Members.Sum(m=>m.Damage));
        Assert.True(t.FullBursts.Sum(w=>w.MemberDamage.Values.Sum())>0);
    }
    [Fact]
    public void Pellets_charge_once_and_additional_damage_and_ammo_events_do_not_charge()
    {
        var extra=F(9,75,31,1000) with { TimingTriggerValue=1,FunctionTarget=4 };
        var m=M("a",3,10); m.Weapon.Weapon.shotCount=10; m.Weapon.Weapon.weaponType="SG";
        m=m with { Skills=m.Skills with { Slots=new Dictionary<string,SkillDefinition>(m.Skills.Slots) { ["skill1"]=Passive(9) } } };
        var r=Run([m],C(6) with { Combat=C(6).Combat with { PelletCoefficientPolicy="per_trigger" } },G(extra));
        Assert.Equal(20,r.Members[0].Hits);
        Assert.Equal(400,r.TeamBurst.GeneratedGaugeByMember["a"]);
        Assert.Equal(20,r.TeamBurst.Timeline.Count(e=>e.Kind=="gauge"));
        Assert.True(r.Members[0].Effects["function:9"]>0);
    }
    [Fact]
    public void Gauge_saturates_without_overflow_and_missing_stage_is_reported()
    {
        var r=Run([M("c",3,700000)],C(90));
        Assert.Equal(1000000,r.TeamBurst.AcceptedGaugeByMember["c"]);
        Assert.Equal(1400000,r.TeamBurst.GeneratedGaugeByMember["c"]);
        Assert.Empty(r.TeamBurst.FullBursts); Assert.Equal("missing_stage_1",r.TeamBurst.WaitingReason);
        Assert.Single(r.TeamBurst.Timeline,e=>e.Kind=="gauge");
    }
    [Fact]
    public void Missing_next_stage_expires_using_source_duration_and_recharges()
    {
        var r=Run([M("a",1)],C(300));
        Assert.Empty(r.TeamBurst.FullBursts);
        Assert.True(r.TeamBurst.Timeline.Count(e=>e.Kind=="stage_expired")>=2);
        Assert.True(r.TeamBurst.Timeline.Count(e=>e.Kind=="gauge_ready")>=3);
    }
    [Fact]
    public void Third_stage_rotation_and_unavailable_fallback_are_explicit()
    {
        var ms=new[]{M("a",1),M("b",2),M("c",3,cooldown:4000),M("d",3)};
        var c=C(600) with { AutoBurst=C().AutoBurst with { Burst3Rotation=new[]{"d","c"} } };
        var r=Run(ms,c);
        Assert.Equal(new[]{"d","c","d"},r.TeamBurst.FullBursts.Take(3).Select(w=>w.Caster));
        var wait=Run(ms,c with { AutoBurst=c.AutoBurst with { Burst3Rotation=new[]{"c"},UnavailablePolicy="wait_preferred" } });
        Assert.Single(wait.TeamBurst.FullBursts); Assert.DoesNotContain(wait.TeamBurst.Timeline,e=>e.Kind=="burst_cast"&&e.CharacterId=="d");
    }
    [Fact]
    public void Full_burst_exit_cooldown_effect_is_seen_without_a_second_cooldown_clock()
    {
        var cd=F(7,83,43,-1000) with { FunctionValueType=1,FunctionTarget=1 };
        var a=M("a",1,cooldown:1000);
        var changed=a with { Skills=a.Skills with { Slots=new Dictionary<string,SkillDefinition>(a.Skills.Slots) { ["skill1"]=Passive(7) } } };
        var before=Run([a,M("b",2),M("c",3)],C(400));
        var after=Run([changed,M("b",2),M("c",3)],C(400),G(cd));
        Assert.Single(before.TeamBurst.FullBursts);
        Assert.True(after.TeamBurst.FullBursts.Count>1);
    }
    [Fact]
    public void Modernia_like_mode_needs_no_replacement_gauge_and_returns_to_base_before_recharge()
    {
        var m=M("m",3,durationCs:1500,cooldown:2000);
        var mode=Active(cooldown:2000) with { Skill=Active(cooldown:2000).Skill with { SkillType=7,DurationType=1,DurationValue=1500,
            SkillValueData=[new(2,2000),new(1,3600),new(1,999),new(0,0),new(1,1)] } };
        m=m with { Skills=m.Skills with { BurstConnection=m.Skills.BurstConnection with { UnresolvedReplacementShotIds=new[]{999} },
            Slots=new Dictionary<string,SkillDefinition>(m.Skills.Slots) { ["burst"]=mode } } };
        var r=Run([M("a",1),M("b",2),m],C(2100));
        Assert.True(r.TeamBurst.FullBursts.Count>=2);
        Assert.All(r.TeamBurst.FullBursts,w=>Assert.Equal(900,w.PlannedEndFrame-w.StartFrame));
        var first=r.TeamBurst.FullBursts[0]; Assert.NotNull(first.EndFrame);
        Assert.Contains(r.TeamBurst.Timeline,e=>e.Kind=="gauge"&&e.CharacterId=="m"&&e.Frame>=first.EndFrame);
    }
    [Fact]
    public void Trace_truncation_never_changes_execution_and_prescribed_inputs_are_rejected()
    {
        var ms=new[]{M("a",1),M("b",2),M("c",3)};
        var a=Run(ms,C());
        var b=Run(ms,C() with { Combat=C().Combat with { Trace=false }, AutoBurst=C().AutoBurst with { TimelineLimit=0 } });
        Assert.Equal(a.TotalDamage,b.TotalDamage); Assert.Equal(a.TeamBurst.FullBurstFrames,b.TeamBurst.FullBurstFrames);
        Assert.Equal(a.TeamBurst.GeneratedGaugeByMember,b.TeamBurst.GeneratedGaugeByMember);
        Assert.True(b.TeamBurst.TimelineTruncated); Assert.Empty(b.TeamBurst.Timeline);
        Assert.Throws<ArgumentException>(()=>Run(ms,C() with { Casts=[new(1,"a")] }));
    }
    [Theory]
    [InlineData(false,35000,196000)]
    [InlineData(true,35000,196000)]
    [InlineData(false,25000,140000)]
    [InlineData(true,25000,140000)]
    [InlineData(false,20000,112000)]
    [InlineData(true,20000,112000)]
    [InlineData(false,15000,84000)]
    [InlineData(true,15000,84000)]
    public void Full_charge_uses_character_source_multiplier_for_auto_and_manual(bool manual,long full,long expected)
    {
        var m=M("a",3,28000); var weapon=m.Weapon.Weapon;
        weapon.weaponType="SR"; weapon.isChargeWeapon=true; weapon.inputType="UP"; weapon.chargeTimeSec=.1;
        m=m with { Skills=m.Skills with { BurstConnection=m.Skills.BurstConnection with { FullChargeEnergyRaw=full } },
            Weapon=m.Weapon with { Hit=m.Weapon.Hit with { ChargeApplicable=true,ChargeBase=9 } } };
        var r=Run([m],C(90) with { Combat=C(90).Combat with { ManualCharacterId=manual?"a":"" } });
        Assert.All(r.TeamBurst.Timeline.Where(e=>e.Kind=="gauge"),e=>Assert.Equal(expected,e.RequestedRaw));
        Assert.Contains(r.TeamBurst.Timeline,e=>e.Kind=="gauge");
    }
    [Fact]
    public void Partial_charge_does_not_receive_full_charge_multiplier_or_old_interpolation()
    {
        var m=M("a",3,28000);m.Weapon.Weapon.weaponType="SR";m.Weapon.Weapon.isChargeWeapon=true;
        m.Weapon.Weapon.inputType="UP";m.Weapon.Weapon.chargeTimeSec=1.5;
        m=m with { Skills=m.Skills with { BurstConnection=m.Skills.BurstConnection with { FullChargeEnergyRaw=35000 } },
            Weapon=m.Weapon with { Hit=m.Weapon.Hit with { ChargeApplicable=true } } };
        var r=Run([m],C(90) with { Combat=C(90).Combat with { ManualCharacterId="a",ManualStyle="tap" } });
        Assert.Contains(r.TeamBurst.Timeline,e=>e.Kind=="gauge");
        Assert.All(r.TeamBurst.Timeline.Where(e=>e.Kind=="gauge"),e=>Assert.Equal(56000,e.RequestedRaw));
        Assert.Throws<ArgumentException>(()=>Run([m with { Skills=m.Skills with { BurstConnection=m.Skills.BurstConnection with { FullChargeEnergyRaw=0 } } }],C()));
        Assert.Throws<ArgumentException>(()=>Run([m],C() with { AutoBurst=C().AutoBurst with { GaugeModel="einkk_normal_hit_v1" } }));
    }

    [Fact]
    public void Magazine_and_charge_speed_change_gauge_timing_through_the_actual_gun()
    {
        var small=M("a",1,10000);small.Weapon.Weapon.maxAmmo=1;small.Weapon.Weapon.reloadTimeSec=2;
        var large=M("a",1,10000);large.Weapon.Weapon.maxAmmo=100;
        var slow=Run([small],C(10800));var fast=Run([large],C(10800));
        Assert.True(fast.TeamBurst.Timeline.First(e=>e.Kind=="gauge_ready").Frame<slow.TeamBurst.Timeline.First(e=>e.Kind=="gauge_ready").Frame);
        var charged=M("s",3,100000);
        charged.Weapon.Weapon.weaponType="SR";charged.Weapon.Weapon.isChargeWeapon=true;
        charged.Weapon.Weapon.inputType="UP";charged.Weapon.Weapon.chargeTimeSec=1;
        charged=charged with { Weapon=charged.Weapon with { Hit=charged.Weapon.Hit with { ChargeApplicable=true } } };
        var initial=Run([charged],C(900));
        charged.Weapon.Weapon.chargeTimeSec=.5;
        var quicker=Run([charged],C(900));
        Assert.True(quicker.TeamBurst.Timeline.First(e=>e.Kind=="gauge_ready").Frame<initial.TeamBurst.Timeline.First(e=>e.Kind=="gauge_ready").Frame);
    }

}

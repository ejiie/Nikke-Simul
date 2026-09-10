using Nikke.Core.Combat;
using Nikke.Core.Stats;
using Nikke.Engine;
using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Data.Dto;

namespace Nikke.Core.Tests;

// Synthetic semantic fixtures, not copied game tables or claims about measured damage.
public class SkillReplayTests
{
    internal static SkillFunction F(int id, int type=1, int timing=0, long value=1000) => new() {
        Id=id,GroupId=id,FunctionType=type,FunctionStandard=2,FunctionTarget=1,FunctionValueType=2,FunctionValue=value,
        TimingTriggerType=timing,TimingTriggerStandard=1,DurationType=1,DurationValue=100,FullCount=1,KeepingType=2 };
    internal static SkillDefinition Passive(params int[] ids) => new() { SkillId=1,FunctionIds=ids };
    internal static SkillDefinition Active(int id=10100, int[]? functions=null, int cooldown=0) => new() {
        SkillId=id, FunctionPhases=new Dictionary<string,int[]> { ["after_use"]=functions??[] },
        Skill=new() { SkillType=8,PreferTarget=17,AttackType=4,SkillCooltime=cooldown,
            SkillValueData=[new(0,0),new(1,1),new(1,1),new(0,0),new(0,0)] } };
    internal static SkillReplayMember Member(string id="a", int[]? roots=null, SkillDefinition? burst=null,
        double attack=100, double hp=1000, string squad="test") => new(
        new WeaponReplayMember(id,new WeaponDto { weaponType="AR",inputType="DOWN",fireType="Instant",fireRate=12,endFireRate=12,
            maxAmmo=100,reloadTimeSec=1,reloadBulletRate=1,shotCount=1,muzzleCount=1 },new HitContext { StatAttack=attack },new()),hp,
        new(squad,new Dictionary<string,int> { ["skill1"]=10,["skill2"]=10,["burst"]=10 },
            new Dictionary<string,SkillDefinition> { ["skill1"]=Passive(roots??[]),["skill2"]=Passive(),["burst"]=burst??Active() }));
    internal static SkillGraph Graph(params SkillFunction[] fs) => new(fs.ToDictionary(f=>f.Id),new Dictionary<int,SkillDefinition>());
    internal static SkillReplayConditions Conditions(int frames=30) => new() { RoundingPolicy="legacy_term_floor",
        Combat=new() { DurationFrames=frames,Trace=true,TraceLimit=20000 } };
    private static SkillReplayResult Run(SkillReplayMember[] ms,SkillGraph g,SkillReplayConditions? c=null) => SkillReplay.Run(ms,g,c??Conditions());

    [Fact]
    public void Caster_attack_is_flat_for_other_recipients_and_never_compounds_OL()
    {
        var aura=F(10, timing:16,value:1400) with { FunctionStandard=1,FunctionTarget=2,DurationType=3,DurationValue=1,
            KeepingType=3,StatusTriggerType=13,StatusTriggerStandard=1,StatusTriggerValue=7000 };
        var caster=Member("a",[10],attack:500);
        caster=caster with { Weapon=caster.Weapon with { Hit=caster.Weapon.Hit with { AttackBuffs=[new("OL",.2)] } } };
        var recipient=Member("b");
        recipient=recipient with { Weapon=recipient.Weapon with { Hit=recipient.Weapon.Hit with { AttackBuffs=[new("OL",.2)] } } };
        var result=Run([caster,recipient],Graph(aura),Conditions(21) with {
            Combat=Conditions(21).Combat with { AttackBuffWindows=[new("b",new("other",.5),1,22)] },
            HpObservations=[new(20,"a",.6)] });
        var first=result.Events.First(e=>e.Kind=="damage" && e.Source=="b");
        Assert.Equal(240,first.Value); // 100 + 20 OL + 50 recipient skill + 500*0.14.
        Assert.Equal(70,Assert.Single(first.Hit.AttackFlatBuffs).Amount);
        Assert.Equal(670,result.Events.First(e=>e.Kind=="damage" && e.Source=="a").Value);
        Assert.Equal(170,result.Events.First(e=>e.Kind=="damage" && e.Source=="b" && e.Frame>=20).Value);
        Assert.DoesNotContain(result.ActiveEffects,e=>e.FunctionId==10);
        Assert.Equal(100,recipient.Weapon.Hit.StatAttack);
    }

    [Fact]
    public void Linked_functions_preserve_targets_and_do_not_repeat_per_recipient()
    {
        var one=F(1,timing:22) with { FunctionTarget=2,TimingTriggerValue=4,ConnectedFunction=[2] };
        var two=F(2,51,value:1000) with { FunctionTarget=2,FunctionValueType=1,FullCount=5 };
        var r=Run([Member("a",[1]),Member("b")],Graph(one,two),Conditions(1) with {
            Combat=Conditions(1).Combat with { FullBurstWindows=[new(1,2)],CritMode="on" } });
        Assert.All(r.ActiveEffects.Where(e=>e.FunctionId==2),e=>Assert.Equal(1,e.Stacks));
        Assert.Equal(2,r.Events.Count(e=>e.Kind=="buff_on" && e.FunctionId==2));
        Assert.Equal(.6,r.Events.First(e=>e.Kind=="damage").Hit.CritBonus,8);
    }

    [Fact]
    public void Skill_use_matches_group_id_and_previous_tiers_repeat_in_source_order()
    {
        var high=F(30,timing:30,value:3000) with { TimingTriggerValue=101,StatusTriggerType=18,StatusTriggerStandard=1,StatusTriggerValue=21 };
        var mid=F(20,51,30,1000) with { TimingTriggerValue=101,StatusTriggerType=18,StatusTriggerStandard=1,StatusTriggerValue=11,ConnectedFunction=[21] };
        var low=F(10,14,30,2000) with { TimingTriggerValue=101,ConnectedFunction=[11] };
        var marker1=F(11,0) with { DurationType=3 }; var marker2=F(21,0) with { DurationType=3 };
        var r=Run([Member(roots:[30,20,10])],Graph(high,mid,low,marker1,marker2),Conditions(11) with { Casts=[new(1,"a"),new(6,"a"),new(11,"a")] });
        Assert.Equal(new[]{11},r.Events.Where(e=>e.Kind=="function" && e.FunctionId==30).Select(e=>e.Frame));
        Assert.Equal(new[]{6,11},r.Events.Where(e=>e.Kind=="function" && e.FunctionId==20).Select(e=>e.Frame));
        Assert.Equal(new[]{1,6,11},r.Events.Where(e=>e.Kind=="function" && e.FunctionId==10).Select(e=>e.Frame));
    }

    [Fact]
    public void Additional_damage_does_not_reenter_normal_hit_counter_and_stacks_cap()
    {
        var extra=F(1,75,31,1000) with { TimingTriggerValue=1,FunctionTarget=4 };
        var crit=F(2,51,31,1000) with { TimingTriggerValue=2,FullCount=2,ConnectedFunction=[3] };
        var ammo=F(3,14,31,-1000) with { TimingTriggerValue=2,FullCount=2 };
        var r=Run([Member(roots:[1,2])],Graph(extra,crit,ammo),Conditions(26));
        Assert.Equal(6,r.Members[0].Shots); Assert.Equal(6,r.Members[0].Hits);
        Assert.Equal(60,r.Members[0].Effects["function:1"]);
        Assert.Equal(12,r.Events.Count(e=>e.Kind=="damage"));
        Assert.Equal(2,r.ActiveEffects.Single(e=>e.FunctionId==2).Stacks);
        Assert.Equal(2,r.ActiveEffects.Single(e=>e.FunctionId==3).Stacks);
        Assert.Equal(80,r.Members[0].MaxAmmo);
    }

    [Fact]
    public void Top_attack_selection_and_caster_charge_time_grants_are_preserved()
    {
        var call=F(1,72,22,99) with { FunctionValueType=1,TimingTriggerValue=4 };
        var charge=F(2,61,value:-1000) with { FunctionStandard=1,FunctionTarget=4,ConnectedFunction=[3] };
        var add=F(3,11,value:700) with { FunctionValueType=1,FunctionTarget=4 };
        var sk=Active(99,[2]) with { Skill=Active().Skill with { SkillValueData=[new(0,0),new(1,2),new(1,10000),new(0,0),new(0,0)] } };
        var caster=Member("a",[1],attack:50);
        var cw=caster.Weapon.Weapon; cw.chargeTimeSec=1.5; cw.isChargeWeapon=true; cw.weaponType="SR"; cw.inputType="UP";
        caster=caster with { Weapon=caster.Weapon with { Hit=caster.Weapon.Hit with { ChargeApplicable=true,ChargeBase=2.5 } } };
        var g=Graph(call,charge,add) with { CharacterSkills=new Dictionary<int,SkillDefinition>{{99,sk}} };
        var buffed=Member("c",attack:200);
        buffed=buffed with { Weapon=buffed.Weapon with { Hit=buffed.Weapon.Hit with { AttackBuffs=[new("OL",1)] } } };
        var r=Run([caster,Member("b",attack:300),buffed],g,Conditions(1) with {
            Combat=Conditions(1).Combat with { FullBurstWindows=[new(1,2)] } });
        Assert.Equal(new[]{"c","b"},r.ActiveEffects.Where(e=>e.FunctionId==2).Select(e=>e.Target));
        Assert.All(r.ActiveEffects.Where(e=>e.FunctionId==3),e=>Assert.Equal(.07,e.Value));
        Assert.DoesNotContain(r.ActiveEffects,e=>e.FunctionId==2 && e.Target=="a");
    }

    [Fact]
    public void Enemy_damage_taken_is_applied_to_all_attackers_and_expires_before_hit()
    {
        var debuff=F(1,42,value:-5000) with { FunctionTarget=3,DurationValue=25 };
        var r=Run([Member("a",burst:Active(functions:[1])),Member("b")],Graph(debuff),Conditions(16) with { Casts=[new(1,"a")] });
        Assert.Equal(150,r.Events.First(e=>e.Kind=="damage" && e.Source=="b").Value);
        Assert.Equal(100,r.Events.Single(e=>e.Kind=="damage" && e.Source=="b" && e.Frame==16).Value);
    }

    [Fact]
    public void Unlimited_ammo_is_a_duration_and_weapon_mode_restores_without_refilling()
    {
        var unlimited=F(1,5,value:0) with { DurationValue=20 };
        var burst=Active(999,[1]) with { Skill=Active().Skill with { SkillType=7,DurationType=1,DurationValue=20,
            SkillValueData=[new(2,2000),new(1,3600),new(1,123),new(0,0),new(1,1)] } };
        var r=Run([Member(burst:burst)],Graph(unlimited),Conditions(26) with { Casts=[new(6,"a")] });
        Assert.Contains(r.Events,e=>e.Kind=="weapon_change" && e.Value==123);
        Assert.Contains(r.Events,e=>e.Kind=="weapon_restored" && e.Frame==18);
        var modeShots=r.Events.Where(e=>e.Kind=="shot" && e.Frame>=6 && e.Frame<18).ToArray();
        Assert.True(modeShots.Length>5);
        Assert.All(modeShots,e=>Assert.Equal(99,e.Value));
        Assert.True(r.Members[0].AmmoConsumed<r.Members[0].Shots);
        Assert.Contains("skill:999:weapon",r.Members[0].Effects.Keys);
    }

    [Fact]
    public void Ammo_consume_counts_trigger_per_round_not_per_pellet()
    {
        var marker=F(1,0,3) with { TimingTriggerValue=2 };
        var member=Member(roots:[1]); member.Weapon.Weapon.weaponType="SG"; member.Weapon.Weapon.shotCount=10;
        var r=Run([member],Graph(marker),Conditions(6) with { Combat=Conditions(6).Combat with { PelletCoefficientPolicy="per_trigger" } });
        Assert.Equal(20,r.Members[0].Hits); Assert.Equal(2,r.Members[0].AmmoConsumed);
        Assert.Single(r.Events,e=>e.Kind=="function" && e.FunctionId==1);
    }

    [Fact]
    public void Healing_ticks_use_caster_max_hp_and_can_switch_hp_condition()
    {
        var heal=F(1,2,value:1000) with { FunctionStandard=1,FunctionTarget=2,DurationValue=200 };
        var aura=F(2,timing:16,value:1000) with { StatusTriggerType=13,StatusTriggerStandard=1,StatusTriggerValue=7000,DurationType=3,KeepingType=3 };
        var r=Run([Member("a",burst:Active(functions:[1]),hp:2000),Member("b",[2],hp:1000)],Graph(heal,aura),Conditions(121) with {
            InitialHpRatios=new Dictionary<string,double>{{"b",.5}},Casts=[new(1,"a")] });
        Assert.Equal(900,r.Members.Single(m=>m.CharacterId=="b").Hp);
        Assert.Equal(new[]{61,121},r.Events.Where(e=>e.Kind=="heal" && e.Target=="b").Select(e=>e.Frame));
        Assert.Contains(r.Events,e=>e.Kind=="buff_on" && e.FunctionId==2 && e.Frame==121);
    }

    [Fact]
    public void Same_squad_cooldown_reduction_requires_the_other_member()
    {
        var reduce=F(1,83,43,-200) with { FunctionStandard=1,FunctionValueType=1,
            StatusTriggerType=11,StatusTriggerStandard=1,StatusTriggerValue=2 };
        var c=Conditions(100) with { Casts=[new(1,"a")],Combat=Conditions(100).Combat with { FullBurstWindows=[new(1,61)] } };
        var alone=Run([Member(roots:[1],burst:Active(cooldown:1000))],Graph(reduce),c);
        var together=Run([Member(roots:[1],burst:Active(cooldown:1000)),Member("b")],Graph(reduce),c);
        Assert.Equal(601,alone.Members[0].CooldownReadyFrames["burst"]);
        Assert.Equal(481,together.Members[0].CooldownReadyFrames["burst"]);
    }

    [Fact]
    public void Trace_truncation_does_not_change_skill_execution_or_damage_totals()
    {
        var f=F(1,75,31) with { TimingTriggerValue=1,FunctionTarget=4 };
        var full=Run([Member(roots:[1])],Graph(f));
        var brief=Run([Member(roots:[1])],Graph(f),Conditions() with { Combat=Conditions().Combat with { Trace=false } });
        var limited=Run([Member(roots:[1])],Graph(f),Conditions() with { Combat=Conditions().Combat with { TraceLimit=3 } });
        Assert.Equal(full.TotalDamage,brief.TotalDamage); Assert.Equal(full.TotalDamage,limited.TotalDamage);
        Assert.Equal(full.EventCount,brief.EventCount); Assert.Equal(full.EventCount,limited.EventCount);
        Assert.Empty(brief.Events); Assert.True(limited.TraceTruncated);
        Assert.Equal(full.TotalDamage,full.Members.Sum(m=>m.Damage));
        Assert.Equal(full.TotalDamage,full.Members.Sum(m=>m.Effects.Values.Sum()));
        Assert.All(full.Events.Where(e=>e.Kind=="damage"),e=>Assert.Contains(full.Events,p=>p.Id==e.ParentId));
    }

    [Fact]
    public void Unknown_graph_and_missing_rounding_and_illegal_cooldown_do_not_produce_saved_results()
    {
        Assert.Throws<ArgumentException>(()=>Run([Member(roots:[1])],Graph(F(1,999))));
        Assert.Throws<ArgumentException>(()=>Run([Member()],Graph(),Conditions() with { RoundingPolicy="" }));
        Assert.Throws<ArgumentException>(()=>Run([Member(burst:Active(cooldown:1000))],Graph(),Conditions() with { Casts=[new(1,"a"),new(2,"a")] }));
    }

    [Fact]
    public void Runtime_without_skills_preserves_reference_firing_and_permanent_buff_results()
    {
        var member=Member();
        member=member with { Weapon=member.Weapon with { Buffs=new() { Ammo=[new("OL",.5)], ReloadSpeed=[new("cube",.2)] } } };
        var c=Conditions(1800);
        var skills=Run([member],Graph(),c);
        var reference=WeaponReplay.Run([member.Weapon],c.Combat);
        Assert.Equal(reference.TotalDamage[c.RoundingPolicy],skills.TotalDamage);
        Assert.Equal(reference.Members[0].Shots,skills.Members[0].Shots);
        Assert.Equal(reference.Members[0].RemainingAmmo,skills.Members[0].RemainingAmmo);
    }

    [Fact]
    public void Charge_buff_keeps_in_progress_charge_and_uses_additive_damage_axis()
    {
        var speed=F(1,61,value:-5000);
        var add=F(2,11,value:700) with { FunctionValueType=1 };
        var member=Member(burst:Active(functions:[1,2]));
        member.Weapon.Weapon.weaponType="SR"; member.Weapon.Weapon.inputType="UP";
        member.Weapon.Weapon.isChargeWeapon=true; member.Weapon.Weapon.chargeTimeSec=1;
        member=member with { Weapon=member.Weapon with { Hit=member.Weapon.Hit with { ChargeApplicable=true,ChargeBase=2.5 } } };
        var r=Run([member],Graph(speed,add),Conditions(35) with { Casts=[new(30,"a")] });
        Assert.Equal(30,r.Events.First(e=>e.Kind=="shot").Frame);
        Assert.Equal(257,r.Events.First(e=>e.Kind=="damage").Value);
    }

    [Fact]
    public void Ammo_grant_uses_new_capacity_and_last_frame_stack_updates_result_immediately()
    {
        var capacity=F(1,14,22,5) with { FunctionValueType=1,TimingTriggerValue=4 };
        var gain=F(2,27,22,10000) with { TimingTriggerValue=4 };
        var r=Run([Member(roots:[1,2])],Graph(capacity,gain),Conditions(1) with {
            Combat=Conditions(1).Combat with { FullBurstWindows=[new(1,2)] } });
        Assert.Equal(105,r.Members[0].MaxAmmo); Assert.Equal(104,r.Members[0].RemainingAmmo);
        Assert.Equal(5,r.Events.Single(e=>e.Kind=="ammo_gain").Value);
        var reduction=F(3,14,31,-2000) with { TimingTriggerValue=1 };
        var reduced=Run([Member(roots:[3])],Graph(reduction),Conditions(1));
        Assert.Equal(80,reduced.Members[0].MaxAmmo); Assert.Equal(80,reduced.Members[0].RemainingAmmo);
    }

    [Fact]
    public void Shared_shield_has_one_pool_and_a_timed_expiry()
    {
        var shield=Active(900) with { Skill=Active().Skill with { SkillType=6,DurationType=1,DurationValue=100,PreferTarget=15,
            SkillValueData=[new(1,1),new(2,1000),new(1,1),new(1,100),new(0,0)] } };
        var call=F(1,72,3,900) with { TimingTriggerValue=100,FunctionValueType=1 };
        var g=Graph(call) with { CharacterSkills=new Dictionary<int,SkillDefinition>{{900,shield}} };
        var member=Member(roots:[1],burst:shield,hp:2000);
        var active=Run([member,Member("b")],g,Conditions(10) with { Casts=[new(1,"a")] });
        Assert.Equal(200,Assert.Single(active.SharedShields).Hp);
        var expired=Run([member,Member("b")],g,Conditions(61) with { Casts=[new(1,"a")] });
        Assert.Empty(expired.SharedShields);
        Assert.Contains(expired.Events,e=>e.Kind=="shield_expired" && e.Frame==61);
    }

    [Fact]
    public void Lowest_cover_targeting_uses_remaining_absolute_hp_when_supplied()
    {
        var heal=F(1,3,value:5000) with { FunctionTarget=4 };
        var burst=Active(functions:[1]) with { Skill=Active().Skill with { AttackType=7,PreferTarget=47,
            SkillValueData=[new(0,0),new(1,1),new(1,10000),new(0,0),new(0,0)] } };
        var r=Run([Member(burst:burst),Member("b")],Graph(heal),Conditions(1) with { Casts=[new(1,"a")],
            InitialCovers=new Dictionary<string,CoverObservation> { ["a"]=new(1000,100),["b"]=new(100,50) } });
        Assert.Equal("b",r.Events.Single(e=>e.Kind=="cover_heal").Target);
        Assert.Equal(1,r.Members[1].CoverRatio);
    }

    [Fact]
    public void Full_burst_duration_request_is_separate_from_prescribed_full_burst_state()
    {
        var member=Member(); member=member with { Skills=member.Skills with { FullBurstDurationFrames=900 } };
        var r=Run([member],Graph(),Conditions(1) with { Casts=[new(1,"a")] });
        Assert.Equal(900,r.Events.Single(e=>e.Kind=="full_burst_duration_request").Value);
        Assert.False(r.Events.Single(e=>e.Kind=="damage").Hit.FullBurst);
    }

    [Fact]
    public void Cooldown_reductions_preserve_centiseconds_before_frame_availability_check()
    {
        var fs=Enumerable.Range(1,3).Select(id=>F(id,83,22,-1) with { TimingTriggerValue=4,FunctionValueType=1 }).ToArray();
        var r=Run([Member(roots:[1,2,3],burst:Active(cooldown:1000))],Graph(fs),Conditions(2) with {
            Casts=[new(1,"a")],Combat=Conditions(2).Combat with { FullBurstWindows=[new(2,3)] } });
        // 601 - 3*0.6 = 599.2; the next usable frame is 600. Rounding each delta loses a frame.
        Assert.Equal(600,r.Members[0].CooldownReadyFrames["burst"]);
        Assert.All(r.Events.Where(e=>e.Kind=="cooldown_change"),e=>Assert.Equal(-1,e.Value));
    }

    [Theory]
    [InlineData("ratio","b")]
    [InlineData("absolute","c")]
    public void Lowest_hp_policy_preserves_the_selected_recipient_and_excludes_caster(string basis,string target)
    {
        var immortal=F(1,40,value:0) with { FunctionTarget=4 };
        var burst=Active(functions:[1]) with { Skill=Active().Skill with { AttackType=6,PreferTarget=11,PreferTargetCondition=1,
            SkillValueData=[new(0,0),new(1,1),new(1,10000),new(0,0),new(0,0)] } };
        var r=Run([Member(burst:burst,hp:10),Member("b",hp:1000),Member("c",hp:100)],Graph(immortal),Conditions(1) with {
            LowestHpTargetBasis=basis,InitialHpRatios=new Dictionary<string,double>{{"a",.1},{"b",.2},{"c",.5}},Casts=[new(1,"a")] });
        Assert.Equal(target,r.ActiveEffects.Single(e=>e.FunctionId==1).Target);
    }

    [Theory]
    [InlineData(.1,true)]
    [InlineData(0,false)]
    [InlineData(-.1,false)]
    public void Conditional_attack_requires_an_accuracy_increase_not_merely_an_option_entry(double rate,bool active)
    {
        var f=F(1,1,31) with { TimingTriggerValue=1,StatusTriggerType=15,StatusTriggerStandard=1,StatusTriggerValue=8 };
        var m=Member(roots:[1]); m=m with { Weapon=m.Weapon with { Buffs=new() { Accuracy=[new("accuracy",rate)] } } };
        var r=Run([m],Graph(f),Conditions(1));
        Assert.Equal(active,r.ActiveEffects.Any(e=>e.FunctionId==1));
    }

    [Fact]
    public void Normal_attack_coefficient_modifier_applies_once_to_changed_weapon_and_never_to_extra_skill_damage()
    {
        var extra=F(1,75,31,1000) with { FunctionTarget=4,TimingTriggerValue=1 };
        var mode=Active(999) with { Skill=Active().Skill with { SkillType=7,DurationType=1,DurationValue=100,
            SkillValueData=[new(2,2000),new(1,3600),new(1,123),new(0,0),new(1,1)] } };
        var m=Member(roots:[1],burst:mode);
        m=m with { Weapon=m.Weapon with { Hit=m.Weapon.Hit with { Coefficient=1.5 },Buffs=new() { NormalAttackMultiplier=.5 } } };
        var r=Run([m],Graph(extra),Conditions(7) with { Casts=[new(6,"a")] });
        Assert.Equal(150,r.Events.First(e=>e.Kind=="damage" && e.Effect=="normal_attack").Value);
        Assert.All(r.Events.Where(e=>e.Kind=="damage" && e.Effect=="skill:999:weapon"),e=>Assert.Equal(30,e.Value));
        Assert.All(r.Events.Where(e=>e.Kind=="damage" && e.Effect=="function:1"),e=>Assert.Equal(10,e.Value));
    }
}

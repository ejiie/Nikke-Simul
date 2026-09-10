using Nikke.Engine;
using Nikke.Engine.Skills;
using static Nikke.Core.Tests.SkillReplayTests;

namespace Nikke.Core.Tests;

public class BattleConnectionTests
{
    private sealed class Sink : ICombatEventSink
    {
        public List<CombatEvent> Events { get; } = [];
        public Action<CombatEvent>? Observe;
        public void OnEvent(CombatEvent value) { Events.Add(value); Observe?.Invoke(value); }
    }
    private sealed class Driver(Action<ISkillBattleControl,BattlePhase> action) : ISkillBattleDriver
    {
        public void OnPhase(ISkillBattleControl b,BattlePhase p) => action(b,p);
    }
    private static SkillReplayConditions WithoutScript(SkillReplayConditions c) => c with {
        Casts=[],Combat=c.Combat with { FullBurstWindows=[] } };
    private static Driver Schedule(SkillReplayConditions c) => new((b,p)=> {
        if (p==BattlePhase.CastSkills)
            foreach (var cast in c.Casts.Where(x=>x.Frame==b.Frame))
                Assert.Equal(BattleCommandStatus.Applied,b.TryCast(cast.CharacterId,cast.Slot).Status);
        if (p==BattlePhase.FullBurstEntry)
            foreach (var w in c.Combat.FullBurstWindows.Where(x=>x.StartFrame==b.Frame))
                Assert.Equal(BattleCommandStatus.Applied,b.TryEnterFullBurst(w.EndFrame-w.StartFrame));
    });

    [Fact]
    public void Driver_and_prescribed_paths_deliver_identical_events_after_trace_limit()
    {
        var extra=F(1,75,31,1000) with { TimingTriggerValue=1,FunctionTarget=4 };
        var reduce=F(2,83,43,-100) with { FunctionValueType=1 };
        var c=Conditions(1800) with { Casts=[new(1,"a"),new(701,"a")],
            Combat=Conditions(1800).Combat with { TraceLimit=3,FullBurstWindows=[new(2,602),new(702,1302)] } };
        var member=Member(roots:[1,2],burst:Active(cooldown:1000));
        var prescribedSink=new Sink(); var driverSink=new Sink();
        var prescribed=SkillReplay.Run([member],Graph(extra,reduce),c,events:prescribedSink);
        var driven=SkillReplay.Run([member],Graph(extra,reduce),WithoutScript(c) with {
            Combat=WithoutScript(c).Combat with { Trace=false } },events:driverSink,driver:Schedule(c));
        Assert.True(prescribed.TraceTruncated); Assert.Empty(driven.Events);
        Assert.Equal(prescribedSink.Events,driverSink.Events);
        Assert.Equal(prescribed.TotalDamage,driven.TotalDamage);
        Assert.Equal(prescribed.Connection.Cooldowns,driven.Connection.Cooldowns);
        Assert.Equal(2,driven.Connection.FullBurst.Cycle);
        Assert.Equal(2,driven.Connection.EventCounts[CombatEventKind.FullBurstExited]);
        Assert.Contains(driven.Connection.Timeline,e=>e.Kind==CombatEventKind.FullBurstExited && e.Frame==1302);
        Assert.Contains(driverSink.Events,e=>e.Frame>1700);
        Assert.Equal(Enumerable.Range(1,driverSink.Events.Count).Select(i=>(long)i),driverSink.Events.Select(e=>e.Sequence));
    }

    [Fact]
    public void Pellets_last_ammo_and_additional_hits_have_separate_causal_events()
    {
        var extra=F(1,75,31,1000) with { TimingTriggerValue=1,FunctionTarget=4 };
        var m=Member(roots:[1]); m.Weapon.Weapon.weaponType="SG"; m.Weapon.Weapon.shotCount=10; m.Weapon.Weapon.maxAmmo=1;
        var sink=new Sink();
        var r=SkillReplay.Run([m],Graph(extra),Conditions(1) with {
            Combat=Conditions(1).Combat with { Trace=false,PelletCoefficientPolicy="per_trigger" } },events:sink);
        var shot=Assert.Single(sink.Events,e=>e.Kind==CombatEventKind.Shot);
        Assert.Equal(1,shot.Shot.AmmoBefore); Assert.Equal(0,shot.Shot.AmmoAfter);
        Assert.Single(sink.Events,e=>e.Kind==CombatEventKind.AmmoConsumed);
        Assert.Equal(10,sink.Events.Count(e=>e.Kind==CombatEventKind.NormalHit));
        Assert.Equal(10,sink.Events.Count(e=>e.Kind==CombatEventKind.AdditionalHit));
        Assert.Equal(10,r.Members[0].Hits);
        Assert.All(sink.Events.Where(e=>e.Hit is not null),e=>Assert.Equal(shot.TraceId,e.Hit.ShotTraceId));
        Assert.Equal(Enumerable.Range(0,10).Select(i=>(int?)i),sink.Events.Where(e=>e.Kind==CombatEventKind.NormalHit).Select(e=>e.Hit.PelletIndex));
        Assert.All(sink.Events.Where(e=>e.Kind==CombatEventKind.AdditionalHit),e=>Assert.Equal(1,e.FunctionId));
    }

    [Fact]
    public void Counter_boundaries_120_ammo_and_200_hits_are_exact_and_do_not_count_extra_damage()
    {
        var ammo=F(1,0,3) with { TimingTriggerValue=120,DurationType=3 };
        var hits=F(2,0,31) with { TimingTriggerValue=200,DurationType=3 };
        var extra=F(3,75,31) with { TimingTriggerValue=1,FunctionTarget=4 };
        var m=Member(roots:[1,2,3]); m.Weapon.Weapon.maxAmmo=1000; m.Weapon.Weapon.fireRate=60; m.Weapon.Weapon.endFireRate=60;
        var r=SkillReplay.Run([m],Graph(ammo,hits,extra),Conditions(201));
        Assert.Equal(120,Assert.Single(r.Events,e=>e.Kind=="function" && e.FunctionId==1).Frame);
        Assert.Equal(200,Assert.Single(r.Events,e=>e.Kind=="function" && e.FunctionId==2).Frame);
        Assert.Equal(201,r.Connection.EventCounts[CombatEventKind.NormalHit]);
        Assert.Equal(201,r.Connection.EventCounts[CombatEventKind.AdditionalHit]);
    }

    [Fact]
    public void Cooldown_queries_see_end_trigger_changes_before_cast_in_same_frame()
    {
        var reduce=F(1,83,43,-1000) with { FunctionValueType=1 };
        var driver=new Driver((b,p)=> {
            if (p==BattlePhase.CastSkills && b.Frame==1) Assert.Equal(BattleCommandStatus.Applied,b.TryCast("a").Status);
            if (p==BattlePhase.FullBurstEntry && b.Frame==1) Assert.Equal(BattleCommandStatus.Applied,b.TryEnterFullBurst(5));
            if (p==BattlePhase.CastSkills && b.Frame==5)
            { Assert.False(b.GetCooldown("a").IsReady); Assert.Equal(BattleCommandStatus.NotReady,b.TryCast("a").Status); }
            if (p==BattlePhase.CastSkills && b.Frame==6)
            {
                Assert.True(b.GetCooldown("a").IsReady);
                Assert.Equal(30,b.GetCooldown("a").ReadyAtTicks);
                Assert.Equal(BattleCommandStatus.Applied,b.TryCast("a").Status);
                Assert.Equal(BattleCommandStatus.DuplicateCast,b.TryCast("a").Status);
            }
        });
        var r=SkillReplay.Run([Member(roots:[1],burst:Active(cooldown:1000))],Graph(reduce),Conditions(6),driver:driver);
        var change=Assert.Single(r.Connection.Timeline,e=>e.FunctionId==1 && e.Kind==CombatEventKind.CooldownChanged);
        Assert.Equal(3005,change.Cooldown.PreviousReadyAtTicks); Assert.Equal(-3000,change.Cooldown.RequestedDeltaTicks);
        Assert.Equal(-2975,change.Cooldown.AppliedDeltaTicks); Assert.Equal(30,change.Cooldown.ReadyAtTicks);
        Assert.Equal(3030,r.Connection.Cooldowns.Single(c=>c.Slot=="burst").ReadyAtTicks);
    }

    [Fact]
    public void Cooldown_reduction_on_ready_member_is_zero_and_tiny_reductions_remain_exact()
    {
        var reductions=Enumerable.Range(1,3).Select(id=>F(id,83,22,-1) with {
            TimingTriggerValue=4,FunctionValueType=1,FunctionTarget=2 }).ToArray();
        var c=Conditions(600) with { Casts=[new(1,"a"),new(600,"a")],
            Combat=Conditions(600).Combat with { FullBurstWindows=[new(2,3)] } };
        var r=SkillReplay.Run([Member("a",[1,2,3],Active(cooldown:1000)),Member("b")],Graph(reductions),c);
        var changes=r.Connection.Timeline.Where(e=>e.FunctionId.HasValue && e.Kind==CombatEventKind.CooldownChanged).ToArray();
        Assert.All(changes.Where(e=>e.Target=="b"),e=>Assert.Equal(0,e.Cooldown.AppliedDeltaTicks));
        Assert.Equal(2996,changes.Last(e=>e.Target=="a").Cooldown.ReadyAtTicks);
        Assert.Equal(600,SkillUnits.ReadyFrame(2996));
    }

    [Fact]
    public void Duplicate_transitions_and_event_callback_commands_cannot_reenter_execution()
    {
        ISkillBattleControl? control=null; var sink=new Sink();
        sink.Observe=e=> {
            if (control is null) return;
            Assert.Equal(BattleCommandStatus.WrongPhase,control.TryCast("a").Status);
            Assert.Equal(BattleCommandStatus.WrongPhase,control.TryEnterFullBurst(600));
            Assert.Equal(BattleCommandStatus.WrongPhase,control.TryExitFullBurst());
        };
        var driver=new Driver((b,p)=> {
            control=b;
            if (p==BattlePhase.FullBurstEntry && b.Frame==1)
            {
                Assert.Equal(BattleCommandStatus.InvalidDuration,b.TryEnterFullBurst(0));
                Assert.Equal(BattleCommandStatus.Applied,b.TryEnterFullBurst(5));
                Assert.Equal(BattleCommandStatus.AlreadyActive,b.TryEnterFullBurst(900));
                Assert.Equal(6,b.FullBurst.EndFrame);
            }
            if (p==BattlePhase.FullBurstExit && b.Frame==6) Assert.Equal(BattleCommandStatus.AlreadyInactive,b.TryExitFullBurst());
        });
        var r=SkillReplay.Run([Member()],Graph(),Conditions(7),events:sink,driver:driver);
        Assert.Equal(1,r.Connection.EventCounts[CombatEventKind.FullBurstEntered]);
        Assert.Equal(1,r.Connection.EventCounts[CombatEventKind.FullBurstExited]);
        Assert.True(sink.Events.First(e=>e.Kind==CombatEventKind.NormalHit).Hit.FullBurst);
        Assert.False(sink.Events.First(e=>e.Kind==CombatEventKind.NormalHit && e.Frame==6).Hit.FullBurst);
        Assert.Equal(BattleCommandStatus.WrongPhase,control!.TryCast("a").Status);
    }

    [Fact]
    public void Modernia_style_mode_expires_separately_from_delayed_full_burst_entry()
    {
        var unlimited=F(1,5,value:0) with { DurationValue=1500 };
        var burst=Active(999,[1],4000) with { Skill=Active(cooldown:4000).Skill with {
            SkillType=7,DurationType=1,DurationValue=1500,
            SkillValueData=[new(2,2000),new(1,3600),new(1,123),new(0,0),new(1,1)] } };
        var m=Member(burst:burst);
        m=m with { Skills=m.Skills with { FullBurstDurationFrames=900,
            BurstConnection=new(3,4,1,1500,100,500,1000,0,[123]) } };
        FullBurstDurationRequest? request=null;
        var driver=new Driver((b,p)=> {
            if (p==BattlePhase.CastSkills && b.Frame==1) request=b.TryCast("a").DurationRequest;
            if (p==BattlePhase.FullBurstEntry && b.Frame==29)
            {
                Assert.Equal(3,request!.BurstStep); Assert.Equal(1500,request.SourceDurationCs);
                Assert.Equal(BattleCommandStatus.Applied,b.TryEnterFullBurst(request.DurationFrames,request.CastTraceId));
                Assert.Equal(929,b.FullBurst.EndFrame);
            }
        });
        var sink=new Sink(); var r=SkillReplay.Run([m],Graph(unlimited),Conditions(935),events:sink,driver:driver);
        Assert.DoesNotContain(sink.Events,e=>e.Kind==CombatEventKind.AmmoConsumed && e.Frame<901);
        Assert.Contains(sink.Events,e=>e.Kind==CombatEventKind.AmmoConsumed && e.Frame>=901);
        Assert.Contains(r.Events,e=>e.Kind=="weapon_restored" && e.Frame==901);
        Assert.Contains(sink.Events,e=>e.Kind==CombatEventKind.NormalHit && e.Frame>=901 && e.Frame<929 && e.Hit.FullBurst && e.Hit.WeaponShotId==100);
        Assert.Equal(929,Assert.Single(sink.Events,e=>e.Kind==CombatEventKind.FullBurstExited).Frame);
    }

    [Fact]
    public void A_direct_skill_hit_is_not_a_normal_or_additional_hit()
    {
        var burst=Active(123) with { Skill=Active().Skill with { SkillType=1,
            SkillValueData=[new(2,2000),new(1,1),new(0,0),new(0,0),new(0,0)] } };
        var sink=new Sink(); SkillReplay.Run([Member(burst:burst)],Graph(),Conditions(1) with { Casts=[new(1,"a")] },events:sink);
        var direct=Assert.Single(sink.Events,e=>e.Kind==CombatEventKind.DirectSkillHit);
        Assert.Null(direct.Hit.ShotTraceId); Assert.Equal(123,direct.SkillId);
        Assert.Single(sink.Events,e=>e.Kind==CombatEventKind.NormalHit);
        Assert.DoesNotContain(sink.Events,e=>e.Kind==CombatEventKind.AdditionalHit);
    }

    [Fact]
    public void Driver_cannot_be_combined_with_prescribed_inputs()
    {
        var c=Conditions() with { Casts=[new(1,"a")] };
        Assert.Throws<ArgumentException>(()=>SkillReplay.Run([Member()],Graph(),c,driver:Schedule(c)));
    }

    [Fact]
    public void Changing_caster_overload_does_not_change_recipient_flat_attack_grant()
    {
        var aura=F(1,value:1400) with { FunctionStandard=1,FunctionTarget=2,DurationType=3 };
        var caster=Member("a",[1],attack:500);
        double Grant(double ol)
        {
            var input=caster with { Weapon=caster.Weapon with { Hit=caster.Weapon.Hit with { AttackBuffs=[new("OL",ol)] } } };
            var result=SkillReplay.Run([input,Member("b")],Graph(aura),Conditions(1));
            return Assert.Single(result.Events.Single(e=>e.Kind=="damage" && e.Source=="b").Hit.AttackFlatBuffs).Amount;
        }
        Assert.Equal(70,Grant(0)); Assert.Equal(70,Grant(.2)); Assert.Equal(70,Grant(.8));
        Assert.Equal(500,caster.Weapon.Hit.StatAttack);
    }

    [Fact]
    public void Adjacent_windows_end_before_reentry_and_the_boundary_hit_uses_new_window()
    {
        var c=Conditions(6) with { Combat=Conditions(6).Combat with { FullBurstWindows=[new(1,6),new(6,7)] } };
        var sink=new Sink();
        var result=SkillReplay.Run([Member()],Graph(),WithoutScript(c),events:sink,driver:Schedule(c));
        Assert.Equal(new[] { CombatEventKind.FullBurstExited,CombatEventKind.FullBurstEntered },
            sink.Events.Where(e=>e.Frame==6 && e.FullBurst is not null).Select(e=>e.Kind));
        Assert.True(sink.Events.Single(e=>e.Frame==6 && e.Kind==CombatEventKind.NormalHit).Hit.FullBurst);
        Assert.Equal(2,result.Connection.FullBurst.Cycle);
    }
}

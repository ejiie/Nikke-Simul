using Nikke.Core.Combat;
using Nikke.Core.Stats;
using Nikke.Engine;
using Nikke.Simulator.Core.Data.Dto;
using Nikke.Simulator.Core.Stats;
using Nikke.Simulator.Engine;

namespace Nikke.Core.Tests;

public class WeaponReplayTests
{
    private static WeaponDto Weapon(string type = "AR") => new() { weaponType = type, inputType = "DOWN", fireType = "Instant",
        fireRate = 12, endFireRate = 12, spotFirstDelaySec = .2, spotLastDelaySec = .2,
        maxAmmo = 60, reloadTimeSec = 1, reloadBulletRate = 1, shotCount = type == "SG" ? 10 : 1, muzzleCount = 1 };
    private static WeaponReplayMember Member(string id = "synthetic", WeaponDto? weapon = null) => new(id, weapon ?? Weapon(),
        new HitContext { StatAttack = 100 }, new StatBuffSet());
    private static WeaponReplayConditions Scenario(int frames = 132) => new() { DurationFrames = frames, Trace = true };

    [Fact]
    public void Ar_timeline_uses_legacy_frame_contract_and_conserves_damage()
    {
        var result = WeaponReplay.Run([Member()], Scenario());
        Assert.Equal(24, result.Members[0].Shots);
        var shots = result.Events.Where(e => e.Kind == "shot").ToArray();
        Assert.Equal(13, shots[0].Frame);
        Assert.All(shots.Zip(shots.Skip(1)), pair => Assert.Equal(5, pair.Second.Frame - pair.First.Frame));
        Assert.All(result.TotalDamage, d => Assert.Equal(2400, d.Value));
        Assert.All(result.Events.Where(e => e.Kind == "hit"), e => Assert.Contains(shots, s => s.Id == e.ParentId));
        Assert.All(result.TotalDamage, d => Assert.Equal(d.Value, result.Members.Sum(m => m.Effects["normal_attack"][d.Key])));
    }

    [Fact]
    public void Scheduled_skill_buffs_join_OL_and_expire_before_boundary_hit()
    {
        var member = Member() with { Hit = new() { StatAttack = 100, AttackBuffs = [new("OL", .2)] } };
        var result = WeaponReplay.Run([member], Scenario(30) with {
            AttackBuffWindows = [new("synthetic", new("skill", .5), 13, 23)], FullBurstWindows = [new(18,23)] });
        var hits = result.Events.Where(e => e.Kind == "hit").ToArray();
        Assert.Equal(170, hits.Single(e => e.Frame == 13).EffectiveAttack);
        Assert.Equal(255, hits.Single(e => e.Frame == 18).Damage["legacy_term_floor"]);
        Assert.Equal(120, hits.Single(e => e.Frame == 23).EffectiveAttack);
        Assert.False(hits.Single(e => e.Frame == 23).FullBurst);
        Assert.Equal(100, member.Hit.StatAttack);
    }

    [Fact]
    public void Trace_sink_and_truncation_never_change_execution()
    {
        var detailed = WeaponReplay.Run([Member("a"),Member("b")], Scenario());
        var summary = WeaponReplay.Run([Member("a"),Member("b")], Scenario() with { Trace = false });
        var limited = WeaponReplay.Run([Member("a"),Member("b")], Scenario() with { TraceLimit = 3 });
        Assert.Equal(detailed.TotalDamage, summary.TotalDamage);
        Assert.Equal(detailed.TotalDamage, limited.TotalDamage);
        Assert.Equal(detailed.EventCount, summary.EventCount);
        Assert.Equal(3, limited.Events.Count); Assert.True(limited.TraceTruncated);
        Assert.Empty(summary.Events); Assert.False(summary.TraceTruncated);
    }

    [Fact]
    public void Sg_policy_is_required_and_pellets_consume_one_round()
    {
        var member = Member(weapon: Weapon("SG"));
        Assert.Throws<ArgumentException>(() => WeaponReplay.Run([member], Scenario(13)));
        var trigger = WeaponReplay.Run([member], Scenario(13) with { PelletCoefficientPolicy = "per_trigger" });
        var pellet = WeaponReplay.Run([member], Scenario(13) with { PelletCoefficientPolicy = "per_pellet" });
        Assert.Equal(1, trigger.Members[0].Shots); Assert.Equal(10, trigger.Members[0].Hits);
        Assert.Equal(59, trigger.Members[0].RemainingAmmo);
        Assert.Equal(100, trigger.TotalDamage["legacy_term_floor"]);
        Assert.Equal(1000, pellet.TotalDamage["legacy_term_floor"]);
    }

    [Fact]
    public void Charge_timing_and_ammo_use_permanent_buffs_without_changing_native_attack()
    {
        var weapon = Weapon("SR"); weapon.inputType = "UP"; weapon.isChargeWeapon = true; weapon.chargeTimeSec = 1;
        var member = Member(weapon: weapon) with { Hit = new() { StatAttack = 100, ChargeApplicable = true, ChargeBase = 2.5 },
            Buffs = new() { Ammo = [new("OL", .5)], ChargeSpeed = [new("OL", .5)] } };
        var result = WeaponReplay.Run([member], Scenario(50));
        Assert.Equal(41, result.Events.First(e => e.Kind == "shot").Frame);
        Assert.Equal(89, result.Members[0].RemainingAmmo);
        Assert.Equal(250, result.TotalDamage["legacy_term_floor"]);
    }

    [Fact]
    public void Mg_reference_ramps_and_never_fires_twice_in_one_frame()
    {
        var w = Weapon("MG"); w.fireRate = 1; w.endFireRate = 70; w.fireRateRampPerShot = 100d/60;
        w.maxAmmo = 300; w.fireRateResetTimeSec = 1;
        var result = WeaponReplay.Run([Member(weapon:w)], Scenario(600));
        var frames = result.Events.Where(e => e.Kind == "shot").Select(e => e.Frame).ToArray();
        Assert.True(frames.Length > 100);
        Assert.Equal(frames.Length, frames.Distinct().Count());
        Assert.Contains(frames.Zip(frames.Skip(1)), p => p.Second - p.First == 1);
    }

    [Fact]
    public void Invalid_windows_duplicate_members_and_unsupported_weapons_are_rejected()
    {
        Assert.Throws<ArgumentException>(() => WeaponReplay.Run([Member(),Member()], Scenario()));
        Assert.Throws<ArgumentException>(() => WeaponReplay.Run([Member()], Scenario() with { FullBurstWindows = [new(20,10)] }));
        Assert.Throws<ArgumentException>(() => WeaponReplay.Run([Member()], Scenario() with { AttackBuffWindows = [new("absent",new("skill",.5),1,10)] }));
        Assert.Throws<ArgumentException>(() => WeaponReplay.Run([Member(weapon:Weapon("unknown"))], Scenario()));
    }
}

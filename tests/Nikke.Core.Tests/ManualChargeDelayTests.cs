using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Data.Dto;
using Nikke.Simulator.Core.Stats;
using Nikke.Simulator.Engine;
using static Nikke.Core.Tests.SkillReplayTests;

namespace Nikke.Core.Tests;

// E-BUG-1: manual full charge of an UP-type charge weapon (Alice) releases the button to fire, so every shot pays
// [spotFirst + re-click] like tap fire. Rejected hypothesis kept in docs/manual-charge-delay-engine.ko.md:
// "aim is held, spotFirst is not paid per shot". Synthetic fixtures; no game observation is inferred.
public class ManualChargeDelayTests
{
    private const int SpotFirst = 12; // 0.2s * 60
    private const int SpotLast = 12;

    private sealed class FixedRandom(double value) : IRandomSource
    {
        public double NextDouble() => value;
    }

    private static WeaponDto Dto(string input, double chargeSec, double fireRate = 1, int ammo = 100) => new()
    {
        weaponType = "SR", isChargeWeapon = true, inputType = input, fireType = "Instant", chargeTimeSec = chargeSec,
        fireRate = fireRate, endFireRate = fireRate, maxAmmo = ammo, reloadTimeSec = 1, reloadBulletRate = 1,
        shotCount = 1, muzzleCount = 1, spotFirstDelaySec = 0.2, spotLastDelaySec = 0.2,
    };

    /// <summary>Frame numbers (1-based) of every shot in <paramref name="frames"/> frames.</summary>
    private static List<int> ShotFrames(Func<FiringFrameResult> advance, int frames)
    {
        var shots = new List<int>();
        for (int f = 1; f <= frames; f++) if (advance().Fired) shots.Add(f);
        return shots;
    }
    private static int[] Intervals(List<int> shots) => shots.Zip(shots.Skip(1), (a, b) => b - a).ToArray();

    private static FiringControl Control(ControlMode mode, FireStyle style = FireStyle.FullCharge) => new() { Mode = mode, Style = style };

    // Both firing models share one state machine; every rule is asserted on both copies.
    public static IEnumerable<object[]> Models() { yield return [true]; yield return [false]; }
    private static Func<FiringFrameResult> Gun(bool skillModel, WeaponDto dto, FiringControl ctl, double rng = 0,
        IReadOnlyList<double>? chargeSpeed = null)
    {
        var profile = new WeaponProfile(dto);
        if (skillModel)
        {
            var g = new SkillFiringModel(profile, dto.maxAmmo, ctl, new FixedRandom(rng), null, chargeSpeed);
            return g.AdvanceFrame;
        }
        var legacy = new FiringModel(profile, dto.maxAmmo, ctl, new FixedRandom(rng), null, chargeSpeed);
        return legacy.AdvanceFrame;
    }

    [Theory, MemberData(nameof(Models))]
    public void Manual_full_charge_up_type_pays_spot_first_and_reclick_each_shot(bool skillModel)
    {
        var fire = Gun(skillModel, Dto("UP", 1.0), Control(ControlMode.Manual));
        var shots = ShotFrames(fire, 600);
        Assert.True(shots.Count >= 6);
        // reclick(1f, rng=0) + spotFirst(12f) + full charge 60f - 1f pre-started charge frame.
        Assert.All(Intervals(shots), i => Assert.Equal(1 + SpotFirst + 60 - 1, i));
    }

    [Theory, MemberData(nameof(Models))]
    public void Self_burst_charge_reduction_never_collapses_the_interval_below_spot_first(bool skillModel)
    {
        // 99% charge speed => 1f charge, the state that produced 2F intervals before the fix.
        var fire = Gun(skillModel, Dto("UP", 1.0), Control(ControlMode.Manual), chargeSpeed: [0.99]);
        var intervals = Intervals(ShotFrames(fire, 600));
        Assert.NotEmpty(intervals);
        Assert.All(intervals, i => Assert.Equal(1 + SpotFirst + 1, i));
        Assert.All(intervals, i => Assert.True(i >= SpotFirst + 1));
    }

    [Theory, MemberData(nameof(Models))]
    public void Manual_full_charge_with_one_frame_charge_equals_tap_interval(bool skillModel)
    {
        var full = Intervals(ShotFrames(Gun(skillModel, Dto("UP", 0.01), Control(ControlMode.Manual)), 600));
        var tap = Intervals(ShotFrames(Gun(skillModel, Dto("UP", 0.01), Control(ControlMode.Manual, FireStyle.Tap)), 600));
        Assert.Equal(tap, full);
        Assert.All(full, i => Assert.Equal(1 + SpotFirst + 1, i));
    }

    [Theory, MemberData(nameof(Models))]
    public void Tap_interval_does_not_depend_on_charge_time(bool skillModel)
    {
        var slow = Intervals(ShotFrames(Gun(skillModel, Dto("UP", 1.5), Control(ControlMode.Manual, FireStyle.Tap)), 600));
        Assert.All(slow, i => Assert.Equal(1 + SpotFirst + 1, i));
    }

    [Theory, MemberData(nameof(Models))]
    public void Auto_up_type_pays_spot_last_and_spot_first_every_shot_even_with_one_frame_charge(bool skillModel)
    {
        var fire = Gun(skillModel, Dto("UP", 1.0), Control(ControlMode.Auto), chargeSpeed: [0.99]);
        var intervals = Intervals(ShotFrames(fire, 800));
        Assert.True(intervals.Length >= 10);
        Assert.All(intervals, i => Assert.Equal(SpotLast + SpotFirst + 1, i));
    }

    [Theory, MemberData(nameof(Models))]
    public void Auto_up_type_keeps_both_delays_at_normal_charge(bool skillModel)
    {
        var intervals = Intervals(ShotFrames(Gun(skillModel, Dto("UP", 1.0), Control(ControlMode.Auto)), 1200));
        Assert.All(intervals, i => Assert.Equal(SpotLast + SpotFirst + 60 - 1, i));
    }

    [Theory, MemberData(nameof(Models))]
    public void Only_full_charge_down_charge_weapon_keeps_the_rate_gate_without_spot_delays(bool skillModel)
    {
        // Liberalio / Neon VE: holding the button fires full charges back to back, rate gate only (unchanged).
        foreach (var mode in new[] { ControlMode.Manual, ControlMode.Auto })
        {
            var fire = Gun(skillModel, Dto("DOWN_Charge", 0.01, fireRate: 10), Control(mode));
            var intervals = Intervals(ShotFrames(fire, 300));
            Assert.NotEmpty(intervals);
            Assert.All(intervals, i => Assert.Equal(6, i));
        }
    }

    [Theory, MemberData(nameof(Models))]
    public void Maintain_stance_weapon_keeps_its_own_after_delay(bool skillModel)
    {
        var dto = Dto("UP", 0.01); dto.maintainFireStanceSec = 0.5;
        var intervals = Intervals(ShotFrames(Gun(skillModel, dto, Control(ControlMode.Manual)), 600));
        Assert.All(intervals, i => Assert.Equal(SpotFirst + 30 + 1, i)); // spotFirst + maintain, then 1f charge
    }

    [Fact]
    public void Mid_run_charge_speed_change_applies_to_following_shots_but_keeps_spot_first()
    {
        var dto = Dto("UP", 1.0);
        var gun = new SkillFiringModel(new WeaponProfile(dto), dto.maxAmmo, Control(ControlMode.Manual), new FixedRandom(0));
        var shots = new List<int>();
        for (int f = 1; f <= 1500; f++)
        {
            if (f == 400) gun.ApplyRuntime(dto.maxAmmo, 1, 100, false, null); // 0.01s charge (self burst)
            if (f == 900) gun.ApplyRuntime(dto.maxAmmo, 100, 100, false, null);
            if (gun.AdvanceFrame().Fired) shots.Add(f);
        }
        var intervals = Intervals(shots);
        Assert.Contains(intervals, i => i == 1 + SpotFirst + 60 - 1);
        Assert.Contains(intervals, i => i == 1 + SpotFirst + 1);
        Assert.All(intervals, i => Assert.True(i >= 1 + SpotFirst + 1));
    }

    // ── replay level: shot interval is recorded in the trace ──
    private static SkillReplayMember Alice(double chargeSec, string input = "UP")
    {
        var m = Member("5004");
        var w = m.Weapon.Weapon;
        w.weaponType = "SR"; w.isChargeWeapon = true; w.inputType = input; w.chargeTimeSec = chargeSec;
        w.spotFirstDelaySec = 0.2; w.spotLastDelaySec = 0.2; w.fireRate = 1; w.endFireRate = 1;
        return m with { Weapon = m.Weapon with { Hit = m.Weapon.Hit with { ChargeApplicable = true, ChargeBase = 3.5 } } };
    }
    private static int?[] TraceIntervals(SkillReplayResult r)
        => r.Events.Where(t => t.Kind == "shot").Select(t => t.ShotIntervalFrames).ToArray();
    private static SkillReplayConditions Cond(string manual, string style = "full_charge") => Conditions(1800) with
    {
        Combat = Conditions(1800).Combat with { ManualCharacterId = manual, ManualStyle = style },
    };

    [Fact]
    public void Trace_records_the_shot_interval_and_the_first_shot_has_none()
    {
        var r = SkillReplay.Run([Alice(1.0)], Graph(), Cond("5004"), new FixedRandom(0));
        var iv = TraceIntervals(r);
        Assert.True(iv.Length > 5);
        Assert.Null(iv[0]);
        Assert.All(iv.Skip(1), i => Assert.Equal(1 + SpotFirst + 60 - 1, i));
        var shots = r.Events.Where(t => t.Kind == "shot").ToArray();
        Assert.Equal(shots.Skip(1).Select((s, k) => s.Frame - shots[k].Frame), iv.Skip(1).Select(i => i!.Value));
        Assert.All(r.Events.Where(t => t.Kind != "shot"), t => Assert.Null(t.ShotIntervalFrames));
    }

    [Fact]
    public void Replay_manual_full_charge_one_frame_equals_tap_and_never_below_spot_first()
    {
        var full = TraceIntervals(SkillReplay.Run([Alice(0.01)], Graph(), Cond("5004"), new FixedRandom(0)));
        var tap = TraceIntervals(SkillReplay.Run([Alice(0.01)], Graph(), Cond("5004", "tap"), new FixedRandom(0)));
        Assert.Equal(tap, full);
        Assert.All(full.Skip(1), i => Assert.True(i >= SpotFirst + 1));
    }

    [Fact]
    public void Replay_auto_and_down_charge_paths_are_unchanged()
    {
        var auto = TraceIntervals(SkillReplay.Run([Alice(0.01)], Graph(), Cond(""), new FixedRandom(0)));
        Assert.All(auto.Skip(1), i => Assert.Equal(SpotLast + SpotFirst + 1, i));
        var down = Alice(0.01, "DOWN_Charge"); down.Weapon.Weapon.fireRate = 10; down.Weapon.Weapon.endFireRate = 10; down.Weapon.Weapon.maxAmmo = 100000;
        var gated = TraceIntervals(SkillReplay.Run([down], Graph(), Cond("5004"), new FixedRandom(0)));
        Assert.All(gated.Skip(1), i => Assert.Equal(6, i));
    }

    [Fact]
    public void Manual_full_charge_fires_fewer_shots_than_the_old_hold_aim_rule_would()
    {
        var r = SkillReplay.Run([Alice(0.01)], Graph(), Cond("5004"), new FixedRandom(0));
        // 1800 frames / 14f per shot (+ reload every 100 shots not reached) — old rule gave one shot per 2 frames (900).
        Assert.InRange(r.Members[0].Shots, 120, 130);
    }
}

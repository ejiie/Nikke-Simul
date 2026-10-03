using Nikke.Engine;
using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Stats;
using static Nikke.Core.Tests.SkillReplayTests;

namespace Nikke.Core.Tests;

// S-SKILL-1 effect types needed by Snow White / Maxwell: instant-damage bodies (2/13/15), StatCritical (9),
// IsBurstStepState = full burst (status 21), IsCheckMonster (28), shots-measured ChangeWeapon with a replacement profile.
// Synthetic fixtures mirror the official graph shapes; no game observation is inferred.
public class SsrBatch1SkillTests
{
    private sealed class FixedRandom(double value) : IRandomSource { public double NextDouble() => value; }

    private static SkillBody Body(int type, int cooldown = 0, int durationType = 1, int durationValue = 0, params long[] values)
        => new() { SkillType = type, SkillCooltime = cooldown, DurationType = durationType, DurationValue = durationValue, PreferTarget = 11,
            SkillValueData = [new(2, values.Length > 0 ? values[0] : 0), new(1, values.Length > 1 ? values[1] : 0),
                new(1, values.Length > 2 ? values[2] : 0), new(0, 0), new(values.Length > 4 ? 1 : 0, values.Length > 4 ? values[4] : 0)] };

    private static SkillReplayMember WithSlots(SkillReplayMember m, SkillDefinition? skill2 = null, SkillDefinition? burst = null, SkillDefinition? skill1 = null)
    {
        var slots = new Dictionary<string, SkillDefinition>(m.Skills.Slots);
        if (skill1 is not null) slots["skill1"] = skill1;
        if (skill2 is not null) slots["skill2"] = skill2;
        if (burst is not null) slots["burst"] = burst;
        return m with { Skills = m.Skills with { Slots = slots } };
    }
    private static SkillDefinition Damaging(int type, long coefficient, int cooldown = 100)
        => new() { SkillId = 7000 + type, Skill = Body(type, cooldown, 1, 0, coefficient, 0, 700) };

    // Direct instant-damage bodies: InstantAll(1), InstantNumber(2), InstantCircle(13), InstantArea(15) all hit the single boss once.
    [Theory]
    [InlineData(2)] [InlineData(13)] [InlineData(15)]
    public void Instant_damage_bodies_match_the_established_instant_all_body(int type)
    {
        var baseline = SkillReplay.Run([WithSlots(Member(), skill2: Damaging(1, 9046))], Graph(), Conditions(130), new FixedRandom(.99));
        var typed = SkillReplay.Run([WithSlots(Member(), skill2: Damaging(type, 9046))], Graph(), Conditions(130), new FixedRandom(.99));
        Assert.True(baseline.Members[0].Damage > 0);
        Assert.Equal(baseline.TotalDamage, typed.TotalDamage);
        Assert.Contains(typed.Events, e => e.Kind == "damage" && e.Effect == $"skill:{7000 + type}");
    }

    private static SkillFunction Crit(int id, long value) => F(id, type: 9, timing: 1, value: value) with { DurationType = 3 };

    [Fact]
    public void Stat_critical_raises_the_sampled_crit_chance_by_its_value()
    {
        // Sampler returns 0.20: below base 15% -> no crit; with +10% (25%) -> crit.
        SkillReplayConditions Cond() => Conditions(70) with { Combat = Conditions(70).Combat with { CritMode = "sample" } };
        var plain = SkillReplay.Run([Member()], Graph(), Cond(), new FixedRandom(.20));
        var buffed = SkillReplay.Run([Member("a", [1])], Graph(Crit(1, 1000)), Cond(), new FixedRandom(.20));
        static int Crits(SkillReplayResult r) => r.Events.Count(e => e.Kind == "damage" && e.Hit!.Crit);
        Assert.Equal(0, Crits(plain));
        Assert.True(Crits(buffed) > 0);
        Assert.Equal(buffed.Members[0].Hits, Crits(buffed));
    }

    private static SkillFunction FullBurstOnly(int id, long statusValue = 4, int statusType = 21)
        => F(id, value: 1000) with { StatusTriggerType = statusType, StatusTriggerStandard = 1, StatusTriggerValue = statusValue };

    [Fact]
    public void Burst_step_four_status_applies_only_while_the_full_burst_window_is_active()
    {
        var gated = FullBurstOnly(20);
        var skill2 = new SkillDefinition { SkillId = 7100, Skill = Body(13, 60, 1, 0, 9046, 0, 700),
            FunctionPhases = new Dictionary<string, int[]> { ["after_use"] = [20] } };
        var m = WithSlots(Member(), skill2: skill2);
        SkillReplayConditions Cond(params FrameWindow[] windows) => Conditions(125) with { Combat = Conditions(125).Combat with { FullBurstWindows = windows } };
        var outside = SkillReplay.Run([m], Graph(gated), Cond(), new FixedRandom(.99));
        var inside = SkillReplay.Run([m], Graph(gated), Cond(new FrameWindow(50, 125)), new FixedRandom(.99));
        Assert.DoesNotContain(outside.Events, e => e.Kind == "buff_on" && e.FunctionId == 20);
        Assert.Contains(inside.Events, e => e.Kind == "buff_on" && e.FunctionId == 20);
    }

    [Fact]
    public void Unmodelled_status_values_are_reported_as_unsupported_instead_of_guessed()
    {
        var m = Member();
        string[] Issues(SkillFunction f) => SkillReplay.CheckSupport(m.Skills with { Slots = new Dictionary<string, SkillDefinition>(m.Skills.Slots) { ["skill1"] = Passive(f.Id) } }, Graph(f)).ToArray();
        Assert.Empty(Issues(FullBurstOnly(30)));
        Assert.Contains("function:31:status21_value", Issues(FullBurstOnly(31, statusValue: 3)));
        Assert.Contains("function:32:status28_value", Issues(FullBurstOnly(32, statusValue: 1, statusType: 28)));
        Assert.Empty(Issues(FullBurstOnly(33, statusValue: 5, statusType: 28)));
    }

    [Fact]
    public void Monster_count_threshold_never_met_by_a_single_boss_and_spawn_timing_never_fires()
    {
        // Maxwell skill 2 shape: OnSpawnMonster(26) + IsCheckMonster(28)=5 -> not active in a one-enemy battle.
        var spawn = F(40, type: 9, timing: 26, value: 500) with { TimingTriggerValue = 5, StatusTriggerType = 28, StatusTriggerStandard = 1, StatusTriggerValue = 5 };
        var r = SkillReplay.Run([Member("a", [40])], Graph(spawn), Conditions(70), new FixedRandom(.5));
        Assert.DoesNotContain(r.Events, e => e.Kind == "buff_on" && e.FunctionId == 40);
        Assert.Empty(SkillReplay.CheckSupport(Member("a", [40]).Skills, Graph(spawn)));
    }

    // ── shots-measured ChangeWeapon with a replacement profile (Snow White / Maxwell burst shape) ──
    private static SkillDefinition ChargeBurst(int shots = 1, double chargeSec = 1, double fullRate = 10, bool pierce = true) => new()
    {
        SkillId = 7200,
        Skill = Body(7, 400, 2, shots, 12487 * 4, 120, 1022002, 0, 1) with
        { WeaponChange = new() { ChargeTimeSec = chargeSec, FullChargeRate = fullRate, MaxAmmo = 1, Pierce = pierce, Source = "test" } },
    };
    private static SkillReplayResult RunBurst(SkillReplayMember m, int frames = 400, int castFrame = 5)
        => SkillReplay.Run([m], Graph(), Conditions(frames) with { Casts = [new(castFrame, m.Weapon.CharacterId)] }, new FixedRandom(.99));
    private static SkillReplayMember Ar(SkillDefinition burst) => WithSlots(Member("5012"), burst: burst);

    [Fact]
    public void Replacement_weapon_fires_one_full_charge_shot_after_its_charge_time_then_the_base_weapon_resumes()
    {
        var r = RunBurst(Ar(ChargeBurst()));
        var shots = r.Events.Where(e => e.Kind == "shot").ToArray();
        var modeHits = r.Events.Where(e => e.Kind == "damage" && e.Effect == "skill:7200:weapon").ToArray();
        var hit = Assert.Single(modeHits);
        Assert.Equal(10, hit.Hit!.ChargeBase); Assert.True(hit.Hit.FullCharge); Assert.True(hit.Hit.ChargeApplicable);
        Assert.True(hit.Hit.Pierce);
        // Cast at frame 5, 60-frame charge, no spot delay: the replacement shot is the 60th gun frame, frame 5 + 59.
        Assert.Equal(5 + 59, hit.Frame);
        var restored = Assert.Single(r.Events, e => e.Kind == "weapon_restored");
        Assert.Equal("shots_spent", restored.Basis);
        Assert.True(restored.Frame >= hit.Frame);
        // The base AR fired before the swap and resumes afterwards; none of its hits are charge hits.
        Assert.Contains(shots, s => s.Frame < 5);
        Assert.Contains(shots, s => s.Frame > hit.Frame);
        Assert.All(r.Events.Where(e => e.Kind == "damage" && e.Effect == "normal_attack"), e => Assert.False(e.Hit!.FullCharge));
    }

    [Fact]
    public void Base_weapon_state_is_frozen_during_the_replacement_and_ammo_continues_afterwards()
    {
        var m = Ar(ChargeBurst());
        var withSwap = RunBurst(m);
        var swapShots = withSwap.Events.Count(e => e.Kind == "shot" && e.Frame is >= 5 and <= 64);
        Assert.Equal(1, swapShots);                                    // only the replacement shot between cast and its release
        int baseShots = withSwap.Members[0].Shots - 1;                  // minus the replacement shot
        Assert.True(baseShots > 5);
        // The replacement gun's single round never touches the base magazine (no reload in this window).
        Assert.Equal(m.Weapon.Weapon.maxAmmo - baseShots, withSwap.Members[0].RemainingAmmo);
    }

    [Fact]
    public void Charge_speed_effects_shorten_the_replacement_charge()
    {
        var charge = F(50, type: 61, timing: 1, value: -5000);        // -50% charge time for the whole battle
        var m = WithSlots(Member("5012", [50]), burst: ChargeBurst());
        var r = SkillReplay.Run([m], Graph(charge), Conditions(300) with { Casts = [new(5, "5012")] }, new FixedRandom(.99));
        var hit = Assert.Single(r.Events, e => e.Kind == "damage" && e.Effect == "skill:7200:weapon");
        Assert.Equal(5 + 29, hit.Frame);                                // 30-frame charge
    }

    [Fact]
    public void Multi_shot_replacement_keeps_the_mode_until_the_last_shot()
    {
        var r = RunBurst(Ar(ChargeBurst(shots: 2, chargeSec: .5)), 400);
        var hits = r.Events.Where(e => e.Kind == "damage" && e.Effect == "skill:7200:weapon").ToArray();
        Assert.Equal(2, hits.Length);
        Assert.Equal(1, r.Events.Count(e => e.Kind == "weapon_restored"));
        Assert.True(r.Events.Single(e => e.Kind == "weapon_restored").Frame >= hits[1].Frame);
    }

    [Fact]
    public void Change_weapon_without_a_profile_keeps_the_time_based_base_gun_path()
    {
        var plain = new SkillDefinition { SkillId = 7300, Skill = Body(7, 400, 1, 100, 20000, 3600, 999, 0, 1) };
        var r = SkillReplay.Run([Ar(plain)], Graph(), Conditions(200) with { Casts = [new(5, "5012")] }, new FixedRandom(.99));
        Assert.Contains(r.Events, e => e.Kind == "weapon_change");
        Assert.Contains(r.Events, e => e.Kind == "weapon_restored" && e.Basis is null);
        Assert.DoesNotContain(r.Events, e => e.Kind == "damage" && e.Hit!.FullCharge);
    }

    [Fact]
    public void Replacement_profiles_are_validated_before_execution()
    {
        string[] Issues(SkillDefinition burst) => SkillReplay.CheckSupport(Ar(burst).Skills, Graph()).ToArray();
        Assert.Empty(Issues(ChargeBurst()));
        var noProfile = new SkillDefinition { SkillId = 7400, Skill = Body(7, 400, 2, 1, 12487, 120, 1022002, 0, 1) };
        Assert.Contains("skill:7400:unreviewed_body", Issues(noProfile));                 // shots duration needs a profile
        Assert.Contains("skill:7200:unreviewed_body", Issues(ChargeBurst(chargeSec: 0)));
        Assert.Contains("skill:7200:unreviewed_body", Issues(ChargeBurst(fullRate: 0)));
    }

    [Fact]
    public void Replacement_weapon_runs_are_labelled_as_a_provisional_policy_in_the_trace_and_limitations()
    {
        var used = RunBurst(Ar(ChargeBurst()));
        var policy = Assert.Single(used.Events, e => e.Kind == "replacement_weapon");
        Assert.StartsWith("provisional_motion_policy", policy.Basis);
        Assert.Contains(used.Limitations, l => l.StartsWith("Replacement-weapon motion"));
        var plain = SkillReplay.Run([Member()], Graph(), Conditions(100), new FixedRandom(.99));
        Assert.DoesNotContain(plain.Events, e => e.Kind == "replacement_weapon");
        Assert.DoesNotContain(plain.Limitations, l => l.StartsWith("Replacement-weapon motion"));
    }

    [Fact]
    public void Manual_tap_with_a_replacement_weapon_is_rejected_not_guessed()
    {
        var m = Ar(ChargeBurst());
        SkillReplayConditions Cond(string style) => Conditions(200) with
        { Combat = Conditions(200).Combat with { ManualCharacterId = "5012", ManualStyle = style } };
        var ex = Assert.Throws<ArgumentException>(() => SkillReplay.Run([m], Graph(), Cond("tap"), new FixedRandom(.99)));
        Assert.Contains("미지원 교체 무기 조작", ex.Message);
        // Full-charge manual and auto control stay executable; a tap user without a replacement weapon is unaffected.
        Assert.True(SkillReplay.Run([m], Graph(), Cond("full_charge"), new FixedRandom(.99)).Members[0].Shots > 0);
        Assert.True(SkillReplay.Run([Member("5012")], Graph(), Cond("tap"), new FixedRandom(.99)).Members[0].Shots > 0);
    }

    [Fact]
    public void Base_ammo_buffs_use_the_integer_path_but_never_enlarge_the_replacement_magazine()
    {
        var ammo = F(60, type: 14, timing: 1, value: 10000) with { DurationType = 3 };   // +100% max ammo for the whole battle
        var m = WithSlots(Member("5012", [60]), burst: ChargeBurst());
        var r = SkillReplay.Run([m], Graph(ammo), Conditions(400) with { Casts = [new(5, "5012")] }, new FixedRandom(.99));
        var swapShot = Assert.Single(r.Events, e => e.Kind == "shot" && e.Frame == 5 + 59);
        Assert.Equal(0, swapShot.Value);                                  // 1-round replacement magazine, not 1 * 2
        Assert.Equal(m.Weapon.Weapon.maxAmmo * 2, r.Members[0].MaxAmmo);   // base weapon: exact +100%
    }

    [Fact]
    public void Prepared_summary_carries_the_replacement_policies_only_for_runs_that_used_the_weapon()
    {
        var c = Conditions(200) with { Casts = [new(5, "5012")] };
        var used = PreparedSkillReplay.Create([Ar(ChargeBurst())], Graph(), c).Run();
        Assert.NotNull(used.Policies);
        Assert.Equal([ReplacementWeaponPolicy.MotionRunId, ReplacementWeaponPolicy.PierceRunId], used.Policies!.Select(p => p.Id));
        Assert.Contains("provisional policy", used.Policies[0].Text);
        Assert.Contains("one hit", used.Policies[1].Text);
        var plain = PreparedSkillReplay.Create([Member("5012")], Graph(), Conditions(200)).Run();
        Assert.Null(plain.Policies);
        Assert.Equal("cpu-summary.7-run-policies", used.ImplementationVersion);
    }
}

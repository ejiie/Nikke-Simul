using System.Numerics;
using Nikke.Core.Combat;
using Nikke.Core.Stats;
using Nikke.Engine;
using Nikke.Engine.Skills;
using static Nikke.Core.Tests.SkillReplayTests;

namespace Nikke.Core.Tests;

// E-PREC-1: client_f32_dprod candidate, true-damage defence ratio, interruption/parts split, long ammo assembly.
// Synthetic semantic fixtures; none of these values are measured game damage.
public class PrecisionFollowupTests
{
    // Exact rational arithmetic oracle: binary32 operands are dyadic rationals, so the product is exact.
    private readonly record struct Q(BigInteger N, BigInteger D)
    {
        public static Q FromFloat(float value)
        {
            int bits = BitConverter.SingleToInt32Bits(value), exponent = (bits >> 23) & 0xFF, mantissa = bits & 0x7FFFFF;
            if (exponent == 0) exponent = 1; else mantissa |= 1 << 23;
            BigInteger n = bits < 0 ? -mantissa : mantissa;
            int shift = exponent - 150;
            return shift >= 0 ? new(n << shift, 1) : new(n, BigInteger.One << -shift);
        }
        public static Q operator *(Q a, Q b) => new(a.N * b.N, a.D * b.D);
        // Round half away from zero for a non-negative value, minimum 1.
        public long Damage() => (long)BigInteger.Max(1, (2 * N + D) / (2 * D));
    }

    // Independent oracle: float32 B/extra/reduction/defence factors, exact rational multiplication chain.
    private static long Oracle(long difference, ClientDamageRates r)
    {
        float bonus = 1f;
        bonus += r.CriticalDamageRate - 1f; bonus += r.CoreDamageRate - 1f;
        bonus += r.BurstDamageRate - 1f; bonus += r.BonusRangeRate - 1f;
        float extra = r.BreakRate + r.AddDamageRate - 1f;
        float reduction = 1f - r.DamageReductionRate, defence = 1f - r.DefenceRatioRate;
        var q = new Q(difference, 1);
        foreach (float f in new[] { r.DamageRatio, r.StatDamageRatio, r.ChargeDamageRate, bonus, extra, reduction, defence, r.ElementRate })
            q *= Q.FromFloat(f);
        return q.Damage();
    }

    private static bool Float32Representable(long value) => (long)(float)value == value;

    private static ClientDamageRates RandomRates(Random rng)
    {
        float R(int tenThousandthMin, int tenThousandthMax) => (float)(rng.Next(tenThousandthMin, tenThousandthMax) / 10000d);
        return new(R(10000, 400000), 1f, R(10000, 30000), R(10000, 20000), R(10000, 30000), R(10000, 15000), R(10000, 13000),
            R(10000, 12000), R(10000, 16000), R(0, 4000), R(0, 5000), R(10000, 11000));
    }

    [Fact]
    public void Double_product_matches_an_independent_rational_oracle_on_large_hits()
    {
        var rng = new Random(20261003);
        int nonRepresentable = 0, large = 0;
        for (int i = 0; i < 2000; i++)
        {
            long defence = rng.Next(0, 200000), difference = rng.Next(100000, 3000000);
            var rates = RandomRates(rng);
            var result = ClientFloatDamage.CalculateDoubleProduct(difference + defence, defence, rates);
            long expected = Oracle(difference, rates);
            Assert.Equal(expected, result.Damage);
            if (expected > 1L << 24)
            {
                large++;
                if (!Float32Representable(result.Damage)) nonRepresentable++;
            }
        }
        // float32 spacing is >= 2 above 2^24: a double chain must regularly land on values float32 cannot hold.
        Assert.True(large > 1500);
        Assert.True(nonRepresentable > large / 2, $"{nonRepresentable}/{large}");
    }

    [Fact]
    public void Default_float32_chain_only_produces_float32_representable_damage_above_2_pow_24()
    {
        var rng = new Random(7);
        for (int i = 0; i < 500; i++)
        {
            long defence = rng.Next(0, 200000), difference = rng.Next(100000, 3000000);
            var rates = RandomRates(rng);
            long damage = ClientFloatDamage.Calculate(difference + defence, defence, rates).Damage;
            Assert.True(Float32Representable(damage));
        }
    }

    [Fact]
    public void Double_product_hand_checked_case_cannot_be_a_float32_value()
    {
        // 7e5 * 25.5 * 1.5 * 1.3 * 1.1 * 1.0 ... check one fixed case with exact fractions: B = 1 + .5 + 1 + .5 + .3 = 3.3f.
        var rates = new ClientDamageRates(25.5f, 1f, 1f, 1.5f, 2f, 1.5f, 1.3f, 1f, 1f, 0f, 0f, 1f);
        var d = ClientFloatDamage.CalculateDoubleProduct(700000, 0, rates);
        var f = ClientFloatDamage.Calculate(700000, 0, rates);
        Assert.Equal(Oracle(700000, rates), d.Damage);
        Assert.Equal(3.299999952316284d, d.Bonus, 15); // B stays binary32 (0x40533333)
        Assert.True(f.Damage > 1L << 24 && Float32Representable(f.Damage));
        Assert.False(Float32Representable(d.Damage));
        Assert.NotEqual(f.Damage, d.Damage);
    }

    [Fact]
    public void Double_product_converts_the_exact_long_difference_without_a_float32_cast()
    {
        var rates = new ClientDamageRates(1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1);
        long difference = (1L << 24) + 1; // not representable in binary32
        Assert.Equal(1L << 24, ClientFloatDamage.Calculate(difference, 0, rates).Damage);
        Assert.Equal(difference, ClientFloatDamage.CalculateDoubleProduct(difference, 0, rates).Damage);
        Assert.Throws<ArgumentException>(() => ClientFloatDamage.CalculateDoubleProduct((1L << 53) + 1, 0, rates));
        Assert.Throws<OverflowException>(() => ClientFloatDamage.RoundToDamage(9223372036854775808d));
        Assert.Equal(1, ClientFloatDamage.RoundToDamage(0.2d));
        Assert.Equal(3, ClientFloatDamage.RoundToDamage(2.5d));
    }

    [Fact]
    public void Double_product_policy_is_a_candidate_and_does_not_change_the_default()
    {
        Assert.Equal("client_f32", HitCalculator.DefaultPolicy);
        Assert.Equal("client_f32", new SkillReplayConditions().RoundingPolicy);
        Assert.True(HitCalculator.IsClientPolicy("client_f32") && HitCalculator.IsClientPolicy("client_f32_dprod"));
        Assert.False(HitCalculator.IsClientPolicy("legacy_term_floor"));
        var c = new HitContext { StatAttack = 700000, Defense = 30925, Coefficient = 25.5, Crit = true, CritBonus = .7948, Core = true,
            FullBurst = true, ProperDistance = true, AttackDamage = .2, DamageTaken = .1 };
        Assert.Equal(HitCalculator.CalculateClient(c).Damage, HitCalculator.Calculate(c));
        var candidate = HitCalculator.Evaluate(c, "client_f32_dprod", 123456);
        Assert.Equal("client_f32_dprod", candidate.Policy);
        Assert.Equal(HitCalculator.CalculateClientDoubleProduct(c).Damage, candidate.Damage);
        Assert.Equal(HitCalculator.Calculate(c, "client_f32_dprod"), candidate.Damage);
        Assert.Equal(candidate.Damage - 123456, candidate.Residual);
        Assert.Equal(new[] { "effectiveAttack", "effectiveDefense", "difference", "base", "B", "extra", "reduction",
            "defenceRatio", "product", "final" }, candidate.Terms.Select(t => t.Name));
        Assert.Equal(candidate.Damage, candidate.Terms.Last().After);
        // Compare keeps its four historical candidates; the new policy is evaluated explicitly.
        Assert.Equal(4, HitCalculator.Compare(c).Candidates.Count);
        Assert.Throws<ArgumentException>(() => HitCalculator.Calculate(c, "client_f32_dprod_x"));
    }

    [Fact]
    public void Double_product_shares_input_validation_and_true_damage_rules_with_the_default()
    {
        foreach (var bad in new[] { new HitContext { StatAttack = 100.5 }, new() { StatAttack = 100, Defense = .5 },
            new() { StatAttack = 100, DefenceRatioRate = 1.01 }, new() { StatAttack = 100, StatDamageRatio = -1 } })
            Assert.Throws<ArgumentException>(() => HitCalculator.Calculate(bad, "client_f32_dprod"));
        var c = new HitContext { StatAttack = 10, DefenceRatioRate = .6, DamageType = "true" };
        Assert.Equal(10, HitCalculator.Calculate(c, "client_f32_dprod"));
        Assert.Equal(4, HitCalculator.Calculate(c with { DamageType = "normal" }, "client_f32_dprod"));
    }

    [Fact]
    public void Double_product_policy_runs_a_replay_with_the_same_integer_attack_path()
    {
        var member = Member() with { Weapon = Member().Weapon with { Hit = new() { StatAttack = 1, Coefficient = 2.5 } } };
        var c = new SkillReplayConditions { RoundingPolicy = "client_f32_dprod", Combat = new() { DurationFrames = 60 },
            DamageLog = new() { CharacterId = "a" } };
        var replay = SkillReplay.Run([member], Graph(), c);
        Assert.Equal(replay.Members[0].Hits * 3, replay.TotalDamage);
        Assert.All(replay.DamageLog.Entries, e => Assert.Equal("client_f32_dprod", e.Calculation.Policy));
        Assert.Equal(replay.TotalDamage, PreparedSkillReplay.Create([member], Graph(), c).Run().TeamDamage);
        Assert.Throws<ArgumentException>(() => SkillReplay.Run([member], Graph(), c with { RoundingPolicy = "client_f32_dprod2" }));
        // Same fractional-attack rejection as client_f32 (integer path), unlike the legacy binary64 policies.
        var fractional = member with { Weapon = member.Weapon with { Hit = member.Weapon.Hit with { StatAttack = 1.5 } } };
        Assert.Throws<ArgumentException>(() => SkillReplay.Run([fractional], Graph(), c));
    }

    [Fact]
    public void Five_member_fixture_double_product_stays_close_to_the_default_policy()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "../../../../../"));
        var json = new System.Text.Json.JsonSerializerOptions(System.Text.Json.JsonSerializerDefaults.Web);
        var fixture = System.Text.Json.JsonSerializer.Deserialize<FixtureInput>(
            File.ReadAllText(Path.Combine(root, "tools/benchmarks/engine/fixture.json")), json)!;
        SkillReplayResult Run(string policy) => SkillReplay.Run(
            fixture.Members.Select(m => m with { Weapon = m.Weapon with { Hit = m.Weapon.Hit with { StatAttack = 100000 } } }).ToArray(),
            fixture.Graph, fixture.Conditions with { RoundingPolicy = policy, DamageLog = null,
                Combat = fixture.Conditions.Combat with { CritMode = "off", ManualCharacterId = "", Trace = false, EnemyDefense = 30925 },
                AutoBurst = fixture.Conditions.AutoBurst with { TimelineLimit = 0, StageDelayMinFrames = 1, StageDelayMaxFrames = 1 } });
        var legacy = Run("legacy_term_floor"); var clientRun = Run("client_f32"); var candidateRun = Run("client_f32_dprod");
        double client = clientRun.TotalDamage, candidate = candidateRun.TotalDamage;
        // Before/after record for the report: default policy total is the pre-change value (1346863834).
        Assert.Equal(1346863834d, client);
        Assert.Equal(1346859763d, legacy.TotalDamage);
        var directory = Path.Combine(root, "artifacts/precision-followup", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(directory);
        File.WriteAllText(Path.Combine(directory, "fixture-5member-180s.json"), System.Text.Json.JsonSerializer.Serialize(new {
            evidence = "synthetic_5_member_180s_fixed_def30925", rules = clientRun.RulesVersion,
            legacy = legacy.TotalDamage, client_f32 = client, client_f32_dprod = candidate,
            members = clientRun.Members.Select((m, i) => new { m.CharacterId, client = m.Damage, dprod = candidateRun.Members[i].Damage }) },
            new System.Text.Json.JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine(directory);
        // Each hit differs from float32 by at most a few units out of ~1.5e5, so 9,000+ hits stay within 1e-4 relative.
        Assert.InRange(Math.Abs(candidate - client) / client, 0, 1e-4);
    }
    private sealed record FixtureInput(SkillReplayMember[] Members, SkillGraph Graph, SkillReplayConditions Conditions);

    [Fact]
    public void True_damage_ignores_the_defence_ratio_in_both_client_policies()
    {
        // User-confirmed 2026-10-03: final 10, defence ratio 60% -> normal 4, true damage 10.
        var normal = new HitContext { StatAttack = 10, DefenceRatioRate = .6 };
        foreach (string policy in new[] { "client_f32", "client_f32_dprod" })
        {
            Assert.Equal(4, HitCalculator.Calculate(normal, policy));
            Assert.Equal(4, HitCalculator.Calculate(normal with { DamageType = "skill" }, policy));
            Assert.Equal(10, HitCalculator.Calculate(normal with { DamageType = "true" }, policy));
            var audit = HitCalculator.Evaluate(normal with { DamageType = "true" }, policy);
            Assert.Equal(1d, audit.Terms.Single(t => t.Name == "defenceRatio").After);
            Assert.Equal(.6, audit.Terms.Single(t => t.Name == "defenceRatio").Before);
        }
        // True damage still ignores defence and keeps validating the input.
        var withDefence = normal with { StatAttack = 100, Defense = 90, DamageType = "true", TrueDamage = .5 };
        Assert.Equal(150, HitCalculator.Calculate(withDefence));
        Assert.Throws<ArgumentException>(() => HitCalculator.Calculate(withDefence with { DefenceRatioRate = double.NaN }));
        // Historical binary64 policies never modelled this input (documented limitation); they stay unchanged.
        Assert.Equal(10, HitCalculator.Calculate(normal, "legacy_term_floor"));
    }

    [Fact]
    public void Interruption_feeds_break_rate_only_for_an_interruption_target_and_parts_feed_add_damage_rate()
    {
        var c = new HitContext { StatAttack = 100, InterruptionDamage = .5, PartsDamage = .3 };
        // Not an interruption target: the increase is ignored, exactly like a non-matching parts/pierce flag.
        Assert.Equal(100, HitCalculator.Calculate(c));
        Assert.Equal(HitCalculator.Calculate(c with { InterruptionDamage = 0 }), HitCalculator.Calculate(c));
        Assert.Equal(150, HitCalculator.Calculate(c with { InterruptionTarget = true }));
        // Parts alone is not an interruption: it enters addDamageRate and leaves breakRate neutral.
        Assert.Equal(130, HitCalculator.Calculate(c with { Parts = true }));
        // Both together add up (extra = break + add - 1), same as one summed increase before the split.
        Assert.Equal(180, HitCalculator.Calculate(c with { Parts = true, InterruptionTarget = true }));
        foreach (string policy in new[] { "client_f32", "client_f32_dprod" })
        {
            var partsOnly = HitCalculator.Evaluate(c with { Parts = true }, policy).Terms.Single(t => t.Name == "extra").After;
            var breakOnly = HitCalculator.Evaluate(c with { InterruptionTarget = true }, policy).Terms.Single(t => t.Name == "extra").After;
            Assert.Equal(1.3f, (float)partsOnly);
            Assert.Equal(1.5f, (float)breakOnly);
        }
        // Not interruption + not parts: BreakRate neutral, rates unchanged from the earlier mapping.
        Assert.Equal(1f, (float)HitCalculator.Evaluate(new HitContext { StatAttack = 100 }).Terms.Single(t => t.Name == "extra").After);
        // Historical policies keep the interruption increase inside the attack-damage term (bit-for-bit as before).
        foreach (string policy in new[] { "legacy_term_floor", "final_round_even", "nested_floor" })
        {
            var before = new HitContext { StatAttack = 100, AttackDamage = .2 + .5 };
            var after = new HitContext { StatAttack = 100, AttackDamage = .2, InterruptionTarget = true, InterruptionDamage = .5 };
            Assert.Equal(HitCalculator.Calculate(before, policy), HitCalculator.Calculate(after, policy));
            Assert.Equal(HitCalculator.Calculate(new HitContext { StatAttack = 100, AttackDamage = .2 }, policy),
                HitCalculator.Calculate(after with { InterruptionTarget = false }, policy));
            Assert.Equal(HitCalculator.Compare(before).Candidates.Single(x => x.Policy == policy).Damage,
                HitCalculator.Compare(after).Candidates.Single(x => x.Policy == policy).Damage);
        }
    }

    [Fact]
    public void Runtime_96_is_no_longer_duplicated_into_attack_damage()
    {
        var f = F(1, 96, value: 5000) with { FunctionTarget = 1, DurationType = 3 };
        SkillReplayResult Run(bool target) => SkillReplay.Run([Member("a", [1])], Graph(f), new SkillReplayConditions {
            InterruptionTarget = target, Combat = new() { DurationFrames = 30, Trace = true, TraceLimit = 20000 } });
        var on = Run(true); var off = Run(false);
        var hitOn = on.Events.First(e => e.Kind == "damage").Hit; var hitOff = off.Events.First(e => e.Kind == "damage").Hit;
        Assert.Equal(0, hitOn.AttackDamage);
        Assert.True(hitOn.InterruptionTarget); Assert.Equal(.5, hitOn.InterruptionDamage);
        Assert.False(hitOff.InterruptionTarget);
        Assert.Equal(150, on.Events.First(e => e.Kind == "damage").Value);
        Assert.Equal(100, off.Events.First(e => e.Kind == "damage").Value);
        // Not a target: results equal a run without the 96 effect (regression: non-target hits are unchanged).
        Assert.Equal(SkillReplay.Run([Member("a")], Graph(), new SkillReplayConditions {
            Combat = new() { DurationFrames = 30 } }).TotalDamage, off.TotalDamage);
    }

    [Theory]
    [InlineData(.145, 1, 115)] [InlineData(-.145, 1, 85)] [InlineData(.014, 2, 103)] [InlineData(-.025, 1, 97)]
    public void Ammo_assembly_uses_the_same_long_group_rounding_as_attack(double rate, int stacks, long expected)
    {
        var buffs = new StatRateBuff[] { new("fixture", rate, stacks) };
        Assert.Equal(expected, StatBuffCalculator.ApplyAmmo(100, buffs));
        Assert.Equal(StatBuffCalculator.ApplyAttack(100, buffs), StatBuffCalculator.ApplyAmmo(100, buffs));
        // The retired binary64 path rounded 14.499999999999998 down.
        if (rate == .145) Assert.Equal(114, StatBuffCalculator.Apply(100, buffs));
    }

    [Fact]
    public void Ammo_assembly_groups_identical_rates_across_sources_and_rejects_off_grid_or_overflow()
    {
        var ol = StatRateBuff.FromRaw("OL", 140);
        Assert.Equal(103, StatBuffCalculator.ApplyAmmo(100, new[] { ol }, new StatRateBuff[] { new("skill", .014) }));
        Assert.Equal(102, StatBuffCalculator.ApplyAmmo(100, new[] { ol }, new[] { StatRateBuff.FromRaw("skill", 130) }));
        Assert.Throws<ArgumentException>(() => StatBuffCalculator.ApplyAmmo(100, new StatRateBuff[] { new("off-grid", .01401) }));
        Assert.Throws<ArgumentException>(() => StatBuffCalculator.ApplyAmmo(100, new StatRateBuff[] { new("neg", -1.5) }));
        Assert.Throws<OverflowException>(() => StatBuffCalculator.ApplyAmmo(long.MaxValue, new[] { StatRateBuff.FromRaw("x", 1) }));
    }

    [Fact]
    public void Skill_and_weapon_replays_assemble_max_ammo_with_the_long_path()
    {
        var member = Member(attack: 1);
        member = member with { Weapon = member.Weapon with { Buffs = new() { Ammo = [new("OL", .145)] } } };
        var skill = SkillReplay.Run([member], Graph(), new SkillReplayConditions { Combat = new() { DurationFrames = 1 } });
        Assert.Equal(115, skill.Members[0].MaxAmmo);
        var weapon = WeaponReplay.Run([member.Weapon], new WeaponReplayConditions { DurationFrames = 1 });
        Assert.Equal(115, weapon.Members[0].RemainingAmmo + weapon.Members[0].Shots);
        // Skill ammo functions (type 14): rate value type shares the group with OL; flat value type adds after.
        var rate = F(1, 14, value: 1450) with { FunctionTarget = 1, DurationType = 3 };
        var flat = F(2, 14, value: 7) with { FunctionTarget = 1, DurationType = 3, FunctionValueType = 1 };
        var plain = Member("a", [1, 2], attack: 1);
        var buffed = SkillReplay.Run([plain], Graph(rate, flat), new SkillReplayConditions { Combat = new() { DurationFrames = 1 } });
        Assert.Equal(100 + 15 + 7, buffed.Members[0].MaxAmmo);
    }

    [Fact]
    public void Rules_versions_changed_with_the_precision_followup()
    {
        Assert.Equal("p02.5-client-f32-prec1", HitCalculator.Version);
        Assert.Equal("native-stat-shared-buffs-v4-ammo-i64", StatBuffCalculator.Version);
        Assert.Equal("p03.skills.7-precision-1", SkillReplay.Version);
        Assert.Equal("p03.weapon-reference.5-precision-1", WeaponReplay.Version);
        Assert.Equal("cpu-summary.6-precision-1", PreparedSkillReplay.Version);
        Assert.Equal("p04.team.7-precision-1", TeamBurstController.Version);
    }
}

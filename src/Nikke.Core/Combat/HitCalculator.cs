using Nikke.Core.Stats;

namespace Nikke.Core.Combat;

// Explicit single damage instance. Rates are fractions; no RNG or trigger inference here.
public sealed record HitContext
{
    public double StatAttack { get; init; }
    public IReadOnlyList<StatRateBuff> AttackBuffs { get; init; } = [];
    public IReadOnlyList<StatRateBuff> RuntimeAttackBuffs { get; init; } = [];
    // Caster-based grants are flat amounts added after recipient-native rate buffs.
    public IReadOnlyList<StatFlatBuff> AttackFlatBuffs { get; init; } = [];
    public double Defense { get; init; }
    public double Coefficient { get; init; } = 1;
    public string DamageType { get; init; } = "normal";
    public string AttackStatBasis { get; init; } = "native_caster_attack";
    public string SnapshotTiming { get; init; } = "explicit_single_hit";
    public bool CanCrit { get; init; } = true;
    public bool CanCore { get; init; } = true;
    public bool Crit { get; init; }
    public bool Core { get; init; }
    public bool ChargeApplicable { get; init; }
    public bool FullCharge { get; init; }
    public double ChargeBase { get; init; } = 1;
    public double ChargeMultiplierBonus { get; init; }
    public double ChargeAdd { get; init; }
    public bool ProperDistance { get; init; }
    public double DistanceBonus { get; init; } = .3;
    public bool FullBurst { get; init; }
    public double BurstBonus { get; init; } = .5;
    public double CritBonus { get; init; } = .5;
    public double CoreBonus { get; init; } = 1;
    public bool Pierce { get; init; }
    public bool Parts { get; init; }
    public double AttackDamage { get; init; }
    public double PierceDamage { get; init; }
    public double PartsDamage { get; init; }
    public double DotDamage { get; init; }
    public double SequentialDamage { get; init; }
    public double TrueDamage { get; init; }
    public double DamageTaken { get; init; }
    public double DistributionDamage { get; init; }
    public bool ElementAdvantage { get; init; }
    public double ElementBase { get; init; } = .1;
    public double ElementBonus { get; init; }
}
public record CalculationTerm(string Name, double Before, double After, string Operation);
public record DamageBreakdown(string Policy, double Damage, double? Residual, double? RelativeError,
    IReadOnlyList<CalculationTerm> Terms);
public record HitComparison(string RulesVersion, string Status, HitContext Input, double EffectiveAttack, double? ObservedDamage,
    IReadOnlyList<DamageBreakdown> Candidates);

public static class HitCalculator
{
    public const string Version = "p02.3";
    public const int InputSchemaVersion = 2;
    public static HitComparison Compare(HitContext c, double? observed = null)
    {
        ArgumentNullException.ThrowIfNull(c);
        var values = typeof(HitContext).GetProperties().Where(p => p.PropertyType == typeof(double))
            .Select(p => (double)p.GetValue(c));
        if (values.Any(v => !double.IsFinite(v) || Math.Abs(v) > 1e12) || c.StatAttack < 0 || c.Defense < 0 || c.Coefficient <= 0
            || (observed is { } o && (!double.IsFinite(o) || o < 1 || o != Math.Floor(o) || o > 9e15)))
            throw new ArgumentException("계산 입력 범위 또는 실측 대미지를 확인하세요.");
        if (!new[] { "normal", "skill", "dot", "sequential", "distribution", "true" }.Contains(c.DamageType))
            throw new ArgumentException("지원하지 않는 대미지 유형입니다.");
        if (c.Crit && !c.CanCrit || c.Core && !c.CanCore || c.FullCharge && !c.ChargeApplicable)
            throw new ArgumentException("이 타격에서 허용하지 않은 크리·코어·차지 조건입니다.");
        var charge = c.FullCharge ? c.ChargeBase * (1 + c.ChargeMultiplierBonus) + c.ChargeAdd : 1;
        var b3 = 1 + c.AttackDamage + (c.Pierce ? c.PierceDamage : 0) + (c.Parts ? c.PartsDamage : 0)
            + (c.DamageType == "dot" ? c.DotDamage : 0) + (c.DamageType == "sequential" ? c.SequentialDamage : 0)
            + (c.DamageType == "true" ? c.TrueDamage : 0);
        var b4 = 1 + c.DamageTaken + (c.DamageType == "distribution" ? c.DistributionDamage : 0);
        var b5 = c.ElementAdvantage ? 1 + c.ElementBase + c.ElementBonus : 1;
        var bonuses = new[] { ("distance", c.ProperDistance ? c.DistanceBonus : 0), ("fullBurst", c.FullBurst ? c.BurstBonus : 0),
            ("critical", c.Crit ? c.CritBonus : 0), ("core", c.Core ? c.CoreBonus : 0) };
        if (charge <= 0 || b3 < 0 || b4 < 0 || b5 < 0 || 1 + bonuses.Sum(x => x.Item2) < 0)
            throw new ArgumentException("유효 대미지 배율이 음수이거나 차지 배율이 0입니다.");
        var ratedAttack = StatBuffCalculator.Apply(c.StatAttack, c.AttackBuffs, c.RuntimeAttackBuffs);
        var attack = StatBuffCalculator.AddFlat(ratedAttack, c.AttackFlatBuffs);
        var defense = c.DamageType == "true" ? 0 : c.Defense;
        var p = (attack - defense) * c.Coefficient * charge;
        var results = new List<DamageBreakdown>();
        foreach (var policy in new[] { "legacy_term_floor", "final_round_even", "nested_floor" })
        {
            var terms = new List<CalculationTerm> { new("effectiveAttack", c.StatAttack, attack, "native + grouped rounded native * (OL + passive + active skill rates) + caster-based flat grants"),
                new("effectiveDefense", c.Defense, defense, c.DamageType == "true" ? "ignore" : "identity"),
                new("charge", c.ChargeBase, charge, "base * (1 + multiplierBonus) + add; gated by fullCharge"),
                new("P", attack - defense, p, "attackDefenseDifference * coefficient * charge") };
            double damage;
            if (defense >= attack) { damage = 1; terms.Add(new("minimum", p, 1, "defense >= attack")); }
            else
            {
                double b2;
                if (policy == "final_round_even") { b2 = p * (1 + bonuses.Sum(x => x.Item2)); terms.Add(new("B2", p, b2, "P * (1 + active bonuses)")); }
                else
                {
                    b2 = Math.Floor(p); terms.Add(new("base", p, b2, "floor"));
                    foreach (var (name, bonus) in bonuses) { var v = p * bonus; b2 += Math.Floor(v); terms.Add(new(name, v, Math.Floor(v), "floor")); }
                    terms.Add(new("B2", p, b2, "sum of floored base and active bonus terms"));
                }
                var current = b2;
                foreach (var (name, factor) in new[] { ("B3", b3), ("B4", b4), ("B5", b5) })
                {
                    var next = current * factor;
                    if (policy == "nested_floor") next = Math.Floor(next);
                    terms.Add(new(name, current, next, $"multiply {factor:R}" + (policy == "nested_floor" ? "; floor" : ""))); current = next;
                }
                damage = policy == "final_round_even" ? Math.Max(1, Math.Round(current, MidpointRounding.ToEven)) : Math.Floor(current);
                if (!double.IsFinite(damage) || Math.Abs(damage) > 9e15) throw new ArgumentException("정밀 비교 가능한 대미지 범위를 초과했습니다.");
                terms.Add(new("final", current, damage, policy == "final_round_even" ? "round ties-to-even; min 1" : "floor"));
            }
            results.Add(new(policy, damage, observed is { } m ? damage - m : null,
                observed is { } m2 ? (damage - m2) / m2 : null, terms));
        }
        return new(Version, "provisional_rounding", c, attack, observed, results);
    }
}

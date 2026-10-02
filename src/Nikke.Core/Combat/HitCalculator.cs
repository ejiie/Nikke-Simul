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
    // Provisional source mapping pending H-SRC; neutral defaults, not inferred skill/boss values.
    public double StatDamageRatio { get; init; } = 1;
    public double DefenceRatioRate { get; init; }
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
    // Interruption (BreakDamage 96) is a separate hit judgement from Parts (PartsDamage 112):
    // client formula breakRate = 1 + InterruptionDamage on an interruption target, otherwise 1.
    // Neutral defaults keep earlier inputs reproducing. No API/UI control is added for these fields.
    public bool InterruptionTarget { get; init; }
    public double InterruptionDamage { get; init; }
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
    public const string Version = "p02.5-client-f32-prec1";
    public const int InputSchemaVersion = 3;
    public const string DefaultPolicy = "client_f32";
    // Comparison candidate (not the default): float32 B and rate operands, binary64 multiplication chain.
    public const string DoubleProductPolicy = "client_f32_dprod";
    // Policies that assemble attack/defence as exact signed longs and use the client rate model.
    public static bool IsClientPolicy(string policy) => policy is DefaultPolicy or DoubleProductPolicy;
    // Single selected policy, without reflection, candidate arrays or audit term allocation.
    // Compare remains the independent audit path for parity tests and detailed damage logs.
    public static double Calculate(HitContext c, string policy = DefaultPolicy)
    {
        if (policy == DefaultPolicy) return CalculateClient(c).Damage;
        if (policy == DoubleProductPolicy) return CalculateClientDoubleProduct(c).Damage;
        ArgumentNullException.ThrowIfNull(c);
        if (policy is not ("legacy_term_floor" or "final_round_even" or "nested_floor"))
            throw new ArgumentException("Unknown rounding policy.", nameof(policy));
        ReadOnlySpan<double> values = [c.StatAttack,c.Defense,c.Coefficient,c.ChargeBase,c.ChargeMultiplierBonus,c.ChargeAdd,
            c.DistanceBonus,c.BurstBonus,c.CritBonus,c.CoreBonus,c.AttackDamage,c.PierceDamage,c.PartsDamage,c.DotDamage,
            c.SequentialDamage,c.TrueDamage,c.DamageTaken,c.DistributionDamage,c.ElementBase,c.ElementBonus,
            c.StatDamageRatio,c.DefenceRatioRate,c.InterruptionDamage];
        foreach (var value in values)
            if (!double.IsFinite(value) || Math.Abs(value)>1e12) throw new ArgumentException("Invalid hit numeric input.");
        if (c.StatAttack<0 || c.Defense<0 || c.Coefficient<=0
            || c.DamageType is not ("normal" or "skill" or "dot" or "sequential" or "distribution" or "true")
            || c.Crit && !c.CanCrit || c.Core && !c.CanCore || c.FullCharge && !c.ChargeApplicable)
            throw new ArgumentException("Invalid hit context.");
        double charge=c.FullCharge ? c.ChargeBase*(1+c.ChargeMultiplierBonus)+c.ChargeAdd : 1;
        // Legacy policies keep the interruption increase inside the attack-damage term (as the runtime did before the split).
        double b3=1+(c.AttackDamage+(c.InterruptionTarget?c.InterruptionDamage:0))+(c.Pierce?c.PierceDamage:0)+(c.Parts?c.PartsDamage:0)
            +(c.DamageType=="dot"?c.DotDamage:0)+(c.DamageType=="sequential"?c.SequentialDamage:0)
            +(c.DamageType=="true"?c.TrueDamage:0);
        double b4=1+c.DamageTaken+(c.DamageType=="distribution"?c.DistributionDamage:0);
        double b5=c.ElementAdvantage ? 1+c.ElementBase+c.ElementBonus : 1;
        double distance=c.ProperDistance?c.DistanceBonus:0, burst=c.FullBurst?c.BurstBonus:0,
            critical=c.Crit?c.CritBonus:0, core=c.Core?c.CoreBonus:0;
        double bonus=distance+burst+critical+core;
        if (charge<=0 || b3<0 || b4<0 || b5<0 || 1+bonus<0) throw new ArgumentException("Invalid hit multiplier.");
        double attack=StatBuffCalculator.AddFlat(StatBuffCalculator.Apply(c.StatAttack,c.AttackBuffs,c.RuntimeAttackBuffs),c.AttackFlatBuffs);
        double defense=c.DamageType=="true"?0:c.Defense;
        if(defense>=attack) return 1;
        double p=(attack-defense)*c.Coefficient*charge;
        double value2=policy=="final_round_even" ? p*(1+bonus)
            : Math.Floor(p)+Math.Floor(p*distance)+Math.Floor(p*burst)+Math.Floor(p*critical)+Math.Floor(p*core);
        value2*=b3; if(policy=="nested_floor") value2=Math.Floor(value2);
        value2*=b4; if(policy=="nested_floor") value2=Math.Floor(value2);
        value2*=b5; if(policy=="nested_floor") value2=Math.Floor(value2);
        double damage=policy=="final_round_even" ? Math.Max(1,Math.Round(value2,MidpointRounding.ToEven)) : Math.Floor(value2);
        if(!double.IsFinite(damage) || Math.Abs(damage)>9e15) throw new ArgumentException("Damage exceeds precision limit.");
        return damage;
    }
    public static HitComparison Compare(HitContext c, double? observed = null, bool includeClient = true)
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
        var b3 = 1 + (c.AttackDamage + (c.InterruptionTarget ? c.InterruptionDamage : 0)) + (c.Pierce ? c.PierceDamage : 0) + (c.Parts ? c.PartsDamage : 0)
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
        if (includeClient) results.Add(Evaluate(c, DefaultPolicy, observed));
        return new(Version, "provisional_rounding", c, includeClient?CalculateClient(c).Attack:attack, observed, results);
    }

    // Shared operand assembly: both client policies use identical long attack/defence and float32 rate operands.
    private static (long Attack, long Defence, ClientDamageRates Rates) PrepareClient(HitContext c)
    {
        ArgumentNullException.ThrowIfNull(c);
        ReadOnlySpan<double> values = [c.StatAttack,c.Defense,c.Coefficient,c.ChargeBase,c.ChargeMultiplierBonus,c.ChargeAdd,
            c.DistanceBonus,c.BurstBonus,c.CritBonus,c.CoreBonus,c.AttackDamage,c.PierceDamage,c.PartsDamage,c.DotDamage,
            c.SequentialDamage,c.TrueDamage,c.DamageTaken,c.DistributionDamage,c.ElementBase,c.ElementBonus,
            c.StatDamageRatio,c.DefenceRatioRate,c.InterruptionDamage];
        foreach (double value in values)
            if (!double.IsFinite(value) || Math.Abs(value)>1e12) throw new ArgumentException("Invalid hit numeric input.");
        if (c.StatAttack<0 || c.Defense<0 || c.DamageType is not ("normal" or "skill" or "dot" or "sequential" or "distribution" or "true")
            || c.Crit && !c.CanCrit || c.Core && !c.CanCore || c.FullCharge && !c.ChargeApplicable)
            throw new ArgumentException("Invalid hit context.");
        long attack=StatBuffCalculator.AddAttackFlat(StatBuffCalculator.ApplyAttack(StatBuffCalculator.RequireInteger(c.StatAttack),
            c.AttackBuffs,c.RuntimeAttackBuffs),c.AttackFlatBuffs);
        long defence=c.DamageType=="true"?0:StatBuffCalculator.RequireInteger(c.Defense);
        static float F(double value) => ClientFloatDamage.Finite((float)value);
        static float Add(float a,float b) => ClientFloatDamage.Finite((float)(a+b));
        float charge=1f;
        if(c.FullCharge)
        {
            charge=ClientFloatDamage.Finite((float)(F(c.ChargeBase)*Add(1f,F(c.ChargeMultiplierBonus))));
            charge=Add(charge,F(c.ChargeAdd));
        }
        // addDamageRate carries the parts (PartsDamage 112) increase; interruption (96) goes to breakRate.
        float add=Add(1f,F(c.AttackDamage));
        add=Add(add,c.Pierce?F(c.PierceDamage):0f);
        add=Add(add,c.Parts?F(c.PartsDamage):0f);
        add=Add(add,c.DamageType=="dot"?F(c.DotDamage):0f);
        add=Add(add,c.DamageType=="sequential"?F(c.SequentialDamage):0f);
        add=Add(add,c.DamageType=="true"?F(c.TrueDamage):0f);
        // True damage ignores the boss defence ratio (user-confirmed 2026-10-03): factor (1 - rate) is 1.
        float defenceRatioRate=c.DamageType=="true"?0f:F(c.DefenceRatioRate);
        var rates=new ClientDamageRates(F(c.Coefficient),F(c.StatDamageRatio),charge,
            c.Crit?Add(1f,F(c.CritBonus)):1f,c.Core?Add(1f,F(c.CoreBonus)):1f,
            c.FullBurst?Add(1f,F(c.BurstBonus)):1f,c.ProperDistance?Add(1f,F(c.DistanceBonus)):1f,
            c.InterruptionTarget?Add(1f,F(c.InterruptionDamage)):1f,add,
            (float)-Add(F(c.DamageTaken),c.DamageType=="distribution"?F(c.DistributionDamage):0f),
            defenceRatioRate,c.ElementAdvantage?Add(Add(1f,F(c.ElementBase)),F(c.ElementBonus)):1f);
        return (attack,defence,rates);
    }

    public static ClientFloatResult CalculateClient(HitContext c)
    {
        var (attack,defence,rates)=PrepareClient(c);
        return ClientFloatDamage.Calculate(attack,defence,rates);
    }

    public static ClientDoubleProductResult CalculateClientDoubleProduct(HitContext c)
    {
        var (attack,defence,rates)=PrepareClient(c);
        return ClientFloatDamage.CalculateDoubleProduct(attack,defence,rates);
    }

    // Selected-policy audit avoids evaluating incompatible legacy precision limits on the client path.
    public static DamageBreakdown Evaluate(HitContext c, string policy = DefaultPolicy, double? observed = null)
    {
        if(!IsClientPolicy(policy)) return Compare(c,observed,includeClient:false).Candidates.Single(p=>p.Policy==policy);
        if(observed is { } o && (!double.IsFinite(o) || o<1 || o!=Math.Truncate(o) || o>=9223372036854775808d))
            throw new ArgumentException("Invalid observed damage.");
        if(policy==DoubleProductPolicy)
        {
            var d=CalculateClientDoubleProduct(c);
            CalculationTerm[] dterms=[new("effectiveAttack",c.StatAttack,d.Attack,"checked int64 grouped rate/10000, then flat grants"),
                new("effectiveDefense",c.Defense,d.Defence,"true damage: 0; otherwise integer defence"),
                new("difference",d.Attack,d.Difference,"checked int64 attack - defence; then exact binary64 (no float32 cast)"),
                new("base",d.Difference,d.Base,"binary64 left-to-right difference * damageRatio * statDamageRatio * chargeDamageRate (float32 rate operands widened)"),
                new("B",1,d.Bonus,"float32 critical -> core -> burst -> range, each rate - 1 then add (same as client_f32)"),
                new("extra",0,d.Extra,"float32 breakRate + addDamageRate - 1 (same as client_f32); breakRate = interruption, addDamageRate includes parts"),
                new("reduction",0,d.ReductionFactor,"float32 1 - damageReductionRate (same as client_f32)"),
                new("defenceRatio",c.DefenceRatioRate,d.DefenceFactor,"float32 1 - defenceRatioRate; true damage: 1"),
                new("product",d.Base,d.BeforeRound,"binary64 left-to-right base * B * extra * reduction * defenceRatio * element (float32 operands widened)"),
                new("final",d.BeforeRound,d.Damage,"Math.Round AwayFromZero; max(1); checked int64")];
            return new(DoubleProductPolicy,d.Damage,observed is { } dv?d.Damage-dv:null,
                observed is { } dd?(d.Damage-dd)/dd:null,dterms);
        }
        var r=CalculateClient(c);
        CalculationTerm[] terms=[new("effectiveAttack",c.StatAttack,r.Attack,"checked int64 grouped rate/10000, then flat grants"),
            new("effectiveDefense",c.Defense,r.Defence,"true damage: 0; otherwise integer defence"),
            new("difference",r.Attack,r.Difference,"checked int64 attack - defence; then cast float32"),
            new("base",r.Difference,r.Base,"float32 left-to-right damageRatio * statDamageRatio * chargeDamageRate"),
            new("B",1,r.Bonus,"float32 critical -> core -> burst -> range, each rate - 1 then add"),
            new("extra",0,r.Extra,"float32 breakRate + addDamageRate - 1; breakRate = interruption (96), addDamageRate includes parts (112)"),
            new("reduction",0,r.ReductionFactor,"float32 1 - damageReductionRate; provisional mapping"),
            new("defenceRatio",c.DefenceRatioRate,r.DefenceFactor,"float32 1 - defenceRatioRate; true damage: 1"),
            new("product",r.Base,r.BeforeRound,"float32 left-to-right base * B * extra * reduction * defenceRatio * element"),
            new("final",r.BeforeRound,r.Damage,"MathF.Round AwayFromZero; max(1); checked int64")];
        return new(DefaultPolicy,r.Damage,observed is { } value?r.Damage-value:null,
            observed is { } denominator?(r.Damage-denominator)/denominator:null,terms);
    }
}

namespace Nikke.Core.Combat;

// Synthetic/SW-future fixture entry: assembled signed-long stats and explicit client rates.
// This does not identify the source fields or establish game accuracy.
public readonly record struct ClientDamageRates(float DamageRatio, float StatDamageRatio, float ChargeDamageRate,
    float CriticalDamageRate, float CoreDamageRate, float BurstDamageRate, float BonusRangeRate,
    float BreakRate, float AddDamageRate, float DamageReductionRate, float DefenceRatioRate, float ElementRate);

public readonly record struct ClientFloatResult(long Attack, long Defence, long Difference, float Base,
    float Bonus, float Extra, float ReductionFactor, float DefenceFactor, float BeforeRound, long Damage);

public static class ClientFloatDamage
{
    public static float Finite(float value)
    {
        if (!float.IsFinite(value)) throw new ArgumentException("Non-finite client_f32 intermediate.");
        return value;
    }

    public static long RoundToDamage(float value)
    {
        float rounded = Finite(MathF.Round(Finite(value), MidpointRounding.AwayFromZero));
        rounded = MathF.Max(1f, rounded);
        // (float)long.MaxValue is 2^63, NOT the maximum representable signed long.
        if (rounded >= 9223372036854775808f) throw new OverflowException("client_f32 damage exceeds signed long.");
        return checked((long)rounded);
    }

    public static ClientFloatResult Calculate(long attack, long defence, ClientDamageRates rates)
    {
        if (attack < 0 || defence < 0) throw new ArgumentException("Negative attack/defence.");
        ReadOnlySpan<float> inputs = [rates.DamageRatio,rates.StatDamageRatio,rates.ChargeDamageRate,
            rates.CriticalDamageRate,rates.CoreDamageRate,rates.BurstDamageRate,rates.BonusRangeRate,
            rates.BreakRate,rates.AddDamageRate,rates.DamageReductionRate,rates.DefenceRatioRate,rates.ElementRate];
        foreach (float value in inputs) Finite(value);
        if (rates.DamageRatio <= 0 || rates.StatDamageRatio < 0 || rates.ChargeDamageRate <= 0 || rates.ElementRate < 0)
            throw new ArgumentException("Invalid client_f32 multiplier.");
        long difference = checked(attack - defence);
        // The first long -> binary32 conversion occurs AFTER the signed-long subtraction.
        float basis = Finite((float)difference);
        basis = Finite((float)(basis * rates.DamageRatio));
        basis = Finite((float)(basis * rates.StatDamageRatio));
        basis = Finite((float)(basis * rates.ChargeDamageRate));
        float bonus = 1f;
        bonus = Finite((float)(bonus + Finite((float)(rates.CriticalDamageRate - 1f))));
        bonus = Finite((float)(bonus + Finite((float)(rates.CoreDamageRate - 1f))));
        bonus = Finite((float)(bonus + Finite((float)(rates.BurstDamageRate - 1f))));
        bonus = Finite((float)(bonus + Finite((float)(rates.BonusRangeRate - 1f))));
        float extra = Finite((float)(rates.BreakRate + rates.AddDamageRate));
        extra = Finite((float)(extra - 1f));
        float reduction = Finite((float)(1f - rates.DamageReductionRate));
        float defenceFactor = Finite((float)(1f - rates.DefenceRatioRate));
        if (bonus < 0 || extra < 0 || reduction < 0 || defenceFactor < 0)
            throw new ArgumentException("Negative client_f32 multiplier.");
        float candidate = Finite((float)(basis * bonus));
        candidate = Finite((float)(candidate * extra));
        candidate = Finite((float)(candidate * reduction));
        candidate = Finite((float)(candidate * defenceFactor));
        candidate = Finite((float)(candidate * rates.ElementRate));
        return new(attack,defence,difference,basis,bonus,extra,reduction,defenceFactor,candidate,RoundToDamage(candidate));
    }
}

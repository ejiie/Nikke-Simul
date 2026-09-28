using Nikke.Simulator.Core.Stats;

namespace Nikke.Core.Stats;

// Rates from OL, equipment effects and active skills share the same native stat basis.
public sealed record StatRateBuff(string Source, double Rate, int Stacks = 1)
{
    // Retain source units when available; legacy double inputs must represent exactly a 1/10000 rate.
    public long? RawRate10000 { get; init; }
    public static StatRateBuff FromRaw(string source, long rate10000, int stacks = 1) =>
        new(source, (double)((decimal)rate10000 / 10000), stacks) { RawRate10000 = rate10000 };
}
public sealed record StatFlatBuff(string Source, double Amount)
{
    public long? ExactAmount { get; init; }
    public static StatFlatBuff FromInteger(string source, long amount) => new(source, amount) { ExactAmount = amount };
}
public sealed record StatBuffSet
{
    public IReadOnlyList<StatRateBuff> Attack { get; init; } = [];
    public IReadOnlyList<StatRateBuff> HP { get; init; } = [];
    public IReadOnlyList<StatRateBuff> Defense { get; init; } = [];
    public IReadOnlyList<StatRateBuff> Ammo { get; init; } = [];
    // Positive rates shorten time; the adapter converts OL time deltas once.
    public IReadOnlyList<StatRateBuff> ChargeSpeed { get; init; } = [];
    public IReadOnlyList<StatRateBuff> ReloadSpeed { get; init; } = [];
    public IReadOnlyList<StatRateBuff> CriticalChance { get; init; } = [];
    public IReadOnlyList<StatRateBuff> Accuracy { get; init; } = [];
    // BasicHit already includes this factor; changed-weapon coefficients need to apply it once as well.
    public double NormalAttackMultiplier { get; init; }
}

public static class StatBuffCalculator
{
    public const string Version = "native-stat-shared-buffs-v3-attack-i64";

    // Binary64 transport compatibility only. No inferred rounding/truncation of fractional native/flat stats.
    public static long RequireInteger(double value)
    {
        if (!double.IsFinite(value) || value != Math.Truncate(value) || Math.Abs(value) > 9007199254740991d)
            throw new ArgumentException("Attack/defence/flat input must be an exactly representable integer; use the long fixture entry for larger values.");
        return checked((long)value);
    }

    public static long ApplyAttack(long nativeStat, params IReadOnlyList<StatRateBuff>[] groups)
    {
        if (nativeStat < 0 || groups is null) throw new ArgumentException("Invalid native attack.");
        var rates = new Dictionary<long, long>();
        long count = 0;
        foreach (var buffs in groups)
        {
            if (buffs is null || buffs.Count > 1024) throw new ArgumentException("Invalid attack buffs.");
            foreach (var buff in buffs)
            {
                if (buff is null || string.IsNullOrWhiteSpace(buff.Source) || buff.Source.Length > 256
                    || !double.IsFinite(buff.Rate) || Math.Abs(buff.Rate) > 1e6 || buff.Stacks is < 1 or > 1000)
                    throw new ArgumentException("Invalid attack buff.");
                count = checked(count + buff.Stacks);
                if (count > 10000) throw new ArgumentException("Too many attack buff stacks.");
                long raw = buff.RawRate10000 ?? checked((long)Math.Round(buff.Rate * 10000, MidpointRounding.AwayFromZero));
                if ((double)((decimal)raw / 10000) != buff.Rate)
                    throw new ArgumentException("Attack rate must retain 1/10000 source units; higher precision or conflicting raw/rate inputs are unsupported, never truncated.");
                rates[raw] = checked(rates.GetValueOrDefault(raw) + buff.Stacks);
            }
        }
        long value = OverloadProcessor.CalculateFinalBaseStat(nativeStat, rates);
        if (value < 0) throw new ArgumentException("Negative effective attack.");
        return value;
    }

    public static long AddAttackFlat(long ratedStat, IReadOnlyList<StatFlatBuff> buffs)
    {
        if (ratedStat < 0 || buffs is null || buffs.Count > 1024) throw new ArgumentException("Invalid flat attack buffs.");
        long total = ratedStat;
        foreach (var buff in buffs)
        {
            if (buff is null || string.IsNullOrWhiteSpace(buff.Source) || buff.Source.Length > 256)
                throw new ArgumentException("Invalid flat attack buff.");
            long amount = buff.ExactAmount ?? RequireInteger(buff.Amount);
            if (!double.IsFinite(buff.Amount) || (double)amount != buff.Amount)
                throw new ArgumentException("Conflicting exact flat attack amount.");
            total = checked(total + amount);
        }
        if (total < 0) throw new ArgumentException("Negative effective attack.");
        return total;
    }

    public static double AddFlat(double ratedStat, IReadOnlyList<StatFlatBuff> buffs)
    {
        if (!double.IsFinite(ratedStat) || ratedStat < 0 || buffs is null || buffs.Count > 1024
            || buffs.Any(b => b is null || string.IsNullOrWhiteSpace(b.Source) || b.Source.Length > 256
                || !double.IsFinite(b.Amount) || Math.Abs(b.Amount) > 1e12))
            throw new ArgumentException("고정 스탯 버프를 확인하세요.");
        var total = ratedStat + buffs.Sum(b => b.Amount);
        if (!double.IsFinite(total) || total < 0 || total > 9e15) throw new ArgumentException("스탯 범위를 확인하세요.");
        return total;
    }

    public static double Apply(double nativeStat, params IReadOnlyList<StatRateBuff>[] groups)
    {
        if (!double.IsFinite(nativeStat) || nativeStat < 0 || nativeStat > 1e12 || groups is null)
            throw new ArgumentException("스탯 원값을 확인하세요.");
        var rates = new List<double>();
        foreach (var buffs in groups)
        {
            if (buffs is null || buffs.Count > 1024) throw new ArgumentException("버프 목록을 확인하세요.");
            foreach (var buff in buffs)
            {
                if (buff is null || string.IsNullOrWhiteSpace(buff.Source) || buff.Source.Length > 256
                    || !double.IsFinite(buff.Rate) || Math.Abs(buff.Rate) > 1e6 || buff.Stacks is < 1 or > 1000
                    || rates.Count + buff.Stacks > 10000)
                    throw new ArgumentException("버프 수치·중첩 수를 확인하세요.");
                rates.AddRange(Enumerable.Repeat(buff.Rate, buff.Stacks));
            }
        }
        // Concatenate BEFORE grouping/rounding: never apply a skill rate to an OL-buffed base.
        var value = OverloadProcessor.CalculateFinalBaseStat(nativeStat, rates);
        if (!double.IsFinite(value) || value < 0 || value > 9e15)
            throw new ArgumentException("버프 적용 후 스탯 범위를 확인하세요.");
        return value;
    }
}

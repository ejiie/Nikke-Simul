using Nikke.Simulator.Core.Stats;

namespace Nikke.Core.Stats;

// Rates from OL, equipment effects and active skills share the same native stat basis.
public sealed record StatRateBuff(string Source, double Rate, int Stacks = 1);
public sealed record StatBuffSet
{
    public IReadOnlyList<StatRateBuff> Attack { get; init; } = [];
    public IReadOnlyList<StatRateBuff> HP { get; init; } = [];
    public IReadOnlyList<StatRateBuff> Defense { get; init; } = [];
    public IReadOnlyList<StatRateBuff> Ammo { get; init; } = [];
}

public static class StatBuffCalculator
{
    public const string Version = "native-stat-shared-buffs-v2";

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

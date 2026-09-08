using Nikke.Simulator.Core.Data.Dto;
using Nikke.Simulator.Core.Stats;

namespace Nikke.Core.Tests;

// Synthetic discriminating inputs: no account or game dataset required.
public class ImportedOverloadTests
{
    [Fact]
    public void Equal_options_are_grouped_before_rounding()
    {
        // Two 1.4 bonuses grouped -> 2.8 -> 3. Per-line rounding would incorrectly yield 2.
        Assert.Equal(103, OverloadProcessor.CalculateFinalBaseStat(100, [0.014, 0.014]));
    }

    [Fact]
    public void Different_options_remain_separate_rounding_groups()
    {
        // 1.4 -> 1 and 1.3 -> 1; rounding their sum would incorrectly yield 3.
        Assert.Equal(102, OverloadProcessor.CalculateFinalBaseStat(100, [0.014, 0.013]));
    }

    [Fact]
    public void Midpoints_round_away_from_zero()
    {
        Assert.Equal(103, OverloadProcessor.CalculateFinalBaseStat(100, [0.025]));
    }

    [Theory]
    [InlineData(100, 0.014, 0.014, 97)]
    [InlineData(100, 0.014, 0.013, 98)]
    [InlineData(250, 0.6, 0.6, 0)]
    public void Time_reduction_preserves_integer_centiseconds(int basis, double a, double b, int expected)
    {
        Assert.Equal(expected, OverloadProcessor.ReduceTimeCs(basis, [a, b]));
    }

    [Fact]
    public void Empty_options_preserve_base_and_flat_bonus()
    {
        Assert.Equal(107, OverloadProcessor.CalculateFinalBaseStat(100, [], 7));
    }

    [Fact]
    public void Integer_options_are_filtered_by_type_and_unit()
    {
        OverloadOptionDto[] options = [
            new() { type = "A", val_type = "Integer", value = 17 },
            new() { type = "A", val_type = "Percent", value = 0.1 },
            new() { type = "B", val_type = "Integer", value = 99 }
        ];
        Assert.Equal(17, OverloadProcessor.CalculateFlatBonus(options, "A"));
    }
}

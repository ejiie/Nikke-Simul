using System.Collections.Immutable;

namespace Nikke.Analysis.Tests;

public class OverloadCatalogTests
{
    [Theory]
    [InlineData("StatChargeTime", -.1, -.2)]
    [InlineData("StatAccuracyCircle", -.1, -.2)]
    [InlineData("StatAtk", .1, .2)]
    public void Authoritative_signed_values_preserve_original_slot_line_and_sign(string optionId, double before, double after)
    {
        var line = new EquipmentLine("alice", "arm", 3, optionId, before);
        EquipmentLine[] current = [line];
        var option = new AllowedOption("alice", "arm", optionId, [before, after], true, true, true);
        var space = OverloadCandidates.Generate("synthetic-signed-catalog", current, [option]);
        var candidate = Assert.Single(space.Candidates);
        Assert.Equal(line, candidate.Before);
        Assert.Equal(line with { Value = after }, candidate.After);
        Assert.True(candidate.ThresholdSensitive);
        Assert.Equal(line, Assert.Single(current));
        Assert.Equal(new[] { before, after }, option.Values);
    }

    [Fact]
    public void Candidate_range_is_exact_catalog_tiers_not_interpolated_or_sign_flipped()
    {
        var line = new EquipmentLine("alice", "head", 1, "StatChargeTime", -.1);
        var option = new AllowedOption("alice", "head", "StatChargeTime", [-.2, -.1, -.05, -.2], true, true, true);
        var space = OverloadCandidates.Generate("synthetic-tiers", [line], [option]);
        Assert.Equal(new[] { -.2, -.05 }, space.Candidates.Select(c => c.After.Value));
        Assert.All(space.Candidates, c => Assert.Contains(c.After.Value, option.Values));
        // No extrapolation beyond either endpoint, interior interpolation, zero or abs(value).
        Assert.DoesNotContain(space.Candidates, c => c.After.Value is -.3 or -.15 or 0 or .05 or .2);
    }

    [Theory]
    [InlineData(double.NaN)]
    [InlineData(double.PositiveInfinity)]
    [InlineData(double.NegativeInfinity)]
    public void Nonfinite_authoritative_tier_is_rejected(double value)
    {
        var line = new EquipmentLine("alice", "head", 1, "StatChargeTime", -.1);
        var option = new AllowedOption("alice", "head", "StatChargeTime", [value], true, true, true);
        Assert.Throws<ArgumentException>(() => OverloadCandidates.Generate("synthetic-invalid", [line], [option]));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Empty_or_missing_allowed_tiers_are_rejected(bool missing)
    {
        var line = new EquipmentLine("alice", "head", 1, "StatChargeTime", -.1);
        var values = missing ? default : ImmutableArray<double>.Empty;
        var option = new AllowedOption("alice", "head", "StatChargeTime", values, true, true, true);
        Assert.Throws<ArgumentException>(() => OverloadCandidates.Generate("synthetic-invalid", [line], [option]));
    }

    [Theory]
    [InlineData(false, true)]
    [InlineData(true, false)]
    public void Unsupported_or_no_modeled_effect_signed_options_remain_excluded(bool supported, bool effect)
    {
        var line = new EquipmentLine("alice", "leg", 2, "StatAccuracyCircle", -.1);
        var option = new AllowedOption("alice", "leg", "StatAccuracyCircle", [-.2], supported, effect, false);
        var space = OverloadCandidates.Generate("synthetic-effects", [line], [option]);
        Assert.Empty(space.Candidates);
        Assert.Contains(space.Exclusions, e => e.EndsWith("unsupported_or_no_effect"));
    }

    [Fact]
    public void Zero_is_generated_only_when_listed_and_unchanged_negative_value_is_skipped()
    {
        var line = new EquipmentLine("alice", "head", 1, "StatChargeTime", -.1);
        var option = new AllowedOption("alice", "head", "StatChargeTime", [-.1, 0], true, true, true);
        var candidate = Assert.Single(OverloadCandidates.Generate("synthetic-zero", [line], [option]).Candidates);
        Assert.Equal(0, candidate.After.Value);
    }
}

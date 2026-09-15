using System.Collections.Immutable;

namespace Nikke.Analysis.Tests;

public class StatisticsTests
{
    internal static Distribution D(params double[] values)
    { var a = new DistributionAccumulator(); foreach (var x in values) a.Add(x); return a.Snapshot(); }
    [Fact] public void Empty_singleton_and_valid_zero_are_distinct()
    {
        var a = new DistributionAccumulator(cut: 0);
        Assert.Null(a.Snapshot().Mean); Assert.Null(a.Snapshot().CutProbability);
        a.Add(0); var s = a.Snapshot();
        Assert.Equal(0, s.Mean); Assert.Null(s.SampleSd); Assert.Null(s.MeanCi);
        Assert.Equal(0, s.P95); Assert.Equal(0, s.CutProbability);
        Assert.InRange(s.CutCi!.Upper, .79344, .79346);
    }
    [Fact] public void Known_distribution_type7_and_sample_variance()
    {
        var d = D(1, 2, 3, 4, 5);
        Assert.Equal(3, d.Mean); Assert.Equal(Math.Sqrt(2.5), d.SampleSd!.Value, 12);
        Assert.Equal(1.2, d.P5!.Value, 12); Assert.Equal(4.8, d.P95!.Value, 12); Assert.Equal(3, d.Median);
        Assert.InRange(d.MeanCi!.Lower, 1.0367, 1.0368);
        Assert.InRange(d.MeanCi.Upper, 4.9632, 4.9633);
    }
    [Theory]
    [InlineData(1, 12.7062047364)] [InlineData(2, 4.3026527297)]
    [InlineData(9, 2.2621571629)] [InlineData(30, 2.0422724563)] [InlineData(1000, 1.9623390808)]
    public void Student_quantiles_match_independent_reference(double df, double expected)
        => Assert.InRange(Inference.StudentCritical(.975, df), expected - 2e-8, expected + 2e-8);
    [Fact] public void Shifted_moments_large_values_and_partition_merge()
    {
        var all = new Moments(); var a = new Moments(); var b = new Moments();
        for (int i = 0; i < 50000; i++) { var value = 8e15 + i % 5; all.Add(value); (i % 2 == 0 ? a : b).Add(value); }
        a.Merge(b);
        Assert.Equal(8e15 + 2, all.Mean); Assert.Equal(all.Mean, a.Mean);
        Assert.InRange(all.Variance!.Value, 2.00003, 2.00005);
        Assert.Equal(all.Variance.Value, a.Variance!.Value, 10);
    }
    [Fact] public void Quantile_merge_retains_distribution_and_rejects_overflow()
    {
        var a = new DistributionAccumulator(4); var b = new DistributionAccumulator(4);
        a.Add(1); a.Add(4); b.Add(2); b.Add(3); a.Merge(b);
        Assert.Equal(2.5, a.Snapshot().Median); Assert.Throws<InvalidOperationException>(() => a.Add(5));
        Assert.Throws<ArgumentException>(() => a.Merge(a));
    }
    [Theory] [InlineData(double.NaN)] [InlineData(double.PositiveInfinity)] [InlineData(1e20)]
    public void Invalid_numbers_rejected(double value) => Assert.Throws<ArgumentOutOfRangeException>(() => new Moments().Add(value));
    [Fact] public void Wilson_and_strict_cut()
    {
        var a = new DistributionAccumulator(cut: 5); foreach (var x in new[] { 0, 5, 6, 8 }) a.Add(x);
        Assert.Equal(.5, a.Snapshot().CutProbability);
        var w = Inference.Wilson(50, 100); Assert.InRange(w.Lower, .4038, .4039); Assert.InRange(w.Upper, .5961, .5962);
        Assert.True(Inference.Wilson(0, 100).Upper > 0); Assert.True(Inference.Wilson(100, 100).Lower < 1);
    }
    [Fact] public void Welch_known_shift_and_family_adjustment()
    {
        var a = D(1, 2, 3, 4, 5); var b = D(11, 12, 13, 14, 15);
        var d = Inference.Compare(a, b); Assert.Equal(10, d.Difference); Assert.Equal(8, d.DegreesOfFreedom);
        Assert.InRange(d.Ci!.Lower, 7.6939, 7.6941); Assert.Equal("model_improvement", d.Decision);
        Assert.True(Inference.Compare(a, b, 10).Ci!.Lower < d.Ci.Lower);
        Assert.Equal("unresolved", Inference.Compare(a, a).Decision);
        Assert.Null(Inference.Compare(D(0), D(1)).Ci);
        Assert.Equal("zero_variance_unresolved", Inference.Compare(D(0, 0), D(1, 1)).Decision);
    }
    [Fact] public void Pilot_size_is_a_plan_not_a_stopping_rule()
    {
        Assert.Null(Inference.Plan(D(), 1).RequiredN);
        Assert.Null(Inference.Plan(D(0, 0), 1).RequiredN);
        var p = Inference.Plan(D(1, 2, 3, 4, 5), .1, 100);
        Assert.Equal(1928, p.RequiredN); Assert.True(p.ExceedsBudget);
        Assert.Equal(1000, p.PilotTarget); Assert.Equal(10000, p.MainTarget); Assert.Equal(50000, p.SustainedTarget);
    }
    [Fact] public void Failed_cancelled_partial_and_duplicate_attempts()
    {
        var id = new SampleIdentity("e", "fp", "cpu", "final");
        var a = new ExperimentAccumulator(id, 4, ["team.damage"]);
        RunObservation R(string run, string state, bool complete, double v = 0) => new(run, 1, state, complete, id,
            ImmutableDictionary<string, double>.Empty.Add("team.damage", v));
        a.Add(R("1", "completed", true)); a.Add(R("2", "failed", false));
        a.Add(R("3", "cancelled", false)); a.Add(R("4", "completed", false));
        var s = a.Snapshot(); Assert.Equal(1, s.Valid); Assert.Equal(1, s.Failed); Assert.Equal(1, s.Cancelled); Assert.Equal(1, s.Incomplete);
        Assert.True(s.Partial); Assert.Equal(0, s.Metrics["team.damage"].Mean);
        Assert.Throws<ArgumentException>(() => a.Add(R("1", "completed", true) with { Attempt = 2 }));
    }
    [Fact] public void Partition_merge_rejects_identity_and_duplicate_ids()
    {
        var id = new SampleIdentity("e", "fp", "cpu", "final");
        var a = new ExperimentAccumulator(id, 4, ["team.damage"]);
        var b = new ExperimentAccumulator(id, 4, ["team.damage"]);
        var row = new RunObservation("1", 1, "completed", true, id, ImmutableDictionary<string, double>.Empty.Add("team.damage", 1));
        a.Add(row); b.Add(row with { RunId = "2" }); a.Merge(b); Assert.Equal(2, a.Snapshot().Valid);
        Assert.Throws<ArgumentException>(() => a.Merge(b));
        Assert.Throws<ArgumentException>(() => a.Add(row with { RunId = "3", Identity = id with { NumericBackend = "gpu" } }));
    }
}

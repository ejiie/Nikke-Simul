using System.Collections.Immutable;
using Nikke.Contracts;

namespace Nikke.Analysis.Tests;

public class ContractAndOlTests
{
    internal static readonly string[] Ids = ["liter", "blanc", "alice", "noir", "modernia"];
    internal static BatchStatus Batch(string id = "e", int n = 3, string phase = "final") => new(id, "completed", 1, n, n, 0, 0, false,
        new("fp-" + id, "synthetic", "data-v1", "engine-v1", "rules-v1", Ids, 400, 10800, phase, "summary", "fixed:30925"),
        new("cpu", "cpu", "portable-test", 1, 1, 1000000, "synthetic", "v1", "v1", "hardware", null), null);
    internal static RunSummary Row(BatchStatus b, int i, double a, double partner = 0) => new($"{b.Id}:{i}", 1, i, b.Id, b.Input.Fingerprint,
        b.Execution.Backend, b.Input.Phase, a + partner,
        Ids.Select((id, j) => new MemberRunSummary(id, j == 0 ? a : j == 1 ? partner : 0, 1, 2, 1, 0, 0)).ToArray(), 0, 1);
    [Fact] public void Wire_adapter_team_quantile_is_not_sum_of_member_quantiles()
    {
        var b = Batch(n: 2); var rows = new[] { Row(b, 0, 0, 100), Row(b, 1, 100, 0) };
        var s = new ComputeAnalysis().Summarize(b, rows, 100);
        Assert.Equal(100, s.Team.P95); Assert.Equal(190, s.Members.Values.Sum(m => m.P95));
        Assert.Equal(0, s.Team.CutSuccess); Assert.False(s.GameVerified);
    }
    [Fact] public void Wire_adapter_partial_failure_not_zero_sample()
    {
        var b = Batch() with { State = "failed", Valid = 1, Failed = 1, Cancelled = 1, Partial = true };
        var s = new ComputeAnalysis().Summarize(b, [Row(b, 0, 0)], null);
        Assert.True(s.Partial); Assert.Equal(1, s.Team.N); Assert.Equal(0, s.Team.Mean); Assert.Null(s.Team.MeanCi);
        Assert.Throws<ArgumentException>(() => new ComputeAnalysis().Summarize(b, [], null));
    }
    [Fact] public void Wire_adapter_duplicates_order_phase_backend_rejected()
    {
        var b = Batch(n: 1); var r = Row(b, 0, 10);
        foreach (var invalid in new[] { r with { Backend = "gpu" }, r with { Phase = "pilot" }, r with { Attempt = 2 },
            r with { Members = r.Members.Reverse().ToArray() }, r with { TeamDamage = 11 } })
            Assert.Throws<ArgumentException>(() => new ComputeAnalysis().Summarize(b, [invalid], null));
        Assert.Throws<ArgumentException>(() => new ComputeAnalysis().Summarize(b, [r, r], null));
    }
    [Theory]
    [InlineData(0, 3)] // Direct skill crits can exist without a normal hit.
    [InlineData(2, 5)] // Normal hits plus additional/direct damage crits.
    public void Wire_adapter_keeps_normal_hits_and_all_damage_crits_independent(long hits, long crits)
    {
        var b = Batch(n: 1); var r = Row(b, 0, 10);
        r = r with { Members = r.Members.Select((m, i) => i == 0 ? m with { Hits = hits, CriticalHits = crits } : m).ToArray() };
        var aggregate = ComputeAnalysis.Aggregate(b, [r]);
        Assert.Equal((double)hits, aggregate.Metrics["liter.hits"].Mean);
        Assert.Equal((double)crits, aggregate.Metrics["liter.criticalHits"].Mean);
        Assert.Equal(10, new ComputeAnalysis().Summarize(b, [r], null).Team.Mean);
    }
    [Theory]
    [InlineData(-1, 0)]
    [InlineData(0, -1)]
    public void Wire_adapter_still_rejects_negative_hit_or_crit_counts(long hits, long crits)
    {
        var b = Batch(n: 1); var r = Row(b, 0, 10);
        r = r with { Members = r.Members.Select((m, i) => i == 0 ? m with { Hits = hits, CriticalHits = crits } : m).ToArray() };
        Assert.Throws<ArgumentException>(() => new ComputeAnalysis().Summarize(b, [r], null));
    }
    [Fact] public void Comparison_needs_frozen_holdout_proof_and_full_results()
    {
        var a = Batch("base"); var b = Batch("candidate");
        var x = Enumerable.Range(0, 3).Select(i => Row(a, i, i + 1)).ToArray();
        var y = Enumerable.Range(0, 3).Select(i => Row(b, i, i + 101)).ToArray();
        OlChange[] changes = [new("alice", "head", 1, "attack", .1m)];
        Assert.Equal("unverified_design_or_input_difference", new ComputeAnalysis().Compare(a, x, b, y, changes).Verdict);
        var report = new ComputeAnalysis((_, _, _) => true).Compare(a, x, b, y, changes);
        Assert.Equal("model_improvement", report.Verdict); Assert.Equal(100, report.TeamMeanDifference);
        Assert.NotNull(report.MemberAndCycleEffects!["team.fullBursts"]);
        Assert.Throws<ArgumentException>(() => new ComputeAnalysis().Compare(a, x, a, x, changes));
    }
    internal static CandidateSpace Space()
    {
        EquipmentLine[] lines = [new("alice", "head", 1, "attack", .1), new("alice", "head", 2, "ammo", .2)];
        AllowedOption[] options = [new("alice", "head", "attack", [.1, .2], true, true, false),
            new("alice", "head", "ammo", [.2, .3], true, true, true), new("alice", "head", "unsupported", [.5], false, true, false),
            new("alice", "head", "accuracy", [.5], true, false, false)];
        return OverloadCandidates.Generate("synthetic-catalog-v1", lines, options);
    }
    [Fact] public void Candidates_preserve_slots_lines_and_exclude_invalid_noop_unsupported()
    {
        var s = Space(); Assert.Equal(2, s.Candidates.Length);
        Assert.Contains(s.Candidates, c => c.After.Line == 1 && c.After.Option == "attack" && c.After.Value == .2);
        Assert.Contains(s.Candidates, c => c.After.Line == 2 && c.After.Option == "ammo" && c.ThresholdSensitive);
        Assert.All(s.Candidates, c => Assert.Equal(c.Before.Slot, c.After.Slot));
        Assert.NotEmpty(s.Exclusions);
    }
    private static EvaluationBatch Evaluation(EvaluationRequest r, double mean, string prefix, bool full = true)
    {
        string candidate = r.Candidate?.Id ?? "base";
        var identity = new SampleIdentity(prefix, "fp-" + candidate, "cpu", r.Phase);
        var acc = new ExperimentAccumulator(identity, r.Requested, ["team.damage", "alice.damage", "team.fullBursts"]);
        var ids = ImmutableHashSet.CreateBuilder<string>();
        for (int i = 0; i < r.Requested; i++)
        {
            var id = prefix + ":" + i; ids.Add(id);
            acc.Add(new(id, 1, "completed", true, identity, new Dictionary<string, double>
            { ["team.damage"] = mean + i % 2, ["alice.damage"] = mean + i % 2, ["team.fullBursts"] = 1 }.ToImmutableDictionary()));
        }
        return new(acc.Snapshot(), ids.ToImmutable(), "same-deck-tactic-def-except-declared-ol", full);
    }
    [Fact] public async Task Winner_selection_does_not_reuse_lucky_screening_in_holdout()
    {
        int sequence = 0;
        var calls = new List<EvaluationRequest>();
        var s = Space();
        var result = await OverloadEvaluation.EvaluateAsync(s, (r, _) =>
        {
            calls.Add(r);
            // Winner is very lucky in exploration, but equal to baseline in fresh holdout.
            double mean = r.Phase == "final" ? 10 : r.Candidate!.Id == "ol-1" ? 1000 : 10;
            return Task.FromResult(Evaluation(r, mean, "experiment-" + sequence++));
        }, 4, 4, 6, 1);
        Assert.Single(result.Evaluations); Assert.Equal("ol-1", result.Shortlisted[0]);
        Assert.Equal("unresolved", result.Evaluations[0].TeamDifference.Decision);
        Assert.Equal(0, result.Evaluations[0].TeamDifference.Difference);
        Assert.Equal(2, calls.Count(c => c.Phase == "final"));
        Assert.False(result.GameVerified);
    }
    [Fact] public async Task Evaluation_rejects_scaled_logs_and_reused_samples()
    {
        await Assert.ThrowsAsync<InvalidOperationException>(() => OverloadEvaluation.EvaluateAsync(Space(),
            (r, _) => Task.FromResult(Evaluation(r, 1, "same", false)), 2, 2, 2));
        await Assert.ThrowsAsync<InvalidOperationException>(() => OverloadEvaluation.EvaluateAsync(Space(),
            (r, _) => Task.FromResult(Evaluation(r, 1, "same")), 2, 2, 2));
    }
    [Fact] public async Task Evaluation_cancel_does_not_run_more_batches()
    {
        using var cts = new CancellationTokenSource(); cts.Cancel(); int calls = 0;
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => OverloadEvaluation.EvaluateAsync(Space(), (r, _) =>
        { calls++; return Task.FromResult(Evaluation(r, 1, "test")); }, 2, 2, 2, cancellationToken: cts.Token));
        Assert.Equal(0, calls);
    }
}

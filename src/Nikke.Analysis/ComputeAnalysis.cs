using System.Collections.Immutable;
using System.Text.Json;
using System.Text.Json.Nodes;
using Nikke.Contracts;

namespace Nikke.Analysis;

/// <summary>Adapter for Backend contract f2327e5. Caller supplies only current accepted valid runs.</summary>
public sealed class ComputeAnalysis(
    Func<BatchStatus, BatchStatus, IReadOnlyList<OlChange>, bool>? verifyFrozenHoldoutDesign = null,
    int comparisonFamilySize = 1) : IComputeAnalysis
{
    public const string Version = "single-deck.analysis.1";
    private static Nikke.Contracts.Interval? Wire(Interval? i) => i is null ? null : new(i.Lower, i.Upper, i.Confidence, i.Method);
    private static MetricStatistics Wire(Distribution d, double? cut = null) => new(d.N, d.Mean, d.SampleSd, Wire(d.MeanCi),
        d.Median, d.P5, d.P95, cut, d.CutProbability, Wire(d.CutCi), d.QuantileMethod, d.Unit,
        d.N < 2 ? "mean_ci_requires_n_at_least_2" : null);
    public static ImmutableDictionary<string, double> Metrics(RunSummary run)
    {
        var values = ImmutableDictionary.CreateBuilder<string, double>();
        values.Add("team.damage", run.TeamDamage);
        values.Add("team.fullBursts", run.FullBursts);
        values.Add("execution.milliseconds", run.ElapsedMilliseconds);
        foreach (var m in run.Members)
        {
            values.Add($"{m.CharacterId}.damage", m.Damage);
            values.Add($"{m.CharacterId}.shots", m.Shots);
            values.Add($"{m.CharacterId}.hits", m.Hits);
            values.Add($"{m.CharacterId}.criticalHits", m.CriticalHits);
            values.Add($"{m.CharacterId}.reloads", m.Reloads);
            values.Add($"{m.CharacterId}.burstCasts", m.BurstCasts);
        }
        return values.ToImmutable();
    }
    public static ExperimentStatistics Aggregate(BatchStatus batch, IEnumerable<RunSummary> runs, double? cut = null)
    {
        var input = batch.Input;
        if (input.CharacterIds.Count != 5 || input.CharacterIds.Distinct().Count() != 5 || input.SynchroLevel != 400
            || batch.Requested < 1 || batch.Requested > 50000 || batch.Valid < 0 || batch.Failed < 0 || batch.Cancelled < 0
            || batch.Valid + batch.Failed + batch.Cancelled > batch.Requested || batch.Attempt < 1
            || input.Phase is not ("pilot" or "exploration" or "final") || (cut.HasValue && !double.IsFinite(cut.Value)))
            throw new ArgumentException("Invalid frozen batch metadata");
        var identity = new SampleIdentity(batch.Id, input.Fingerprint, batch.Execution.Backend,
            input.Phase == "exploration" ? "screening" : input.Phase);
        var names = new[] { "team.damage", "team.fullBursts", "execution.milliseconds" }.Concat(input.CharacterIds.SelectMany(id =>
            new[] { "damage", "shots", "hits", "criticalHits", "reloads", "burstCasts" }.Select(k => $"{id}.{k}")));
        var accumulator = new ExperimentAccumulator(identity, batch.Requested, names, cut);
        var indexes = new HashSet<int>();
        foreach (var run in runs)
        {
            if (run.ExperimentId != batch.Id || run.InputFingerprint != input.Fingerprint || run.Backend != batch.Execution.Backend
                || run.Phase != input.Phase || run.Attempt < 1 || run.Attempt > batch.Attempt || run.Index < 0 || run.Index >= batch.Requested
                || !indexes.Add(run.Index) || run.RunId != $"{batch.Id}:{run.Index}"
                || !run.Members.Select(m => m.CharacterId).SequenceEqual(input.CharacterIds)
                || run.Members.Any(m => m.CriticalHits > m.Hits)
                || Math.Abs(run.Members.Sum(m => m.Damage) - run.TeamDamage) > Math.Max(1e-7, Math.Abs(run.TeamDamage) * 1e-12))
                throw new ArgumentException("Mixed, duplicate, inconsistent or stale run summary");
            accumulator.Add(new(run.RunId, run.Attempt, "completed", true, identity, Metrics(run)));
        }
        var stats = accumulator.Snapshot();
        if (stats.Valid != batch.Valid || (!batch.Partial && (batch.State != "completed" || stats.Valid != batch.Requested)))
            throw new ArgumentException("Incomplete enumeration or inconsistent batch counts");
        return stats with { Failed = batch.Failed, Cancelled = batch.Cancelled,
            Incomplete = batch.Requested - batch.Valid - batch.Failed - batch.Cancelled, Partial = batch.Partial || stats.Partial };
    }
    public StatisticsResult Summarize(BatchStatus batch, IEnumerable<RunSummary> runs, double? cut)
    {
        var s = Aggregate(batch, runs, cut);
        return new(batch.Id, s.Partial, Wire(s.Metrics["team.damage"], cut),
            batch.Input.CharacterIds.ToImmutableDictionary(id => id, id => Wire(s.Metrics[$"{id}.damage"])),
            Version + "; shifted-Welford/Chan; fixed-N Student-t; type7; strict-cut Wilson; sample-error-only", false);
    }
    public OlComparison Compare(BatchStatus baseline, IEnumerable<RunSummary> baselineRuns,
        BatchStatus candidate, IEnumerable<RunSummary> candidateRuns, IReadOnlyList<OlChange> changes)
    {
        var a = baseline.Input; var b = candidate.Input;
        if (baseline.Id == candidate.Id || a.Fingerprint == b.Fingerprint || changes.Count == 0
            || a.SnapshotId != b.SnapshotId || a.DataVersion != b.DataVersion || a.EngineVersion != b.EngineVersion
            || a.RulesVersion != b.RulesVersion || a.DefPolicy != b.DefPolicy || a.DurationFrames != b.DurationFrames
            || !a.CharacterIds.SequenceEqual(b.CharacterIds) || baseline.Execution.Backend != candidate.Execution.Backend
            || a.Phase != b.Phase || changes.Any(c => !a.CharacterIds.Contains(c.CharacterId) || c.LineIndex < 1 || c.LineIndex > 3)
            || changes.GroupBy(c => (c.CharacterId, c.Slot, c.LineIndex)).Any(g => g.Count() > 1))
            throw new ArgumentException("Invalid independent OL comparison");
        var x = Aggregate(baseline, baselineRuns); var y = Aggregate(candidate, candidateRuns);
        var difference = Inference.Compare(x.Metrics["team.damage"], y.Metrics["team.damage"], comparisonFamilySize);
        var effects = new JsonObject();
        foreach (var k in x.Metrics.Keys.Where(k => k != "team.damage"))
            effects[k] = JsonSerializer.SerializeToNode(Inference.Compare(x.Metrics[k], y.Metrics[k], comparisonFamilySize), new JsonSerializerOptions(JsonSerializerDefaults.Web));
        // Fingerprint alone does not prove only the declared OL changed or that holdout was independent.
        string verdict = x.Partial || y.Partial ? "partial_unresolved" : a.Phase != "final" ? "exploratory_only"
            : verifyFrozenHoldoutDesign?.Invoke(baseline, candidate, changes) != true ? "unverified_design_or_input_difference"
            : difference.Decision;
        return new(baseline.Id, candidate.Id, changes.ToArray(), difference.Difference, Wire(difference.Ci), verdict, a.Phase,
            Version + "; independent Welch; Bonferroni; companion/cycle intervals exploratory", effects, false);
    }
}

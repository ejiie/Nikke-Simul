using System.Collections.Immutable;

namespace Nikke.Analysis;

// Slots/lines/values come from Backend's frozen, versioned catalog adapter. No invented rates/costs.
public sealed record EquipmentLine(string CharacterId, string Slot, int Line, string Option, double Value);
// Values is the exact signed tier allow-list validated by Backend's authoritative catalog adapter.
// Negative normalized charge-time/accuracy values must not be negated or rejected by Analysis.
public sealed record AllowedOption(string CharacterId, string Slot, string Option, ImmutableArray<double> Values,
    bool Supported, bool HasModeledEffect, bool ThresholdSensitive);
public sealed record OverloadCandidate(string Id, EquipmentLine Before, EquipmentLine After, bool ThresholdSensitive);
public sealed record CandidateSpace(string CatalogVersion, ImmutableArray<OverloadCandidate> Candidates,
    ImmutableArray<string> Exclusions);

public static class OverloadCandidates
{
    public static CandidateSpace Generate(string catalogVersion, IEnumerable<EquipmentLine> current, IEnumerable<AllowedOption> catalog)
    {
        if (string.IsNullOrWhiteSpace(catalogVersion)) throw new ArgumentException("Pinned OL catalog required");
        var lines = current.ToArray(); var options = catalog.ToArray();
        if (lines.Any(l => string.IsNullOrWhiteSpace(l.CharacterId) || string.IsNullOrWhiteSpace(l.Slot) || l.Line < 1 || l.Line > 3
            || string.IsNullOrWhiteSpace(l.Option) || !double.IsFinite(l.Value))
            || lines.GroupBy(l => (l.CharacterId, l.Slot, l.Line)).Any(g => g.Count() > 1)) throw new ArgumentException("Invalid actual equipment lines");
        var candidates = ImmutableArray.CreateBuilder<OverloadCandidate>();
        var exclusions = ImmutableArray.CreateBuilder<string>();
        foreach (var line in lines)
        foreach (var option in options.Where(o => o.CharacterId == line.CharacterId && o.Slot == line.Slot))
        {
            if (!option.Supported || !option.HasModeledEffect) { exclusions.Add($"{line.CharacterId}/{line.Slot}/{option.Option}:unsupported_or_no_effect"); continue; }
            if (string.IsNullOrWhiteSpace(option.Option) || option.Values.IsDefaultOrEmpty || option.Values.Any(v => !double.IsFinite(v)))
                throw new ArgumentException("Invalid authoritative option values");
            if (lines.Any(l => l.CharacterId == line.CharacterId && l.Slot == line.Slot && l.Line != line.Line && l.Option == option.Option))
            { exclusions.Add($"{line.CharacterId}/{line.Slot}/{line.Line}/{option.Option}:duplicate_on_equipment"); continue; }
            foreach (var value in option.Values.Distinct().Order())
            {
                if (option.Option == line.Option && value == line.Value) continue;
                var after = line with { Option = option.Option, Value = value };
                if (candidates.Any(c => c.Before == line && c.After == after)) continue;
                candidates.Add(new($"ol-{candidates.Count + 1}", line, after, option.ThresholdSensitive));
            }
        }
        return new(catalogVersion, candidates.ToImmutable(), exclusions.Distinct().ToImmutableArray());
    }
}

public sealed record EvaluationRequest(string Phase, int Requested, OverloadCandidate? Candidate);
public sealed record EvaluationBatch(ExperimentStatistics Statistics, ImmutableHashSet<string> RunIds,
    string ComparisonFingerprint, bool FullBattleRerun);
public sealed record CandidateEvaluation(OverloadCandidate Candidate, string BaselineExperimentId, string CandidateExperimentId,
    MeanDifference TeamDifference, ImmutableDictionary<string, MeanDifference> MetricDifferences);
public sealed record OverloadResult(ImmutableArray<string> Shortlisted, ImmutableArray<CandidateEvaluation> Evaluations,
    string Status = "model_based_option_value_only", bool GameVerified = false,
    string CostEfficiency = "unsupported: lock/probability/module-cost data not supplied");

/// <summary>Backend callback executes complete battles on immutable virtual inputs with independent RNG.
/// Screening selects a fixed family before fresh baseline/candidate holdout batches are requested.</summary>
public static class OverloadEvaluation
{
    public static async Task<OverloadResult> EvaluateAsync(CandidateSpace space,
        Func<EvaluationRequest, CancellationToken, Task<EvaluationBatch>> execute,
        int screeningN = 100, int refinementN = 1000, int finalN = 10000, int maxFinalists = 3,
        CancellationToken cancellationToken = default)
    {
        if (new[] { screeningN, refinementN, finalN }.Any(n => n < 2 || n > 50000) || maxFinalists < 1
            || space.Candidates.IsDefaultOrEmpty || space.Candidates.Select(c => c.Id).Distinct().Count() != space.Candidates.Length)
            throw new ArgumentException("Invalid frozen candidate space or sample budgets");
        var seenRuns = new HashSet<string>(); var seenExperiments = new HashSet<string>();
        string? common = null, backend = null;
        var candidateFingerprints = new Dictionary<string, string>();
        async Task<EvaluationBatch> Run(string phase, int n, OverloadCandidate? candidate)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var batch = await execute(new(phase, n, candidate), cancellationToken);
            var s = batch.Statistics;
            if (!batch.FullBattleRerun || s.Partial || s.Valid != n || s.Requested != n || s.Failed != 0 || s.Cancelled != 0 || s.Incomplete != 0
                || s.Identity.Phase != phase || batch.RunIds.Count != n || !s.Metrics.ContainsKey("team.damage")
                || s.Metrics.Values.Any(m => m.N != n) || batch.RunIds.Overlaps(seenRuns) || !seenExperiments.Add(s.Identity.ExperimentId))
                throw new InvalidOperationException("Full independent complete evaluation samples required; no reuse, log scaling or partial final ranking");
            if (string.IsNullOrWhiteSpace(batch.ComparisonFingerprint)) throw new InvalidOperationException("Frozen common settings fingerprint required");
            common ??= batch.ComparisonFingerprint; backend ??= s.Identity.NumericBackend;
            if (common != batch.ComparisonFingerprint || backend != s.Identity.NumericBackend) throw new InvalidOperationException("Mixed conditions/numeric backend");
            string key = candidate?.Id ?? "baseline";
            if (candidateFingerprints.TryGetValue(key, out var fp) && fp != s.Identity.InputFingerprint)
                throw new InvalidOperationException("Candidate input changed between phases");
            if (!candidateFingerprints.ContainsKey(key) && candidateFingerprints.Values.Contains(s.Identity.InputFingerprint))
                throw new InvalidOperationException("Different candidates have identical prepared input fingerprint");
            candidateFingerprints[key] = s.Identity.InputFingerprint;
            seenRuns.UnionWith(batch.RunIds);
            return batch;
        }
        var screening = new List<(OverloadCandidate Candidate, EvaluationBatch Batch)>();
        foreach (var c in space.Candidates) screening.Add((c, await Run("screening", screeningN, c)));
        // Sample mean is the first objective. Upper mean CI preserves uncertain candidates for refinement.
        var ranked = screening.OrderByDescending(x => x.Batch.Statistics.Metrics["team.damage"].Mean).ToArray();
        double leaderLower = ranked[0].Batch.Statistics.Metrics["team.damage"].MeanCi?.Lower ?? double.NegativeInfinity;
        var promising = ranked.Where((x, i) => i < maxFinalists || x.Candidate.ThresholdSensitive
            || (x.Batch.Statistics.Metrics["team.damage"].MeanCi?.Upper ?? double.PositiveInfinity) >= leaderLower).ToArray();
        var refined = new List<(OverloadCandidate Candidate, EvaluationBatch Batch)>();
        foreach (var c in promising) refined.Add((c.Candidate, await Run("refinement", refinementN, c.Candidate)));
        var finalists = refined.OrderByDescending(x => x.Batch.Statistics.Metrics["team.damage"].Mean)
            .Take(maxFinalists).Select(x => x.Candidate).ToArray();
        // Freeze family before any final data; no adaptive stopping or common random numbers.
        var baseline = await Run("final", finalN, null);
        var results = ImmutableArray.CreateBuilder<CandidateEvaluation>();
        foreach (var candidate in finalists)
        {
            var final = await Run("final", finalN, candidate);
            if (!final.Statistics.Metrics.Keys.ToHashSet().SetEquals(baseline.Statistics.Metrics.Keys)) throw new InvalidOperationException("Missing companion/cycle metrics");
            var changes = final.Statistics.Metrics.ToImmutableDictionary(p => p.Key,
                p => Inference.Compare(baseline.Statistics.Metrics[p.Key], p.Value, finalists.Length));
            results.Add(new(candidate, baseline.Statistics.Identity.ExperimentId, final.Statistics.Identity.ExperimentId,
                changes["team.damage"], changes));
        }
        return new(finalists.Select(c => c.Id).ToImmutableArray(), results.ToImmutable());
    }
}

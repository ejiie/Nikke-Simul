using System.Collections.Immutable;

namespace Nikke.Analysis;

// Internal analysis inputs, not an HTTP DTO. Backend owns the wire adapter.
public sealed record SampleIdentity(string ExperimentId, string InputFingerprint, string NumericBackend, string Phase);
public sealed record RunObservation(string RunId, int Attempt, string State, bool Complete,
    SampleIdentity Identity, ImmutableDictionary<string, double> Metrics);
public sealed record ExperimentStatistics(SampleIdentity Identity, long Requested, long Valid, long Failed,
    long Cancelled, long Incomplete, bool Partial, ImmutableDictionary<string, Distribution> Metrics);

/// <summary>One frozen experiment/phase/backend. Rejects duplicate runs including old attempts.</summary>
public sealed class ExperimentAccumulator
{
    private readonly SampleIdentity identity;
    private readonly int requested;
    private readonly ImmutableDictionary<string, DistributionAccumulator> metrics;
    private readonly HashSet<string> runIds = new(StringComparer.Ordinal);
    private long valid, failed, cancelled, incomplete;
    public ExperimentAccumulator(SampleIdentity identity, int requested, IEnumerable<string> metricNames, double? teamCut = null)
    {
        if (requested < 1 || requested > 50000 || new[] { identity.ExperimentId, identity.InputFingerprint, identity.NumericBackend }.Any(string.IsNullOrWhiteSpace)
            || identity.Phase is not ("pilot" or "screening" or "refinement" or "final")) throw new ArgumentException("Invalid experiment identity/budget");
        this.identity = identity;
        this.requested = requested;
        var names = metricNames.ToArray();
        if (names.Length == 0 || names.Distinct().Count() != names.Length || names.Any(string.IsNullOrWhiteSpace)) throw new ArgumentException("Invalid metric names");
        metrics = names.ToImmutableDictionary(n => n, n => new DistributionAccumulator(requested, n == "team.damage" ? teamCut : null,
            n.EndsWith(".damage", StringComparison.Ordinal) ? "damage" : n.EndsWith(".milliseconds", StringComparison.Ordinal) ? "ms" : "count"));
    }
    public void Add(RunObservation run)
    {
        // Validate before mutation: rejected input never poisons counts or accepted run IDs.
        if (run.Identity != identity || string.IsNullOrWhiteSpace(run.RunId) || run.Attempt < 1 || runIds.Contains(run.RunId))
            throw new ArgumentException("Mixed identity/backend/phase or duplicate run/attempt");
        if (runIds.Count >= requested) throw new InvalidOperationException("Experiment requested capacity exceeded");
        if (run.State is not ("completed" or "failed" or "cancelled")) throw new ArgumentException("Only terminal runs can be analyzed");
        bool accept = run.State == "completed" && run.Complete;
        if (accept && (run.Metrics.Count != metrics.Count || metrics.Keys.Any(k => !run.Metrics.TryGetValue(k, out var v)
            || !double.IsFinite(v) || v < 0 || v > 9e15))) throw new ArgumentException("Missing/nonfinite/invalid metrics");
        runIds.Add(run.RunId);
        if (run.State == "failed") { failed++; return; }
        if (run.State == "cancelled") { cancelled++; return; }
        if (!run.Complete) { incomplete++; return; }
        foreach (var pair in metrics) pair.Value.Add(run.Metrics[pair.Key]);
        valid++;
    }
    public void Merge(ExperimentAccumulator other)
    {
        if (ReferenceEquals(this, other) || identity != other.identity || metrics.Count != other.metrics.Count
            || !metrics.Keys.ToHashSet().SetEquals(other.metrics.Keys) || runIds.Overlaps(other.runIds)
            || runIds.Count + other.runIds.Count > requested) throw new ArgumentException("Incompatible experiment partitions");
        // All accumulators use the same requested capacity. Cut compatibility is checked before merging.
        foreach (var k in metrics.Keys)
            if (metrics[k].Threshold != other.metrics[k].Threshold) throw new ArgumentException("Mixed cut thresholds");
        foreach (var k in metrics.Keys) metrics[k].Merge(other.metrics[k]);
        runIds.UnionWith(other.runIds);
        valid += other.valid; failed += other.failed; cancelled += other.cancelled; incomplete += other.incomplete;
    }
    public ExperimentStatistics Snapshot() => new(identity, requested, valid, failed, cancelled, incomplete,
        valid != requested, metrics.ToImmutableDictionary(p => p.Key, p => p.Value.Snapshot()));
}

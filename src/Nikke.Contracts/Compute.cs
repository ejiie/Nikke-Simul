using System.Text.Json.Nodes;

namespace Nikke.Contracts;

public record GpuProfile(string DeviceId, string Name, string Vendor, string? Driver,
    long? MemoryBytes, string Backend, string RuntimeStatus, string SelfTestStatus,
    string CorrectnessStatus, string BenchmarkStatus, bool? SupportsFp64, bool Eligible, string? Reason);
public record HardwareProfile(string Fingerprint, string Os, string Architecture, int AvailableProcessors,
    int? PhysicalCores, long MemoryLimitBytes, bool RemoteSession, IReadOnlyList<GpuProfile> Gpus,
    IReadOnlyList<string> ProbeFailures);
public record ComputeOptions(string Requested = "auto", int? MaxWorkers = null, long? MemoryLimitBytes = null,
    string? DeviceId = null, bool Retune = false);
public record ExecutionSelection(string Requested, string Backend, string DeviceId, int Workers, int ChunkSize,
    long MemoryLimitBytes, string Reason, string ValidationVersion, string BenchmarkVersion,
    string Fingerprint, string? FallbackReason);
public record OlChange(string CharacterId, string Slot, int LineIndex, string OptionId, decimal Value);
public record OlCandidate(string Id, OlChange Before, OlChange After, bool ThresholdSensitive);
public record OlCandidateCatalog(string CatalogVersion, IReadOnlyList<OlCandidate> Candidates,
    IReadOnlyList<string> Exclusions, bool GameVerified = false);
public record ExperimentRequest(string SnapshotId, IReadOnlyList<string> CharacterIds, JsonObject Conditions,
    int Runs = 1000, string Phase = "final", string RecordLevel = "summary",
    ComputeOptions? Execution = null, IReadOnlyList<OlChange>? OlChanges = null, string? BaselineExperimentId = null,
    bool UseSavedTactic = true);
public record ExperimentInput(string Fingerprint, string SnapshotId, string DataVersion, string EngineVersion,
    string RulesVersion, IReadOnlyList<string> CharacterIds, int SynchroLevel, int DurationFrames,
    string Phase, string RecordLevel, string DefPolicy, bool GameVerified = false);
public record MemberRunSummary(string CharacterId, double Damage, long Shots, long Hits, long CriticalHits,
    long Reloads, long BurstCasts);
public record RunSummary(string RunId, int Attempt, int Index, string ExperimentId, string InputFingerprint,
    string Backend, string Phase, double TeamDamage, IReadOnlyList<MemberRunSummary> Members,
    int FullBursts, double ElapsedMilliseconds);
public record BatchStatus(string Id, string State, int Attempt, int Requested, int Valid, int Failed, int Cancelled,
    bool Partial, ExperimentInput Input, ExecutionSelection Execution, string? ErrorCode);
public record BatchResults(BatchStatus Batch, int Offset, int Limit, IReadOnlyList<RunSummary> Runs);
public record Interval(double Lower, double Upper, double Confidence, string Method);
public record MetricStatistics(long N, double? Mean, double? SampleSd, Interval? MeanCi,
    double? Median, double? P5, double? P95, double? Cut, double? CutSuccess, Interval? CutCi,
    string QuantileMethod, string Unit, string? UnsupportedReason = null);
public record StatisticsResult(string ExperimentId, bool Partial, MetricStatistics Team,
    IReadOnlyDictionary<string, MetricStatistics> Members, string MethodVersion, bool GameVerified = false);
public record OlComparison(string BaselineExperimentId, string CandidateExperimentId,
    IReadOnlyList<OlChange> Changes, double? TeamMeanDifference, Interval? DifferenceCi,
    string Verdict, string Phase, string MethodVersion, JsonObject? MemberAndCycleEffects = null,
    bool GameVerified = false);

// In-process boundaries. No engine, storage or analysis implementation dependency in wire DTOs.
public interface IPreparedExperiment
{
    ExperimentInput Input { get; }
    string PersistedInput { get; }
    RunSummary Run(string experimentId, int index, int attempt, CancellationToken cancellationToken);
}
public interface IComputeAnalysis
{
    StatisticsResult Summarize(BatchStatus batch, IEnumerable<RunSummary> runs, double? cut);
    OlComparison Compare(BatchStatus baseline, IEnumerable<RunSummary> baselineRuns,
        BatchStatus candidate, IEnumerable<RunSummary> candidateRuns, IReadOnlyList<OlChange> changes);
}

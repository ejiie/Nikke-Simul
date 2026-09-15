using System.Collections.Immutable;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using Nikke.Analysis;
using Nikke.Contracts;
using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Stats;

var json = new JsonSerializerOptions(JsonSerializerDefaults.Web) { WriteIndented = true };
if (args.Length < 2 || args[0] is not ("--engine-input" or "--batch-results"))
{
    Console.Error.WriteLine("Usage: --engine-input <native synthetic input.json> [runs 2..10] OR --batch-results <complete BatchResults JSON>; output in own artifacts/single-deck-statistics.");
    return 2;
}
var root = Directory.GetCurrentDirectory();
if (!File.Exists(Path.Combine(root, "tools", "single-deck-analysis", "SingleDeckAnalysis.csproj")))
    throw new InvalidOperationException("Run from this checkout root");
var output = Path.Combine(root, "artifacts", "single-deck-statistics", "integration-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(output);
var bytes = File.ReadAllBytes(args[1]);
var inputHash = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
if (args[0] == "--batch-results")
{
    var batch = JsonSerializer.Deserialize<BatchResults>(bytes, json)!;
    var report = new ComputeAnalysis().Summarize(batch.Batch, batch.Runs, null);
    File.WriteAllText(Path.Combine(output, "statistics.json"), JsonSerializer.Serialize(new { inputHash, report }, json));
}
else
{
    int n = args.Length > 2 ? int.Parse(args[2]) : 3;
    if (n < 2 || n > 10) throw new ArgumentOutOfRangeException(nameof(n), "This integration smoke test is capped at ten sequential runs; QA owns load benchmarks");
    var input = JsonSerializer.Deserialize<NativeInput>(bytes, json)!;
    if (input.Members.Length != 5 || input.Conditions.Combat.DurationFrames != 10800)
        throw new ArgumentException("Provide a five-member 180-second native synthetic engine fixture");
    // This is a test harness, not the product prepare/OL adapter. No seed, account, or cache access.
    var conditions = input.Conditions with { DamageLog = null!, Combat = input.Conditions.Combat with { Trace = false } };
    string experimentId = "native-synthetic-" + Guid.NewGuid().ToString("N");
    var identity = new SampleIdentity(experimentId, inputHash + ":damageLog-off", "cpu", "pilot");
    var rows = new List<RunSummary>();
    for (int i = 0; i < n; i++)
    {
        var sink = new Counters(); var watch = Stopwatch.StartNew();
        var result = SkillReplay.Run(input.Members, input.Graph, conditions, new FreshRandom(), sink);
        watch.Stop();
        if (result.Members.Count != 5 || result.Members.Any(m => !double.IsFinite(m.Damage))) throw new InvalidOperationException("Invalid engine output");
        var members = result.Members.Select(m => new MemberRunSummary(m.CharacterId, m.Damage, m.Shots, m.Hits, m.CriticalHits,
            sink.Reloads.GetValueOrDefault(m.CharacterId), sink.Bursts.GetValueOrDefault(m.CharacterId))).ToArray();
        rows.Add(new($"{experimentId}:{i}", 1, i, experimentId, identity.InputFingerprint, "cpu", "pilot", result.TotalDamage,
            members, result.TeamBurst?.FullBursts.Count ?? 0, watch.Elapsed.TotalMilliseconds));
    }
    var accumulator = new ExperimentAccumulator(identity, n, ComputeAnalysis.Metrics(rows[0]).Keys);
    foreach (var row in rows) accumulator.Add(new(row.RunId, row.Attempt, "completed", true, identity, ComputeAnalysis.Metrics(row)));
    var stats = accumulator.Snapshot();
    if (Math.Abs(stats.Metrics["team.damage"].Mean!.Value - rows.Average(r => r.TeamDamage)) > 1e-6)
        throw new InvalidOperationException("Independent array mean mismatch");
    var report = new { evidence = "synthetic_input_actual_engine_execution", gameVerified = false, inputHash,
        engineVersion = SkillReplay.Version, fixedDefense = conditions.Combat.EnemyDefense,
        durationFrames = conditions.Combat.DurationFrames, nativeFixtureHasNoSynchroLevel = true,
        rng = "new Random() per run; no explicit seed", statistics = stats, runs = rows,
        note = "Integration smoke test, not throughput benchmark or official five-character OL evaluation" };
    File.WriteAllText(Path.Combine(output, "statistics.json"), JsonSerializer.Serialize(report, json));
}
if (inputHash != Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[1]))).ToLowerInvariant()) throw new IOException("Source changed during analysis");
Console.WriteLine(JsonSerializer.Serialize(new { output }));
return 0;

sealed record NativeInput(SkillReplayMember[] Members, SkillGraph Graph, SkillReplayConditions Conditions);
sealed class FreshRandom : IRandomSource
{
    private readonly Random random = new();
    public double NextDouble() => random.NextDouble();
}
sealed class Counters : ICombatEventSink
{
    public readonly Dictionary<string, long> Reloads = [];
    public readonly Dictionary<string, long> Bursts = [];
    public void OnEvent(CombatEvent e)
    {
        if (e.Kind == CombatEventKind.ReloadCompleted) Reloads[e.Source] = Reloads.GetValueOrDefault(e.Source) + 1;
        // A burst requests its full-burst duration once; ordinary skill casts do not.
        if (e.Kind == CombatEventKind.FullBurstDurationRequested) Bursts[e.Source] = Bursts.GetValueOrDefault(e.Source) + 1;
    }
}

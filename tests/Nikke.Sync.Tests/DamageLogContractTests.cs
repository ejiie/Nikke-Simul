using System.Globalization;
using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Data;

namespace Nikke.Sync.Tests;

public sealed class DamageLogContractTests
{
    [Fact]
    public void Missing_log_and_collected_zero_are_distinct_and_csv_retains_metadata()
    {
        const string legacy = "{\"id\":\"synthetic\",\"result\":{}}";
        Assert.Equal("not_collected", DamageLogExport.Read(legacy)["collectionStatus"]!.GetValue<string>());
        const string zero = "{\"id\":\"synthetic\",\"result\":{\"damageLog\":{\"schemaVersion\":1,\"status\":\"complete\",\"entries\":[],\"totalDamage\":0}}}";
        Assert.Equal("complete", DamageLogExport.Read(zero)["collectionStatus"]!.GetValue<string>());
        Assert.Contains("not_collected", DamageLogExport.Csv(legacy));
        Assert.Contains("totalDamage", DamageLogExport.Csv(zero));
        Assert.Equal(2, DamageLogExport.Csv(zero).Split("\r\n", StringSplitOptions.RemoveEmptyEntries).Length);
    }

    [Fact]
    public void Csv_keeps_capture_order_units_sums_and_context_under_non_english_culture()
    {
        // E1 contract-shaped synthetic hits, not actual engine output or game observations.
        var replay = new { id = "synthetic", accountSnapshotId = "account-snapshot", runtimeDataId = "runtime",
            result = new { conditions = new { roundingPolicy = "synthetic" }, damageLog = new { schemaVersion = 1, status = "complete", totalDamage = 3.75,
                entries = new[] {
                    new { frame = 60, seconds = 1.0, hitId = 9, shotId = 7, damage = 1.25, cumulativeDamage = 1.25, effect = "comma,quote\"", ownBurstEffectActive = false },
                    new { frame = 60, seconds = 1.0, hitId = 10, shotId = 7, damage = 2.5, cumulativeDamage = 3.75, effect = "second", ownBurstEffectActive = true }
                } } } };
        var before = CultureInfo.CurrentCulture;
        try
        {
            CultureInfo.CurrentCulture = CultureInfo.GetCultureInfo("fr-FR");
            var csv = DamageLogExport.Csv(Wire.Serialize(replay));
            var lines = csv.Split("\r\n", StringSplitOptions.RemoveEmptyEntries);
            Assert.Equal(4, lines.Length);
            Assert.StartsWith("hit,\"60\",\"1\",\"9\",\"7\",\"1.25\",\"1.25\",", lines[2]);
            Assert.StartsWith("hit,\"60\",\"1\",\"10\",\"7\",\"2.5\",\"3.75\",", lines[3]);
            Assert.Contains("account-snapshot", lines[1]);
            Assert.Contains("roundingPolicy", lines[1]);
            Assert.Contains("ownBurstEffectActive", lines[2]);
            Assert.Contains("comma,quote", lines[2]);
        }
        finally { CultureInfo.CurrentCulture = before; }
    }

    [Fact]
    public void Unknown_schema_is_preserved_in_json_but_not_misinterpreted_as_csv()
    {
        const string json = "{\"result\":{\"damageLog\":{\"schemaVersion\":99,\"status\":\"future\"}}}";
        Assert.Equal(99, DamageLogExport.Read(json)["replay"]!["result"]!["damageLog"]!["schemaVersion"]!.GetValue<int>());
        Assert.Throws<InvalidOperationException>(() => DamageLogExport.Csv(json));
    }

    [Fact]
    public void Unintegrated_engine_features_are_not_silently_ignored()
    {
        // Baseline e693585 has neither new engine property.
        if (typeof(Nikke.Engine.Skills.SkillReplayConditions).GetProperty("DamageLog") is null)
            Assert.Throws<InvalidOperationException>(() => RuntimeReplayService.ReadSkillRequest(JsonNode.Parse("{\"conditions\":{\"damageLog\":{}}}")!.AsObject()));
        if (typeof(Nikke.Engine.Skills.TeamBurstOptions).GetProperty("Tactic") is null)
            Assert.Throws<InvalidOperationException>(() => RuntimeReplayService.ReadSkillRequest(JsonNode.Parse("{\"conditions\":{\"autoBurst\":{\"tactic\":{}}}}")!.AsObject()));
    }

    private static readonly Dictionary<string, int> Stages = new() { ["i"] = 1, ["ii"] = 2, ["5004"] = 3, ["other"] = 3 };
    private static BurstTacticSettings Valid => new() { AllowedCharacterIds = ["i", "ii", "5004"], Stage1Priority = ["i"], Stage2Priority = ["ii"], Stage3Priority = ["5004"], Burst3Rotation = ["5004"] };

    [Fact]
    public void Tactic_rejects_excluded_stale_duplicate_and_wrong_stage_candidates()
    {
        Assert.Empty(BurstTacticValidation.Validate(Valid, Stages));
        foreach (var bad in new[] { Valid with { AllowedCharacterIds = ["i", "ii", "missing"] },
            Valid with { Stage1Priority = ["ii"] }, Valid with { Stage3Priority = ["5004", "5004"] },
            Valid with { Burst3Rotation = ["other"] }, Valid with { FirstBurst3CharacterId = "other" },
            Valid with { SchemaVersion = 2 }, Valid with { AllowedCharacterIds = null! } })
            Assert.Throws<ArgumentException>(() => BurstTacticValidation.Validate(bad, Stages));
        var changed = new Dictionary<string, int>(Stages); changed.Remove("5004");
        Assert.Throws<ArgumentException>(() => BurstTacticValidation.Validate(Valid, changed));
    }

    [Fact]
    public void Incomplete_draft_is_distinct_from_legacy_and_executable_tactic()
    {
        Assert.Equal(new[] { "missing_stage_1", "missing_stage_2", "missing_stage_3" }, BurstTacticValidation.Validate(new(), Stages));
        Assert.Empty(BurstTacticValidation.Validate(null, Stages));
        Assert.Empty(BurstTacticValidation.Validate(Valid, Stages));
    }
}

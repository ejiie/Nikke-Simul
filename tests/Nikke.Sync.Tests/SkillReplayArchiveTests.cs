using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Data;
using Nikke.Engine.Skills;

namespace Nikke.Sync.Tests;

// Synthetic persistence fixtures; these do not establish a new engine/API schema.
public sealed class SkillReplayArchiveTests : IDisposable
{
    private readonly string root = Path.Combine(Path.GetTempPath(), "nikke-replay-archive-tests", Guid.NewGuid().ToString("N"));
    private readonly string id = Guid.NewGuid().ToString("N");
    private SkillReplayArchive Archive => new(root);

    [Fact]
    public void Restart_and_json_export_preserve_unknown_fields_nulls_order_and_decimal_text()
    {
        string json = $$$"""
        {"id":"{{{id}}}","accountSnapshotId":"synthetic-account-snapshot","calculationDataId":"synthetic-calculation","runtimeDataId":"synthetic-runtime","mockOnly":true,"futureOpaqueResult":{"schemaVersion":"mock-not-contract","complete":false,"reason":"synthetic truncation","rows":[{"frame":60,"hit":2,"damage":0.1250,"ownBurst":null},{"frame":60,"hit":3,"damage":7}],"unsupported":["synthetic"]}}
        """;
        Archive.Save(id, json);
        Assert.Equal(json, new SkillReplayArchive(root).ReadJson(id));
        Assert.Single(Directory.GetFiles(root));
    }

    [Fact]
    public void Legacy_missing_log_is_not_fabricated_as_empty_or_zero()
    {
        var json = Wire.Serialize(new { id, result = new { rulesVersion = "p04.team.2", totalDamage = 123 } });
        Archive.Save(id, json);
        var restored = JsonNode.Parse(Archive.ReadJson(id))!;
        Assert.False(restored["result"]!.AsObject().ContainsKey("damageLog"));
        Assert.Equal(json, Archive.ReadJson(id));
    }

    [Fact]
    public void Legacy_tactic_defaults_and_explicit_rotation_survive_storage()
    {
        var defaults = Wire.Read<TeamBurstOptions>("{}");
        Assert.Equal("source_full_charge_v2", defaults.GaugeModel);
        Assert.Equal("next_ready", defaults.UnavailablePolicy);
        Assert.Empty(defaults.Burst3Rotation);
        Assert.Equal(1, defaults.StageDelayMinFrames);
        Assert.Equal(10, defaults.StageDelayMaxFrames);
        Assert.Equal(28, defaults.FullBurstEntryDelayFrames);
        var options = defaults with { Burst3Rotation = ["5004", "synthetic-burst3"], UnavailablePolicy = "wait_preferred" };
        var json = Wire.Serialize(new { id, result = new { conditions = new { autoBurst = options } } });
        Archive.Save(id, json);
        Assert.Equal(json, Archive.ReadJson(id));
    }

    [Fact]
    public void Duplicate_save_cannot_overwrite_result_and_cleans_its_temporary_file()
    {
        var json = Wire.Serialize(new { id, value = 1 });
        Archive.Save(id, json);
        Assert.Throws<IOException>(() => Archive.Save(id, Wire.Serialize(new { id, value = 2 })));
        Assert.Equal(json, Archive.ReadJson(id));
        Assert.Single(Directory.GetFiles(root));
    }

    [Fact]
    public void Invalid_identity_and_paths_cannot_publish_files()
    {
        Assert.Throws<InvalidDataException>(() => Archive.Save(id, "{}"));
        Assert.Throws<InvalidDataException>(() => Archive.Save(id, Wire.Serialize(new { id = Guid.NewGuid().ToString("N") })));
        foreach (var invalid in new[] { "../outside", "", "C:/outside", id + ".json" })
        {
            Assert.Throws<ArgumentException>(() => Archive.Save(invalid, "{}"));
            Assert.Throws<ArgumentException>(() => Archive.ReadJson(invalid));
        }
        Assert.False(Directory.Exists(root));
    }

    [Fact]
    public void Missing_or_misidentified_saved_result_is_not_returned()
    {
        Assert.Throws<KeyNotFoundException>(() => Archive.ReadJson(id));
        Directory.CreateDirectory(root);
        File.WriteAllText(Path.Combine(root, id + ".json"), "{\"id\":\"different\"}");
        Assert.Throws<InvalidDataException>(() => Archive.ReadJson(id));
    }

    [Fact]
    public void Independent_storage_roots_do_not_share_results()
    {
        Archive.Save(id, Wire.Serialize(new { id }));
        Assert.Throws<KeyNotFoundException>(() => new SkillReplayArchive(Path.Combine(root, "other")).ReadJson(id));
        Assert.False(Directory.Exists(Path.Combine(root, "other")));
    }

    public void Dispose()
    {
        var expected = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "nikke-replay-archive-tests")) + Path.DirectorySeparatorChar;
        if (!Path.GetFullPath(root).StartsWith(expected, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("Unsafe test cleanup path");
        if (Directory.Exists(root)) Directory.Delete(root, true);
    }
}

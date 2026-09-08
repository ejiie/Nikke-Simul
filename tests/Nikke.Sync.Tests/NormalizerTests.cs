using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Data;

namespace Nikke.Sync.Tests;

public class NormalizerTests
{
    private static AccountSnapshot Normalize(RawEnvelope raw, GameSnapshot? game = null) => new SnapshotNormalizer().Normalize(raw, game ?? Fixtures.Game(), "account", "synthetic-account", 83, "manifest");
    [Fact] public void Round_trip_preserves_source_slots_units_and_equipment_identity()
    {
        var result = Wire.Read<AccountSnapshot>(Wire.Serialize(Normalize(Fixtures.Raw())));
        Assert.True(result.Valid); var c = Assert.Single(result.Characters);
        Assert.Equal(400, c.Level); Assert.Equal(200, c.NativeLevel); Assert.Equal(25, c.Bond);
        Assert.Equal(4, c.Equipment.Count); Assert.All(c.Equipment, eq => Assert.Equal(3, eq.Lines.Count));
        var line = c.Equipment[0].Lines[0]; Assert.Equal("11", line.OptionId); Assert.Equal(1181m, line.RawValue);
        Assert.Equal(0.1181m, line.NormalizedValue); Assert.Equal("Percent", line.RawUnit); Assert.Equal("ratio", line.Unit);
        Assert.Equal(-0.014m, c.Equipment[0].Lines[1].NormalizedValue);
        Assert.Equal("absent", c.Equipment[0].Lines[2].Presence); Assert.Equal("unknown", line.LockState);
        Assert.Equal("SSR", c.CollectionGrade); Assert.Equal(2, c.FavoriteStage); Assert.Equal("5", c.CubeId);
    }
    [Fact] public void Duplicate_details_cannot_disguise_a_missing_character()
    {
        var raw = Fixtures.Raw(); raw.Characters.Add(JsonNode.Parse("""{"name_code":102,"lv":400,"grade":3,"core":2}""")); raw.Details.Add(raw.Details[0]!.DeepClone());
        Assert.Contains(Normalize(raw).Issues, x => x.Code == "missing_detail");
    }
    [Fact] public void Equal_duplicates_are_deduplicated_but_conflicts_fail()
    {
        var raw = Fixtures.Raw(); raw.Details.Add(raw.Details[0]!.DeepClone());
        Assert.True(Normalize(raw).Valid); raw.Details[1]!["attractive_lv"] = 30;
        Assert.Contains(Normalize(raw).Issues, x => x.Code == "duplicate_conflict" && x.Severity == "error");
    }
    [Fact] public void Account_and_server_mismatch_never_pass()
    {
        Assert.False(Normalize(Fixtures.Raw() with { Area = 81 }).Valid);
        Assert.False(Normalize(Fixtures.Raw() with { OpenId = "different" }).Valid);
    }
    [Fact] public void Optional_unknown_values_do_not_become_zero_or_maximum()
    {
        var result = Normalize(Fixtures.Raw() with { Outpost = null });
        Assert.True(result.Valid); Assert.Null(result.Consoles); Assert.Null(result.SynchroLevel);
        Assert.Equal("unknown", result.Characters[0].Equipment[0].Lines[0].LockState);
    }
    [Fact] public void Missing_skill_and_option_slot_are_errors()
    {
        var raw = Fixtures.Raw(); raw.Details[0]!.AsObject().Remove("skill1_lv"); raw.Details[0]!.AsObject().Remove("head_equip_option2_id");
        var result = Normalize(raw); Assert.False(result.Valid); Assert.Null(result.Characters[0].Skills["1"]);
        Assert.Equal("unknown", result.Characters[0].Equipment[0].Lines[1].Presence);
    }
    [Fact] public void Unknown_character_is_preserved_without_claiming_engine_support()
    {
        var result = Normalize(Fixtures.Raw(), Fixtures.Game() with { Names = [] });
        Assert.True(result.Valid); Assert.Equal("101", result.Characters[0].CharacterId);
        Assert.False(result.Characters[0].CatalogKnown); Assert.Equal("not_evaluated", result.Characters[0].CombatSupport);
    }
    [Fact] public void Unknown_collection_keeps_id_and_level()
    {
        var raw = Fixtures.Raw(); raw.Details[0]!["favorite_item_tid"] = 999;
        var c = Normalize(raw).Characters[0]; Assert.Equal("999", c.CollectionId); Assert.Equal(1, c.CollectionLevel); Assert.Null(c.CollectionGrade);
    }
    [Fact] public void Off_table_option_is_not_snapped_to_nearest_tier()
    {
        var raw = Fixtures.Raw(); raw.StateEffects[0]!["function_details"]![0]!["function_value"] = 1181.5m;
        var line = Normalize(raw).Characters[0].Equipment[0].Lines[0]; Assert.Null(line.ValueTier); Assert.Equal(0.11815m, line.NormalizedValue);
    }
    [Theory] [InlineData("Bogus")] [InlineData("")]
    public void Unknown_option_unit_blocks_publish(string unit)
    {
        var raw = Fixtures.Raw(); raw.StateEffects[0]!["function_details"]![0]!["function_value_type"] = unit;
        Assert.False(Normalize(raw).Valid);
    }
    [Fact] public void Changed_roster_is_rejected()
    {
        var raw = Fixtures.Raw(); raw.RosterAfter![0]!["core"] = 3;
        Assert.Contains(Normalize(raw).Issues, x => x.Code == "roster_changed");
    }
    [Theory] [InlineData("StatCritical")] [InlineData("StatCriticalDamage")] [InlineData("StatChargeDamage")]
    public void Integer_encoded_rate_options_are_not_flat_counts(string type)
    {
        var raw = Fixtures.Raw(); var effect = raw.StateEffects[0]!["function_details"]![0]!;
        effect["function_type"] = type; effect["function_value_type"] = "Integer";
        var line = Normalize(raw).Characters[0].Equipment[0].Lines[0];
        Assert.Equal("Integer", line.RawUnit); Assert.Equal(1181m, line.RawValue);
        Assert.Equal("ratio", line.Unit); Assert.Equal(0.1181m, line.NormalizedValue);
    }
}

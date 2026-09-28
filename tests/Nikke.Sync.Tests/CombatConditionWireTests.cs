using System.Text.Json.Nodes;
using Nikke.Data;

namespace Nikke.Sync.Tests;

public class CombatConditionWireTests
{
    [Fact] public void Case_insensitive_envelope_cannot_disagree_with_typed_engine_or_candidate_mode()
    {
        var upper=JsonNode.Parse("""{"Combat":{"bossDistance":35,"bossWeakElement":"Fire"}}""")!.AsObject();
        Assert.Equal("per_member",CombatConditionWire.Inspect(CombatConditionWire.ReadCombat(upper)).Mode);
        upper["combat"]=new JsonObject();
        Assert.Throws<ArgumentException>(()=>CombatConditionWire.ReadCombat(upper));
    }
    [Fact] public void Old_archive_label_does_not_rewrite_conditions_or_results()
    {
        const string json="""{"id":"historical","result":{"conditions":{"combat":{"properDistance":true,"elementAdvantage":true}},"totalDamage":123,"unknown":{"x":0.1250}}}""";
        var result=CombatConditionWire.FromReplay(json);
        Assert.Equal("legacy_global",result.Mode);Assert.True(result.LegacyProperDistance);Assert.True(result.LegacyElementAdvantage);
    }
    [Fact] public void Explicit_null_new_fields_and_legacy_false_are_different_saved_modes()
    {
        var modern=CombatConditionWire.Inspect(JsonNode.Parse("""{"bossDistance":null,"bossWeakElement":null}""")!.AsObject());
        var old=CombatConditionWire.Inspect(JsonNode.Parse("""{"properDistance":false,"elementAdvantage":false}""")!.AsObject());
        Assert.Equal("per_member",modern.Mode);Assert.Equal("legacy_global",old.Mode);
        Assert.Contains("전원 적용",old.Label);Assert.Null(modern.BossDistance);Assert.Null(modern.BossWeakElement);
    }
    [Theory]
    [InlineData("{\"bossDistance\":35,\"properDistance\":false}")]
    [InlineData("{\"bossDistance\":null,\"elementAdvantage\":false}")]
    [InlineData("{\"bossDistance\":35.5}")]
    [InlineData("{\"bossDistance\":-1}")]
    [InlineData("{\"bossDistance\":101}")]
    [InlineData("{\"bossWeakElement\":\"Electric\"}")]
    [InlineData("{\"bossWeakElement\":\"fire\"}")]
    [InlineData("{\"BossDistance\":35}")]
    public void Invalid_or_ambiguous_wire_is_not_silently_reinterpreted(string json)
        =>Assert.Throws<ArgumentException>(()=>CombatConditionWire.Inspect(JsonNode.Parse(json)!.AsObject()));
}

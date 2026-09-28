using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Core.Stats;
using Nikke.Data;

namespace Nikke.Sync.Tests;

public sealed class HitWireTests
{
    private static JsonObject Input(string json) => JsonNode.Parse(json)!.AsObject();
    [Fact] public void V2_conversion_is_explicit_preserves_source_and_saves_the_selected_audit()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"../../../../../artifacts/client-f32-integration/hit",Guid.NewGuid().ToString("N")));
        var service=new HitCalculationService(root);
        var source=Input("""{"statAttack":100,"runtimeAttackBuffs":[{"source":"skill","rate":0.145}]}""");
        var before=source.ToJsonString();var result=service.Calculate(new(source,null,2));
        Assert.Equal(before,source.ToJsonString());Assert.Equal(2,result.Conversion.OriginalSchemaVersion);
        Assert.True(result.Conversion.Converted);Assert.Equal(1,result.Input["statDamageRatio"]!.GetValue<double>());
        Assert.Equal(0,result.Input["defenceRatioRate"]!.GetValue<double>());Assert.Equal("115",result.ExactEffectiveAttack);
        Assert.Equal(HitWire.Policies,result.Candidates.Select(c=>c.Policy));Assert.Equal("client_f32",result.SelectedPolicy);
        Assert.Contains(result.SelectedCandidate.Terms,t=>t.Name=="B");
        Assert.Equal(Wire.Serialize(result),Wire.Serialize(service.Read(result.Id)));
    }
    [Fact] public void Saved_v2_download_import_retains_original_artifact_without_modification()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"../../../../../artifacts/client-f32-integration/hit",Guid.NewGuid().ToString("N")));
        var artifact=Input("""{"schemaVersion":2,"inputSchemaVersion":2,"kind":"single_hit_calibration","notes":"historical","comparison":{"input":{"statAttack":100},"observedDamage":99,"candidates":[]}}""");
        var before=artifact.ToJsonString();var service=new HitCalculationService(root);var result=service.Import(artifact);
        Assert.Equal(before,artifact.ToJsonString());Assert.Equal(before,result.SourceArtifact!.ToJsonString());
        Assert.True(service.Read(result.Id).Conversion.Converted);Assert.Equal(99,result.ObservedDamage);
    }
    [Fact] public void New_rates_affect_client_but_historical_policies_remain_selectable()
    {
        var input=Input("""{"statAttack":100,"statDamageRatio":2,"defenceRatioRate":0.25}""");
        var result=HitCalculationService.Evaluate(new(input,null,3,"legacy_term_floor"));
        Assert.False(result.Conversion.Converted);Assert.Equal(100,result.SelectedCandidate.Damage);
        Assert.Equal(150,result.Candidates[0].Damage);Assert.Equal("150",result.Candidates[0].ExactDamage);
        Assert.Contains(result.SelectedCandidate.Terms,t=>t.Name=="B3");
    }
    [Theory]
    [InlineData("{\"statAttack\":100.5}")]
    [InlineData("{\"statAttack\":100.000000000000000000000000000001}")]
    [InlineData("{\"statAttack\":1e-400}")]
    [InlineData("{\"statAttack\":100,\"attackFlatBuffs\":[{\"source\":\"x\",\"amount\":1.000000000000000000000000000001,\"exactAmount\":\"1\"}]}")]
    [InlineData("{\"statAttack\":100,\"defense\":0.1}")]
    [InlineData("{\"statAttack\":100,\"runtimeAttackBuffs\":[{\"source\":\"x\",\"rate\":0.01401}]}")]
    [InlineData("{\"statAttack\":100,\"runtimeAttackBuffs\":[{\"source\":\"x\",\"rate\":0.01400000000000000001}]}")]
    [InlineData("{\"statAttack\":100,\"attackFlatBuffs\":[{\"source\":\"x\",\"amount\":0.5}]}")]
    [InlineData("{\"statAttack\":100,\"attackBuffs\":[{\"source\":\"x\",\"rate\":0.1,\"rawRate10000\":\"2000\"}]}")]
    [InlineData("{\"statAttack\":100,\"attackFlatBuffs\":[{\"source\":\"x\",\"exactAmount\":9007199254740993}]}")]
    [InlineData("{\"statAttack\":100,\"StatAttack\":200}")]
    [InlineData("{\"statAttack\":100,\"attackBuffs\":null}")]
    public void Invalid_inputs_fail_without_truncation(string json)
        =>Assert.Throws<ArgumentException>(()=>HitCalculationService.Evaluate(new(Input(json),null,3)));
    [Fact] public void Exact_integer_strings_roundtrip_and_unavailable_legacy_is_explicit()
    {
        var input=Input("""{"statAttack":0,"attackFlatBuffs":[{"source":"fixture","exactAmount":"9007199254740993"}]}""");
        var result=HitCalculationService.Evaluate(new(input,null,3));
        Assert.Equal("9007199254740993",result.ExactEffectiveAttack);
        Assert.Equal("9007199254740993",result.Input["attackFlatBuffs"]![0]!["exactAmount"]!.GetValue<string>());
        Assert.Equal("available",result.Candidates[0].Status);
        Assert.All(result.Candidates.Skip(1),c=>{Assert.Equal("unavailable",c.Status);Assert.Null(c.Damage);});
        var buff=Wire.Read<StatFlatBuff>(Wire.Serialize(StatFlatBuff.FromInteger("fixture",long.MaxValue)));
        Assert.Equal(long.MaxValue,buff.ExactAmount);
    }
    [Fact] public void Raw_rate_wire_and_snapshot_adapter_keep_source_numerator()
    {
        var line=new EquipmentLine{NormalizedValue=.145m,RawValue=1450,RawUnit="Percent"};
        var buff=CalculationService.AttackOption("source",line);Assert.Equal(1450,buff.RawRate10000);
        Assert.Equal("1450",Input(Wire.Serialize(buff))["rawRate10000"]!.GetValue<string>());
        var input=Input("""{"statAttack":100,"attackBuffs":[{"source":"OL","rawRate10000":"1450"}]}""");
        Assert.Equal("115",HitCalculationService.Evaluate(new(input,null,3)).ExactEffectiveAttack);
        Assert.Throws<ArgumentException>(()=>CalculationService.AttackOption("x",line with {RawValue=1400}));
        Assert.Throws<ArgumentException>(()=>CalculationService.AttackOption("x",line with {RawValue=null,NormalizedValue=.01401m}));
    }
    [Fact] public void Version_and_overflow_errors_are_not_silent_fallbacks()
    {
        Assert.Throws<ArgumentException>(()=>HitCalculationService.Evaluate(new(Input("""{"statAttack":100}"""),null,1)));
        Assert.Throws<ArgumentException>(()=>HitCalculationService.Evaluate(new(Input("""{"statAttack":100,"statDamageRatio":2}"""),null,2)));
        var error=Assert.Throws<ArgumentException>(()=>HitCalculationService.Evaluate(new(Input("""{"statAttack":1000000000000,"coefficient":1000000000000}"""),null,3)));
        Assert.Contains("overflow",error.Message);
    }
}

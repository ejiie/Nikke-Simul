using System.Text.Json.Nodes;
using Nikke.Data;

namespace Nikke.Sync.Tests;

public class SoloRaidRequestPolicyTests
{
    [Fact] public void New_defaults_are_explicit_and_original_JSON_is_unchanged()
    {
        var original=JsonNode.Parse("{\"Combat\":{\"enemyDefense\":31784}}")!.AsObject();
        var normalized=SoloRaidRequestPolicy.Normalize(original,null);
        Assert.Null(original["Combat"]!["defenseMode"]);
        Assert.False(normalized.ContainsKey("Combat"));
        var c=normalized["combat"]!;
        Assert.Equal(10800,c["durationFrames"]!.GetValue<int>());
        Assert.Equal("per_trigger",c["pelletCoefficientPolicy"]!.GetValue<string>());
        Assert.Equal("team_damage_threshold",c["defenseMode"]!.GetValue<string>());
        Assert.Equal(30925,c["enemyDefense"]!.GetValue<double>());
        Assert.Equal("sample",c["critMode"]!.GetValue<string>());
    }
    [Theory]
    [InlineData("durationFrames","120")][InlineData("durationFrames","null")]
    [InlineData("durationFrames","\"10800\"")][InlineData("durationFrames","10800.5")]
    [InlineData("pelletCoefficientPolicy","\"per_pellet\"")][InlineData("pelletCoefficientPolicy","null")]
    [InlineData("defenseMode","\"fixed\"")][InlineData("defenseMode","null")]
    [InlineData("enemyDefense","0.5")][InlineData("enemyDefense","\"30925\"")]
    [InlineData("enemyDefense","null")][InlineData("DurationFrames","10800")]
    public void Invalid_new_fixed_values_are_not_silently_reinterpreted(string key,string value)
    {
        var c=new JsonObject{[key]=JsonNode.Parse(value)};
        Assert.Throws<ArgumentException>(()=>SoloRaidRequestPolicy.Normalize(new(){["combat"]=c},null));
    }
    [Fact] public void Legacy_is_explicit_and_preserves_old_time_DEF_pellet_and_crit_values()
    {
        var old=JsonNode.Parse("{\"combat\":{\"durationFrames\":120,\"enemyDefense\":31784,\"pelletCoefficientPolicy\":\"per_pellet\",\"critMode\":\"off\"}}")!.AsObject();
        var normalized=SoloRaidRequestPolicy.Normalize(old,"legacy");
        var display=SoloRaidRequestPolicy.FromJson(normalized);
        Assert.Equal("fixed",display.DefenseMode);Assert.Equal(31784,display.InitialDefense);
        Assert.Equal(120,display.DurationFrames);Assert.Equal("per_pellet",display.PelletCoefficientPolicy);
        Assert.Null(display.DamageThreshold);Assert.Equal("off",normalized["combat"]!["critMode"]!.GetValue<string>());
        Assert.Null(old["combat"]!["defenseMode"]);
    }
    [Fact] public void Unknown_profile_and_mixed_old_boss_flags_are_errors()
    {
        Assert.Throws<ArgumentException>(()=>SoloRaidRequestPolicy.Normalize(new(),"other"));
        Assert.Throws<ArgumentException>(()=>SoloRaidRequestPolicy.Normalize(JsonNode.Parse("{\"combat\":{\"bossDistance\":null,\"properDistance\":false}}")!.AsObject(),null));
    }
    [Fact] public void Missing_prepared_boss_catalog_is_explicit_and_does_not_invent_names()
    {
        var catalog=new SoloRaidBossCatalogService(Path.Combine(Path.GetTempPath(),Guid.NewGuid().ToString("N")));
        var response=catalog.Read();Assert.False(response.Complete);
        Assert.Equal("더미 보스",Assert.Single(response.Bosses).Name);
        Assert.Equal("boss_catalog_not_prepared",Assert.Single(response.Diagnostics).Code);
        Assert.Throws<ArgumentException>(()=>catalog.Resolve("solo-raid-1"));
    }
}

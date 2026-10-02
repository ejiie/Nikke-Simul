using System.Text.Json.Nodes;
using Nikke.Contracts;
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
    static string TempWith(string json)
    {
        var root=Path.Combine(Path.GetTempPath(),Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);
        File.WriteAllText(Path.Combine(root,"solo-raid-boss-attributes.json"),json);return root;
    }
    static SoloRaidBossAttributeCatalog ReadCatalog(string json)=>new SoloRaidBossAttributeCatalogService(TempWith(json)).Read();
    const string Stats="{\"level\":390,\"hp\":5866372929,\"attack\":111269,\"defence\":30925}";
    const string Part="{\"id\":1,\"partsType\":6,\"isMain\":true,\"damageable\":true,\"hpRatio\":10000,\"damageHpRatio\":0,\"defenceRatio\":10000,\"passiveSkillId\":0,\"visibleHp\":true,\"coreMarkers\":[]}";
    const string Step="{\"step\":1,\"rangeFrom\":0,\"rangeTo\":2000000000,\"level\":390,\"stats\":STATS}";
    // Same shape the preparer writes: every key present, explicit null for unconfirmed values.
    static string Boss(string challengeStats=Stats,string unconfirmed="",string part=Part,string element="{\"id\":100001,\"key\":\"Fire\",\"weakId\":200001,\"weakKey\":\"Water\"}",
        string step=Step,string rate="6000")=>
        "{\"schemaVersion\":1,\"kind\":\"solo_raid_boss_static_attributes\",\"fields\":[],\"diagnostics\":[],\"complete\":false,\"source\":null,\"bosses\":["
        +"{\"id\":\"solo-raid-1\",\"season\":1,\"status\":\"available\",\"reason\":null,\"defenceRatio\":10000,\"defenceRatioRate\":"+rate+",\"hpRatio\":10000,\"attackRatio\":10000,"
        +"\"element\":"+element+",\"challenge\":{\"presetId\":1,\"level\":390,\"characterLevel\":400,\"stats\":"+challengeStats+",\"levelChange\":{\"groupId\":904,\"steps\":["
        +step.Replace("STATS",Stats)+"]}},\"ladder\":[],\"parts\":["+part+"],\"core\":{\"kind\":\"unconfirmed\",\"partIds\":[],\"evidence\":null},\"unconfirmed\":["+unconfirmed+"]}]}";
    [Fact] public void Missing_boss_attributes_are_explicit_and_not_defaulted()
    {
        var response=new SoloRaidBossAttributeCatalogService(Path.Combine(Path.GetTempPath(),Guid.NewGuid().ToString("N"))).Read();
        Assert.False(response.Complete);Assert.Empty(response.Bosses);
        Assert.Equal("boss_attributes_not_prepared",Assert.Single(response.Diagnostics).Code);
    }
    [Fact] public void Unavailable_season_keeps_null_attributes_and_defence_ratio_rate_is_raw()
    {
        var ok=Boss();
        var json=ok.Replace("\"bosses\":[","\"bosses\":[{\"id\":\"solo-raid-41\",\"season\":41,\"status\":\"unavailable\",\"reason\":\"static_data_season_missing\"},");
        var catalog=ReadCatalog(json);
        var missing=catalog.Bosses[0];
        Assert.Equal("unavailable",missing.Status);Assert.Null(missing.Challenge);Assert.Null(missing.Element);Assert.Null(missing.DefenceRatioRate);
        var boss=catalog.Bosses[1];
        Assert.Equal(6000,boss.DefenceRatioRate);Assert.Equal(30925,boss.Challenge!.Stats!.Defence);Assert.Equal(5866372929L,boss.Challenge.Stats.Hp);
        Assert.Equal("Water",boss.Element!.WeakKey);
    }
    [Fact] public void Declared_unconfirmed_challenge_stats_keep_the_other_confirmed_attributes()
    {
        var boss=ReadCatalog(Boss(challengeStats:"null",unconfirmed:"\"challenge_level_stats\"")).Bosses[0];
        Assert.Null(boss.Challenge!.Stats);
        Assert.Equal("Fire",boss.Element!.Key);Assert.Equal(390,boss.Challenge.Level);Assert.Single(boss.Parts!);
        Assert.Equal("challenge_level_stats",Assert.Single(boss.Unconfirmed!));
    }
    [Fact] public void Declared_unconfirmed_level_change_step_stats_are_accepted_only_when_listed()
    {
        var nullStep=Step.Replace("STATS","null");
        var boss=ReadCatalog(Boss(step:nullStep,unconfirmed:"\"level_change_step_1_stats\"")).Bosses[0];
        Assert.Null(boss.Challenge!.LevelChange!.Steps[0].Stats);Assert.Equal(390,boss.Challenge.LevelChange.Steps[0].Level);
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(Boss(step:nullStep)));
    }
    [Fact] public void Undeclared_null_challenge_stats_is_corruption_not_unconfirmed()=>
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(Boss(challengeStats:"null")));
    [Fact] public void An_actual_zero_is_kept_and_distinguished_from_a_missing_number()
    {
        var zero=ReadCatalog(Boss(challengeStats:Stats.Replace("30925","0"),rate:"0")).Bosses[0];
        Assert.Equal(0,zero.Challenge!.Stats!.Defence);Assert.Equal(0,zero.DefenceRatioRate);
    }
    [Theory]
    [InlineData("{}")]
    [InlineData("{\"level\":390,\"hp\":5866372929,\"attack\":111269}")]
    [InlineData("{\"level\":390,\"hp\":5866372929,\"defence\":30925}")]
    [InlineData("{\"hp\":5866372929,\"attack\":111269,\"defence\":30925}")]
    [InlineData("{\"level\":390,\"hp\":null,\"attack\":111269,\"defence\":30925}")]
    [InlineData("{\"level\":390,\"hp\":\"5866372929\",\"attack\":111269,\"defence\":30925}")]
    public void Missing_or_malformed_nested_stat_numbers_are_rejected_not_zero_filled(string stats)=>
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(Boss(challengeStats:stats)));
    [Theory]
    [InlineData("part","{\"id\":1,\"partsType\":6,\"isMain\":true,\"damageable\":true,\"damageHpRatio\":0,\"defenceRatio\":10000,\"passiveSkillId\":0,\"visibleHp\":true,\"coreMarkers\":[]}")]
    [InlineData("part","{\"id\":1,\"partsType\":6,\"isMain\":true,\"damageable\":true,\"hpRatio\":10000,\"damageHpRatio\":0,\"passiveSkillId\":0,\"visibleHp\":true,\"coreMarkers\":[]}")]
    [InlineData("element","{\"id\":100001,\"key\":\"Fire\",\"weakKey\":\"Water\"}")]
    [InlineData("step","{\"step\":1,\"rangeFrom\":0,\"rangeTo\":2000000000,\"stats\":STATS}")]
    [InlineData("step","{\"step\":1,\"rangeTo\":2000000000,\"level\":390,\"stats\":STATS}")]
    public void Missing_numbers_in_other_nested_records_are_rejected(string kind,string value)
    {
        var json=kind switch{"part"=>Boss(part:value),"element"=>Boss(element:value),_=>Boss(step:value)};
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(json));
    }
    [Theory]
    [InlineData("{\"schemaVersion\":2,\"kind\":\"solo_raid_boss_static_attributes\",\"fields\":[],\"diagnostics\":[],\"complete\":true,\"source\":null,\"bosses\":[]}")]
    [InlineData("{\"schemaVersion\":1,\"kind\":\"solo_raid_boss_static_attributes\",\"fields\":[],\"diagnostics\":[],\"complete\":true,\"source\":null,\"bosses\":[{\"id\":\"solo-raid-9\",\"season\":1,\"status\":\"unavailable\",\"reason\":\"x\"}]}")]
    [InlineData("{\"schemaVersion\":1,\"kind\":\"solo_raid_boss_static_attributes\",\"fields\":[],\"diagnostics\":[],\"complete\":true,\"source\":null,\"bosses\":[{\"id\":\"solo-raid-1\",\"season\":1,\"status\":\"available\",\"reason\":null}]}")]
    [InlineData("{\"schemaVersion\":1,\"kind\":\"solo_raid_boss_static_attributes\",\"fields\":[],\"diagnostics\":[],\"complete\":true,\"source\":null,\"bosses\":[{\"id\":\"solo-raid-1\",\"season\":1,\"status\":\"unavailable\"}]}")]
    [InlineData("{\"schemaVersion\":1,\"kind\":\"solo_raid_boss_static_attributes\",\"fields\":[],\"diagnostics\":[],\"complete\":true,\"source\":null}")]
    [InlineData("not json")]
    public void Invalid_boss_attributes_are_rejected(string json)=>
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(json));
}

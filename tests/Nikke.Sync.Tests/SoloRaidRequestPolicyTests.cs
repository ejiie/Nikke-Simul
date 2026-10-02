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
    // The shape the preparer writes: every key present, explicit null only for declared-unconfirmed values.
    // Boss 0 is a fully confirmed season (unconfirmed: []), boss 1 is an unavailable season.
    static JsonObject ValidCatalog()=>JsonNode.Parse("""
    {"schemaVersion":1,"kind":"solo_raid_boss_static_attributes","complete":false,
     "fields":[{"key":"element","label":"속성","source":"s","unit":"u","confidence":"확인","note":"n"}],
     "diagnostics":[{"id":"solo-raid-2","season":2,"code":"static_data_season_missing","displayable":false,"message":"m"}],
     "source":{"entries":{"MonsterTable.mpk":{"sha256":"a","size":10,"records":3},"WaveData.GroupDict.csv":{"sha256":"b","size":5,"records":null}},
               "schemaFingerprint":"f","archiveSha256":"c","archiveBytes":100,"preparedAt":"2026-10-02T00:00:00+00:00"},
     "bosses":[
      {"id":"solo-raid-1","season":1,"status":"available","reason":null,"imageResource":"full_x","monsterId":1000,"monsterModelId":500,"modelPrefab":"x",
       "statEnhanceGroup":230000,"element":{"id":100001,"key":"Fire","weakId":200001,"weakKey":"Water"},"hpRatio":10000,"defenceRatio":10000,
       "defenceRatioRate":6000,"attackRatio":10000,
       "challenge":{"presetId":1,"level":390,"characterLevel":400,"levelChangeGroupId":904,
         "stats":{"level":390,"hp":5866372929,"attack":111269,"defence":30925},
         "levelChange":{"groupId":904,"steps":[
           {"step":1,"rangeFrom":0,"rangeTo":2000000000,"level":390,"stats":{"level":390,"hp":5866372929,"attack":111269,"defence":30925}},
           {"step":2,"rangeFrom":2000000001,"rangeTo":null,"level":400,"stats":{"level":400,"hp":6083218659,"attack":114344,"defence":31784}}]}},
       "ladder":[{"level":45,"hp":12445632,"attack":2285,"defence":656}],
       "parts":[{"id":1,"partsType":6,"isMain":true,"damageable":true,"hpRatio":10000,"damageHpRatio":0,"defenceRatio":10000,"passiveSkillId":0,"visibleHp":true,"coreMarkers":["core_col"]}],
       "core":{"kind":"separate_part","partIds":[1],"evidence":"collider_name_contains_core"},"unconfirmed":["note"]},
      {"id":"solo-raid-2","season":2,"status":"unavailable","reason":"static_data_season_missing"}]}
    """)!.AsObject();
    static JsonNode Parent(JsonNode root,string path)
    {
        var node=root;
        foreach(var part in path.Split('/').SkipLast(1))node=int.TryParse(part,out var index)?node.AsArray()[index]!:node[part]!;
        return node;
    }
    static void Put(JsonNode root,string path,JsonNode? value)
    {
        var container=Parent(root,path);var last=path.Split('/')[^1];
        if(int.TryParse(last,out var index))container.AsArray()[index]=value;else container.AsObject()[last]=value;
    }
    static string Edit(Action<JsonObject> edit){var doc=ValidCatalog();edit(doc);return doc.ToJsonString();}
    static string SetAt(string path,JsonNode? value)=>Edit(doc=>Put(doc,path,value));
    static string RemoveAt(string path)=>Edit(doc=>Parent(doc,path).AsObject().Remove(path.Split('/')[^1]));
    // "note" is an unrelated declared code present in the valid sample so that unconfirmed[0] exists as a collection element.
    static string Declare(string json,string code)
    {
        var doc=JsonNode.Parse(json)!.AsObject();((JsonArray)doc["bosses"]![0]!["unconfirmed"]!).Add(code);return doc.ToJsonString();
    }
    [Fact] public void Missing_boss_attributes_are_explicit_and_not_defaulted()
    {
        var response=new SoloRaidBossAttributeCatalogService(Path.Combine(Path.GetTempPath(),Guid.NewGuid().ToString("N"))).Read();
        Assert.False(response.Complete);Assert.Empty(response.Bosses);
        Assert.Equal("boss_attributes_not_prepared",Assert.Single(response.Diagnostics).Code);
    }
    [Fact] public void A_valid_prepared_file_reads_with_raw_values_and_unavailable_seasons_empty()
    {
        var catalog=ReadCatalog(ValidCatalog().ToJsonString());
        var boss=catalog.Bosses[0];var missing=catalog.Bosses[1];
        Assert.Equal(6000,boss.DefenceRatioRate);Assert.Equal(30925,boss.Challenge!.Stats!.Defence);Assert.Equal(5866372929L,boss.Challenge.Stats.Hp);
        Assert.Equal("Water",boss.Element!.WeakKey);Assert.Null(boss.Challenge.LevelChange!.Steps[1].RangeTo);
        Assert.Equal("unavailable",missing.Status);Assert.Null(missing.Challenge);Assert.Null(missing.Element);Assert.Null(missing.DefenceRatioRate);
    }
    [Fact] public void An_actual_zero_is_kept_and_distinguished_from_a_missing_number()
    {
        var json=Edit(doc=>{doc["bosses"]![0]!["challenge"]!["stats"]!["defence"]=0;doc["bosses"]![0]!["defenceRatioRate"]=0;});
        var boss=ReadCatalog(json).Bosses[0];
        Assert.Equal(0,boss.Challenge!.Stats!.Defence);Assert.Equal(0,boss.DefenceRatioRate);
    }
    // BD1-Q-1/Q-2 and every sibling: a null anywhere that the preparer did not declare is a corrupt file (409), whether it is an
    // object member, a collection element or a whole element object. Collections are checked at the first element.
    [Theory]
    [InlineData("bosses/0")][InlineData("bosses/1")][InlineData("diagnostics/0")][InlineData("fields/0")]
    [InlineData("bosses/0/challenge/levelChange/steps/0")][InlineData("bosses/0/parts/0")][InlineData("bosses/0/ladder/0")]
    [InlineData("bosses/0/parts/0/coreMarkers/0")][InlineData("bosses/0/unconfirmed/0")][InlineData("bosses/0/core/partIds/0")]
    [InlineData("source/entries/MonsterTable.mpk")][InlineData("source")]
    public void Null_collection_elements_and_objects_are_rejected_not_500_or_passed_through(string path) =>
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(SetAt(path,null)));
    [Theory]
    [InlineData("bosses/0/element")][InlineData("bosses/0/element/weakKey")][InlineData("bosses/0/modelPrefab")]
    [InlineData("bosses/0/challenge/stats")][InlineData("bosses/0/challenge/levelChange")]
    [InlineData("bosses/0/challenge/levelChange/steps/0/stats")][InlineData("bosses/0/core/evidence")]
    [InlineData("bosses/0/imageResource")][InlineData("bosses/0/monsterId")][InlineData("bosses/0/monsterModelId")][InlineData("bosses/0/statEnhanceGroup")]
    [InlineData("bosses/0/hpRatio")][InlineData("bosses/0/defenceRatio")][InlineData("bosses/0/defenceRatioRate")][InlineData("bosses/0/attackRatio")]
    [InlineData("bosses/0/challenge")][InlineData("bosses/0/ladder")][InlineData("bosses/0/parts")][InlineData("bosses/0/core")][InlineData("bosses/0/unconfirmed")]
    [InlineData("bosses/0/challenge/levelChange/steps/0/rangeTo")][InlineData("bosses/1/reason")][InlineData("diagnostics/0/season")]
    [InlineData("fields/0/label")][InlineData("diagnostics/0/message")][InlineData("source/schemaFingerprint")]
    [InlineData("bosses/0/parts/0/hpRatio")][InlineData("bosses/0/ladder/0/defence")][InlineData("bosses/0/challenge/stats/hp")]
    public void Undeclared_null_in_any_object_member_is_rejected_and_so_is_a_missing_key(string path)
    {
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(SetAt(path,null)));
        // a missing key must not read as null/0 either (optional members would otherwise default to null)
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(RemoveAt(path)));
    }
    [Theory]
    [InlineData("bosses/0/element","element")][InlineData("bosses/0/element/weakKey","weak_element")]
    [InlineData("bosses/0/modelPrefab","model_prefab")][InlineData("bosses/0/challenge/stats","challenge_level_stats")]
    [InlineData("bosses/0/challenge/levelChange","level_change_rows")]
    [InlineData("bosses/0/challenge/levelChange/steps/0/stats","level_change_step_1_stats")]
    [InlineData("bosses/0/challenge/levelChange/steps/1/stats","level_change_step_2_stats")]
    public void A_declared_unconfirmed_null_is_accepted_and_keeps_the_other_attributes(string path,string code)
    {
        var boss=ReadCatalog(Declare(SetAt(path,null),code)).Bosses[0];
        Assert.Equal(1000,boss.MonsterId);Assert.Single(boss.Parts!);Assert.Equal(390,boss.Challenge!.Level);Assert.Contains(code,boss.Unconfirmed!);
    }
    [Fact] public void An_unconfirmed_core_requires_no_evidence_no_parts_and_a_declaration()
    {
        var unconfirmed=Edit(doc=>doc["bosses"]![0]!["core"]=JsonNode.Parse("{\"kind\":\"unconfirmed\",\"partIds\":[],\"evidence\":null}"));
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(unconfirmed));
        Assert.Equal("unconfirmed",ReadCatalog(Declare(unconfirmed,"core_position")).Bosses[0].Core!.Kind);
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(Declare(SetAt("bosses/0/core/partIds",new JsonArray()),"core_position")));
    }
    [Fact] public void Level_change_null_is_legitimate_only_when_the_group_is_zero()
    {
        var noGroup=Edit(doc=>{var c=doc["bosses"]![0]!["challenge"]!.AsObject();c["levelChangeGroupId"]=0;c["levelChange"]=null;});
        Assert.Null(ReadCatalog(noGroup).Bosses[0].Challenge!.LevelChange);
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(SetAt("bosses/0/challenge/levelChangeGroupId",0)));
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(SetAt("bosses/0/challenge/levelChangeGroupId",905)));
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(SetAt("bosses/0/challenge/levelChangeGroupId",-1)));
    }
    [Fact] public void Unavailable_seasons_must_not_carry_attributes_and_ids_must_match_seasons()
    {
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(SetAt("bosses/1/hpRatio",10000)));
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(SetAt("bosses/1/element",JsonNode.Parse("{\"id\":1,\"key\":\"Fire\",\"weakId\":2,\"weakKey\":\"Water\"}"))));
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(SetAt("bosses/1/unconfirmed",new JsonArray())));
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(SetAt("bosses/1/id","solo-raid-9")));
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(SetAt("bosses/0/reason","x")));
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(SetAt("bosses/1/status","other")));
    }
    [Theory]
    [InlineData("{}")]
    [InlineData("{\"level\":390,\"hp\":5866372929,\"attack\":111269}")]
    [InlineData("{\"level\":390,\"hp\":5866372929,\"defence\":30925}")]
    [InlineData("{\"hp\":5866372929,\"attack\":111269,\"defence\":30925}")]
    [InlineData("{\"level\":390,\"hp\":null,\"attack\":111269,\"defence\":30925}")]
    [InlineData("{\"level\":390,\"hp\":\"5866372929\",\"attack\":111269,\"defence\":30925}")]
    [InlineData("{\"level\":390,\"hp\":5866372929,\"attack\":111269.5,\"defence\":30925}")]
    public void Missing_or_malformed_nested_stat_numbers_are_rejected_not_zero_filled(string stats)=>
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(SetAt("bosses/0/challenge/stats",JsonNode.Parse(stats))));
    [Theory]
    [InlineData("{\"schemaVersion\":2,\"kind\":\"solo_raid_boss_static_attributes\",\"fields\":[],\"diagnostics\":[],\"complete\":true,\"source\":null,\"bosses\":[]}")]
    [InlineData("{\"schemaVersion\":1,\"kind\":\"other\",\"fields\":[],\"diagnostics\":[],\"complete\":true,\"source\":null,\"bosses\":[]}")]
    [InlineData("{\"schemaVersion\":1,\"kind\":\"solo_raid_boss_static_attributes\",\"fields\":[],\"diagnostics\":[],\"complete\":true,\"source\":null}")]
    [InlineData("null")][InlineData("[]")][InlineData("not json")]
    public void Invalid_boss_attribute_files_are_rejected(string json)=>
        Assert.Throws<InvalidOperationException>(()=>ReadCatalog(json));
}

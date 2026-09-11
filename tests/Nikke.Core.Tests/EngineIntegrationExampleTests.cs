using System.Text.Json;
using System.Text.Json.Nodes;
using Nikke.Core.Combat;
using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Stats;
using static Nikke.Core.Tests.SkillReplayTests;

namespace Nikke.Core.Tests;

// Engine-only tests. Web defaults match bf19679 Models.cs; this does not execute B1's adapter or HTTP.
public class EngineIntegrationExampleTests
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    public sealed record ExampleInput(SkillReplayMember[] Members, SkillGraph Graph, SkillReplayConditions Conditions);
    private sealed class FixtureRandom : IRandomSource
    {
        public int Calls;
        public double NextDouble() => (++Calls % 13) / 13d;
    }
    private static SkillReplayMember Actor(string id,int step,int[]? functions=null)
    {
        var m=Member(id,burst:Active(functions:functions,cooldown:2000));
        return m with { Skills=m.Skills with { FullBurstDurationFrames=600,
            BurstConnection=new(step,step+1,1,1000,123,28000,56000,35000,[]) } };
    }
    private static ExampleInput Input()
    {
        // IDs other than 5004 and all weapon/skill/stat data are synthetic, not an account snapshot.
        var alice=Actor("5004",3,[10,11]);
        alice.Weapon.Weapon.weaponType="SR"; alice.Weapon.Weapon.inputType="UP";
        alice.Weapon.Weapon.isChargeWeapon=true; alice.Weapon.Weapon.chargeTimeSec=1;
        alice.Weapon.Weapon.maxAmmo=6;
        alice=alice with { Weapon=alice.Weapon with { Hit=alice.Weapon.Hit with { ChargeApplicable=true,ChargeBase=3.5 } } };
        const string conditionsJson="""
        {
          "roundingPolicy":"legacy_term_floor",
          "damageLog":{},
          "combat":{"durationFrames":10800,"enemyDefense":10,"critMode":"sample","core":true,
            "manualCharacterId":"5004","manualStyle":"full_charge","trace":false,"traceLimit":1},
          "autoBurst":{"tactic":{"schemaVersion":1,
            "allowedCharacterIds":["fixture-i","fixture-ii","5004","fixture-iii"],
            "stage1Priority":["fixture-i"],"stage2Priority":["fixture-ii"],
            "stage3Priority":["5004","fixture-iii"],"burst3Rotation":["5004","fixture-iii"],
            "firstBurst3CharacterId":"5004","unavailablePolicy":"next_ready"}}
        }
        """;
        return new([Actor("fixture-i",1),Actor("fixture-ii",2),alice,Actor("fixture-iii",3),Actor("fixture-excluded",3)],
            Graph(F(10,value:5000) with { DurationValue=1000 },F(11,61,value:-5000) with { DurationValue=1000 }) with {
                GaugeConstants=new(1000000,new Dictionary<string,long>(),"synthetic_source_fixture","raw") },
            JsonSerializer.Deserialize<SkillReplayConditions>(conditionsJson,Json)!);
    }

    [Fact]
    public void Web_json_round_trip_reexecutes_real_engine_and_can_export_a_private_data_free_example()
    {
        var input=Input();
        var inputJson=JsonSerializer.Serialize(input,Json);
        var restored=JsonSerializer.Deserialize<ExampleInput>(inputJson,Json)!;
        var rng=new FixtureRandom(); var repeatRng=new FixtureRandom();
        var result=SkillReplay.Run(input.Members,input.Graph,input.Conditions,rng);
        var repeat=SkillReplay.Run(restored.Members,restored.Graph,restored.Conditions,repeatRng);
        var resultJson=JsonSerializer.Serialize(result,Json);
        Assert.Equal(resultJson,JsonSerializer.Serialize(repeat,Json));
        Assert.Equal(rng.Calls,repeatRng.Calls);
        var roundTripResult=JsonSerializer.Deserialize<SkillReplayResult>(resultJson,Json)!;
        Assert.Equal(resultJson,JsonSerializer.Serialize(roundTripResult,Json));
        var log=result.DamageLog;
        Assert.Equal("5004",log.CharacterId); Assert.Equal(1,log.SchemaVersion); Assert.False(log.Truncated);
        Assert.Equal(result.Members.Single(m=>m.CharacterId=="5004").Damage,log.TotalDamage);
        Assert.Equal(log.TotalDamage,log.Entries.Sum(e=>e.Damage));
        Assert.True(log.Entries[^1].Frame>10700); Assert.True(result.TeamBurst.FullBursts.Count>1);
        Assert.DoesNotContain(result.TeamBurst.Timeline,e=>e.Kind=="burst_cast" && e.CharacterId=="fixture-excluded");
        Assert.All(result.TeamBurst.Timeline.Where(e=>e.Kind=="gauge" && e.CharacterId=="5004"),e=>Assert.Equal(196000,e.RequestedRaw));
        Assert.Contains(log.Entries,e=>e.OwnBurstEffectActive && !e.Hit.FullBurst);
        Assert.Contains(log.Entries,e=>!e.OwnBurstEffectActive && e.Hit.FullBurst);
        var node=JsonNode.Parse(resultJson)!;
        Assert.Equal((int)CombatEventKind.NormalHit,node["damageLog"]!["entries"]![0]!["kind"]!.GetValue<int>());
        Assert.Null(node["damageLog"]!["truncationReason"]);
        Assert.Equal("5004",node["conditions"]!["autoBurst"]!["tactic"]!["firstBurst3CharacterId"]!.GetValue<string>());

        var offRng=new FixtureRandom();
        var off=SkillReplay.Run(restored.Members,restored.Graph,restored.Conditions with { DamageLog=null! },offRng);
        Assert.Equal(rng.Calls,offRng.Calls); Assert.Equal(result.TotalDamage,off.TotalDamage);
        Assert.Equal(result.Members.Select(m=>(m.Shots,m.Hits,m.RemainingAmmo)),off.Members.Select(m=>(m.Shots,m.Hits,m.RemainingAmmo)));
        Assert.Equal(result.TeamBurst.Timeline,off.TeamBurst.Timeline);

        // Opt-in output always creates a new subdirectory; no old artifact or account data is read/overwritten.
        var outputRoot=Environment.GetEnvironmentVariable("NIKKE_E2_EXAMPLE_ROOT");
        if (string.IsNullOrWhiteSpace(outputRoot)) return;
        var directory=Path.Combine(Path.GetFullPath(outputRoot),"engine-example-"+Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(directory);
        File.WriteAllText(Path.Combine(directory,"input.json"),inputJson);
        File.WriteAllText(Path.Combine(directory,"result.json"),resultJson);
        File.WriteAllText(Path.Combine(directory,"manifest.json"),JsonSerializer.Serialize(new {
            exampleSchemaVersion=1,evidence="synthetic_input_actual_engine_execution",engineBaseCommit="908047f",
            backendComparedCommit="bf19679",gameVerified=false,accountSnapshotId=(string?)null,
            randomSource="test_only_next=(++calls%13)/13d",randomCalls=rng.Calls,
            replayRules=result.RulesVersion,hitRules=HitCalculator.Version,
            durationFrames=10800,log.EventCount,log.TotalDamage,lastHitFrame=log.Entries[^1].Frame,
            fullBurstCount=result.TeamBurst.FullBursts.Count,logOnOffIdentical=true,
            note="Native engine input/result, not a SavedSkillReplay or HTTP request; no account/runtime catalog used."
        },Json));
    }

    [Fact]
    public void Legacy_and_collected_zero_remain_distinct_after_web_json_round_trip()
    {
        var input=Input();
        var c=input.Conditions with { AutoBurst=null!,Combat=input.Conditions.Combat with { DurationFrames=1 } };
        var alice=input.Members.Single(m=>m.Weapon.CharacterId=="5004");
        var empty=SkillReplay.Run([alice],input.Graph,c,new FixtureRandom());
        var node=JsonNode.Parse(JsonSerializer.Serialize(empty,Json))!;
        Assert.Empty(node["damageLog"]!["entries"]!.AsArray());
        Assert.Equal(0,node["damageLog"]!["totalDamage"]!.GetValue<double>());
        node.AsObject().Remove("damageLog");
        Assert.Null(node.Deserialize<SkillReplayResult>(Json)!.DamageLog);
        var legacy=JsonSerializer.Deserialize<SkillReplayConditions>("{\"autoBurst\":{}}",Json)!;
        Assert.Null(legacy.AutoBurst.Tactic); Assert.Null(legacy.DamageLog);
        Assert.Equal("next_ready",legacy.AutoBurst.UnavailablePolicy);
    }
}

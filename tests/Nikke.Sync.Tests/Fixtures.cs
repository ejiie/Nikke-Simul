using System.Text.Json.Nodes;
using Nikke.Contracts;

namespace Nikke.Sync.Tests;

public static class Fixtures
{
    public static GameSnapshot Game() => new() { Id = "synthetic-game-v1", Source = "synthetic", Names = new() { ["101"] = "테스트 니케" },
        OptionSteps = new() { ["atk_pct"] = [0.1181m], ["charge_speed_pct"] = [0.014m] }, FavoriteGrades = new() { ["900"] = "SSR" } };
    public static RawEnvelope Raw()
    {
        var detail = JsonNode.Parse("""
            {"name_code":101,"lv":200,"attractive_lv":25,"skill1_lv":7,"skill2_lv":8,"ulti_skill_lv":9,
             "harmony_cube_tid":5,"harmony_cube_lv":7,"favorite_item_tid":900,"favorite_item_lv":1}
            """)!;
        foreach (var part in new[] { "head", "torso", "arm", "leg" })
        {
            detail[part + "_equip_tid"] = 1000;
            detail[part + "_equip_tier"] = 10; detail[part + "_equip_lv"] = 5; detail[part + "_equip_corporation_type"] = 4;
            detail[part + "_equip_option1_id"] = part == "head" ? 11 : 0;
            detail[part + "_equip_option2_id"] = part == "head" ? 12 : 0;
            detail[part + "_equip_option3_id"] = 0;
        }
        var roster = JsonNode.Parse("""[{"name_code":101,"lv":400,"grade":3,"core":2}]""")!.AsArray();
        return new() { OpenId = "synthetic-account", Area = 83, Characters = roster, RosterAfter = roster.DeepClone().AsArray(), Details = new(detail),
            StateEffects = JsonNode.Parse("""
              [{"id":"11","function_details":[{"function_type":"StatAtk","function_value":1181,"function_value_type":"Percent"}]},
               {"id":12,"function_details":[{"function_type":"StatChargeTime","function_value":-140,"function_value_type":"Percent"}]}]
              """)!.AsArray(), Outpost = JsonNode.Parse("""{"synchro_level":400,"recycle_room_researches":[{"tid":1001,"lv":150}]}""")!.AsObject() };
    }
}

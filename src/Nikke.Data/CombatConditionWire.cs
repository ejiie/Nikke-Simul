using System.Text.Json;
using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Engine;

namespace Nikke.Data;

// Preserve the difference between absent fields and explicit null/false before typed deserialization.
public static class CombatConditionWire
{
    public static JsonObject ReadCombat(JsonObject conditions)
    {
        var fields=conditions.Where(p=>string.Equals(p.Key,"combat",StringComparison.OrdinalIgnoreCase)).ToArray();
        if(fields.Length>1)throw new ArgumentException("ambiguous_combat_conditions");
        return fields.SingleOrDefault().Value switch {
            null=>new JsonObject(),JsonObject combat=>combat,
            _=>throw new ArgumentException("combat_conditions_must_be_object")};
    }
    public static CombatConditionCompatibility FromConditions(WeaponReplayConditions combat)
    {
        BossConditionResolver.Validate(combat); // before null boss fields disappear on JSON serialization
        return new(combat.BossFieldsSpecified?"per_member":"legacy_global",
            combat.BossFieldsSpecified?"보스 거리·약점(멤버별)":"이전 방식(전원 적용)",
            combat.ProperDistance,combat.ElementAdvantage,combat.BossDistance,combat.BossWeakElement);
    }
    public static CombatConditionCompatibility FromReplay(string json)
    {
        var artifact=JsonNode.Parse(json)!.AsObject();
        // New records can carry explicit metadata; old JSON remains byte-for-byte untouched.
        return artifact["conditionCompatibility"]?.Deserialize<CombatConditionCompatibility>(Wire.Json)
            ?? Inspect(artifact["result"]?["conditions"]?["combat"]?.AsObject() ?? new JsonObject());
    }
    public static CombatConditionCompatibility Inspect(JsonObject combat)
    {
        var fields=new[]{"bossDistance","bossWeakElement","properDistance","elementAdvantage"};
        foreach(var name in fields)
            if(combat.Any(p=>string.Equals(p.Key,name,StringComparison.OrdinalIgnoreCase) && p.Key!=name))
                throw new ArgumentException("combat_condition_fields_require_canonical_camelCase");
        bool modern=combat.ContainsKey("bossDistance") || combat.ContainsKey("bossWeakElement");
        bool legacy=combat.ContainsKey("properDistance") || combat.ContainsKey("elementAdvantage");
        if(modern && legacy) throw new ArgumentException("boss_conditions_mixed_with_legacy");
        try
        {
            int? distance=combat["bossDistance"]?.GetValue<int>();
            string? element=combat["bossWeakElement"]?.GetValue<string>();
            if(distance is <0 or >100)throw new ArgumentException("boss_distance_requires_integer_0_to_100_or_null");
            if(element is not null && !CombatProfileCatalog.Elements.Contains(element))
                throw new ArgumentException("boss_weak_element_requires_Fire_Water_Wind_Iron_Electronic_or_null");
            bool proper=combat["properDistance"]?.GetValue<bool>()??false;
            bool advantage=combat["elementAdvantage"]?.GetValue<bool>()??false;
            return new(modern?"per_member":"legacy_global",modern?"보스 거리·약점(멤버별)":"이전 방식(전원 적용)",proper,advantage,distance,element);
        }
        catch(Exception ex) when(ex is JsonException or InvalidOperationException or FormatException)
        {throw new ArgumentException("invalid_combat_condition_value",ex);}
    }
}

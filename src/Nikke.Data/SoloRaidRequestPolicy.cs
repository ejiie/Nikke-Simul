using System.Text.Json;
using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Engine;

namespace Nikke.Data;

// Apply only at NEW request boundaries. Historical reads and prepared restoration never pass here.
public static class SoloRaidRequestPolicy
{
    public static JsonObject Normalize(JsonObject conditions,string? profile)
    {
        profile??="solo_raid";
        if(profile is not ("solo_raid" or "legacy"))throw new ArgumentException("condition_profile_invalid");
        var copy=(JsonObject)conditions.DeepClone();
        var combat=(JsonObject)CombatConditionWire.ReadCombat(copy).DeepClone();
        foreach(var name in new[]{"durationFrames","pelletCoefficientPolicy","defenseMode","enemyDefense","critMode"})
            if(combat.Any(p=>p.Key!=name && string.Equals(p.Key,name,StringComparison.OrdinalIgnoreCase)))
                throw new ArgumentException("combat_condition_fields_require_canonical_camelCase");
        _=CombatConditionWire.Inspect(combat);
        if(profile=="solo_raid")
        {
            Require(combat,"durationFrames",10800,"solo_raid_duration_fixed_10800");
            Require(combat,"pelletCoefficientPolicy","per_trigger","solo_raid_pellet_policy_fixed_per_trigger");
            Require(combat,"defenseMode",DefenseMode.TeamDamageThreshold,"solo_raid_defense_mode_requires_team_damage_threshold");
            // This value is not a user setting in automatic mode; validate supplied numeric shape before canonicalizing.
            if(combat.TryGetPropertyValue("enemyDefense",out var defense)
                && (defense is not JsonValue value || value.GetValueKind()!=JsonValueKind.Number
                    || !value.TryGetValue<double>(out var number) || !double.IsFinite(number) || number<0 || number%1!=0))
                throw new ArgumentException("invalid_enemy_defense");
            combat["enemyDefense"]=DefenseMode.InitialDefense;
            if(!combat.ContainsKey("critMode"))combat["critMode"]="sample";
        }
        else Require(combat,"defenseMode",DefenseMode.Fixed,"legacy_defense_mode_requires_fixed");
        foreach(var key in copy.Select(p=>p.Key).Where(k=>string.Equals(k,"combat",StringComparison.OrdinalIgnoreCase)).ToArray())copy.Remove(key);
        copy["combat"]=combat;
        return copy;
    }
    private static void Require<T>(JsonObject node,string key,T expected,string error)
    {
        if(node.TryGetPropertyValue(key,out var input))
        {
            if(input is not JsonValue value || !value.TryGetValue<T>(out var actual) || !EqualityComparer<T>.Default.Equals(actual,expected))
                throw new ArgumentException(error);
        }
        node[key]=JsonSerializer.SerializeToNode(expected);
    }
    public static BattleConditionDisplay Describe(WeaponReplayConditions combat)
    {
        bool automatic=combat.DefenseMode==DefenseMode.TeamDamageThreshold;
        return new(automatic?"solo_raid":"legacy",automatic?"덱 누적 피해에 따라 방어력 자동 전환":"이전 방식(고정 방어력)",
            combat.DefenseMode,automatic?DefenseMode.InitialDefense:combat.EnemyDefense,
            automatic?DefenseMode.SwitchedDefense:null,automatic?DefenseMode.DamageThreshold:null,
            combat.DurationFrames,combat.PelletCoefficientPolicy);
    }
    public static BattleConditionDisplay FromJson(JsonObject conditions) => Describe(
        CombatConditionWire.ReadCombat(conditions).Deserialize<WeaponReplayConditions>(Wire.Json)
        ??throw new ArgumentException("missing_combat"));
}

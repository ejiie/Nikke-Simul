namespace Nikke.Engine;

public readonly record struct MemberHitBonuses(bool ProperDistance, bool ElementAdvantage);

// Only consumes caller-supplied character metadata. Inclusive range and RL 0..0 are provisional rules.
public static class BossConditionResolver
{
    public const string Version="boss-distance-element.1-inclusive";
    public static bool IsElement(string value) => value is "Fire" or "Water" or "Wind" or "Iron" or "Electronic";

    public static void Validate(WeaponReplayConditions conditions)
    {
        ArgumentNullException.ThrowIfNull(conditions);
        if (conditions.BossFieldsSpecified && (conditions.LegacyProperDistance.HasValue || conditions.LegacyElementAdvantage.HasValue))
            throw new ArgumentException("boss_conditions_mixed_with_legacy: omit both legacy bool fields for new boss conditions.");
        if (conditions.BossDistance is < 0 or > 100)
            throw new ArgumentException("boss_distance_out_of_range: expected an integer from 0 to 100, or null.");
        if (conditions.BossWeakElement is { } weak && !IsElement(weak))
            throw new ArgumentException("boss_weak_element_invalid: expected Fire/Water/Wind/Iron/Electronic, or null.");
    }

    public static MemberHitBonuses Resolve(WeaponReplayMember member, WeaponReplayConditions conditions, bool normal)
    {
        ArgumentNullException.ThrowIfNull(member);
        Validate(conditions);
        bool distance=false, element=false;
        if (!conditions.BossFieldsSpecified)
            return new(normal && conditions.ProperDistance,conditions.ElementAdvantage);
        if (conditions.BossDistance is { } value)
        {
            if (member.BonusRangeMin is not { } min || member.BonusRangeMax is not { } max)
                throw new ArgumentException($"member_bonus_range_unknown: {member.CharacterId}");
            if (min<0 || max>100 || min>max || member.Weapon is null)
                throw new ArgumentException($"member_bonus_range_invalid: {member.CharacterId}");
            bool rlWithoutBonus=member.Weapon.weaponType=="RL" && min==0 && max==0;
            distance=normal && !rlWithoutBonus && min<=value && value<=max;
        }
        if (conditions.BossWeakElement is { } weak)
        {
            if (!IsElement(member.Element)) throw new ArgumentException($"member_element_unknown_or_invalid: {member.CharacterId}");
            element=member.Element==weak;
        }
        return new(distance,element);
    }
}

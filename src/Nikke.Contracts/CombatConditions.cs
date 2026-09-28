namespace Nikke.Contracts;

public record CombatProfileSource(string Path, string Sha256, string Version, string Origin, string Locale);
public record CombatMemberProfile(string CharacterId, string Name, string WeaponType,
    int BonusRangeMin, int BonusRangeMax, string Element)
{
    public bool RangeBonusAvailable => !(WeaponType == "RL" && BonusRangeMin == 0 && BonusRangeMax == 0);
    public string? Diagnostic => RangeBonusAvailable ? null : "rl_zero_range_no_bonus_unverified";
}
public record WeaponRangeVariant(int Min, int Max, int Count, bool IsTypical, IReadOnlyList<string> CharacterIds);
public record WeaponRangeGroup(string WeaponType, int CharacterCount, IReadOnlyList<WeaponRangeVariant> Ranges,
    IReadOnlyList<CombatMemberProfile> Exceptions, bool RangeBonusAvailable, IReadOnlyList<string> Diagnostics);
public record CombatElementChoice(string Value, string IconUrl);
public record CombatConditionCatalog(string RuntimeDataId, int SchemaVersion, CombatProfileSource Source,
    IReadOnlyList<WeaponRangeGroup> WeaponRanges, IReadOnlyList<CombatElementChoice> Elements,
    string RangeRule = "inclusive_character_range_normal_only", bool GameVerified = false);
public record DeckCombatProfiles(string RuntimeDataId, string SnapshotId, IReadOnlyList<CombatMemberProfile> Members);

// Readable compatibility metadata; neither migration nor recomputation of old results.
public record CombatConditionCompatibility(string Mode, string Label, bool LegacyProperDistance,
    bool LegacyElementAdvantage, int? BossDistance, string? BossWeakElement);

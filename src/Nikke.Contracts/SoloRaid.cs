namespace Nikke.Contracts;

public record SoloRaidBoss(string Id,string Name,string? ImageUrl,int? Season=null);
public record BossCatalogDiagnostic(string Id,int? Season,string Code,bool Displayable,string Message);
public record SoloRaidBossCatalog(int SchemaVersion,string DefaultBossId,IReadOnlyList<SoloRaidBoss> Bosses,
    IReadOnlyList<BossCatalogDiagnostic> Diagnostics,bool Complete);
public record DefenseTransition(int Frame,long HitTraceId,long HitOrdinal,string CharacterId,string Effect,
    double CumulativeDamage,double PreviousDefense,double NewDefense);
public record DefenseResult(string Mode,double InitialDefense,double FinalDefense,double? DamageThreshold,
    DefenseTransition? SwitchAfterHit);
public record BattleConditionDisplay(string Profile,string Label,string DefenseMode,double InitialDefense,
    double? SwitchedDefense,double? DamageThreshold,int DurationFrames,string PelletCoefficientPolicy);

// Display-only static boss attributes (B-DATA-1). Null means unconfirmed/unavailable; never a default value.
public record BossElement(int Id,string Key,int WeakId,string? WeakKey);
public record BossLevelStats(int Level,long Hp,int Attack,int Defence);
public record BossLevelChangeStep(int Step,long RangeFrom,long? RangeTo,int Level,BossLevelStats? Stats);
public record BossLevelChange(int GroupId,IReadOnlyList<BossLevelChangeStep> Steps);
public record BossChallenge(int PresetId,int Level,int CharacterLevel,BossLevelStats? Stats,BossLevelChange? LevelChange);
public record BossPart(int Id,int PartsType,bool IsMain,bool Damageable,int HpRatio,int DamageHpRatio,int DefenceRatio,
    int PassiveSkillId,bool VisibleHp,IReadOnlyList<string> CoreMarkers);
public record BossCore(string Kind,IReadOnlyList<int> PartIds,string? Evidence);
public record BossAttributes(string Id,int Season,string Status,string? Reason,string? ImageResource,long? MonsterId,int? MonsterModelId,
    string? ModelPrefab,int? StatEnhanceGroup,BossElement? Element,int? HpRatio,int? DefenceRatio,int? DefenceRatioRate,int? AttackRatio,
    BossChallenge? Challenge,IReadOnlyList<BossLevelStats>? Ladder,IReadOnlyList<BossPart>? Parts,BossCore? Core,
    IReadOnlyList<string>? Unconfirmed);
public record BossAttributeField(string Key,string Label,string Source,string Unit,string Confidence,string Note);
public record BossAttributeSourceEntry(string Sha256,long Size,int? Records);
public record BossAttributeSource(IReadOnlyDictionary<string,BossAttributeSourceEntry> Entries,string SchemaFingerprint,
    string ArchiveSha256,long ArchiveBytes,string PreparedAt);
public record SoloRaidBossAttributeCatalog(int SchemaVersion,string Kind,IReadOnlyList<BossAttributeField> Fields,
    IReadOnlyList<BossAttributes> Bosses,IReadOnlyList<BossCatalogDiagnostic> Diagnostics,bool Complete,BossAttributeSource? Source);

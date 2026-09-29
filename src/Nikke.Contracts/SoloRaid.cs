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

using Nikke.Core.Combat;

namespace Nikke.Engine.Skills;

public sealed record DamageLogOptions
{
    public string CharacterId { get; init; } = "5004";
}
public sealed record DamageBuffSnapshot(SkillEffectView Effect, int AppliedAtFrame, long EventId, long? BurstCastId);
public sealed record DamageLogEntry(long HitId, long ParentId, long? ShotId, int? PelletIndex,
    int Frame, double Seconds, string Source, string Target, string Effect, CombatEventKind Kind,
    int? SkillId, int? FunctionId, double Damage, double CumulativeDamage, int? WeaponShotId,
    int? ChargeRatioRaw, bool? FullCharge, int? EffectiveChargeFrames, int? ActualChargeFrames,
    ShotEventData Shot, bool OwnBurstEffectActive, long? OwnBurstCastId,
    HitContext Hit, DamageBreakdown Calculation, IReadOnlyList<DamageBuffSnapshot> Buffs);
public sealed record DamageLogSummary(string CharacterId, long EventCount, double TotalDamage,
    IReadOnlyList<DamageLogEntry> Entries)
{
    public int SchemaVersion { get; init; } = 1;
    public string Status { get; init; } = "complete";
    public bool Truncated { get; init; }
    public string TruncationReason { get; init; }
}

namespace Nikke.Engine.Skills;

// Classification informed by the legacy BattleEvent contract. Payloads and execution
// boundary are new; no UI, serializer, legacy Combatant or trace-storage dependency.
public enum CombatEventKind
{
    Shot, AmmoConsumed, NormalHit, DirectSkillHit, AdditionalHit, ReloadCompleted,
    SkillCast, CooldownChanged, FullBurstDurationRequested, FullBurstEntered, FullBurstExited
}
public enum BattlePhase { FullBurstExit, CastSkills, FullBurstEntry, AfterHits }
public enum BattleCommandStatus { Applied, NotReady, NotCastable, DuplicateCast, AlreadyActive, AlreadyInactive, WrongPhase, InvalidDuration }
public sealed record BurstConnectionProfile(int Step, int NextStep, int ApplyDelayCs, int FullBurstDurationCs,
    int ShotId, long EnergyPerShotRaw, long TargetEnergyPerShotRaw, long FullChargeEnergyRaw,
    IReadOnlyList<int> UnresolvedReplacementShotIds);
public sealed record GaugeSourceConstants(long CapacityRaw, IReadOnlyDictionary<string, long> AllyRaw,
    string FormulaStatus, string Unit);
public sealed record CooldownState(string CharacterId, string Slot, long NowTicks, long ReadyAtTicks, bool Castable)
{
    public bool IsReady => Castable && NowTicks >= ReadyAtTicks;
    public int ReadyAtFrame => SkillUnits.ReadyFrame(ReadyAtTicks);
}
public sealed record CooldownChange(string Slot, long RequestedDeltaTicks, long AppliedDeltaTicks,
    long PreviousReadyAtTicks, long ReadyAtTicks, string Cause = "effect");
public sealed record FullBurstDurationRequest(long CastTraceId, string CharacterId, int? BurstStep,
    int DurationFrames, int? SourceDurationCs)
{
    public string Meaning => "total_duration_from_full_burst_entry";
}
public sealed record FullBurstState(bool Active, int Cycle, int? StartFrame, int? EndFrame, long? CauseTraceId);
public sealed record ShotEventData(int? WeaponShotId, int AmmoBefore, int AmmoAfter, bool UnlimitedAmmo,
    bool FullCharge, int Pellets);
public sealed record HitEventData(long? ShotTraceId, int? PelletIndex, int? WeaponShotId,
    bool FullCharge, bool Crit, bool Core, bool FullBurst, double Damage)
{
    // P04 must resolve gauge eligibility from event kind and pinned rules, not normal-hit participation.
    public string GaugeEligibility => "unresolved";
}
public sealed record CombatEvent(long Sequence, long TraceId, long? ParentTraceId, int Frame, long Ticks,
    CombatEventKind Kind, string Source, string Target, int? SkillId = null, int? FunctionId = null,
    ShotEventData Shot = null, HitEventData Hit = null, CooldownChange Cooldown = null,
    FullBurstDurationRequest DurationRequest = null, FullBurstState FullBurst = null);
public sealed record SkillCastResult(BattleCommandStatus Status, long? CastTraceId = null,
    FullBurstDurationRequest DurationRequest = null);
public interface ICombatEventSink { void OnEvent(CombatEvent value); }
public interface ISkillBattleControl
{
    int Frame { get; }
    FullBurstState FullBurst { get; }
    CooldownState GetCooldown(string characterId, string slot = "burst");
    BurstConnectionProfile GetBurstProfile(string characterId);
    SkillCastResult TryCast(string characterId, string slot = "burst");
    BattleCommandStatus TryEnterFullBurst(int durationFrames, long? causeTraceId = null);
    BattleCommandStatus TryExitFullBurst();
}
// Calls are synchronous on the battle thread. Mutations are legal only in their matching
// phase callback, never from event callbacks. A driver replaces the prescribed schedule.
public interface ISkillBattleDriver { void OnPhase(ISkillBattleControl battle, BattlePhase phase); }
public sealed record BattleConnectionSummary(string ContractVersion, bool ConnectionReady, bool GameVerified,
    long EventCount, IReadOnlyDictionary<CombatEventKind, long> EventCounts,
    IReadOnlyList<CombatEvent> Timeline, bool TimelineTruncated, FullBurstState FullBurst,
    IReadOnlyList<CooldownState> Cooldowns);

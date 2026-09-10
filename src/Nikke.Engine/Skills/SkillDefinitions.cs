using Nikke.Core.Combat;
using Nikke.Core.Stats;

namespace Nikke.Engine.Skills;

// Engine domain objects. The Data adapter owns JSON names and source selection.
public sealed record SkillFunction
{
    public int Id { get; init; }
    public int GroupId { get; init; }
    public int FunctionType { get; init; }
    public int FunctionStandard { get; init; }
    public int FunctionTarget { get; init; }
    public int FunctionValueType { get; init; }
    public long FunctionValue { get; init; }
    public int TimingTriggerType { get; init; }
    public int TimingTriggerStandard { get; init; }
    public int TimingTriggerValue { get; init; }
    public int StatusTriggerType { get; init; }
    public int StatusTriggerStandard { get; init; }
    public long StatusTriggerValue { get; init; }
    public int StatusTrigger2Type { get; init; }
    public int StatusTrigger2Standard { get; init; }
    public long StatusTrigger2Value { get; init; }
    public int DurationType { get; init; }
    public int DurationValue { get; init; }
    public int FullCount { get; init; } = 1;
    public int KeepingType { get; init; } = 2;
    public int DelayType { get; init; }
    public int DelayValue { get; init; }
    public int LimitValue { get; init; }
    public bool IsCancel { get; init; }
    public int Buff { get; init; }
    public IReadOnlyList<int> ConnectedFunction { get; init; } = [];
    public double Rate => (double)((decimal)FunctionValue / 10000);
}
public sealed record SkillValueParameter(int SkillValueType, long SkillValue);
public sealed record SkillBody
{
    public int SkillType { get; init; }
    public int SkillCooltime { get; init; }
    public int DurationType { get; init; }
    public int DurationValue { get; init; }
    public int AttackType { get; init; }
    public int PreferTarget { get; init; }
    public int PreferTargetCondition { get; init; }
    public IReadOnlyList<SkillValueParameter> SkillValueData { get; init; } = [];
}
public sealed record SkillDefinition
{
    public int SkillId { get; init; }
    public IReadOnlyList<int> FunctionIds { get; init; } = [];
    public IReadOnlyDictionary<string, int[]> FunctionPhases { get; init; } = new Dictionary<string, int[]>();
    public SkillBody Skill { get; init; }
}
public record SkillLoadout(string Squad, IReadOnlyDictionary<string, int> Levels,
    IReadOnlyDictionary<string, SkillDefinition> Slots)
{
    public int FullBurstDurationFrames { get; init; } = 600;
    public BurstConnectionProfile BurstConnection { get; init; }
}
public record SkillGraph(IReadOnlyDictionary<int, SkillFunction> Functions,
    IReadOnlyDictionary<int, SkillDefinition> CharacterSkills)
{
    public GaugeSourceConstants GaugeConstants { get; init; }
}
public record SkillReplayMember(WeaponReplayMember Weapon, double NativeHp, SkillLoadout Skills);
public record SkillCast(int Frame, string CharacterId, string Slot = "burst");
public record HpObservation(int Frame, string CharacterId, double Ratio);
public record SkillReplayConditions
{
    public WeaponReplayConditions Combat { get; init; } = new();
    public string RoundingPolicy { get; init; } = "";
    public IReadOnlyList<SkillCast> Casts { get; init; } = [];
    public IReadOnlyDictionary<string, double> InitialHpRatios { get; init; } = new Dictionary<string, double>();
    public IReadOnlyList<HpObservation> HpObservations { get; init; } = [];
    // Absolute cover HP is not derived by the P02 stat calculator. A fixture can supply it for target ranking.
    public IReadOnlyDictionary<string, CoverObservation> InitialCovers { get; init; } = new Dictionary<string, CoverObservation>();
    public string LowestHpTargetBasis { get; init; } = "ratio"; // pinned upstream candidate; verify against actual buff recipient
    public string LowestCoverTargetBasis { get; init; } = "absolute";
    public bool InterruptionTarget { get; init; }
}
public record CoverObservation(double MaxHp, double CurrentHp);
public record SkillTrace(long Id, long? ParentId, int Frame, string Kind, string Source, string Target,
    string Effect, int? FunctionId = null, int? SkillId = null, double? Value = null,
    int? Stacks = null, string Basis = null, int? ExpiresAt = null, HitContext Hit = null);
public record SkillEffectView(string Source, string Target, int FunctionId, int GroupId, int Type,
    double Value, int Stacks, int? ExpiresAt, string Basis);
public record SkillMemberResult(string CharacterId, double Damage, IReadOnlyDictionary<string, double> Effects,
    int Shots, int Hits, int CriticalHits, int AmmoConsumed, int RemainingAmmo, int MaxAmmo,
    double Hp, double MaxHp, double CoverRatio, IReadOnlyDictionary<string, int> CooldownReadyFrames);
public record SharedShieldView(string Source, int SkillId, double Hp, int ExpiresAt, long EventId);
public record SkillReplayResult(string RulesVersion, string Status, string SkillExecutionStatus,
    SkillReplayConditions Conditions, double TotalDamage, IReadOnlyList<SkillMemberResult> Members,
    IReadOnlyList<SkillTrace> Events, long EventCount, bool TraceTruncated,
    IReadOnlyList<SkillEffectView> ActiveEffects, IReadOnlyList<SharedShieldView> SharedShields, IReadOnlyList<string> Limitations)
{
    // Absent on p03.skills.1 saved records. Never retrofit readiness onto an old run.
    public BattleConnectionSummary Connection { get; init; }
}

public static class SkillUnits
{
    // 1/300 second units retain both frame (5 units) and centisecond (3 units) deadlines exactly.
    public const int TicksPerFrame = 5;
    public const int TicksPerCs = 3;
    public static int ReadyFrame(long ticks) => checked((int)((ticks + TicksPerFrame - 1) / TicksPerFrame));
    public static int Frames(int centiseconds) => Math.Max(0, checked((int)Math.Round(centiseconds * .6)));
    public static double Rate(long raw) => (double)((decimal)raw / 10000);
    public static int Cs(double seconds) => checked((int)Math.Round(seconds * 100));
}

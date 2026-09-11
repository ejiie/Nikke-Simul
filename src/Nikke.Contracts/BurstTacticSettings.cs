namespace Nikke.Contracts;

// External JSON contract aligned with E1 d7ce350; distinct from engine-owned DTOs.
public sealed record BurstTacticSettings
{
    public int SchemaVersion { get; init; } = 1;
    public string[] AllowedCharacterIds { get; init; } = [];
    public string[] Stage1Priority { get; init; } = [];
    public string[] Stage2Priority { get; init; } = [];
    public string[] Stage3Priority { get; init; } = [];
    public string[] Burst3Rotation { get; init; } = [];
    public string? FirstBurst3CharacterId { get; init; }
    public string UnavailablePolicy { get; init; } = "next_ready";
}

public sealed record SaveBurstTactic(string SnapshotId, string?[] FormationSlots, BurstTacticSettings? Tactic);
public sealed record SavedBurstTactic(string AccountId, string SnapshotId, string?[] FormationSlots,
    BurstTacticSettings? Tactic, DateTimeOffset SavedAt);

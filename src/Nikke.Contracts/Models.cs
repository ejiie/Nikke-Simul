using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Nikke.Contracts;

public static class Wire
{
    public static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web) { WriteIndented = false };
    public static string Serialize<T>(T value) => JsonSerializer.Serialize(value, Json);
    public static T Read<T>(string text) => JsonSerializer.Deserialize<T>(text, Json) ?? throw new InvalidDataException("Empty JSON");
    public static string Hash(string value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
    public static string Canonical(JsonNode? node) => node switch
    {
        JsonObject obj => "{" + string.Join(",", obj.OrderBy(x => x.Key, StringComparer.Ordinal).Select(x => Serialize(x.Key) + ":" + Canonical(x.Value))) + "}",
        JsonArray arr => "[" + string.Join(",", arr.Select(Canonical)) + "]",
        _ => node?.ToJsonString() ?? "null"
    };
}

public record Issue(string Severity, string Code, string Path, string Message);
public record AreaChoice(int Area, string Label, int CharacterCount, string OpenId);
public sealed record AccountConnection
{
    public int? ProfileIconId { get; set; }
    public string? AvatarPath { get; set; }
    public string? Nickname { get; set; }
    public string Id { get; init; } = Guid.NewGuid().ToString("N");
    public string Status { get; set; } = "awaiting_login";
    public string? OpenId { get; set; }
    public int? Area { get; set; }
    public string? AccountId { get; set; }
    public List<AreaChoice> Choices { get; set; } = [];
    public string? ErrorCode { get; set; }
    public string? Message { get; set; }
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}
public sealed record SyncJob
{
    public string Id { get; init; } = Guid.NewGuid().ToString("N");
    public string ConnectionId { get; init; } = "";
    public string AccountId { get; init; } = "";
    public string Status { get; set; } = "queued";
    public string Stage { get; set; } = "queued";
    public int Collected { get; set; }
    public int Expected { get; set; }
    public DateTimeOffset StartedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? FinishedAt { get; set; }
    public string? ErrorCode { get; set; }
    public string? Message { get; set; }
    public string? SnapshotId { get; set; }
    public List<Issue> Issues { get; set; } = [];
}
public sealed record GameSnapshot
{
    public int SchemaVersion { get; init; } = 1;
    public string Id { get; set; } = "";
    public string Source { get; init; } = "";
    public Dictionary<string, string> FileHashes { get; init; } = [];
    public Dictionary<string, string> Names { get; init; } = [];
    public Dictionary<string, decimal[]> OptionSteps { get; init; } = [];
    public Dictionary<string, string> FavoriteGrades { get; init; } = [];
}
public sealed record RawEnvelope
{
    public int? ProfileIconId { get; init; }
    public string? AvatarPath { get; init; }
    public string? Nickname { get; init; }
    public int SchemaVersion { get; init; } = 1;
    public string Source { get; init; } = "blablalink";
    public string CollectorVersion { get; init; } = "p01.1";
    public string OpenId { get; init; } = "";
    public int Area { get; init; }
    public DateTimeOffset StartedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset CompletedAt { get; init; } = DateTimeOffset.UtcNow;
    public JsonArray Characters { get; init; } = [];
    public JsonArray Details { get; init; } = [];
    public JsonArray StateEffects { get; init; } = [];
    public JsonObject? Outpost { get; init; }
    public JsonArray? RosterAfter { get; init; }
    public JsonArray Responses { get; init; } = [];
}
public sealed record EquipmentLine
{
    public int LineIndex { get; init; }
    public string Presence { get; init; } = "unknown";
    public string? OptionId { get; init; }
    public string? OptionType { get; init; }
    public decimal? RawValue { get; init; }
    public string? RawUnit { get; init; }
    public decimal? NormalizedValue { get; init; }
    public string? Unit { get; init; }
    public int? ValueTier { get; init; }
    public string LockState { get; set; } = "unknown";
    public string Source { get; set; } = "api";
}
public sealed record Equipment
{
    public string Slot { get; init; } = "";
    public string? ItemId { get; init; }
    public int? Tier { get; init; }
    public int? Level { get; init; }
    public int? Manufacturer { get; init; }
    public string Fingerprint { get; set; } = "";
    public List<EquipmentLine> Lines { get; init; } = [];
}
public sealed record CharacterBuild
{
    public string BuildSource { get; init; } = "api";
    public string CharacterId { get; init; } = "";
    public string Name { get; init; } = "";
    public bool CatalogKnown { get; init; }
    // Catalog membership is not proof of C# combat-effect support.
    public string CombatSupport { get; init; } = "not_evaluated";
    public int? Level { get; init; }
    public int? NativeLevel { get; init; }
    public int? LimitBreak { get; init; }
    public int? Core { get; init; }
    public int? Bond { get; init; }
    public Dictionary<string, int?> Skills { get; init; } = [];
    public string? CubeId { get; init; }
    public int? CubeLevel { get; init; }
    public string? CollectionId { get; init; }
    public int? CollectionLevel { get; init; }
    public string? CollectionGrade { get; init; }
    public int? FavoriteStage { get; init; }
    public List<Equipment> Equipment { get; init; } = [];
}
public record ManualOverride(string CharacterId, string Slot, int LineIndex, string LockState,
    string Fingerprint, DateTimeOffset UpdatedAt);
public sealed record AccountSnapshot
{
    public int SchemaVersion { get; init; } = 1;
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string AccountId { get; init; } = "";
    public string OpenId { get; init; } = "";
    public int Area { get; init; }
    public string GameSnapshotId { get; init; } = "";
    public string RawManifestId { get; init; } = "";
    public string NormalizerVersion { get; init; } = "p01.1";
    public DateTimeOffset ObservedAt { get; init; }
    public DateTimeOffset SavedAt { get; set; } = DateTimeOffset.UtcNow;
    public int Revision { get; set; }
    public string? PreviousId { get; set; }
    public string ContentHash { get; set; } = "";
    public int? SynchroLevel { get; set; }
    public Dictionary<string, int>? Consoles { get; set; }
    public Dictionary<string, int> CubeLevels { get; set; } = [];
    public string AccountStatsSource { get; set; } = "api";
    public Dictionary<string, string> AccountStatSources { get; set; } = [];
    public List<CharacterBuild> Characters { get; init; } = [];
    public List<Issue> Issues { get; set; } = [];
    public List<ManualOverride> ManualOverrides { get; set; } = [];
    public List<string> Changes { get; set; } = [];
    public bool Valid => !Issues.Any(x => x.Severity == "error");
}
public record OverrideRequest(string ExpectedSnapshotId, string? CharacterId, string? Slot, int? LineIndex,
    string? LockState, string? Fingerprint, int? SynchroLevel = null, Dictionary<string, int>? Consoles = null,
    Dictionary<string, int>? CubeLevels = null);
public record RunInputReference(string AccountSnapshotId, string GameSnapshotId, int ManualRevision,
    string ScenarioId, string TeamId, string TacticId);
public record CharacterEditRequest(string ExpectedSnapshotId, CharacterBuild Build);

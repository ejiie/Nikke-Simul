using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Engine;
using Nikke.Simulator.Core.Data.Dto;

namespace Nikke.Data;

public record WeaponReplayRequest(string SnapshotId, IReadOnlyList<string> CharacterIds, int? ScenarioLevel,
    WeaponReplayConditions Conditions);
public record SavedWeaponReplay(string Id, string Kind, DateTimeOffset CreatedAt, string AccountSnapshotId,
    string GameSnapshotId, string CalculationDataId, string RuntimeDataId, string StatRulesVersion,
    string HitRulesVersion, IReadOnlyDictionary<string, int> AppliedLevels, IReadOnlyList<WeaponReplayMember> Inputs, WeaponReplayResult Result);

public sealed partial class RuntimeReplayService
{
    private readonly string runtimeId;
    private readonly JsonObject catalog;
    private readonly string replayRoot;
    public RuntimeReplayService(string runtimeRoot, string replayRoot)
    {
        this.replayRoot = Path.GetFullPath(replayRoot);
        var manifest = JsonNode.Parse(File.ReadAllText(Path.Combine(runtimeRoot, "current.json")))!;
        runtimeId = manifest["id"]!.GetValue<string>();
        if (runtimeId.Length != 64 || runtimeId.Any(c => !Uri.IsHexDigit(c))) throw new InvalidDataException("Invalid runtime data ID");
        var bytes = File.ReadAllBytes(Path.Combine(runtimeRoot, runtimeId, "catalog.json"));
        if (Convert.ToHexStringLower(SHA256.HashData(bytes)) != runtimeId) throw new InvalidDataException("Runtime catalog hash mismatch");
        catalog = JsonNode.Parse(bytes)!.AsObject();
        if (catalog["schemaVersion"]!.GetValue<int>() != 1) throw new InvalidDataException("Unsupported runtime catalog schema");
    }

    public object Summary() => new { runtimeDataId = runtimeId, phase = "P04 team burst", skillExecutionStatus = "selected_five_effects_connected",
        weaponReferenceSkillExecutionStatus = "not_connected", skillReplayAvailable = true,
        weaponReferenceAvailable = true, functions = catalog["functions"]!.AsObject().Count,
        characterSkills = catalog["characterSkills"]!.AsObject().Count, missing = catalog["missing"]!.DeepClone(),
        characters = catalog["characters"]!.AsObject().Select(pair => new { characterId = pair.Key,
            name = pair.Value!["name"]!.GetValue<string>(), weapon = pair.Value["weapon"]!["weaponType"]!.GetValue<string>(),
            functionCount = pair.Value["functionIds"]!.AsArray().Count,
            skillExecutionStatus = "selected_five_effects_connected", support = SkillSupport(pair.Key) }).ToArray() };

    public SavedWeaponReplay Run(AccountSnapshot snapshot, WeaponReplayRequest request, CalculationService calculation)
    {
        if (request.SnapshotId != snapshot.Id || request.CharacterIds is null || request.CharacterIds.Count is < 1 or > 5
            || request.CharacterIds.Distinct().Count() != request.CharacterIds.Count)
            throw new ArgumentException("저장 스냅샷과 중복 없는 1~5명 편성을 지정하세요.");
        var reports = new List<StatReport>(); var members = new List<WeaponReplayMember>();
        foreach (var characterId in request.CharacterIds)
        {
            if (characterId is null || catalog["characters"]![characterId] is not JsonObject source)
                throw new ArgumentException("이번 P03 대상은 리타·블랑·누아르·앨리스·모더니아입니다.");
            var report = calculation.Calculate(snapshot, characterId, request.ScenarioLevel);
            if (report.Status == "incomplete" || report.BasicHit is null)
                throw new ArgumentException($"{report.Name}: 스탯 입력을 먼저 보완하세요.");
            var weapon = source["weapon"]!.Deserialize<WeaponDto>(Wire.Json)!;
            reports.Add(report); members.Add(new(characterId, weapon, report.BasicHit, report.PermanentBuffs));
        }
        var result = WeaponReplay.Run(members, request.Conditions);
        var saved = new SavedWeaponReplay(Guid.NewGuid().ToString("N"), "weapon_reference_replay", DateTimeOffset.UtcNow,
            snapshot.Id, snapshot.GameSnapshotId, reports[0].CalculationDataId, runtimeId, reports[0].StatRulesVersion,
            Nikke.Core.Combat.HitCalculator.Version, reports.ToDictionary(r => r.CharacterId, r => r.AppliedLevel), members, result);
        // Replays are immutable local artifacts, separate from account snapshots and future statistical run tables.
        Directory.CreateDirectory(replayRoot);
        string path = Path.Combine(replayRoot, saved.Id + ".json");
        string pending = path + ".tmp";
        File.WriteAllText(pending, Wire.Serialize(saved)); File.Move(pending, path);
        return saved;
    }

    public SavedWeaponReplay Read(string id)
    {
        if (!Guid.TryParseExact(id, "N", out _)) throw new ArgumentException("검산 기록 ID를 확인하세요.");
        string path = Path.Combine(replayRoot, id + ".json");
        if (!File.Exists(path)) throw new KeyNotFoundException();
        return Wire.Read<SavedWeaponReplay>(File.ReadAllText(path));
    }
}

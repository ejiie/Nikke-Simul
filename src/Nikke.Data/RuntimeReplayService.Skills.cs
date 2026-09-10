using System.Text.Json;
using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Engine;
using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Data.Dto;

namespace Nikke.Data;

public record SkillReplayRequest(string SnapshotId, IReadOnlyList<string> CharacterIds, int? ScenarioLevel, SkillReplayConditions Conditions);
public record SavedSkillReplay(string Id, string Kind, DateTimeOffset CreatedAt, string AccountSnapshotId, string GameSnapshotId,
    string CalculationDataId, string RuntimeDataId, string StatRulesVersion, string HitRulesVersion,
    IReadOnlyDictionary<string,int> AppliedLevels, IReadOnlyList<SkillReplayMember> Inputs, SkillReplayResult Result);

public sealed partial class RuntimeReplayService
{
    private static readonly JsonSerializerOptions OfficialJson = new() { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
    private SkillGraph Graph() => new(catalog["functions"]!.AsObject().ToDictionary(p=>int.Parse(p.Key),p=>p.Value!.Deserialize<SkillFunction>(OfficialJson)!),
        catalog["characterSkills"]!.AsObject().ToDictionary(p=>int.Parse(p.Key),p=>p.Value!.Deserialize<SkillDefinition>(OfficialJson)!))
        { GaugeConstants = catalog["gaugeConstants"]?.Deserialize<GaugeSourceConstants>(Wire.Json) };

    private SkillLoadout Loadout(string id, IReadOnlyDictionary<string,int> levels)
    {
        if (catalog["characters"]![id] is not JsonObject source) throw new ArgumentException("이번 P03의 5인 대상이 아닙니다.");
        var slots = new Dictionary<string,SkillDefinition>();
        foreach (var slot in new[] { "skill1", "skill2", "burst" })
        {
            if (!levels.TryGetValue(slot,out int lv) || lv is < 1 or > 10
                || source["official"]!["skills"]![slot]!["levels"]![lv.ToString()] is not JsonObject definition)
                throw new ArgumentException($"{id} {slot}: 스킬 레벨·공식 자료가 필요합니다.");
            slots[slot] = definition.Deserialize<SkillDefinition>(OfficialJson)!;
        }
        // Official public role metadata is preferred; old catalog fallback is explicitly pinned upstream metadata.
        string squad = source["sourceRole"]?["squad"]?.GetValue<string>() ?? source["upstreamCharacter"]!["squad"]!.GetValue<string>();
        int burstCs=source["sourceRole"]?["burstDurationCs"]?.GetValue<int>() ?? source["official"]!["burst_duration"]!.GetValue<int>();
        return new(squad,levels,slots) { FullBurstDurationFrames=SkillUnits.Frames(burstCs),
            BurstConnection=source["burstConnection"]?.Deserialize<BurstConnectionProfile>(Wire.Json) };
    }
    private object SkillSupport(string id)
    {
        var graph=Graph();
        var levels=Enumerable.Range(1,10).Select(lv=>new { level=lv, unsupported=SkillReplay.CheckSupport(
            Loadout(id,new Dictionary<string,int> { ["skill1"]=lv,["skill2"]=lv,["burst"]=lv }),graph) }).ToArray();
        var profile=Loadout(id,new Dictionary<string,int> { ["skill1"]=1,["skill2"]=1,["burst"]=1 }).BurstConnection;
        return new { allLevelsExecutable=levels.All(l=>l.unsupported.Count==0), levels, gameVerified=false,
            connectionReady=levels.All(l=>l.unsupported.Count==0), burstSourceAvailable=profile is not null && graph.GaugeConstants is not null,
            burstConnection=profile, gaugeFormulaStatus=graph.GaugeConstants?.FormulaStatus ?? "missing",
            automaticCycleReady=levels.All(l=>l.unsupported.Count==0) && profile is not null && graph.GaugeConstants is not null,
            automaticGaugeModel="source_full_charge_v2", automaticGaugeFormulaStatus="reference_candidate" };
    }
    public SavedSkillReplay RunSkills(AccountSnapshot snapshot, SkillReplayRequest request, CalculationService calculation)
    {
        if (request.SnapshotId!=snapshot.Id || request.CharacterIds is null || request.CharacterIds.Count is < 1 or > 5
            || request.CharacterIds.Distinct().Count()!=request.CharacterIds.Count)
            throw new ArgumentException("스냅샷과 중복 없는 1~5인 편성을 지정하세요.");
        var reports=new List<StatReport>(); var members=new List<SkillReplayMember>();
        foreach (var id in request.CharacterIds)
        {
            var build=snapshot.Characters.SingleOrDefault(c=>c.CharacterId==id) ?? throw new ArgumentException("보유 캐릭터를 지정하세요.");
            if (build.FavoriteStage is > 0) throw new ArgumentException($"{id}: 애장품 스킬 교체는 아직 지원하지 않습니다.");
            var report=calculation.Calculate(snapshot,id,request.ScenarioLevel);
            if (report.Status=="incomplete" || report.BasicHit is null || report.NativeStats is null)
                throw new ArgumentException($"{id}: 스탯 입력을 보완하세요.");
            var levels=new Dictionary<string,int>();
            foreach (var (slot, snapshotKey) in new[] { ("skill1", "1"), ("skill2", "2"), ("burst", "3") })
            {
                if (!build.Skills.TryGetValue(snapshotKey,out int? lv) || lv is null) throw new ArgumentException($"{id}: {slot} 레벨이 없습니다.");
                levels[slot]=lv.Value;
            }
            var loadout=Loadout(id,levels);
            var weapon=catalog["characters"]![id]!["weapon"]!.Deserialize<WeaponDto>(Wire.Json)!;
            members.Add(new(new(id,weapon,report.BasicHit,report.PermanentBuffs),report.NativeStats.HP,loadout));
            reports.Add(report);
        }
        var result=SkillReplay.Run(members,Graph(),request.Conditions);
        var saved=new SavedSkillReplay(Guid.NewGuid().ToString("N"),request.Conditions.AutoBurst is null ? "skill_reference_replay" : "team_burst_replay",DateTimeOffset.UtcNow,snapshot.Id,snapshot.GameSnapshotId,
            reports[0].CalculationDataId,runtimeId,reports[0].StatRulesVersion,Nikke.Core.Combat.HitCalculator.Version,
            reports.ToDictionary(r=>r.CharacterId,r=>r.AppliedLevel),members,result);
        string folder=Path.Combine(Path.GetDirectoryName(replayRoot)!,"skill-replays"); Directory.CreateDirectory(folder);
        string path=Path.Combine(folder,saved.Id+".json");
        File.WriteAllText(path+".tmp",Wire.Serialize(saved)); File.Move(path+".tmp",path);
        return saved;
    }
    public SavedSkillReplay ReadSkills(string id)
    {
        if (!Guid.TryParseExact(id,"N",out _)) throw new ArgumentException("스킬 검산 기록 ID를 확인하세요.");
        string path=Path.Combine(Path.GetDirectoryName(replayRoot)!,"skill-replays",id+".json");
        if (!File.Exists(path)) throw new KeyNotFoundException();
        return Wire.Read<SavedSkillReplay>(File.ReadAllText(path));
    }
}

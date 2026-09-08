using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Core.Combat;
using Nikke.Simulator.Core.Data.Dto;
using Nikke.Simulator.Core.Stats;

namespace Nikke.Data;

public record StatVector(double HP, double ATK, double DEF)
{
    public static StatVector From((double HP, double ATK, double DEF) v) => new(v.HP, v.ATK, v.DEF);
    public static StatVector operator +(StatVector a, StatVector b) => new(a.HP + b.HP, a.ATK + b.ATK, a.DEF + b.DEF);
    public static StatVector operator -(StatVector a, StatVector b) => new(a.HP - b.HP, a.ATK - b.ATK, a.DEF - b.DEF);
}
public record StatStep(string Name, StatVector Value, string Source);
public record StatReport(string AccountSnapshotId, string GameSnapshotId, string CalculationDataId,
    string CharacterId, string Name, int AccountLevel, int AppliedLevel, string LevelSource,
    string Status, IReadOnlyList<Issue> Issues, IReadOnlyList<StatStep> Steps,
    StatVector? Total, HitContext? BasicHit, IReadOnlyList<string> DeferredEffects);

// One immutable table set per API process. Legacy StatTable is initialized only in this constructor.
public sealed class CalculationService
{
    private readonly JsonObject roles, equipment, cubeBase, cubes, collection, names, metadata;
    private readonly string dataId;
    public CalculationService(string calculationRoot)
    {
        var manifest = JsonNode.Parse(File.ReadAllText(Path.Combine(calculationRoot, "current.json")))!;
        dataId = manifest["id"]!.GetValue<string>();
        if (dataId.Length != 64 || dataId.Any(c => !Uri.IsHexDigit(c))) throw new InvalidDataException("Invalid calculation ID");
        var folder = Path.Combine(calculationRoot, dataId);
        foreach (var entry in manifest["fileHashes"]!.AsObject())
        {
            if (Path.GetFileName(entry.Key) != entry.Key) throw new InvalidDataException("Invalid table filename");
            var actual = Convert.ToHexStringLower(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(Path.Combine(folder, entry.Key))));
            if (actual != entry.Value!.GetValue<string>()) throw new InvalidDataException("Calculation table hash mismatch");
        }
        if (Wire.Hash(Wire.Canonical(manifest["fileHashes"])) != dataId) throw new InvalidDataException("Calculation manifest ID mismatch");
        JsonObject Read(string name) => JsonNode.Parse(File.ReadAllText(Path.Combine(folder, name)))!.AsObject();
        roles = Read("roledata_clean.json"); equipment = Read("equip_stat_table.json");
        names = Read("name_codes.json"); metadata = Read("parsed_nikke.json");
        cubeBase = Read("cube_base_table.json"); cubes = Read("cube_effect_table.json"); collection = Read("collection.json");
        StatTable.Initialize(Path.Combine(folder, "stat_table.csv"));
        StatTable.InitializeEquipment(Path.Combine(folder, "equip_stat_table.json"));
    }

    public StatReport Calculate(AccountSnapshot snapshot, string characterId, int? scenarioLevel = null)
    {
        var c = snapshot.Characters.SingleOrDefault(x => x.CharacterId == characterId) ?? throw new KeyNotFoundException();
        var issues = new List<Issue>(); var steps = new List<StatStep>(); var deferred = new List<string>();
        void Error(string code, string path, string message) => issues.Add(new("error", code, path, message));
        var level = scenarioLevel ?? c.Level ?? 0;
        StatReport Result(StatVector? total = null, HitContext? hit = null) => new(snapshot.Id, snapshot.GameSnapshotId, dataId, c.CharacterId,
            c.Name, c.Level ?? 0, level, scenarioLevel is null ? "account_snapshot" : "scenario_override", issues.Any(x => x.Severity == "error") ? "incomplete" : "stat_ready_hit_provisional",
            issues, steps, total, hit, deferred);
        var role = roles[characterId];
        if (role is null) { Error("missing_role", characterId, "고정된 정적 테이블에 캐릭터가 없습니다."); return Result(); }
        string Str(string key) => role[key]?.GetValue<string>() ?? "";
        var cls = Str("class"); var weapon = Str("weapon"); var manufacturer = Str("manufacturer");
        var shortWeapon = weapon switch { "Assault Rifle" => "AR", "Sniper Rifle" => "SR", "Shotgun" => "SG", "Rocket Launcher" => "RL", "Minigun" or "Machine Gun" => "MG", "SMG" or "Submachine Gun" => "SMG", _ => "" };
        var classId = cls switch { "Attacker" => "1101", "Defender" => "1102", "Supporter" => "1103", _ => "" };
        var companyId = manufacturer switch { "Elysion" => "1201", "Missilis" => "1202", "Tetra" => "1203", "Pilgrim" => "1204", "Abnormal" => "1205", _ => "" };
        if (shortWeapon == "" || classId == "" || companyId == "") Error("unknown_metadata", characterId, "무기·직업·제조사 매핑을 확인해야 합니다.");
        // The legacy class-level table has no rarity axis. Do not apply it silently to R/SR characters.
        var name = names[characterId]?.GetValue<string>();
        if (name is null || metadata[name]?["rarity"]?.GetValue<string>() != "SSR") Error("unsupported_rarity", characterId, "이 등급의 기초 스탯 표는 아직 검증되지 않았습니다.");
        foreach (var key in new[] { "1001", classId, companyId })
            if (snapshot.Consoles is null || !snapshot.Consoles.ContainsKey(key)) Error("missing_console", key, "해당 연구실 레벨을 먼저 보완하세요.");
        if (c.LimitBreak is null or < 0 or > 3 || c.Core is null or < 0 or > 7 || c.Bond is null or < 0 or > 40)
            Error("missing_growth", characterId, "돌파·코어·호감도 입력을 확인하세요.");
        var lv = StatTable.GetLevelClassStat(level, cls);
        var bond = StatTable.GetBondClassStat(c.Bond ?? 0, cls);
        if (level <= 0 || lv.HP <= 0 || lv.ATK <= 0) Error("missing_level_table", "level", "적용 레벨의 기초 스탯 표가 없습니다.");
        if (c.Bond > 0 && bond.HP == 0) Error("missing_bond_table", "bond", "호감도 스탯 표가 없습니다.");
        if (c.Equipment.Count != 4 || c.Equipment.Select(x => x.Slot).Distinct().Count() != 4) Error("equipment_slots", "equipment", "4부위 입력이 필요합니다.");
        var parts = new EquipmentPartsDto();
        foreach (var eq in c.Equipment)
        {
            if (eq.Tier is null or < 0 || eq.Level is null or < 0 or > 5 || eq.Manufacturer is null || !new[] { 0, 1, 2, 3, 4, 7 }.Contains(eq.Manufacturer.Value))
                Error("equipment_input", eq.Slot, "장비 티어·강화·제조사를 확인하세요.");
            if (eq.Tier > 0 && equipment[cls]?[eq.Tier.ToString()!]?[eq.Slot] is null) Error("equipment_table", eq.Slot, "장비 기초 스탯 표가 없습니다.");
            var dto = new EquipmentInfoDto { tier = eq.Tier ?? 0, level = eq.Level ?? 0, corp = eq.Manufacturer ?? 0 };
            switch (eq.Slot) { case "head": parts.head = dto; break; case "torso": parts.torso = dto; break; case "arm": parts.arm = dto; break; case "leg": parts.leg = dto; break; default: Error("unknown_slot", eq.Slot, "알 수 없는 장비 부위입니다."); break; }
            foreach (var line in eq.Lines)
            {
                if (line.Presence == "unknown" || line.Presence == "present" && (line.NormalizedValue is null || line.Unit != "ratio"))
                    Error("unknown_option", eq.Slot, "단위가 확인되지 않은 OL 옵션입니다.");
                if (line.Presence == "present" && !new[] { "StatAtk", "StatMaxHP", "StatDef", "IncHurtDef", "StatCritical", "StatCriticalDamage", "StatChargeDamage", "StatChargeTime", "StatAmmoLoad", "IncElementDmg", "StatAccuracyCircle", "StatReloadTime" }.Contains(line.OptionType))
                    Error("unmapped_option", eq.Slot, "계산에 연결되지 않은 OL 옵션 종류입니다.");
            }
        }
        var effects = new Dictionary<string, double>();
        void Add(string key, double value) => effects[key] = effects.GetValueOrDefault(key) + value;
        var cube = new StatVector(0, 0, 0); var coll = cube;
        if (c.CubeId is null) Error("unknown_cube", "cube", "큐브 장착 여부가 미확인입니다.");
        else if (c.CubeId != "0")
        {
            var row = cubeBase[c.CubeLevel?.ToString() ?? ""];
            var effectRows = cubes[c.CubeId]?["effects"] as JsonArray;
            if (row is null || effectRows is null) Error("cube_table", "cube", "큐브 종류·레벨에 해당하는 표가 없습니다.");
            else
            {
                cube = Vector(row, upper: true);
                foreach (var effect in effectRows.OfType<JsonObject>())
                {
                    var type = effect["type"]!.GetValue<string>();
                    if (effect["conditional"]?.GetValue<bool>() == true) { deferred.Add($"cube:{type}:conditional"); continue; }
                    var vals = effect["values"]!.AsArray(); var index = c.CubeLevel!.Value - 1;
                    if (index < 0 || index >= vals.Count) Error("cube_effect_level", "cube", "큐브 효과 레벨이 표 범위를 벗어났습니다.");
                    else Add(type, vals[index]!.GetValue<double>() / 100);
                }
            }
        }
        if (c.CollectionId is null || c.CollectionGrade is null) Error("unknown_collection", "collection", "소장품 종류가 미확인입니다.");
        else if (c.CollectionId != "0")
        {
            var grade = c.CollectionGrade == "SSR" ? "SR" : c.CollectionGrade;
            var collLevel = c.CollectionGrade == "SSR" ? 15 : c.CollectionLevel;
            if (c.CollectionGrade == "SSR" && c.CollectionLevel is not (>= 0 and <= 2)) Error("favorite_stage", "collection", "애장품 단계가 표 범위를 벗어났습니다.");
            var row = collection["_stat_table"]?[$"{grade}{collLevel}"];
            if (row is null) Error("collection_table", "collection", "소장품 등급·레벨에 해당하는 표가 없습니다.");
            else
            {
                coll = Vector(row, upper: false); var skillIndex = row["skill_lv"]!.GetValue<int>() - 1;
                var entries = collection["common"]!.AsObject().Select(x => x.Value).Append(collection[shortWeapon]);
                foreach (var entry in entries)
                    if (entry?[grade] is JsonArray vals)
                    {
                        var type = entry["buff_type"]!.GetValue<string>();
                        var mapped = type switch { "def_pct" => "Def", "core_dmg_pct" => "CoreDamage", "max_ammo_pct" => "MaxAmmo", "charge_dmg_mag_pct" => "ChargeDamageMultiplier", "normal_atk_dmg_pct" => "NormalAttackMultiplier", _ => type };
                        Add(mapped, vals[skillIndex]!.GetValue<double>() / 100);
                    }
                if (c.CollectionGrade == "SSR") deferred.Add("favorite:skill_replacement:P03");
            }
        }
        if (issues.Any(x => x.Severity == "error")) return Result();
        var baseStat = new StatVector(lv.HP, lv.ATK, lv.DEF[shortWeapon]);
        var bondStat = new StatVector(bond.HP, bond.ATK, bond.DEF["ALL"]);
        var consoles = StatVector.From(StatCalculator.GetConsoleStats(cls, manufacturer, snapshot.Consoles!));
        int g = c.LimitBreak!.Value;
        var gradeBonus = new StatVector(Math.Floor(baseStat.HP * g * .02) + 3000 * g, Math.Floor(baseStat.ATK * g * .02) + 20 * g, Math.Floor(baseStat.DEF * g * .02) + 100 * g);
        var core = StatVector.From(StatCalculator.GetCoreAppliedStats(cls, weapon, manufacturer, level, g, c.Core!.Value, c.Bond!.Value, snapshot.Consoles!));
        steps.Add(new("level", baseStat, "legacy StatTable")); steps.Add(new("limitBreak", gradeBonus, "legacy StatCalculator: floor + flat"));
        steps.Add(new("bond", bondStat, "legacy StatTable")); steps.Add(new("console", consoles, "legacy StatCalculator"));
        steps.Add(new("coreEnhancement", core - baseStat - gradeBonus - bondStat - consoles, "legacy: round away from zero"));
        foreach (var eq in c.Equipment.Where(x => x.Tier > 0))
        {
            var only = new EquipmentPartsDto(); var dto = new EquipmentInfoDto { tier = eq.Tier!.Value, level = eq.Level!.Value, corp = eq.Manufacturer!.Value };
            switch (eq.Slot) { case "head": only.head = dto; break; case "torso": only.torso = dto; break; case "arm": only.arm = dto; break; case "leg": only.leg = dto; break; }
            steps.Add(new("equipment:" + eq.Slot, StatVector.From(StatCalculator.GetEquipmentStats(cls, manufacturer, only)), "legacy: per slot/stat round"));
        }
        var gear = StatVector.From(StatCalculator.GetEquipmentStats(cls, manufacturer, parts));
        steps.Add(new("cube", cube, "legacy cube table; exact level"));
        steps.Add(new("collection", coll, "upstream grade + API level (SSR: SR15)"));
        var native = core + gear + cube + coll;
        var rated = new StatVector(native.HP * (1 + effects.GetValueOrDefault("MaxHp")), native.ATK, native.DEF * (1 + effects.GetValueOrDefault("Def")));
        steps.Add(new("accessoryRates", rated - native, "legacy assembly order; passive HP/DEF rates"));
        double[] Options(string type) => c.Equipment.SelectMany(x => x.Lines).Where(x => x.Presence == "present" && (x.OptionType == type || type == "StatDef" && x.OptionType == "IncHurtDef")).Select(x => (double)x.NormalizedValue!.Value).ToArray();
        double Final(double n, string type) => OverloadProcessor.CalculateFinalBaseStat(n, Options(type));
        var total = new StatVector(Final(rated.HP, "StatMaxHP"), Final(rated.ATK, "StatAtk"), Final(rated.DEF, "StatDef"));
        steps.Add(new("overload", total - rated, "legacy group equal values then round; normalized ratios"));
        var basic = role["basicAttack"];
        if (basic is null || basic["multiplier"] is null) { Error("missing_weapon", characterId, "평타 계수가 없습니다."); return Result(total); }
        var chargeWeapon = role["weaponData"]?["isChargeWeapon"]?.GetValue<bool>() ?? false;
        var hit = new HitContext { Attack = total.ATK, Defense = 0, Coefficient = basic["multiplier"]!.GetValue<double>() / 100 * (1 + effects.GetValueOrDefault("NormalAttackMultiplier")),
            ChargeApplicable = chargeWeapon, ChargeBase = basic["chargeDamage"]!.GetValue<double>(),
            ChargeAdd = Options("StatChargeDamage").Sum() + effects.GetValueOrDefault("ChargeDamage"), ChargeMultiplierBonus = effects.GetValueOrDefault("ChargeDamageMultiplier"),
            CritBonus = .5 + Options("StatCriticalDamage").Sum(), CoreBonus = basic["coreHitBonus"]!.GetValue<double>() + effects.GetValueOrDefault("CoreDamage"),
            ElementBonus = Options("IncElementDmg").Sum() + effects.GetValueOrDefault("ElementAdvantageDamage"),
            PartsDamage = effects.GetValueOrDefault("PartsDamage"), PierceDamage = effects.GetValueOrDefault("PierceDamage"), TrueDamage = effects.GetValueOrDefault("TrueDamage") };
        deferred.Add("character_skills_and_team_buffs:P03/P04");
        foreach (var type in new[] { "StatAccuracyCircle", "StatAmmoLoad", "StatChargeTime", "StatReloadTime", "StatCritical" })
            if (Options(type).Length > 0) deferred.Add("overload:" + type + ":weapon_runtime_or_rng:P03");
        foreach (var effect in effects.Keys.Where(x => !new[] { "MaxHp", "Def", "NormalAttackMultiplier", "ChargeDamage", "ChargeDamageMultiplier", "CoreDamage", "ElementAdvantageDamage", "PartsDamage", "PierceDamage", "TrueDamage" }.Contains(x))) deferred.Add("accessory:" + effect + ":not_consumed_in_single_hit");
        return Result(total, hit);
    }
    private static StatVector Vector(JsonNode row, bool upper) => new(row[upper ? "HP" : "hp"]!.GetValue<double>(), row[upper ? "ATK" : "atk"]!.GetValue<double>(), row[upper ? "DEF" : "def"]!.GetValue<double>());
}

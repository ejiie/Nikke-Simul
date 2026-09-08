using System.Globalization;
using System.Text.Json.Nodes;
using Nikke.Contracts;

namespace Nikke.Data;

public sealed class SnapshotNormalizer
{
    public static readonly string[] Parts = ["head", "torso", "arm", "leg"];
    // These API effects use Integer storage but represent basis-point rates, not flat counts.
    // Cross-checked against profile_fetch.py's mapping and the pinned OL step table.
    public static readonly HashSet<string> IntegerRates = ["StatCritical", "StatCriticalDamage", "StatChargeDamage"];
    // Adapted from upstream profile_fetch.py FUNC_TO_EQUIP. Preserve signed raw values.
    public static readonly Dictionary<string, string> OptionKeys = new()
    {
        ["StatAtk"] = "atk_pct", ["IncElementDmg"] = "element_bonus", ["StatAmmoLoad"] = "max_ammo_pct",
        ["StatCritical"] = "crit_rate", ["StatCriticalDamage"] = "crit_dmg", ["StatChargeTime"] = "charge_speed_pct",
        ["StatChargeDamage"] = "charge_dmg_pct", ["StatAccuracyCircle"] = "accuracy_pct",
        ["IncHurtDef"] = "def_pct", ["StatDef"] = "def_pct"
    };
    public AccountSnapshot Normalize(RawEnvelope raw, GameSnapshot game, string accountId, string openId, int area, string manifestId)
    {
        var issues = new List<Issue>();
        void Error(string code, string path, string message) => issues.Add(new("error", code, path, message));
        void Note(string code, string path, string message) => issues.Add(new("warning", code, path, message));
        int? Number(JsonNode node, string field, string path, bool required = true, int min = 0, int max = int.MaxValue)
        {
            var value = node[field];
            if (value is null) { if (required) Error("missing_field", path + "." + field, "필수 원천 필드가 없습니다."); return null; }
            if (!int.TryParse(value.ToString(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var n) || n < min || n > max)
            { Error("invalid_field", path + "." + field, "수치 형식 또는 범위가 올바르지 않습니다."); return null; }
            return n;
        }
        Dictionary<string, JsonNode> Index(JsonArray rows, string field, string path)
        {
            var result = new Dictionary<string, JsonNode>();
            foreach (var row in rows)
            {
                var id = row is JsonObject ? Id(row[field]) : null;
                if (id is null) { Error("missing_id", path, "원천 ID가 없거나 잘못되었습니다."); continue; }
                if (result.TryGetValue(id, out var prior))
                {
                    if (Wire.Canonical(prior) != Wire.Canonical(row)) Error("duplicate_conflict", path + "." + id, "같은 ID의 응답이 서로 다릅니다.");
                    else Note("duplicate_identical", path + "." + id, "동일한 중복 응답을 하나로 정리했습니다.");
                }
                else result[id] = row!;
            }
            return result;
        }
        if (raw.SchemaVersion != 1) Error("schema_version", "raw", "지원하지 않는 원천 계약 버전입니다.");
        if (raw.OpenId != openId || raw.Area != area) Error("account_mismatch", "raw", "선택한 계정·서버와 수집 응답이 다릅니다.");
        if (raw.CompletedAt < raw.StartedAt) Error("invalid_time", "raw", "수집 시각이 역전되었습니다.");
        var roster = Index(raw.Characters, "name_code", "characters");
        var details = Index(raw.Details, "name_code", "details");
        var effects = Index(raw.StateEffects, "id", "stateEffects");
        if (roster.Count == 0) Error("empty_roster", "characters", "로스터가 비어 있습니다.");
        foreach (var id in roster.Keys.Except(details.Keys)) Error("missing_detail", id, "캐릭터 상세가 누락되었습니다.");
        foreach (var id in details.Keys.Except(roster.Keys)) Error("unexpected_detail", id, "로스터에 없는 캐릭터 상세입니다.");
        if (raw.RosterAfter is not null)
        {
            var after = Index(raw.RosterAfter, "name_code", "rosterAfter");
            if (!roster.Keys.ToHashSet().SetEquals(after.Keys)) Error("roster_changed", "rosterAfter", "수집 중 로스터가 변경되었습니다.");
            foreach (var id in roster.Keys.Intersect(after.Keys))
                foreach (var field in new[] { "lv", "grade", "core" })
                    if (Wire.Canonical(roster[id][field]) != Wire.Canonical(after[id][field])) Error("roster_changed", id, "수집 중 육성값이 변경되었습니다.");
        }
        else Note("no_roster_recheck", "raw", "보관된 원천에는 수집 후 로스터 재확인 정보가 없습니다.");

        var builds = new List<CharacterBuild>();
        foreach (var (id, entry) in roster.OrderBy(x => x.Key, StringComparer.Ordinal))
        {
            if (!details.TryGetValue(id, out var detail)) continue;
            var equipment = new List<Equipment>();
            foreach (var part in Parts)
            {
                var path = id + "." + part;
                var lines = new List<EquipmentLine>();
                for (var i = 1; i <= 3; i++)
                {
                    var field = $"{part}_equip_option{i}_id";
                    var oid = Id(detail[field]);
                    if (oid is null) { Error("missing_option_slot", path + "." + i, "옵션 줄 정보가 없습니다."); lines.Add(new() { LineIndex = i }); continue; }
                    if (oid == "0") { lines.Add(new() { LineIndex = i, OptionId = oid, Presence = "absent", LockState = "not_applicable" }); continue; }
                    if (!effects.TryGetValue(oid, out var effect) || effect["function_details"] is not JsonArray functions || functions.Count != 1)
                    { Error("missing_option_mapping", path + "." + i, "옵션 ID에 대응하는 단일 효과를 확인할 수 없습니다."); lines.Add(new() { LineIndex = i, OptionId = oid, Presence = "present" }); continue; }
                    var f = functions[0];
                    var type = f?["function_type"]?.ToString();
                    var unit = f?["function_value_type"]?.ToString();
                    decimal? value = decimal.TryParse(f?["function_value"]?.ToString(), NumberStyles.Float, CultureInfo.InvariantCulture, out var v) ? v : null;
                    bool ratio = unit == "Percent" || (unit == "Integer" && type is not null && IntegerRates.Contains(type));
                    decimal? normalized = ratio ? value / 10000m : unit == "Integer" ? value : null;
                    if (type is null || normalized is null) Error("invalid_option", path + "." + i, "옵션의 종류·값·단위를 해석할 수 없습니다.");
                    int? valueTier = null;
                    if (type is not null && OptionKeys.TryGetValue(type, out var key) && normalized.HasValue && ratio)
                    {
                        if (game.OptionSteps.TryGetValue(key, out var steps))
                        {
                            var index = Array.FindIndex(steps, n => n == Math.Abs(normalized.Value));
                            if (index >= 0) valueTier = index + 1;
                        }
                        if (valueTier is null) Note("option_off_table", path + "." + i, "옵션 단계표와 일치하지 않아 원천 수치를 보존했습니다.");
                    }
                    else Note("unsupported_option", path + "." + i, "아직 지원 여부를 확인하지 않은 옵션입니다.");
                    lines.Add(new() { LineIndex = i, Presence = "present", OptionId = oid, OptionType = type,
                        RawValue = value, RawUnit = unit, NormalizedValue = normalized, Unit = ratio ? "ratio" : unit == "Integer" ? "integer" : null, ValueTier = valueTier });
                }
                var equip = new Equipment { Slot = part, ItemId = Id(detail[part + "_equip_tid"]),
                    Tier = Number(detail, part + "_equip_tier", path), Level = Number(detail, part + "_equip_lv", path, max: 5),
                    Manufacturer = Number(detail, part + "_equip_corporation_type", path), Lines = lines };
                if (equip.Tier == 0 && lines.Any(x => x.Presence == "present")) Error("inconsistent_equipment", path, "미장착 장비에 옵션이 존재합니다.");
                equip.Fingerprint = Wire.Hash(Wire.Canonical(JsonNode.Parse(Wire.Serialize(equip))));
                equipment.Add(equip);
            }
            var favoriteId = Id(detail["favorite_item_tid"]);
            var favoriteLv = Number(detail, "favorite_item_lv", id);
            var grade = favoriteId == "0" ? "none" : favoriteId is not null ? game.FavoriteGrades.GetValueOrDefault(favoriteId) : null;
            if (favoriteId is null) Error("missing_collection_id", id, "소장품 ID가 없습니다.");
            else if (grade is null) Note("unknown_collection", id, "소장품 종류를 확인하지 못했습니다. 원천 ID·레벨을 보존합니다.");
            var known = game.Names.TryGetValue(id, out var name);
            if (!known) Note("unknown_character", id, "표시 목록에 없는 캐릭터입니다. 원천 스펙은 보존합니다.");
            builds.Add(new() { CharacterId = id, Name = name ?? $"미등록 니케 {id}", CatalogKnown = known,
                Level = Number(entry, "lv", id), NativeLevel = Number(detail, "lv", id),
                LimitBreak = Number(entry, "grade", id), Core = Number(entry, "core", id), Bond = Number(detail, "attractive_lv", id),
                Skills = new() { ["1"] = Number(detail, "skill1_lv", id, min: 1, max: 10), ["2"] = Number(detail, "skill2_lv", id, min: 1, max: 10), ["3"] = Number(detail, "ulti_skill_lv", id, min: 1, max: 10) },
                CubeId = Id(detail["harmony_cube_tid"]), CubeLevel = Number(detail, "harmony_cube_lv", id),
                CollectionId = favoriteId, CollectionLevel = favoriteLv, CollectionGrade = grade,
                FavoriteStage = grade == "SSR" ? favoriteLv + 1 : grade is null ? null : 0, Equipment = equipment });
        }
        Dictionary<string, int>? consoles = null;
        if (raw.Outpost?["recycle_room_researches"] is JsonArray researches)
        {
            consoles = [];
            foreach (var row in researches.OfType<JsonObject>())
            {
                var tid = Id(row["tid"]); var lv = Number(row, "lv", "consoles");
                if (tid is null) Error("invalid_console", "consoles", "연구실 ID가 없습니다.");
                else if (lv.HasValue) { if (consoles.TryGetValue(tid, out var prior) && prior != lv) Error("duplicate_console", tid, "연구실 레벨이 충돌합니다."); consoles[tid] = lv.Value; }
            }
        }
        if (consoles is null) Note("unknown_consoles", "account", "재활용 연구실 정보가 미확인입니다.");
        var synchro = raw.Outpost is null ? null : Number(raw.Outpost, "synchro_level", "account", required: false, min: 1);
        if (synchro is null) Note("unknown_synchro", "account", "싱크로 레벨이 미확인입니다.");
        var statSources = new Dictionary<string, string>();
        if (synchro.HasValue) statSources["synchro"] = "api";
        if (consoles is not null) foreach (var id in consoles.Keys) statSources["console:" + id] = "api";
        return new() { AccountId = accountId, OpenId = raw.OpenId, Area = raw.Area, RawManifestId = manifestId,
            GameSnapshotId = game.Id, ObservedAt = raw.CompletedAt, Characters = builds, Consoles = consoles, SynchroLevel = synchro,
            AccountStatSources = statSources, Issues = issues };
    }
    public static string? Id(JsonNode? node) => long.TryParse(node?.ToString(), NumberStyles.None, CultureInfo.InvariantCulture, out var n) && n >= 0 ? n.ToString(CultureInfo.InvariantCulture) : null;
}

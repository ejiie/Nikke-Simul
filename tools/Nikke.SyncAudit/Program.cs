using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Data;
using Nikke.Storage;

if (args.Length != 4) { Console.Error.WriteLine("Usage: Nikke.SyncAudit <raw-envelope.json> <game-catalog.json> <isolated-store-dir> <report.json>"); return 2; }
var raw = Wire.Read<RawEnvelope>(File.ReadAllText(args[0])); var game = Wire.Read<GameSnapshot>(File.ReadAllText(args[1]));
var store = new SnapshotStore(args[2]); store.SaveGame(game);
var connection = new AccountConnection { Status = "ready", Area = raw.Area, OpenId = raw.OpenId,
    AccountId = Wire.Hash($"blablalink:{raw.OpenId}:{raw.Area}"), Choices = [new(raw.Area, "검증용 저장 데이터", raw.Characters.Count, raw.OpenId)] };
store.SaveConnection(connection);
var job = store.CreateJob(connection).Job;
var manifest = store.SaveRaw(job.Id, raw, game);
var snapshot = new SnapshotNormalizer().Normalize(raw, game, connection.AccountId!, raw.OpenId, raw.Area, manifest);
int comparisons = 0; var differences = new List<string>();
void Compare(object? actual, JsonNode? expected, string path)
{
    comparisons++;
    if (actual?.ToString() != expected?.ToString()) differences.Add(path);
}
if (snapshot.Valid)
{
    store.Commit(snapshot, job); snapshot = store.Snapshot(snapshot.Id)!;
    foreach (var c in snapshot.Characters)
    {
        var d = raw.Details.First(x => SnapshotNormalizer.Id(x?["name_code"]) == c.CharacterId)!;
        var r = raw.Characters.First(x => SnapshotNormalizer.Id(x?["name_code"]) == c.CharacterId)!;
        foreach (var (value, field) in new (object?, string)[] { (c.Level,"lv"), (c.LimitBreak,"grade"), (c.Core,"core") }) Compare(value,r[field],c.CharacterId+".roster."+field);
        foreach (var (value, field) in new (object?, string)[] { (c.NativeLevel,"lv"), (c.Bond,"attractive_lv"), (c.Skills["1"],"skill1_lv"), (c.Skills["2"],"skill2_lv"), (c.Skills["3"],"ulti_skill_lv"), (c.CubeId,"harmony_cube_tid"), (c.CubeLevel,"harmony_cube_lv"), (c.CollectionId,"favorite_item_tid"), (c.CollectionLevel,"favorite_item_lv") }) Compare(value,d[field],c.CharacterId+"."+field);
        foreach (var eq in c.Equipment)
        {
            foreach (var (value, field) in new (object?, string)[] { (eq.Tier,"tier"), (eq.Level,"lv"), (eq.Manufacturer,"corporation_type"), (eq.ItemId,"tid") }) Compare(value,d[$"{eq.Slot}_equip_{field}"],$"{c.CharacterId}.{eq.Slot}.{field}");
            foreach (var line in eq.Lines)
            {
                Compare(line.OptionId,d[$"{eq.Slot}_equip_option{line.LineIndex}_id"],$"{c.CharacterId}.{eq.Slot}.{line.LineIndex}.id");
                if (line.Presence == "present")
                {
                    var effect = raw.StateEffects.First(x => SnapshotNormalizer.Id(x?["id"]) == line.OptionId)!["function_details"]![0]!;
                    Compare(line.RawValue,effect["function_value"],$"{c.CharacterId}.{eq.Slot}.{line.LineIndex}.value");
                    Compare(line.RawUnit,effect["function_value_type"],$"{c.CharacterId}.{eq.Slot}.{line.LineIndex}.unit");
                }
            }
        }
    }
}
else { job.Status = "failed"; job.ErrorCode = "validation_failed"; job.Issues = snapshot.Issues; store.SaveJob(job); }
SnapshotStore.AtomicWrite(args[3], Wire.Serialize(new { valid = snapshot.Valid, characters = snapshot.Characters.Count, comparisons,
    differences, issues = snapshot.Issues, snapshotId = snapshot.Valid ? snapshot.Id : null, connectionId = connection.Id,
    limitation = "Stored source replay; not a live API or in-game accuracy verification." }));
Console.WriteLine(Wire.Serialize(new { valid = snapshot.Valid, characters = snapshot.Characters.Count, comparisons, differences = differences.Count,
    errors = snapshot.Issues.Count(x => x.Severity == "error"), warnings = snapshot.Issues.Count(x => x.Severity == "warning") }));
return snapshot.Valid && differences.Count == 0 ? 0 : 1;

using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Data;
using Nikke.Simulator.Core.Stats;
using Nikke.Simulator.Core.Data.Dto;

var root = Path.GetFullPath(args.Length > 0 ? args[0] : ".");
var legacy = Path.Combine(root, ".reference/legacy-simulator");
var database = Path.Combine(legacy, "Database/processed");
var dll = Path.Combine(legacy, "SimulatorEngine/Nikke.Simulator.Core/bin/Release/net8.0/Nikke.Simulator.Core.dll");
// Independent original assembly, built during P00; never load account credentials or modify originals.
var assembly = AssemblyLoadContext.Default.LoadFromAssemblyPath(dll);
var oldTables = assembly.GetType("Nikke.Simulator.Core.Stats.StatTable")!;
var oldCalculator = assembly.GetType("Nikke.Simulator.Core.Stats.StatCalculator")!;
oldTables.GetMethod("Initialize")!.Invoke(null, [Path.Combine(database, "stat_table.csv")]);
oldTables.GetMethod("InitializeEquipment")!.Invoke(null, [Path.Combine(database, "equip_stat_table.json")]);
var service = new CalculationService(Path.Combine(root, "data/local/calculation"));
int coreChecks = 0, gearChecks = 0;
var consoles = new Dictionary<string, int> { ["1001"] = 137, ["1101"] = 83, ["1102"] = 47, ["1103"] = 59,
    ["1201"] = 61, ["1202"] = 71, ["1203"] = 79, ["1204"] = 89, ["1205"] = 97 };
foreach (var cls in new[] { "Attacker", "Defender", "Supporter" })
foreach (var weapon in new[] { "Assault Rifle", "Sniper Rifle", "SMG", "Shotgun", "Rocket Launcher", "Minigun" })
foreach (var company in new[] { "Elysion", "Missilis", "Tetra", "Pilgrim", "Abnormal" })
foreach (var level in new[] { 1, 200, 400, 1000 })
foreach (var grade in new[] { 0, 1, 3 })
foreach (var core in new[] { 0, 1, 7 })
foreach (var bond in new[] { 0, 1, 10, 40 })
{
    var before = ((double, double, double))oldCalculator.GetMethod("GetCoreAppliedStats")!.Invoke(null, [cls, weapon, company, level, grade, core, bond, consoles])!;
    var after = StatCalculator.GetCoreAppliedStats(cls, weapon, company, level, grade, core, bond, consoles);
    if (before != after) throw new InvalidDataException("Legacy core stat mismatch"); coreChecks++;
}
var gearTable = JsonNode.Parse(File.ReadAllText(Path.Combine(database, "equip_stat_table.json")))!.AsObject();
foreach (var cls in gearTable)
foreach (var tier in cls.Value!.AsObject())
foreach (var slot in tier.Value!.AsObject())
foreach (var level in new[] { 0, 1, 5 })
foreach (var corp in new[] { 0, 1, 2, 3, 4, 7 })
{
    var parts = new EquipmentPartsDto(); var info = new EquipmentInfoDto { tier = int.Parse(tier.Key), level = level, corp = corp };
    typeof(EquipmentPartsDto).GetProperty(slot.Key)!.SetValue(parts, info);
    var oldPartsType = assembly.GetType("Nikke.Simulator.Core.Data.Dto.EquipmentPartsDto")!;
    var oldInfoType = assembly.GetType("Nikke.Simulator.Core.Data.Dto.EquipmentInfoDto")!;
    var oldParts = Activator.CreateInstance(oldPartsType)!; var oldInfo = Activator.CreateInstance(oldInfoType)!;
    oldInfoType.GetProperty("tier")!.SetValue(oldInfo, info.tier); oldInfoType.GetProperty("level")!.SetValue(oldInfo, level); oldInfoType.GetProperty("corp")!.SetValue(oldInfo, corp);
    oldPartsType.GetProperty(slot.Key)!.SetValue(oldParts, oldInfo);
    var before = ((double, double, double))oldCalculator.GetMethod("GetEquipmentStats")!.Invoke(null, [cls.Key, "Pilgrim", oldParts])!;
    var after = StatCalculator.GetEquipmentStats(cls.Key, "Pilgrim", parts);
    if (before != after) throw new InvalidDataException("Legacy equipment mismatch"); gearChecks++;
}
var report = new { coreCases = coreChecks, gearCases = gearChecks, scalarChecks = (coreChecks + gearChecks) * 3, differences = 0,
    originalAssemblySha256 = Convert.ToHexStringLower(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(dll))) };
Directory.CreateDirectory(Path.Combine(root, "artifacts/p02"));
File.WriteAllText(Path.Combine(root, "artifacts/p02/legacy-parity.json"), Wire.Serialize(report));
Console.WriteLine(Wire.Serialize(report));

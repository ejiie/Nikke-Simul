using Nikke.Simulator.Core.Stats;
using Nikke.Simulator.Core.Data.Dto;

namespace Nikke.Core.Tests;

public class StatCalculatorTests
{
    [Fact]
    public void Synthetic_table_preserves_grade_floor_core_round_and_weapon_columns()
    {
        var row = Enumerable.Repeat("0", 37).ToArray(); row[0] = "1";
        foreach (var start in new[] { 1, 9, 17 })
        {
            row[start] = "101"; row[start + 1] = "103";
            for (var weapon = 0; weapon < 6; weapon++) row[start + 2 + weapon] = (201 + weapon).ToString();
        }
        row[26] = "1"; row[27] = "1";
        foreach (var start in new[] { 28, 31, 34 }) { row[start] = "11"; row[start + 1] = "13"; row[start + 2] = "17"; }
        var path = Path.GetTempFileName();
        try
        {
            File.WriteAllText(path, string.Join(',', row)); StatTable.Initialize(path);
            var result = StatCalculator.GetCoreAppliedStats("Attacker", "Minigun", "Elysion", 1, 1, 1, 1,
                new() { ["1001"] = 1, ["1101"] = 1, ["1201"] = 1 });
            // HP pre=4314, ATK pre=163, DEF pre=337; core increments=86,3,7.
            Assert.Equal((4400d, 166d, 344d), result);
            Assert.Equal(result, StatCalculator.GetCoreAppliedStats("Attacker", "Machine Gun", "Elysion", 1, 1, 1, 1,
                new() { ["1001"] = 1, ["1101"] = 1, ["1201"] = 1 }));
        }
        finally { File.Delete(path); }
    }
    [Theory]
    [InlineData(0, 9021, 73772)] [InlineData(4, 10825, 88526)]
    public void Historical_equipment_fixture_preserves_rounding(int manufacturer, double atk, double hp)
    {
        var path = Path.GetTempFileName();
        try
        {
            File.WriteAllText(path, """{"Attacker":{"10":{"head":{"ATK":6014,"HP":49181,"DEF":0}}}}""");
            StatTable.InitializeEquipment(path);
            var r = StatCalculator.GetEquipmentStats("Attacker", "Pilgrim", new() { head = new EquipmentInfoDto { tier = 10, level = 5, corp = manufacturer } });
            Assert.Equal(atk, r.ATK); Assert.Equal(hp, r.HP); Assert.Equal(0, r.DEF);
        }
        finally { File.Delete(path); }
    }
}

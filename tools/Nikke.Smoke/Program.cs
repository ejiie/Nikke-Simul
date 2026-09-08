using System.Text.Json;
using Nikke.Simulator.Core.Stats;

double finalStat = OverloadProcessor.CalculateFinalBaseStat(100, [0.014, 0.014]);
int timeCs = OverloadProcessor.ReduceTimeCs(100, [0.014, 0.014]);
Console.WriteLine(JsonSerializer.Serialize(new {
    milestone = "P00", fixture = "synthetic-overload-rounding",
    source = "Nikke-Dmg-Simulator/OverloadProcessor.cs",
    finalStat, timeCs, passed = finalStat == 103 && timeCs == 97,
    combatSimulatorAvailable = false
}, new JsonSerializerOptions { WriteIndented = true }));
return finalStat == 103 && timeCs == 97 ? 0 : 1;

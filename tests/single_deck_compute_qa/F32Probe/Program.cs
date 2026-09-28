using System.Text.Json;
using System.Text.Json.Serialization;
using Nikke.Core.Combat;
using Nikke.Core.Stats;
using Nikke.Simulator.Core.Stats;
using Nikke.Engine.Skills;

var json=new JsonSerializerOptions(JsonSerializerDefaults.Web) { NumberHandling=JsonNumberHandling.AllowNamedFloatingPointLiterals };
object Bits(ClientFloatResult r)=>new { r.Attack,r.Defence,r.Difference,r.Damage,bits=new[]{r.Base,r.Bonus,r.Extra,r.ReductionFactor,r.DefenceFactor,r.BeforeRound}.Select(BitConverter.SingleToUInt32Bits).ToArray() };
foreach(var line in File.ReadLines(args[0])) {
 var e=JsonDocument.Parse(line).RootElement; var id=e.GetProperty("id").GetString();
 try {
  object result=e.GetProperty("kind").GetString() switch {
   "direct"=>Bits(ClientFloatDamage.Calculate(e.GetProperty("attack").GetInt64(),e.GetProperty("defence").GetInt64(),e.GetProperty("rates").Deserialize<ClientDamageRates>(json))),
   "context"=>Bits(HitCalculator.CalculateClient(e.GetProperty("context").Deserialize<HitContext>(json))),
   "attack"=>StatBuffCalculator.AddAttackFlat(StatBuffCalculator.ApplyAttack(e.GetProperty("native").GetInt64(),e.GetProperty("groups").Deserialize<StatRateBuff[][]>(json)),e.GetProperty("flats").Deserialize<StatFlatBuff[]>(json)),
   "raw"=>OverloadProcessor.CalculateFinalBaseStat(e.GetProperty("native").GetInt64(),e.GetProperty("groups").Deserialize<Dictionary<long,long>>(json),e.GetProperty("flat").GetInt64()),
   _=>throw new ArgumentException("kind") };
  Console.WriteLine(JsonSerializer.Serialize(new{id,result},json));
 } catch(Exception ex) { Console.WriteLine(JsonSerializer.Serialize(new{id,error=ex.GetType().Name,message=ex.Message},json)); }
}

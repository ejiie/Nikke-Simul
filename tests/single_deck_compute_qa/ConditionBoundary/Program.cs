using System.Text.Json;
using Nikke.Engine;
// Product resolver is the subject, not the expected-value generator. Python builds independent cases.
var options=new JsonSerializerOptions {PropertyNameCaseInsensitive=true,PropertyNamingPolicy=JsonNamingPolicy.CamelCase};
var cases=JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
var output=new List<object>();
foreach(var row in cases.EnumerateArray()) {
 try {
  var member=row.GetProperty("member").Deserialize<WeaponReplayMember>(options);
  var conditions=row.GetProperty("conditions").Deserialize<WeaponReplayConditions>(options);
  var result=BossConditionResolver.Resolve(member,conditions,row.GetProperty("normal").GetBoolean());
  output.Add(new {id=row.GetProperty("id").GetString(),result,error=(string)null});
 } catch(Exception e) {output.Add(new {id=row.GetProperty("id").GetString(),error=e.Message});}
}
File.WriteAllText(args[1],JsonSerializer.Serialize(output,options));

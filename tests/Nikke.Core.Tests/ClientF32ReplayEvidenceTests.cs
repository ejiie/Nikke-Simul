using System.Text.Json;
using Nikke.Core.Combat;
using Nikke.Engine.Skills;

namespace Nikke.Core.Tests;

public class ClientF32ReplayEvidenceTests
{
    private sealed record Input(SkillReplayMember[] Members,SkillGraph Graph,SkillReplayConditions Conditions);
    [Theory]
    [InlineData("legacy_term_floor")]
    [InlineData("client_f32")]
    public void Record_fixed_five_member_replay_without_account_data(string policy)
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"../../../../../"));
        var json=new JsonSerializerOptions(JsonSerializerDefaults.Web) { WriteIndented=true };
        var fixture=JsonSerializer.Deserialize<Input>(File.ReadAllText(Path.Combine(root,"tools/benchmarks/engine/fixture.json")),json)!;
        var conditions=fixture.Conditions with { RoundingPolicy=policy,DamageLog=null,
            Combat=fixture.Conditions.Combat with { CritMode="off",ManualCharacterId="",Trace=false,EnemyDefense=30925 },
            AutoBurst=fixture.Conditions.AutoBurst with { TimelineLimit=0,StageDelayMinFrames=1,StageDelayMaxFrames=1 } };
        var members=fixture.Members.Select(m=>m with { Weapon=m.Weapon with { Hit=m.Weapon.Hit with { StatAttack=100000 } } }).ToArray();
        var result=SkillReplay.Run(members,fixture.Graph,conditions);
        Assert.Equal(5,result.Members.Count);
        var summary=PreparedSkillReplay.Create(members,fixture.Graph,conditions).Run();
        Assert.Equal(result.TotalDamage,summary.TeamDamage);
        Assert.Equal(result.Members.Select(m=>m.Damage),summary.Members.Select(m=>m.Damage));
        var differences=new List<object>();
        if(policy=="client_f32")
        {
            foreach(var id in new[] { "fixture-i","5004" })
            {
                var logged=SkillReplay.Run(members,fixture.Graph,conditions with { DamageLog=new() { CharacterId=id } });
                Assert.Equal(result.TotalDamage,logged.TotalDamage);
                var changes=logged.DamageLog.Entries.Select(e=>new { e.Hit,
                    legacy=HitCalculator.Calculate(e.Hit,"legacy_term_floor"),client=e.Damage }).ToArray();
                double legacyTotal=changes.Sum(e=>e.legacy);
                Assert.Equal(id=="5004"?136253255:302651627,legacyTotal);
                differences.Add(new { id,legacyTotal,clientTotal=changes.Sum(e=>e.client),
                    deltas=changes.GroupBy(e=>e.client-e.legacy).Select(g=>new { delta=g.Key,count=g.Count() }) });
            }
        }
        var directory=Path.Combine(root,"artifacts/hit-f32",Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(directory);
        File.WriteAllText(Path.Combine(directory,"replay.json"),JsonSerializer.Serialize(new {
            evidence="synthetic_5_member_180s_fixed_def30925",policy,result.RulesVersion,result.TotalDamage,
            members=result.Members.Select(m=>new { m.CharacterId,m.Damage,m.Shots,m.Hits,m.CriticalHits }),
            fullBursts=result.Connection.FullBurst.Cycle,summary.ImplementationVersion,differences },json));
        Console.WriteLine(directory);
    }
}

using Nikke.Core.Combat;
using Nikke.Engine.Skills;
using static Nikke.Core.Tests.SkillReplayTests;

namespace Nikke.Core.Tests;

public class PreparedSkillReplayTests
{
    [Theory]
    [InlineData("legacy_term_floor")]
    [InlineData("nested_floor")]
    [InlineData("final_round_even")]
    public void Single_policy_matches_audit_across_fractional_bonus_and_integer_boundaries(string policy)
    {
        foreach(double attack in new[]{0,10,100.5,100000.014,1e12})
        foreach(double defense in new[]{0,10,30925,31784})
        foreach(double coefficient in new[]{.001,1,1.014,3.5})
        foreach(int flags in Enumerable.Range(0,32))
        {
            var h=new HitContext { StatAttack=attack,Defense=defense,Coefficient=coefficient,
                ChargeApplicable=true,FullCharge=(flags&1)!=0,ChargeBase=3.5,ChargeAdd=.1,
                FullBurst=(flags&2)!=0,Crit=(flags&4)!=0,Core=(flags&8)!=0,ProperDistance=(flags&16)!=0,
                AttackBuffs=[new("OL",.014)],RuntimeAttackBuffs=[new("skill",.014)],AttackFlatBuffs=[new("caster",.5)],
                AttackDamage=.121,DamageTaken=.15,ElementAdvantage=true };
            Assert.Equal(HitCalculator.Compare(h).Candidates.Single(c=>c.Policy==policy).Damage,HitCalculator.Calculate(h,policy));
        }
    }
    [Fact]
    public void Fast_validation_covers_every_double_field_and_invalid_buffs_and_types()
    {
        foreach(var field in typeof(HitContext).GetProperties().Where(p=>p.PropertyType==typeof(double)))
        foreach(double bad in new[]{double.NaN,double.PositiveInfinity,double.NegativeInfinity,1e13})
        {
            var h=new HitContext { StatAttack=100 }; field.SetValue(h,bad);
            Assert.Throws<ArgumentException>(()=>HitCalculator.Calculate(h,"legacy_term_floor"));
        }
        HitContext[] invalid=[new() { DamageType="unknown" },new() { Coefficient=0 },
            new() { ChargeApplicable=false,FullCharge=true },new() { CanCrit=false,Crit=true },
            new() { AttackBuffs=[new("bad",double.NaN)] },new() { AttackFlatBuffs=[new("bad",double.NaN)] },
            new() { DamageTaken=-2 },new() { StatAttack=1e12,Coefficient=1e12 }];
        foreach(var h in invalid) Assert.Throws<ArgumentException>(()=>HitCalculator.Calculate(h,"final_round_even"));
        Assert.Throws<ArgumentException>(()=>HitCalculator.Calculate(new(),"invalid"));
    }
    [Fact]
    public void Prepared_input_is_private_and_parallel_runs_reset_all_battle_state()
    {
        var m=Member("a",[10]); var graph=Graph(F(10,value:5000));
        var c=Conditions(180) with { DamageLog=new() { CharacterId="a" } };
        var audit=SkillReplay.Run([m],graph,c);
        var prepared=PreparedSkillReplay.Create([m],graph,c);
        m.Weapon.Weapon.maxAmmo=1; m.Weapon.Weapon.fireRate=1;
        ((Dictionary<int,SkillFunction>)graph.Functions).Clear();
        var results=new SkillRunSummary[8];
        Parallel.For(0,results.Length,new ParallelOptions { MaxDegreeOfParallelism=2 },i=>results[i]=prepared.Run());
        Assert.All(results,r=> {
            Assert.Equal(audit.TotalDamage,r.TeamDamage); Assert.Equal(audit.Members[0].Shots,r.Members[0].Shots);
            Assert.Equal(audit.Members[0].Hits,r.Members[0].Hits); Assert.Equal("cpu-summary.1",r.ImplementationVersion);
        });
        Assert.Equal(results[0].Members,prepared.Run().Members);
    }
    [Fact]
    public void Summary_preserves_automatic_cast_reload_and_full_burst_counts()
    {
        SkillReplayMember M(string id,int step)
        {
            var m=Member(id,burst:Active(cooldown:200)); m.Weapon.Weapon.maxAmmo=3;
            return m with { Skills=m.Skills with { FullBurstDurationFrames=60,
                BurstConnection=new(step,step+1,1,100,123,100000,200000,25000,[]) } };
        }
        var members=new[]{M("a",1),M("b",2),M("c",3)};
        var graph=Graph() with { GaugeConstants=new(1000000,new Dictionary<string,long>(),"fixture","raw") };
        var c=Conditions(1200) with { AutoBurst=new() { StageDelayMinFrames=1,StageDelayMaxFrames=1 } };
        var sink=new Events(); var audit=SkillReplay.Run(members,graph,c,events:sink);
        var summary=PreparedSkillReplay.Create(members,graph,c).Run();
        Assert.Equal(audit.TotalDamage,summary.TeamDamage); Assert.Equal(audit.TeamBurst.FullBursts.Count,summary.FullBursts);
        foreach(var m in summary.Members)
        {
            Assert.Equal(sink.Values.Count(e=>e.Source==m.CharacterId && e.Kind==CombatEventKind.ReloadCompleted),m.Reloads);
            Assert.Equal(sink.Values.Count(e=>e.Source==m.CharacterId && e.Kind==CombatEventKind.FullBurstDurationRequested),m.BurstCasts);
        }
    }
    [Fact]
    public void Cancellation_never_returns_a_partial_normal_sample_and_does_not_poison_prepared_input()
    {
        var prepared=PreparedSkillReplay.Create([Member()],Graph(),Conditions(180));
        using var cancel=new CancellationTokenSource(); cancel.Cancel();
        Assert.Throws<OperationCanceledException>(()=>prepared.Run(cancel.Token));
        Assert.True(prepared.Run().TeamDamage>0);
    }
    [Fact]
    public void Independently_created_production_rng_runs_match_predeclared_binomial_bound()
    {
        var prepared=PreparedSkillReplay.Create([Member()],Graph(),Conditions(600) with { Combat=Conditions(600).Combat with { CritMode="sample" } });
        var results=new SkillRunSummary[24];
        Parallel.For(0,24,new ParallelOptions { MaxDegreeOfParallelism=2 },i=>results[i]=prepared.Run());
        double n=results.Sum(r=>r.Members[0].Hits),crit=results.Sum(r=>r.Members[0].CriticalHits);
        // Fixed sample count, 6 sigma binomial acceptance; not a measured game distribution.
        Assert.InRange(crit,.15*n-6*Math.Sqrt(n*.15*.85),.15*n+6*Math.Sqrt(n*.15*.85));
        Assert.True(results.Select(r=>r.TeamDamage).Distinct().Count()>1);
    }
    [Fact]
    public void In_flight_cancellation_interrupts_at_the_next_frame()
    {
        var prepared=PreparedSkillReplay.Create(Enumerable.Range(0,5).Select(i=>Member(i.ToString())).ToArray(),Graph(),Conditions(10800));
        using var cancel=new CancellationTokenSource();
        cancel.CancelAfter(10);
        var watch=System.Diagnostics.Stopwatch.StartNew();
        Assert.Throws<OperationCanceledException>(()=>prepared.Run(cancel.Token));
        Assert.True(watch.Elapsed<TimeSpan.FromSeconds(5));
        Assert.Equal(5,prepared.Run().Members.Count);
    }
    private sealed class Events : ICombatEventSink
    {
        public List<CombatEvent> Values=[];
        public void OnEvent(CombatEvent e)=>Values.Add(e);
    }
}

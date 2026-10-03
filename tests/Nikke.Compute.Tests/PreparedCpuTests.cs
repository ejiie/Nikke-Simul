using Nikke.Contracts;
using Nikke.Core.Combat;
using Nikke.Data;
using Nikke.Engine;
using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Data.Dto;

namespace Nikke.Compute.Tests;

public sealed class PreparedCpuTests
{
    [Fact] public async Task Actual_cpu_preparation_is_frozen_restorable_and_parallel_isolated()
    {
        var members=Enumerable.Range(0,5).Select(i=>new SkillReplayMember(new WeaponReplayMember(i.ToString(),
            new WeaponDto{weaponType="AR",inputType="DOWN",fireType="Instant",fireRate=12,endFireRate=12,maxAmmo=100,reloadTimeSec=1,reloadBulletRate=1,shotCount=1,muzzleCount=1},
            new HitContext{StatAttack=1000},new()),1000,
            new SkillLoadout("fixture",new Dictionary<string,int>{{"skill1",10},{"skill2",10},{"burst",10}},
                new Dictionary<string,SkillDefinition>{{"skill1",new(){SkillId=1}},{"skill2",new(){SkillId=2}},{"burst",new(){SkillId=3}}}))).ToArray();
        var conditions=new SkillReplayConditions{RoundingPolicy="final_round_even",Combat=new(){DurationFrames=120,Trace=false}};
        var prepared=PreparedCompute.Create(members,new(new Dictionary<int,SkillFunction>(),new Dictionary<int,SkillDefinition>()),conditions,"synthetic","synthetic","final");
        var pilot=PreparedCompute.Create(members,new(new Dictionary<int,SkillFunction>(),new Dictionary<int,SkillDefinition>()),conditions,"synthetic","synthetic","pilot");
        Assert.Equal(prepared.Input.Fingerprint,pilot.Input.Fingerprint);Assert.NotEqual(prepared.Input.Phase,pilot.Input.Phase);
        members[0].Weapon.Weapon.maxAmmo=1;
        var restored=PreparedCompute.Restore(prepared.PersistedInput);
        var runs=await Task.WhenAll(Enumerable.Range(0,6).Select(i=>Task.Run(()=>restored.Run("batch",i,1,default))));
        Assert.All(runs,r=>{Assert.Equal(runs[0].TeamDamage,r.TeamDamage);Assert.Equal(runs[0].Members.Select(m=>m.Shots),r.Members.Select(m=>m.Shots));Assert.Equal(r.TeamDamage,r.Members.Sum(m=>m.Damage));});
        Assert.Equal(prepared.Input.Fingerprint,restored.Input.Fingerprint);
        using var cancelled=new CancellationTokenSource();cancelled.Cancel();Assert.Throws<OperationCanceledException>(()=>restored.Run("batch",7,1,cancelled.Token));
    }

    [Fact] public void Compute_summary_exposes_the_replacement_policies_and_old_summary_versions_cannot_resume()
    {
        SkillReplayMember Member(int i,SkillDefinition? burst=null)=>new(new WeaponReplayMember(i.ToString(),
            new WeaponDto{weaponType="AR",inputType="DOWN",fireType="Instant",fireRate=12,endFireRate=12,maxAmmo=100,reloadTimeSec=1,reloadBulletRate=1,shotCount=1,muzzleCount=1},
            new HitContext{StatAttack=1000},new()),1000,
            new SkillLoadout("fixture",new Dictionary<string,int>{{"skill1",10},{"skill2",10},{"burst",10}},
                new Dictionary<string,SkillDefinition>{{"skill1",new(){SkillId=1}},{"skill2",new(){SkillId=2}},{"burst",burst??new(){SkillId=3}}}));
        var replacement=new SkillDefinition{SkillId=77,Skill=new(){SkillType=7,SkillCooltime=400,DurationType=2,DurationValue=1,PreferTarget=11,
            SkillValueData=[new(2,40000),new(1,120),new(1,1022002),new(0,0),new(1,1)],
            WeaponChange=new(){ChargeTimeSec=1,FullChargeRate=10,MaxAmmo=1,Pierce=true,Source="test"}}};
        var graph=new SkillGraph(new Dictionary<int,SkillFunction>(),new Dictionary<int,SkillDefinition>());
        SkillReplayConditions Conditions(bool cast)=>new(){RoundingPolicy="final_round_even",Casts=cast?[new(5,"0")]:[],Combat=new(){DurationFrames=200,Trace=false}};
        var used=PreparedCompute.Create(Enumerable.Range(0,5).Select(i=>Member(i,i==0?replacement:null)).ToArray(),graph,Conditions(true),"synthetic","synthetic","final");
        var run=used.Run("b",0,1,default);
        Assert.Equal([ReplacementWeaponPolicy.MotionRunId,ReplacementWeaponPolicy.PierceRunId],run.Limitations!.Select(l=>l.Id));
        Assert.Contains("\"limitations\"",Wire.Serialize(run));
        var plain=PreparedCompute.Create(Enumerable.Range(0,5).Select(i=>Member(i)).ToArray(),graph,Conditions(false),"synthetic","synthetic","final").Run("b",0,1,default);
        Assert.Null(plain.Limitations);Assert.DoesNotContain("imitations",Wire.Serialize(plain));
        // Frozen input restores with the same summary; a persisted input from the previous summary version is refused.
        Assert.Equal(run.TeamDamage,PreparedCompute.Restore(used.PersistedInput).Run("b",0,1,default).TeamDamage);
        Assert.Equal("cpu-summary.7-run-policies",used.Input.SummaryVersion);
        var old=used.PersistedInput.Replace("cpu-summary.7-run-policies","cpu-summary.6-precision-1");
        Assert.Throws<InvalidOperationException>(()=>PreparedCompute.Restore(old));
    }
}

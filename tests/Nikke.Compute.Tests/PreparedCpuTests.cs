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
}

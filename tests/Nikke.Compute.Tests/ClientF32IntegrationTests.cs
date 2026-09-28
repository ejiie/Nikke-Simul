using System.Text.Json.Nodes;
using Nikke.Analysis;
using Nikke.Compute;
using Nikke.Contracts;
using Nikke.Core.Combat;
using Nikke.Core.Stats;
using Nikke.Data;
using Nikke.Engine;
using Nikke.Engine.Skills;
using Nikke.Simulator.Core.Data.Dto;
using Nikke.Storage;

namespace Nikke.Compute.Tests;

public sealed class ClientF32IntegrationTests
{
    private static PreparedCompute Prepare(string policy="client_f32",HitContext? hit=null,WeaponReplayConditions? combat=null,int rangeMin=25)
    {
        var members=Enumerable.Range(0,5).Select(i=>new SkillReplayMember(new WeaponReplayMember(i.ToString(),
            new WeaponDto{weaponType="AR",inputType="DOWN",fireType="Instant",fireRate=12,endFireRate=12,maxAmmo=100,reloadTimeSec=1,reloadBulletRate=1,shotCount=1,muzzleCount=1},
            hit??new HitContext{StatAttack=100},new()){BonusRangeMin=rangeMin,BonusRangeMax=45,Element="Fire"},1000,
            new SkillLoadout("fixture",new Dictionary<string,int>{{"skill1",10},{"skill2",10},{"burst",10}},
                new Dictionary<string,SkillDefinition>{{"skill1",new(){SkillId=1}},{"skill2",new(){SkillId=2}},{"burst",new(){SkillId=3}}}))).ToArray();
        return PreparedCompute.Create(members,new(new Dictionary<int,SkillFunction>(),new Dictionary<int,SkillDefinition>()),
            new(){RoundingPolicy=policy,Combat=combat??new(){DurationFrames=60,Trace=false}},"synthetic","synthetic","final");
    }
    private static HardwareProfile Hardware=>HardwareProbe.Normalize(new(),2,8L<<30,"integration","Windows","X64",false);
    [Fact] public void Boss_conditions_metadata_and_explicit_unset_mode_survive_restore_and_partition_cache()
    {
        var inputs=new[]{Prepare(),Prepare(combat:new(){DurationFrames=60,BossDistance=null,BossWeakElement=null}),
            Prepare(combat:new(){DurationFrames=60,BossDistance=35}),Prepare(combat:new(){DurationFrames=60,BossDistance=36}),
            Prepare(combat:new(){DurationFrames=60,BossDistance=35,BossWeakElement="Fire"}),
            Prepare(combat:new(){DurationFrames=60,BossDistance=35},rangeMin:26)};
        Assert.Equal(inputs.Length,inputs.Select(p=>p.Input.Fingerprint).Distinct().Count());
        Assert.Equal(inputs.Length,inputs.Select(p=>ExecutionPolicy.Conservative(Hardware,p.Input,new()).Fingerprint).Distinct().Count());
        foreach(var input in inputs)
        {
            var restored=PreparedCompute.Restore(input.PersistedInput);
            Assert.Equal(input.Input.ConditionCompatibility,restored.Input.ConditionCompatibility);
            Assert.Equal(input.Run("x",0,1,default).TeamDamage,restored.Run("x",0,1,default).TeamDamage);
        }
        Assert.Equal("legacy_global",inputs[0].Input.ConditionCompatibility!.Mode);
        Assert.Equal("per_member",inputs[1].Input.ConditionCompatibility!.Mode);
    }
    [Fact] public void Explicit_null_boss_and_false_legacy_mix_fails_before_prepared_json_erases_nulls()
    {
        Assert.Throws<ArgumentException>(()=>Prepare(combat:new(){DurationFrames=60,BossDistance=null,ProperDistance=false}));
        var json=JsonNode.Parse(Prepare().PersistedInput)!;json["input"]!["conditionCompatibility"]!["label"]="changed";
        Assert.Throws<InvalidOperationException>(()=>PreparedCompute.Restore(json.ToJsonString()));
    }
    // Storage/cache fixture for pre-upgrade metadata, not an old-engine arithmetic oracle.
    private sealed class HistoricalFixture(PreparedCompute inner) : IPreparedExperiment
    {
        public ExperimentInput Input => inner.Input with {Fingerprint=Wire.Hash("pre-f32:"+inner.Input.Fingerprint),
            EngineVersion="cpu-summary.1",SummaryVersion=null,RulesVersion="pre-client-f32",InputSchemaVersion=2,RoundingPolicy=null};
        public string PersistedInput=>inner.PersistedInput;
        public RunSummary Run(string experimentId,int index,int attempt,CancellationToken token)
            =>inner.Run(experimentId,index,attempt,token) with {InputFingerprint=Input.Fingerprint};
    }
    [Fact] public void Rates_raw_representation_and_policy_all_partition_fingerprints()
    {
        var inputs=new[]{Prepare(),Prepare("legacy_term_floor"),Prepare(hit:new(){StatAttack=100,StatDamageRatio=2}),
            Prepare(hit:new(){StatAttack=100,DefenceRatioRate=.25}),Prepare(hit:new(){StatAttack=100,RuntimeAttackBuffs=[new("x",.145)]}),
            Prepare(hit:new(){StatAttack=100,RuntimeAttackBuffs=[StatRateBuff.FromRaw("x",1450)]})};
        Assert.Equal(inputs.Length,inputs.Select(p=>p.Input.Fingerprint).Distinct().Count());
        Assert.Equal(inputs.Length,inputs.Select(p=>ExecutionPolicy.Conservative(Hardware,p.Input,new()).Fingerprint).Distinct().Count());
        Assert.Equal(3,inputs[0].Input.InputSchemaVersion);Assert.Equal("client_f32",inputs[0].Input.RoundingPolicy);
        Assert.Equal(inputs[0].Input.Fingerprint,PreparedCompute.Restore(inputs[0].PersistedInput).Input.Fingerprint);
        Assert.Equal(inputs[4].Run("x",0,1,default).TeamDamage,inputs[5].Run("x",0,1,default).TeamDamage);
    }
    [Theory][InlineData("engineVersion")][InlineData("rulesVersion")][InlineData("summaryVersion")][InlineData("inputSchemaVersion")]
    public void Old_payload_cannot_resume_under_current_engine(string field)
    {
        var json=JsonNode.Parse(Prepare().PersistedInput)!;
        json["input"]![field]=field=="inputSchemaVersion"?JsonValue.Create(2):JsonValue.Create("historical");
        Assert.Throws<InvalidOperationException>(()=>PreparedCompute.Restore(json.ToJsonString()));
    }
    [Fact] public void Changed_persisted_inputs_cannot_reuse_original_fingerprint()
    {
        var json=JsonNode.Parse(Prepare().PersistedInput)!;json["members"]![0]!["weapon"]!["hit"]!["statDamageRatio"]=2;
        Assert.Throws<InvalidOperationException>(()=>PreparedCompute.Restore(json.ToJsonString()));
    }
    [Fact] public async Task Historical_cache_is_not_reused_by_current_workload()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"../../../../../artifacts/client-f32-integration/cache",Guid.NewGuid().ToString("N")));
        var policy=new ExecutionPolicy(root,new(TimeSpan.FromMilliseconds(200),TimeSpan.FromSeconds(2)),()=>0);
        var old=new HistoricalFixture(Prepare("legacy_term_floor"));var first=await policy.Select(Hardware,old,new(MaxWorkers:1),default);
        Assert.Equal("measured",first.Tuning!.Status);
        var current=Prepare();var second=await policy.Select(Hardware,current,new(MaxWorkers:1),default);
        Assert.NotEqual(first.Fingerprint,second.Fingerprint);Assert.NotEqual("measured_cache",second.Reason);
        Assert.Equal("miss",second.Tuning!.CacheSource);
    }
    [Fact] public void Old_results_remain_readable_and_cannot_enter_new_statistics()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"../../../../../artifacts/client-f32-integration/batch",Guid.NewGuid().ToString("N")));
        var store=new BatchStore(root);var old=new HistoricalFixture(Prepare("legacy_term_floor"));var current=Prepare();
        var request=new ExperimentRequest("synthetic",["0","1","2","3","4"],new(),Runs:1);
        var a=store.Create(old,request,ExecutionPolicy.Conservative(Hardware,old.Input,new()));
        var b=store.Create(current,request,ExecutionPolicy.Conservative(Hardware,current.Input,new()));
        store.Running(a.Id,1,a.Execution);var oldRun=old.Run(a.Id,0,1,default);store.Write(a.Id,1,[new(0,1,oldRun,null)]);store.Finish(a.Id,1,false);
        store.Running(b.Id,1,b.Execution);
        Assert.Throws<ArgumentException>(()=>store.Write(b.Id,1,[new(0,1,oldRun with {ExperimentId=b.Id,RunId=b.Id+":0"},null)]));
        var run=current.Run(b.Id,0,1,default);store.Write(b.Id,1,[new(0,1,run,null)]);store.Finish(b.Id,1,false);
        Assert.Single(store.Results(a.Id));Assert.Single(store.Results(b.Id));
        var snapshot=store.AnalysisSnapshot(b.Id);var stats=new ComputeAnalysis().Summarize(snapshot.Batch,snapshot.Runs,null);
        Assert.Equal(1,stats.Team.N);Assert.Equal(run.TeamDamage,stats.Team.Mean);
    }
}

using System.Text.Json.Nodes;
using Nikke.Compute;
using Nikke.Contracts;
using Nikke.Data;
using Nikke.Jobs;
using Nikke.Storage;

namespace Nikke.Api;

public static class ComputeEndpoints
{
    public static void MapCompute(this WebApplication app,string dataRoot,SnapshotStore snapshots,GameSnapshot game,
        Lazy<RuntimeReplayService> runtime,Lazy<CalculationService> calculation)
    {
        var root=Path.Combine(dataRoot,"compute");var store=new BatchStore(root);var probe=new HardwareProbe();
        var jobs=new BatchCoordinator(store,probe,new ExecutionPolicy(Path.Combine(root,"tuning")));
        var analysisGate=new object();var statisticsCache=new Dictionary<string,(DateTimeOffset At,StatisticsResult Result)>();
        app.Lifetime.ApplicationStopping.Register(()=>jobs.DisposeAsync().AsTask().GetAwaiter().GetResult());
        app.MapGet("/api/compute/hardware",(CancellationToken ct)=>probe.Detect(ct));
        app.MapPost("/api/compute/experiments",async(ExperimentRequest request,CancellationToken ct)=> {
            if(request.Conditions is null || request.CharacterIds is null || request.Runs is <1 or >50000)throw new ArgumentException("invalid_experiment_input");
            var snapshot=snapshots.Snapshot(request.SnapshotId)??throw new KeyNotFoundException();
            var conditions=(JsonObject)request.Conditions.DeepClone();
            if(request.UseSavedTactic && snapshots.BurstTactic(snapshot.AccountId) is {} saved)
            {
                if(saved.SnapshotId!=snapshot.Id || !saved.FormationSlots.SequenceEqual(request.CharacterIds))throw new InvalidOperationException("saved_tactic_stale");
                if(saved.Tactic is not null){conditions["autoBurst"]??=new JsonObject();conditions["autoBurst"]!["tactic"]=System.Text.Json.JsonSerializer.SerializeToNode(saved.Tactic,Wire.Json);}
            }
            request=request with {Conditions=conditions};
            if(request.BaselineExperimentId is {} baseline) {
                var existing=store.Read(baseline);if(existing.Status.Input.SnapshotId!=request.SnapshotId || !existing.Status.Input.CharacterIds.SequenceEqual(request.CharacterIds)
                    || Wire.Canonical(existing.Request.Conditions)!=Wire.Canonical(conditions) || existing.Request.Phase!=request.Phase)throw new ArgumentException("baseline_input_mismatch");}
            var prepared=runtime.Value.PrepareCompute(snapshot,game,request,calculation.Value);
            var batch=await jobs.Create(prepared,request,ct);return Results.Accepted($"/api/compute/experiments/{batch.Id}",batch);
        });
        app.MapGet("/api/compute/experiments/{id}",(string id)=>store.Read(id).Status);
        app.MapGet("/api/compute/experiments/{id}/ol-candidates",(string id)=> {
            var experiment=store.Read(id);var snapshot=snapshots.Snapshot(experiment.Request.SnapshotId)??throw new KeyNotFoundException();
            var space=runtime.Value.ComputeCandidates(snapshot,game,experiment.Request);
            return new OlCandidateCatalog(space.CatalogVersion,space.Candidates.Select(c=>new OlCandidate(c.Id,
                new(c.Before.CharacterId,c.Before.Slot,c.Before.Line,c.Before.Option,(decimal)c.Before.Value),
                new(c.After.CharacterId,c.After.Slot,c.After.Line,c.After.Option,(decimal)c.After.Value),c.ThresholdSensitive)).ToArray(),space.Exclusions);
        });
        app.MapPost("/api/compute/experiments/{id}/cancel",(string id)=>jobs.Cancel(id));
        app.MapPost("/api/compute/experiments/{id}/resume",(string id)=>jobs.Resume(id,PreparedCompute.Restore(store.Read(id).Prepared)));
        app.MapGet("/api/compute/experiments/{id}/results",(string id,int? offset,int? limit)=>new BatchResults(store.Read(id).Status,offset??0,limit??100,store.Results(id,offset??0,limit??100)));
        app.MapGet("/api/compute/experiments/{id}/statistics",(string id,double? cut)=> {
            var analysis=app.Services.GetService<IComputeAnalysis>()??throw new InvalidOperationException("analysis_not_integrated");
            lock(analysisGate){var current=store.Read(id).Status;if(current.Input.Phase=="warmup")throw new InvalidOperationException("warmup_excluded_from_statistics");
                var key=$"{id}:{current.Attempt}:{cut?.ToString("R",System.Globalization.CultureInfo.InvariantCulture)}";
                if(statisticsCache.TryGetValue(key,out var cached) && DateTimeOffset.UtcNow-cached.At<TimeSpan.FromSeconds(2))return cached.Result;
                var snapshot=store.AnalysisSnapshot(id);var result=analysis.Summarize(snapshot.Batch,snapshot.Runs,cut);
                if(statisticsCache.Count>=16)statisticsCache.Remove(statisticsCache.MinBy(p=>p.Value.At).Key);
                statisticsCache[key]=(DateTimeOffset.UtcNow,result);return result;}
        });
        app.MapGet("/api/compute/experiments/{id}/comparison",(string id)=> {
            var analysis=app.Services.GetService<IComputeAnalysis>()??throw new InvalidOperationException("analysis_not_integrated");
            var candidate=store.Read(id);var baseline=candidate.Request.BaselineExperimentId??throw new ArgumentException("baseline_required");
            var a=store.AnalysisSnapshot(baseline);var b=store.AnalysisSnapshot(id);
            return analysis.Compare(a.Batch,a.Runs,b.Batch,b.Runs,candidate.Request.OlChanges??[]);
        });
    }
}

using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using Nikke.Core.Combat;
using Nikke.Engine.Skills;
using Nikke.Engine.Gpu;

var json=new JsonSerializerOptions(JsonSerializerDefaults.Web);
if(args.FirstOrDefault()=="--gpu-child")
{
    Console.WriteLine(JsonSerializer.Serialize(OpenClPrimitiveProbe.RunInIsolatedProcess(),json));
    return;
}
if(args.FirstOrDefault()=="--gpu-probe")
{
    var start=new ProcessStartInfo(Environment.ProcessPath!) { UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true };
    if(string.Equals(Path.GetFileNameWithoutExtension(Environment.ProcessPath),"dotnet",StringComparison.OrdinalIgnoreCase))
        start.ArgumentList.Add(typeof(BenchInput).Assembly.Location);
    start.ArgumentList.Add("--gpu-child");
    using var process=Process.Start(start)!;
    var stdout=process.StandardOutput.ReadToEndAsync(); var stderr=process.StandardError.ReadToEndAsync();
    using var timeout=new CancellationTokenSource(TimeSpan.FromSeconds(30));
    object probe;
    try { await process.WaitForExitAsync(timeout.Token); probe=new { status=process.ExitCode==0?"probe_finished":"probe_failed",exitCode=process.ExitCode,output=await stdout,error=await stderr,fullBattleEligible=false }; }
    catch(OperationCanceledException) { process.Kill(entireProcessTree:true); await process.WaitForExitAsync(); probe=new { status="probe_timeout",fullBattleEligible=false }; }
    var target=Path.GetFullPath(args.Length>1?args[1]:Path.Combine("artifacts","gpu-probe",Guid.NewGuid().ToString("N")));
    Directory.CreateDirectory(target);
    using(var file=new FileStream(Path.Combine(target,"probe.json"),FileMode.CreateNew)) JsonSerializer.Serialize(file,probe,json);
    Console.WriteLine(JsonSerializer.Serialize(probe,json)); return;
}
var inputBytes=File.ReadAllBytes(Path.Combine(AppContext.BaseDirectory,"fixture.json"));
var input=JsonSerializer.Deserialize<BenchInput>(inputBytes,json)!;
var conditions=input.Conditions with { DamageLog=null!,Combat=input.Conditions.Combat with {
    CritMode="off",ManualCharacterId="",Trace=false,EnemyDefense=30925 },
    AutoBurst=input.Conditions.AutoBurst with { TimelineLimit=0,StageDelayMinFrames=1,StageDelayMaxFrames=1 } };
var members=input.Members.Select(m=>m with { Weapon=m.Weapon with { Hit=m.Weapon.Hit with { StatAttack=100000 } } }).ToArray();
var rows=new List<object>();
void Measure(string name,int warmup,int count,Func<double> run)
{
    for(int i=0;i<warmup;i++) run();
    GC.Collect(); GC.WaitForPendingFinalizers(); GC.Collect();
    long allocated=GC.GetAllocatedBytesForCurrentThread();
    int[] collections=[GC.CollectionCount(0),GC.CollectionCount(1),GC.CollectionCount(2)];
    var watch=Stopwatch.StartNew(); double checksum=0;
    for(int i=0;i<count;i++) checksum+=run();
    watch.Stop();
    rows.Add(new { name,count,elapsedMs=watch.Elapsed.TotalMilliseconds,msPerRun=watch.Elapsed.TotalMilliseconds/count,
        bytesPerRun=(GC.GetAllocatedBytesForCurrentThread()-allocated)/count,
        gc=collections.Select((v,i)=>GC.CollectionCount(i)-v).ToArray(),checksum });
}
Measure("replay_trace_log_off",2,5,()=>SkillReplay.Run(members,input.Graph,conditions).TotalDamage);
var prepared=PreparedSkillReplay.Create(members,input.Graph,conditions);
Measure("prepared_summary",2,5,()=>prepared.Run().TeamDamage);
var hit=members[2].Weapon.Hit with { Defense=30925,FullCharge=true,FullBurst=true };
Measure("hit_compare_three_policies",100,10000,()=>HitCalculator.Compare(hit).Candidates[0].Damage);
Measure("hit_single_policy",100,10000,()=>HitCalculator.Calculate(hit,"legacy_term_floor"));
var output=new { schemaVersion=1,evidence="synthetic_5_member_180s_fixed_defense",createdAt=DateTimeOffset.UtcNow,
    inputSha256=Convert.ToHexStringLower(SHA256.HashData(inputBytes)),framework=RuntimeInformation.FrameworkDescription,
    os=RuntimeInformation.OSDescription,architecture=RuntimeInformation.ProcessArchitecture.ToString(),
    processors=Environment.ProcessorCount,rows };
var root=Path.GetFullPath(args.Length>0?args[0]:Path.Combine("artifacts","engine-bench",Guid.NewGuid().ToString("N")));
Directory.CreateDirectory(root);
using(var file=new FileStream(Path.Combine(root,"metrics.json"),FileMode.CreateNew)) JsonSerializer.Serialize(file,output,json);
Console.WriteLine(JsonSerializer.Serialize(output,json));
Console.WriteLine(root);
record BenchInput(SkillReplayMember[] Members,SkillGraph Graph,SkillReplayConditions Conditions);

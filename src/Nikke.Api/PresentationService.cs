using System.Diagnostics;
using System.Text.Json.Nodes;

namespace Nikke.Api;

public sealed class PresentationService(string root, string output, string python, string? dataRoot = null) : IHostedService
{
    private readonly object gate = new();
    private string status = "idle";
    private string? message;
    private long revision;
    private JsonNode? failureSummary;
    private JsonNode? unresolved;
    private readonly CancellationTokenSource stopping = new();
    private Task work = Task.CompletedTask;
    public Task StartAsync(CancellationToken cancellationToken)
    {
        if (!File.Exists(Path.Combine(output,"presentation.json")) && Environment.GetEnvironmentVariable("NIKKE_TEST_FIXTURE") is null) Start(false);
        return Task.CompletedTask;
    }
    public async Task StopAsync(CancellationToken cancellationToken)
    {
        Task pending;
        lock(gate) { stopping.Cancel(); pending=work; }
        try { await pending.WaitAsync(cancellationToken); } catch (OperationCanceledException) { }
    }
    public JsonNode Read()
    {
        var result = File.Exists(Path.Combine(output,"presentation.json"))
        ? JsonNode.Parse(File.ReadAllText(Path.Combine(output,"presentation.json")))!
        : new JsonObject { ["characters"] = new JsonArray(), ["unresolved"] = new JsonArray(), ["source"] = "not_prepared" };
        var accountPath=Path.Combine(output,"account-presentation.json");
        if(File.Exists(accountPath))
        {
            var account=JsonNode.Parse(File.ReadAllText(accountPath))!;
            result["consoles"]=account["consoles"]?.DeepClone();
            result["cubes"]=account["cubes"]?.DeepClone();
        }
        var specPath=Path.Combine(output,"spec-presentation.json");
        if(File.Exists(specPath))
        {
            var spec=JsonNode.Parse(File.ReadAllText(specPath))!;
            result["supportDefinitions"]=spec["supportDefinitions"]?.DeepClone();
            result["overloadOptions"]=spec["overloadOptions"]?.DeepClone();
        }
        return result;
    }
    public object Status() { lock(gate) return new { status, message, revision, failureSummary, unresolved }; }
    public object Start(bool refreshExisting = true)
    {
        lock(gate)
        {
            if (stopping.IsCancellationRequested) return new { status = "stopped", message = "백엔드가 종료 중입니다." };
            if (status=="running") return new { status, message };
            status="running"; message="이미지 및 카탈로그 준비 중"; failureSummary=null; unresolved=null;
            work=Task.Run(()=>Refresh(refreshExisting));
            return new { status, message };
        }
    }
    private async Task Refresh(bool refreshExisting)
    {
        try
        {
            var start=new ProcessStartInfo(python) { WorkingDirectory=root,UseShellExecute=false,CreateNoWindow=true,
                RedirectStandardOutput=true,RedirectStandardError=true,
                StandardOutputEncoding=System.Text.Encoding.UTF8,StandardErrorEncoding=System.Text.Encoding.UTF8 };
            start.Environment["PYTHONIOENCODING"]="utf-8";
            foreach (var arg in new[] { Path.Combine(root,"tools/data-pipeline/presentation_assets.py"),"--output",output }) start.ArgumentList.Add(arg);
            start.ArgumentList.Add("--data-root");
            start.ArgumentList.Add(Path.GetFullPath(dataRoot ?? Path.GetDirectoryName(Path.GetFullPath(output))!));
            if (refreshExisting) start.ArgumentList.Add("--refresh");
            else start.ArgumentList.Add("--update-index");
            using var process=Process.Start(start) ?? throw new InvalidOperationException();
            var result=process.StandardOutput.ReadToEndAsync(); var errors=process.StandardError.ReadToEndAsync();
            using var timeout=CancellationTokenSource.CreateLinkedTokenSource(stopping.Token);
            timeout.CancelAfter(TimeSpan.FromMinutes(8));
            using var registration=timeout.Token.Register(()=> { try { if (!process.HasExited) process.Kill(true); } catch (InvalidOperationException) { } });
            await process.WaitForExitAsync(timeout.Token); await errors;
            var receipt=JsonNode.Parse(await result)!;
            if (process.ExitCode!=0 && receipt["status"]?.GetValue<string>() is not ("partial" or "failed")) throw new InvalidOperationException();
            var summary=receipt["failureSummary"]!;
            int images=summary["imageFailures"]!.GetValue<int>(), catalogs=summary["catalogFailures"]!.GetValue<int>();
            int cached=summary["cachedFailures"]!.GetValue<int>();
            var failures=new List<string>();
            if(images>0)failures.Add($"이미지 파일 {images}개");
            if(catalogs>0)failures.Add($"카탈로그 준비 {catalogs}건");
            lock(gate) { revision++; failureSummary=summary.DeepClone(); unresolved=receipt["unresolved"]?.DeepClone(); status=receipt["status"]!.GetValue<string>();
                message=failures.Count==0?"이미지 및 카탈로그 준비 완료":string.Join(" · ",failures)+" 실패."+
                    (cached>0?$" 실패 항목 중 {cached}건은 기존 캐시를 사용합니다.":" 실패 항목에 사용할 캐시가 없습니다."); }
        }
        catch { lock(gate) { revision++; status="failed"; failureSummary=null; unresolved=new JsonArray(new JsonObject { ["kind"]="catalog", ["code"]="process_failed", ["cached"]=false }); message="이미지·카탈로그 준비 작업을 완료하지 못했습니다. 캐시 사용 여부는 확인되지 않았습니다."; } }
    }
}

using System.Diagnostics;
using System.Text.Json.Nodes;

namespace Nikke.Api;

public sealed class PresentationService(string root, string output, string python) : IHostedService
{
    private readonly object gate = new();
    private string status = "idle";
    private string? message;
    private long revision;
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
    public object Status() { lock(gate) return new { status, message, revision }; }
    public object Start(bool refreshExisting = true)
    {
        lock(gate)
        {
            if (stopping.IsCancellationRequested) return new { status = "stopped", message = "백엔드가 종료 중입니다." };
            if (status=="running") return new { status, message };
            status="running"; message="블라블라 이미지 수집 중";
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
            if (refreshExisting) start.ArgumentList.Add("--refresh");
            else start.ArgumentList.Add("--update-index");
            using var process=Process.Start(start) ?? throw new InvalidOperationException();
            var result=process.StandardOutput.ReadToEndAsync(); var errors=process.StandardError.ReadToEndAsync();
            using var timeout=CancellationTokenSource.CreateLinkedTokenSource(stopping.Token);
            timeout.CancelAfter(TimeSpan.FromMinutes(8));
            using var registration=timeout.Token.Register(()=> { try { if (!process.HasExited) process.Kill(true); } catch (InvalidOperationException) { } });
            await process.WaitForExitAsync(timeout.Token); await errors;
            if (process.ExitCode!=0) throw new InvalidOperationException();
            var receipt=JsonNode.Parse(await result)!;
            var unresolved=receipt["unresolved"]!.AsArray().Count;
            lock(gate) { revision++; status=unresolved==0?"succeeded":"partial"; message=unresolved==0?"이미지 저장 완료":$"이미지 {unresolved}개를 수집하지 못했습니다. 다시 시도하세요."; }
        }
        catch { lock(gate) { status="failed"; message="블라블라 이미지를 갱신하지 못했습니다. 저장된 이미지를 유지합니다."; } }
    }
}

using System.Diagnostics;
using System.Text.Json.Nodes;
using Nikke.Contracts;

namespace Nikke.Api;

public sealed class CollectorFailure(string code, string message) : Exception(message) { public string Code { get; } = code; }
public sealed class CollectorProcess(string projectRoot, string dataRoot, string python)
{
    public string ResultPath(string id) => Path.Combine(dataRoot, "staging", id + ".json");
    public async Task Run(string action, AccountConnection connection, string runId, Action<JsonNode> progress, CancellationToken token)
    {
        Directory.CreateDirectory(Path.Combine(dataRoot, "staging"));
        var fixture = Environment.GetEnvironmentVariable("NIKKE_TEST_FIXTURE");
        if (fixture is not null)
        {
            if (action != "collect") throw new CollectorFailure("test_mode", "검증 모드에서는 실제 로그인하지 않습니다.");
            progress(new JsonObject { ["type"] = "progress", ["stage"] = "collecting", ["collected"] = 0, ["expected"] = 1 });
            await Task.Delay(300, token);
            File.Copy(fixture, ResultPath(runId), true); return;
        }
        var start = new ProcessStartInfo(python) { WorkingDirectory = projectRoot, UseShellExecute = false,
            CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true,
            StandardOutputEncoding = System.Text.Encoding.UTF8, StandardErrorEncoding = System.Text.Encoding.UTF8 };
        foreach (var argument in new[] { Path.Combine(projectRoot, "tools/data-pipeline/collector.py"), action, "--session",
            Path.Combine(dataRoot, "sessions", connection.Id + ".bin"), "--result", ResultPath(runId) }) start.ArgumentList.Add(argument);
        if (action == "collect")
        { start.ArgumentList.Add("--openid"); start.ArgumentList.Add(connection.OpenId!); start.ArgumentList.Add("--area"); start.ArgumentList.Add(connection.Area!.Value.ToString()); }
        using var process = Process.Start(start) ?? throw new CollectorFailure("launch", "수집기를 시작하지 못했습니다.");
        using var registration = token.Register(() => { try { if (!process.HasExited) process.Kill(entireProcessTree: true); } catch (InvalidOperationException) { } });
        var errors = process.StandardError.ReadToEndAsync(token); // Drain; never expose possible request metadata.
        CollectorFailure? failure = null;
        while (await process.StandardOutput.ReadLineAsync(token) is { } line)
        {
            JsonNode? packet;
            try { packet = JsonNode.Parse(line); } catch { continue; }
            if (packet is null) continue;
            if (packet["type"]?.ToString() == "error") failure = new(packet["code"]?.ToString() ?? "collector", packet["message"]?.ToString() ?? "수집 실패");
            else if (packet["type"]?.ToString() == "progress") progress(packet);
        }
        await process.WaitForExitAsync(token); await errors;
        if (failure is not null) throw failure;
        if (process.ExitCode != 0 || !File.Exists(ResultPath(runId))) throw new CollectorFailure("collector", "수집기를 완료하지 못했습니다.");
    }
}

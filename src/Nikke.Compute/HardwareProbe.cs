using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json.Nodes;
using Nikke.Contracts;

namespace Nikke.Compute;

public interface IHardwareInventory { Task<JsonObject> Read(CancellationToken token); }

// Read-only Windows inventory, no runtime/driver installation. A WMI name is not kernel capability.
public sealed class WindowsInventory : IHardwareInventory
{
    public async Task<JsonObject> Read(CancellationToken token)
    {
        if (!OperatingSystem.IsWindows()) throw new PlatformNotSupportedException();
        var start = new ProcessStartInfo("powershell.exe") { UseShellExecute=false, CreateNoWindow=true,
            RedirectStandardOutput=true, RedirectStandardError=true };
        foreach (var arg in new[] { "-NoProfile", "-NonInteractive", "-Command",
            "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; " +
            "$c=@(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores); " +
            "$g=@(Get-CimInstance Win32_VideoController | Select-Object PNPDeviceID,Name,AdapterCompatibility,DriverVersion,ConfigManagerErrorCode); " +
            "@{cpu=$c;gpu=$g} | ConvertTo-Json -Depth 4 -Compress" }) start.ArgumentList.Add(arg);
        using var process = Process.Start(start) ?? throw new IOException();
        var output = process.StandardOutput.ReadToEndAsync(token);
        var errors = process.StandardError.ReadToEndAsync(token);
        try { await process.WaitForExitAsync(token); await errors;
            if (process.ExitCode != 0) throw new IOException("inventory_failed");
            return JsonNode.Parse(await output)!.AsObject(); }
        finally { if (!process.HasExited) { process.Kill(true); await process.WaitForExitAsync(); } }
    }
}

public sealed class HardwareProbe(IHardwareInventory? inventory = null, TimeSpan? probeTimeout = null)
{
    public async Task<HardwareProfile> Detect(CancellationToken token = default)
    {
        JsonObject data = new(); var failures = new List<string>();
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(token);
        timeout.CancelAfter(probeTimeout ?? TimeSpan.FromSeconds(8));
        try { data = await (inventory ?? new WindowsInventory()).Read(timeout.Token).WaitAsync(timeout.Token); }
        catch (OperationCanceledException) when (!token.IsCancellationRequested) { failures.Add("inventory_timeout"); }
        catch (Exception ex) when (ex is not OperationCanceledException) { failures.Add(ex switch {
            UnauthorizedAccessException => "inventory_access_denied", PlatformNotSupportedException => "inventory_os_unsupported",
            _ => "inventory_failed" }); }
        token.ThrowIfCancellationRequested();
        return Normalize(data, Environment.ProcessorCount, GC.GetGCMemoryInfo().TotalAvailableMemoryBytes,
            Environment.MachineName, RuntimeInformation.OSDescription, RuntimeInformation.ProcessArchitecture.ToString(),
            Environment.GetEnvironmentVariable("SESSIONNAME")?.StartsWith("RDP", StringComparison.OrdinalIgnoreCase)==true, failures);
    }

    public static HardwareProfile Normalize(JsonObject data, int available, long memory, string machine,
        string os, string architecture, bool remote, IEnumerable<string>? errors = null)
    {
        var failures = errors?.ToList() ?? [];
        if (memory < 64L*1024*1024 || memory > 1L<<52) { memory = 512L*1024*1024; failures.Add("memory_unknown_conservative_limit"); }
        int? cores = null;
        try { var counts = (data["cpu"] as JsonArray)?.Select(c => c?["NumberOfCores"]?.GetValue<int>() ?? 0).ToArray();
            if (counts is { Length: > 0 } && counts.All(c => c is > 0 and < 65536)) cores = counts.Sum(); }
        catch { failures.Add("cpu_topology_invalid"); }
        var gpus = new List<GpuProfile>();
        foreach (var item in data["gpu"] as JsonArray ?? [])
        {
            try {
                var pnp = item?["PNPDeviceID"]?.GetValue<string>();
                var name = item?["Name"]?.GetValue<string>() ?? "unknown";
                var vendor = pnp?.Contains("VEN_10DE",StringComparison.OrdinalIgnoreCase)==true ? "NVIDIA" :
                    pnp?.Contains("VEN_1002",StringComparison.OrdinalIgnoreCase)==true ? "AMD" :
                    pnp?.Contains("VEN_8086",StringComparison.OrdinalIgnoreCase)==true ? "Intel" : "unknown";
                var driver = item?["DriverVersion"]?.GetValue<string>();
                var issue = item?["ConfigManagerErrorCode"]?.GetValue<int>() is > 0 ? "device_unavailable" :
                    string.IsNullOrWhiteSpace(driver) ? "driver_missing" : "full_battle_provider_not_implemented";
                // AdapterRAM is uint32 WMI inventory, not an authoritative compute memory limit.
                gpus.Add(new(Wire.Hash(pnp ?? name+":"+gpus.Count),name,vendor,driver,null,"none",
                    "not_implemented","not_run","not_run","not_run",null,false,issue));
            } catch { failures.Add("gpu_entry_invalid"); }
        }
        var fingerprint = Wire.Hash(Wire.Serialize(new { machine, os, architecture, available,
            cpu=data["cpu"], gpus=gpus.OrderBy(g=>g.DeviceId), runtime=RuntimeInformation.FrameworkDescription }));
        return new(fingerprint,os,architecture,Math.Max(1,available),cores,memory,remote,gpus,failures);
    }
}

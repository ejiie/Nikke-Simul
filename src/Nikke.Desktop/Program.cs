// WinForms/WebView2 window layout adapted from Nikke-Local-Lab c05fc1c.
// This host starts only Nikke-Simul; Local Lab's admin/install/game controls are not imported.
using System.Diagnostics;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace Nikke.Desktop;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        try { Application.Run(new MainForm(args)); }
        catch (Exception error) { MessageBox.Show(error.Message, "Nikke Simul", MessageBoxButtons.OK, MessageBoxIcon.Error); }
    }
}

internal sealed record DesktopSettings(string ProjectRoot, string Python, int Port = 5180);

internal sealed class MainForm : Form
{
    private readonly WebView2 view = new() { Dock = DockStyle.Fill };
    private readonly Label loading = new() { Dock = DockStyle.Fill, Text = "지휘관 관리 도구를 준비하고 있습니다…",
        TextAlign = ContentAlignment.MiddleCenter, Font = new Font("Malgun Gothic",14,FontStyle.Bold),
        ForeColor = Color.FromArgb(30,63,92), BackColor = Color.FromArgb(244,248,252) };
    private readonly HttpClient http = new() { Timeout = TimeSpan.FromSeconds(2) };
    private readonly CancellationTokenSource lifetime = new();
    private readonly string[] arguments;
    private Process? backend;
    private string? origin, token;
    private bool closing, finished;
    private DesktopSettings settings = null!;

    internal MainForm(string[] args)
    {
        arguments = args;
        Text="Nikke Simul · 지휘관 관리 도구"; StartPosition=FormStartPosition.CenterScreen;
        MinimumSize=new Size(1180,760); Size=new Size(1500,940);
        Controls.Add(loading);
        Shown += async (_,_) =>
        {
            var area=Screen.FromControl(this).WorkingArea;
            var scale=DeviceDpi/96d;
            Size=new Size(Math.Min(area.Width,(int)(1500*scale)),Math.Min(area.Height,(int)(940*scale)));
            CenterToScreen();
            await StartAsync();
        };
        FormClosing += async (_,e) => { if (finished) return; e.Cancel=true; if (!closing) await StopAsync(); };
    }

    private async Task StartAsync()
    {
        try
        {
            var config=Path.Combine(AppContext.BaseDirectory,"desktop.settings.json");
            settings=JsonSerializer.Deserialize<DesktopSettings>(File.ReadAllText(config),new JsonSerializerOptions(JsonSerializerDefaults.Web))
                ?? throw new InvalidDataException("실행 설정을 읽을 수 없습니다. npm run build:desktop을 실행하세요.");
            if (!File.Exists(Path.Combine(settings.ProjectRoot,"Nikke.Simul.slnx"))) throw new InvalidOperationException("프로젝트 폴더를 찾을 수 없습니다. 이동한 경로에서 실행 파일을 다시 빌드하세요.");
            origin=$"http://127.0.0.1:{settings.Port}";
            var existing=await HealthAsync();
            if (existing is not null && !IsOurBackend(existing.Value)) throw new InvalidOperationException("설정한 포트를 다른 프로그램이 사용 중입니다.");
            if (existing is null)
            {
                var executable=Path.Combine(AppContext.BaseDirectory,"backend","Nikke.Api.exe");
                var start=new ProcessStartInfo(executable) { WorkingDirectory=settings.ProjectRoot,UseShellExecute=false,
                    CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true };
                start.Environment["NIKKE_PROJECT_ROOT"]=settings.ProjectRoot;
                start.Environment["NIKKE_PYTHON"]=settings.Python;
                start.Environment["NIKKE_PORT"]=settings.Port.ToString();
                backend=Process.Start(start) ?? throw new InvalidOperationException("백엔드를 시작하지 못했습니다.");
                // Drain pipes without logging account/token data.
                backend.OutputDataReceived += (_,_)=>{}; backend.ErrorDataReceived += (_,_)=>{};
                backend.BeginOutputReadLine(); backend.BeginErrorReadLine();
                using var timeout=CancellationTokenSource.CreateLinkedTokenSource(lifetime.Token);
                timeout.CancelAfter(TimeSpan.FromSeconds(35));
                while (await HealthAsync() is not { } health || !IsOurBackend(health))
                {
                    if (backend.HasExited) throw new InvalidOperationException("백엔드 시작 실패. 기존 프로세스 또는 데이터 준비 상태를 확인하세요.");
                    await Task.Delay(250,timeout.Token);
                }
            }
            var bootstrap=await http.GetFromJsonAsync<JsonElement>(origin+"/api/bootstrap",lifetime.Token);
            token=bootstrap.GetProperty("token").GetString();
            var environment=await CoreWebView2Environment.CreateAsync(null,Path.Combine(settings.ProjectRoot,"data/local/desktop-webview"));
            await view.EnsureCoreWebView2Async(environment);
            if (closing) return;
            view.CoreWebView2.Settings.IsStatusBarEnabled=false;
            view.CoreWebView2.Settings.AreDefaultContextMenusEnabled=false;
            view.CoreWebView2.NavigationStarting += (_,e)=> { if (!IsLocal(e.Uri)) e.Cancel=true; };
            view.CoreWebView2.NewWindowRequested += (_,e)=> { e.Handled=true; if (IsLocal(e.Uri)) view.Source=new Uri(e.Uri); };
            view.CoreWebView2.PermissionRequested += (_,e)=> e.State=CoreWebView2PermissionState.Deny;
            Controls.Remove(loading); Controls.Add(view);
            view.Source=new Uri(origin+"/editor/");
            // Opt-in local acceptance mode verifies the real WebView2, then captures and closes.
            var smoke=Array.IndexOf(arguments,"--smoke-output");
            if (smoke>=0 && smoke+1<arguments.Length) await SmokeAsync(arguments[smoke+1]);
        }
        catch (OperationCanceledException) when (closing) { }
        catch (Exception error)
        {
            loading.Text="시작하지 못했습니다.\n"+error.Message;
            var smoke=Array.IndexOf(arguments,"--smoke-output");
            if (smoke>=0 && smoke+1<arguments.Length)
            {
                Directory.CreateDirectory(arguments[smoke+1]);
                await File.WriteAllTextAsync(Path.Combine(arguments[smoke+1],"desktop-error.txt"),error.ToString());
                Environment.ExitCode=1; await StopAsync();
            }
        }
    }

    private bool IsLocal(string url) => Uri.TryCreate(url,UriKind.Absolute,out var uri) && uri.GetLeftPart(UriPartial.Authority)==origin;
    private bool IsOurBackend(JsonElement health) => health.TryGetProperty("application",out var app) && app.GetString()=="nikke-simul"
        && health.TryGetProperty("projectRoot",out var root) && string.Equals(root.GetString(),settings.ProjectRoot,StringComparison.OrdinalIgnoreCase);
    private async Task<JsonElement?> HealthAsync()
    {
        try { return await http.GetFromJsonAsync<JsonElement>(origin+"/api/health",lifetime.Token); }
        catch (HttpRequestException) { return null; }
        catch (TaskCanceledException) when (!closing) { return null; }
    }

    private async Task StopAsync()
    {
        closing=true; lifetime.Cancel(); Enabled=false;
        try
        {
            // Only shut down a backend created by this window. Attached development hosts stay alive.
            if (backend is not null && !backend.HasExited)
            {
                try
                {
                    using var request=new HttpRequestMessage(HttpMethod.Post,origin+"/api/desktop/shutdown");
                    request.Headers.Add("X-Nikke-Token",token);
                    await http.SendAsync(request);
                    using var timeout=new CancellationTokenSource(TimeSpan.FromSeconds(8));
                    await backend.WaitForExitAsync(timeout.Token);
                }
                catch { if (!backend.HasExited) backend.Kill(entireProcessTree:true); }
            }
        }
        finally { view.Dispose(); http.Dispose(); backend?.Dispose(); finished=true; Close(); }
    }

    private async Task SmokeAsync(string output)
    {
        Directory.CreateDirectory(output);
        var timer=Stopwatch.StartNew(); string ready="";
        while (timer.Elapsed<TimeSpan.FromSeconds(25))
        {
            await Task.Delay(250,lifetime.Token);
            ready=await view.ExecuteScriptAsync("document.body.dataset.ready || ''");
            if (ready=="\"true\"") break;
        }
        if (ready!="\"true\"") throw new InvalidOperationException("Desktop UI did not become ready");
        await view.ExecuteScriptAsync("document.querySelector('[data-tab=\"nikkes\"]').click()");
        await Task.Delay(1200,lifetime.Token);
        var result=await view.ExecuteScriptAsync("JSON.stringify({title:document.title,cards:document.querySelectorAll('.nikke-card').length,broken:[...document.images].filter(x=>x.offsetParent!==null && x.complete && !x.naturalWidth).map(x=>x.src)})");
        await File.WriteAllTextAsync(Path.Combine(output,"desktop-smoke.json"),JsonSerializer.Deserialize<string>(result));
        await using (var stream=File.Create(Path.Combine(output,"desktop.png")))
            await view.CoreWebView2.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png,stream);
        await StopAsync();
    }
}

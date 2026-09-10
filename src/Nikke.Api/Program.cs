using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;
using Nikke.Api;
using Nikke.Contracts;
using Nikke.Storage;
using Nikke.Data;
using Nikke.Core.Combat;

var builder = WebApplication.CreateBuilder(args);
builder.Logging.AddFilter("Microsoft.AspNetCore", LogLevel.Warning);
var root = Environment.GetEnvironmentVariable("NIKKE_PROJECT_ROOT") ?? Directory.GetCurrentDirectory();
while (!File.Exists(Path.Combine(root, "Nikke.Simul.slnx"))) root = Directory.GetParent(root)?.FullName ?? throw new InvalidOperationException("Project root not found");
var dataRoot = Environment.GetEnvironmentVariable("NIKKE_DATA_ROOT") ?? Path.Combine(root, "data/local");
var python = Environment.GetEnvironmentVariable("NIKKE_PYTHON") ?? "python";
var port = int.TryParse(Environment.GetEnvironmentVariable("NIKKE_PORT"), out var configuredPort) ? configuredPort : 5180;
if (port is < 1024 or > 65535) throw new InvalidOperationException("Invalid local port");
builder.WebHost.UseUrls($"http://127.0.0.1:{port}");
var store = new SnapshotStore(dataRoot);
// A second backend must not interrupt jobs owned by the first one.
using var instanceLock = new FileStream(Path.Combine(dataRoot, "backend.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
var gamePath = Environment.GetEnvironmentVariable("NIKKE_GAME_CATALOG") ?? Path.Combine(root, "data/local/game-catalog.json");
if (!File.Exists(gamePath)) throw new InvalidOperationException("Run npm run setup:sync to prepare the pinned game catalog.");
var game = Wire.Read<GameSnapshot>(File.ReadAllText(gamePath)); store.SaveGame(game);
builder.Services.AddSingleton(store); builder.Services.AddSingleton(game);
builder.Services.AddSingleton(new CollectorProcess(root, dataRoot, python));
builder.Services.AddSingleton(new PresentationService(root, Path.Combine(dataRoot, "presentation"), python));
builder.Services.AddHostedService(sp => sp.GetRequiredService<PresentationService>());
builder.Services.AddSingleton<SyncCoordinator>(); builder.Services.AddHostedService(sp => sp.GetRequiredService<SyncCoordinator>());
builder.Services.ConfigureHttpJsonOptions(options => options.SerializerOptions.PropertyNamingPolicy = Wire.Json.PropertyNamingPolicy);
var app = builder.Build();
var token = Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(32));
var allowedOrigins = new[] { $"http://127.0.0.1:{port}", "http://127.0.0.1:5174" };
app.Use(async (context, next) =>
{
    if (context.Request.Host.Host != "127.0.0.1") { context.Response.StatusCode = 403; return; }
    if (context.Request.Path.StartsWithSegments("/api"))
    {
        var origin = context.Request.Headers.Origin.ToString();
        if ((origin.Length > 0 && !allowedOrigins.Contains(origin)) || context.Request.Headers["Sec-Fetch-Site"] == "cross-site") { context.Response.StatusCode = 403; return; }
        context.Response.Headers.CacheControl = "no-store";
        if (context.Request.Method is not ("GET" or "HEAD") && context.Request.Headers["X-Nikke-Token"] != token) { context.Response.StatusCode = 403; return; }
    }
    try { await next(); }
    catch (KeyNotFoundException) { context.Response.StatusCode = 404; await context.Response.WriteAsJsonAsync(new { message = "항목을 찾을 수 없습니다." }); }
    catch (ArgumentException ex) { context.Response.StatusCode = 400; await context.Response.WriteAsJsonAsync(new { message = ex.Message }); }
    catch (InvalidOperationException ex) { context.Response.StatusCode = 409; await context.Response.WriteAsJsonAsync(new { message = ex.Message }); }
});
app.MapGet("/api/bootstrap", () => new { token, connections = store.Connections(), jobs = store.Jobs().Take(30), connectionFailure = store.LastConnectionFailure(),
    game = new { game.Id, characters = game.Names.Count }, testMode = Environment.GetEnvironmentVariable("NIKKE_TEST_FIXTURE") is not null });
app.MapGet("/api/connections/{id}", (string id) => store.Connection(id) ?? throw new KeyNotFoundException());
app.MapPost("/api/connections", (SyncCoordinator sync) => Results.Accepted(value: sync.Connect()));
app.MapPost("/api/connections/{id}/reauth", (string id, SyncCoordinator sync) => Results.Accepted(value: sync.Connect(id)));
app.MapPatch("/api/connections/{id}", (string id, AreaSelection selection, SyncCoordinator sync) => sync.Select(id, selection.Area));
app.MapPost("/api/sync-jobs", (StartSync request, SyncCoordinator sync) => { var job = sync.Start(request.ConnectionId); return Results.Accepted($"/api/sync-jobs/{job.Id}", job); });
app.MapGet("/api/sync-jobs/{id}", (string id) => store.Job(id) ?? throw new KeyNotFoundException());
app.MapPost("/api/sync-jobs/{id}/cancel", (string id, SyncCoordinator sync) => sync.Cancel(id));
app.MapGet("/api/accounts/{id}/snapshot", (string id) => store.Current(id) is { } snapshot ? Results.Ok(snapshot) : Results.NoContent());
app.MapGet("/api/accounts/{id}/formation", (string id) => store.Formation(id));
app.MapPut("/api/accounts/{id}/formation", (string id, SaveFormation request) => store.SaveFormation(id, request.Slots));
app.MapGet("/api/snapshots/{id}", (string id) => store.Snapshot(id) ?? throw new KeyNotFoundException());
app.MapGet("/api/snapshots/{id}/changes", (string id) => (store.Snapshot(id) ?? throw new KeyNotFoundException()).Changes);
app.MapPost("/api/accounts/{id}/overrides", (string id, OverrideRequest request) =>
{
    if(request.CubeLevels is not null)
    {
        var cubes=app.Services.GetRequiredService<PresentationService>().Read()["cubes"]?.AsArray();
        foreach(var (cubeId,level) in request.CubeLevels)
            if(cubes?.Any(c=>c?["definitionUid"]?.ToString()==cubeId && c["levels"]!.AsArray().Any(l=>l?["level"]?.GetValue<int>()==level))!=true)
                throw new ArgumentException("큐브 카탈로그에 없는 종류 또는 레벨입니다.");
    }
    return store.ApplyOverride(id, request);
});
var calculationPath = Path.Combine(root, "data/local/calculation");
var calculations = new Lazy<CalculationService>(() => new CalculationService(calculationPath));
var runtimeRoot = Path.Combine(dataRoot, "runtime");
var runtimeReplay = new Lazy<RuntimeReplayService>(() => new(runtimeRoot, Path.Combine(dataRoot, "weapon-replays")));
var presentationRoot = Path.Combine(dataRoot, "presentation");
var presentation = app.Services.GetRequiredService<PresentationService>();
app.MapGet("/api/presentation", () => presentation.Read());
app.MapGet("/api/presentation/status", () => presentation.Status());
app.MapPost("/api/presentation/refresh", () => presentation.Start());
app.MapPost("/api/desktop/shutdown", (IHostApplicationLifetime lifetime) =>
{
    lifetime.StopApplication(); return Results.Accepted();
});
app.MapGet("/api/runtime/catalog", () => File.Exists(Path.Combine(runtimeRoot, "current.json"))
    ? Results.Ok(runtimeReplay.Value.Summary())
    : Results.Conflict(new { message = "P03 자료 준비가 필요합니다. npm run prepare:p03을 실행하세요." }));
app.MapPost("/api/runtime/weapon-replays", (WeaponReplayRequest request) =>
{
    if (string.IsNullOrWhiteSpace(request.SnapshotId)) throw new ArgumentException("저장 스냅샷을 지정하세요.");
    if (!File.Exists(Path.Combine(runtimeRoot, "current.json")))
        throw new InvalidOperationException("P03 자료 준비가 필요합니다. npm run prepare:p03을 실행하세요.");
    return runtimeReplay.Value.Run(store.Snapshot(request.SnapshotId) ?? throw new KeyNotFoundException(), request, calculations.Value);
});
app.MapGet("/api/runtime/weapon-replays/{id}", (string id) => runtimeReplay.Value.Read(id));
app.MapPost("/api/runtime/skill-replays", (SkillReplayRequest request) =>
{
    if (string.IsNullOrWhiteSpace(request.SnapshotId)) throw new ArgumentException("저장 스냅샷을 지정하세요.");
    if (!File.Exists(Path.Combine(runtimeRoot, "current.json")))
        throw new InvalidOperationException("P03 자료 준비가 필요합니다. npm run prepare:p03을 실행하세요.");
    return runtimeReplay.Value.RunSkills(store.Snapshot(request.SnapshotId) ?? throw new KeyNotFoundException(), request, calculations.Value);
});
app.MapGet("/api/runtime/skill-replays/{id}", (string id) => runtimeReplay.Value.ReadSkills(id));
app.MapGet("/api/snapshots/{id}/combat-powers", (string id) =>
{
    var snapshot = store.Snapshot(id) ?? throw new KeyNotFoundException();
    // Read the captured roster so older snapshots work without another account sync.
    var powers = new Dictionary<string, long>();
    foreach (var row in store.Raw(snapshot.RawManifestId).Characters.OfType<JsonObject>())
    {
        var characterId = row["name_code"]?.ToString();
        if (characterId is not null && long.TryParse(row["combat"]?.ToString(), out var power) && power >= 0)
            powers[characterId] = power;
    }
    return powers;
});
app.MapGet("/api/snapshots/{id}/characters/{characterId}/stats", (string id, string characterId, int? scenarioLevel) =>
{
    if (!File.Exists(Path.Combine(calculationPath, "current.json"))) return Results.Conflict(new { message = "P02 계산 자료 준비가 필요합니다. npm run setup:sync를 실행하세요." });
    return Results.Ok(calculations.Value.Calculate(store.Snapshot(id) ?? throw new KeyNotFoundException(), characterId, scenarioLevel));
});
app.MapPost("/api/accounts/{id}/characters/{characterId}/preview", (string id,string characterId,CharacterEditRequest request) =>
{
    var next=CharacterEditService.Preview(store.Current(id)??throw new KeyNotFoundException(),characterId,request,presentation.Read());
    return calculations.Value.Calculate(next,characterId);
});
app.MapPost("/api/accounts/{id}/characters/{characterId}/edit", (string id,string characterId,CharacterEditRequest request) =>
{
    var next=CharacterEditService.Preview(store.Current(id)??throw new KeyNotFoundException(),characterId,request,presentation.Read());
    next.Id=Guid.NewGuid().ToString("N");
    return store.Commit(next,expectedId:request.ExpectedSnapshotId);
});
app.MapPost("/api/calculations/hit", (HitRequest request) =>
{
    if (request.InputSchemaVersion != HitCalculator.InputSchemaVersion)
        throw new ArgumentException("계산 입력 형식이 변경되었습니다. 화면을 새로고침한 뒤 다시 계산하세요.");
    if (request.Input is null || !request.Input.ContainsKey("statAttack"))
        throw new ArgumentException("버프 적용 전 statAttack 입력이 필요합니다.");
    HitContext input;
    try { input = request.Input.Deserialize<HitContext>(new JsonSerializerOptions(Wire.Json) { UnmappedMemberHandling = System.Text.Json.Serialization.JsonUnmappedMemberHandling.Disallow })!; }
    catch (JsonException) { throw new ArgumentException("계산 입력 필드를 확인하세요. 기존 attack은 statAttack과 버프 목록으로 분리되었습니다."); }
    return HitCalculator.Compare(input, request.ObservedDamage);
});
var editor = Path.Combine(root, "apps/desktop-ui");
if (Directory.Exists(editor))
{
    var provider = new Microsoft.Extensions.FileProviders.PhysicalFileProvider(editor);
    app.UseDefaultFiles(new DefaultFilesOptions { FileProvider = provider, RequestPath = "/editor" });
    app.UseStaticFiles(new StaticFileOptions { FileProvider = provider, RequestPath = "/editor",
        OnPrepareResponse = context => context.Context.Response.Headers.CacheControl = "no-store" });
}
var assets = Path.Combine(presentationRoot, "assets"); Directory.CreateDirectory(assets);
app.UseStaticFiles(new StaticFileOptions { FileProvider = new Microsoft.Extensions.FileProviders.PhysicalFileProvider(assets), RequestPath = "/editor/assets" });
app.MapGet("/", () => Results.Redirect("/editor/"));
var web = Path.Combine(root, "apps/web/dist");
if (Directory.Exists(web))
{
    var provider = new Microsoft.Extensions.FileProviders.PhysicalFileProvider(web);
    // Preserve the prior workbench during migration. Product entry is /editor/.
    app.UseDefaultFiles(new DefaultFilesOptions { FileProvider = provider, RequestPath = "/legacy" }); app.UseStaticFiles(new StaticFileOptions { FileProvider = provider, RequestPath = "/legacy" });
    app.UseStaticFiles(new StaticFileOptions { FileProvider = provider });
}
app.MapGet("/api/health", () => new { status = "ok", application = "nikke-simul", projectRoot = root, milestone = "P03", combatEngineConnected = false, singleHitCalculator = true, desktopUi = true });
await app.RunAsync();
record AreaSelection(int Area);
record StartSync(string ConnectionId);
record HitRequest(JsonObject Input, double? ObservedDamage, int InputSchemaVersion);

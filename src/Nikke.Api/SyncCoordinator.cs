using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Data;
using Nikke.Storage;

namespace Nikke.Api;

public sealed class SyncCoordinator(SnapshotStore store, CollectorProcess collector, GameSnapshot game, PresentationService? presentation = null) : IHostedService
{
    private readonly object gate = new();
    private readonly Dictionary<string, (CancellationTokenSource Cancellation, Task Task)> running = [];
    private bool stopping;
    public Task StartAsync(CancellationToken cancellationToken) { store.RecoverInterrupted(); return Task.CompletedTask; }
    public async Task StopAsync(CancellationToken cancellationToken)
    {
        Task[] tasks;
        lock (gate) { stopping = true; foreach (var run in running.Values) run.Cancellation.Cancel(); tasks = running.Values.Select(x => x.Task).ToArray(); }
        try { await Task.WhenAll(tasks).WaitAsync(cancellationToken); } catch (OperationCanceledException) { }
    }
    public AccountConnection Connect(string? id = null)
    {
        lock (gate)
        {
            if (stopping) throw new InvalidOperationException("백엔드가 종료 중입니다.");
            var active = store.Connections().FirstOrDefault(x => x.Status == "awaiting_login");
            if (active is not null) return active;
            var connection = id is null ? new AccountConnection() : store.Connection(id) ?? throw new KeyNotFoundException();
            if (store.Jobs().Any(x => x.ConnectionId == connection.Id && x.Status is "queued" or "running" or "cancelling")) throw new InvalidOperationException("진행 중인 동기화가 끝난 뒤 다시 연결하세요.");
            connection.Status = "awaiting_login"; connection.ErrorCode = null; connection.Message = "열린 브라우저에서 로그인하세요.";
            store.SaveConnection(connection);
            Launch("auth-" + connection.Id, async token =>
            {
                try
                {
                    await collector.Run("login", connection, connection.Id, packet =>
                    { lock (gate) { connection.Message = packet["message"]?.ToString(); store.SaveConnection(connection); } }, token);
                    var result = JsonNode.Parse(await File.ReadAllTextAsync(collector.ResultPath(connection.Id), token))!;
                    var choices = Wire.Read<List<AreaChoice>>(result["choices"]!.ToJsonString());
                    if (choices.Count == 0) throw new CollectorFailure("empty_account", "조회 가능한 계정이 없습니다.");
                    if (connection.OpenId is not null && choices.All(x => x.OpenId != connection.OpenId)) throw new CollectorFailure("account_mismatch", "기존 연결과 다른 계정입니다. 원래 계정으로 다시 로그인하세요.");
                    lock (gate)
                    {
                        connection.Choices = choices; connection.Status = "select_account"; connection.Message = "사용할 서버를 선택하세요."; store.SaveConnection(connection);
                        var previous = choices.FirstOrDefault(x => x.Area == connection.Area && x.OpenId == connection.OpenId);
                        if (previous is not null || choices.Count == 1) Select(connection.Id, (previous ?? choices[0]).Area);
                    }
                }
                catch (Exception ex)
                {
                    lock (gate) { connection.Status = "reauth_required"; connection.ErrorCode = ex is CollectorFailure cf ? cf.Code : ex is OperationCanceledException ? "login_interrupted" : "login_failure";
                        connection.Message = ex is CollectorFailure ? ex.Message : "로그인을 완료하지 못했습니다. 다시 연결하세요."; store.SaveConnection(connection); }
                }
            });
            return connection;
        }
    }
    public AccountConnection Select(string id, int area)
    {
        lock (gate)
        {
            var connection = store.Connection(id) ?? throw new KeyNotFoundException();
            if (connection.Status != "select_account") throw new InvalidOperationException("서버 선택 상태가 아닙니다.");
            var choice = connection.Choices.FirstOrDefault(x => x.Area == area) ?? throw new ArgumentException("조회된 서버를 선택하세요.");
            connection.Area = area; connection.OpenId = choice.OpenId;
            connection.AccountId = Wire.Hash($"blablalink:{choice.OpenId}:{area}");
            connection.Status = "ready"; connection.Message = null; store.SaveConnection(connection);
            Start(connection.Id); return connection;
        }
    }
    public SyncJob Start(string connectionId)
    {
        lock (gate)
        {
            if (stopping) throw new InvalidOperationException("백엔드가 종료 중입니다.");
            var connection = store.Connection(connectionId) ?? throw new KeyNotFoundException();
            var (job, created) = store.CreateJob(connection);
            if (created) Launch(job.Id, token => Collect(job, connection, token));
            return job;
        }
    }
    private void Launch(string id, Func<CancellationToken, Task> action)
    {
        var cts = new CancellationTokenSource(TimeSpan.FromMinutes(12));
        var task = Task.Run(async () =>
        {
            try { await action(cts.Token); }
            finally { lock (gate) { running.Remove(id); cts.Dispose(); } }
        });
        running[id] = (cts, task);
    }
    public SyncJob Cancel(string id)
    {
        lock (gate)
        {
            var job = store.Job(id) ?? throw new KeyNotFoundException();
            if (job.Status is "queued" or "running" or "cancelling")
            { if (running.TryGetValue(id, out var run)) run.Cancellation.Cancel(); job.Status = "cancelling"; store.SaveJob(job); }
            return job;
        }
    }
    private async Task Collect(SyncJob job, AccountConnection connection, CancellationToken token)
    {
        bool rawSaved = false;
        try
        {
            lock (gate) { token.ThrowIfCancellationRequested(); job.Status = "running"; job.Stage = "collecting"; store.SaveJob(job); }
            await collector.Run("collect", connection, job.Id, packet =>
            {
                lock (gate)
                {
                    if (token.IsCancellationRequested) return;
                    job.Stage = packet["stage"]?.ToString() ?? "collecting";
                    job.Collected = packet["collected"]?.GetValue<int>() ?? job.Collected;
                    job.Expected = packet["expected"]?.GetValue<int>() ?? job.Expected;
                    store.SaveJob(job);
                }
            }, token);
            token.ThrowIfCancellationRequested();
            var raw = Wire.Read<RawEnvelope>(await File.ReadAllTextAsync(collector.ResultPath(job.Id), token));
            var manifest = store.SaveRaw(job.Id, raw, game); rawSaved = true;
            lock (gate) { job.Stage = "validating"; store.SaveJob(job); }
            var snapshot = new SnapshotNormalizer().Normalize(raw, game, job.AccountId, connection.OpenId!, connection.Area!.Value, manifest);
            job.Issues = snapshot.Issues; job.Collected = snapshot.Characters.Count;
            if (!snapshot.Valid) throw new CollectorFailure("validation_failed", "수집 데이터 검증에 실패했습니다. 이전 정상 스펙을 유지합니다.");
            lock (gate) { token.ThrowIfCancellationRequested(); store.Commit(snapshot, job, cancellation: token); }
            // Image refresh is independent; a CDN outage cannot invalidate a successfully stored account snapshot.
            if (Environment.GetEnvironmentVariable("NIKKE_TEST_FIXTURE") is null) presentation?.Start(false);
        }
        catch (Exception ex)
        {
            if (!rawSaved && File.Exists(collector.ResultPath(job.Id)))
            { try { store.SaveRaw(job.Id, Wire.Read<RawEnvelope>(File.ReadAllText(collector.ResultPath(job.Id))), game); } catch { /* Incomplete JSON is never published. */ } }
            lock (gate)
            {
                job.Status = token.IsCancellationRequested ? "cancelled" : "failed";
                job.ErrorCode = ex is CollectorFailure cf ? cf.Code : token.IsCancellationRequested ? "cancelled" : "internal_error";
                job.Message = ex is CollectorFailure ? ex.Message : token.IsCancellationRequested ? "동기화가 취소되거나 대기 시간이 끝났습니다." : "처리에 실패했습니다. 이전 정상 스펙은 유지됩니다.";
                job.FinishedAt = DateTimeOffset.UtcNow; store.SaveJob(job);
                if (job.ErrorCode == "reauth_required") { connection.Status = "reauth_required"; connection.Message = job.Message; store.SaveConnection(connection); }
            }
        }
    }
}

using System.Text.Json.Nodes;
using Microsoft.Data.Sqlite;
using Nikke.Contracts;

namespace Nikke.Storage;

public sealed class SnapshotStore
{
    private readonly string connectionString;
    private readonly object gate = new();
    public string Root { get; }
    public SnapshotStore(string root)
    {
        Root = Path.GetFullPath(root); Directory.CreateDirectory(Root);
        connectionString = new SqliteConnectionStringBuilder { DataSource = Path.Combine(Root, "accounts.db"), ForeignKeys = true }.ToString();
        using var db = Open();
        Execute(db, null, """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS connections(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, account_id TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS active_job ON jobs(account_id) WHERE status IN ('queued','running','cancelling');
            CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY, account_id TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY, current_id TEXT NOT NULL REFERENCES snapshots(id));
            CREATE TABLE IF NOT EXISTS game_snapshots(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            PRAGMA user_version=1;
            """);
    }
    private SqliteConnection Open() { var db = new SqliteConnection(connectionString); db.Open(); return db; }
    private static void Execute(SqliteConnection db, SqliteTransaction? tx, string sql, params (string, object?)[] parameters)
    {
        using var cmd = db.CreateCommand(); cmd.Transaction = tx; cmd.CommandText = sql;
        foreach (var (key, value) in parameters) cmd.Parameters.AddWithValue(key, value ?? DBNull.Value);
        cmd.ExecuteNonQuery();
    }
    private static string? Scalar(SqliteConnection db, SqliteTransaction? tx, string sql, string id)
    {
        using var cmd = db.CreateCommand(); cmd.Transaction = tx; cmd.CommandText = sql; cmd.Parameters.AddWithValue("$id", id);
        return cmd.ExecuteScalar() as string;
    }
    private T? Get<T>(string table, string id)
    {
        lock (gate) { using var db = Open(); var json = Scalar(db, null, $"SELECT payload FROM {table} WHERE id=$id", id); return json is null ? default : Wire.Read<T>(json); }
    }
    private List<T> All<T>(string table)
    {
        lock (gate)
        {
            using var db = Open(); using var cmd = db.CreateCommand(); cmd.CommandText = $"SELECT payload FROM {table} ORDER BY rowid DESC";
            using var reader = cmd.ExecuteReader(); var values = new List<T>(); while (reader.Read()) values.Add(Wire.Read<T>(reader.GetString(0))); return values;
        }
    }
    public AccountConnection? Connection(string id) => Get<AccountConnection>("connections", id);
    public List<AccountConnection> Connections() => All<AccountConnection>("connections");
    public SyncJob? Job(string id) => Get<SyncJob>("jobs", id);
    public List<SyncJob> Jobs() => All<SyncJob>("jobs");
    public AccountSnapshot? Snapshot(string id) => Get<AccountSnapshot>("snapshots", id);
    public GameSnapshot? Game(string id) => Get<GameSnapshot>("game_snapshots", id);
    public void SaveGame(GameSnapshot game)
    {
        lock (gate)
        {
            var prior = Game(game.Id);
            if (prior is not null && Wire.Serialize(prior) != Wire.Serialize(game)) throw new InvalidDataException("동일한 game snapshot ID의 내용이 다릅니다.");
            using var db = Open(); Execute(db, null, "INSERT OR IGNORE INTO game_snapshots VALUES($id,$json)", ("$id", game.Id), ("$json", Wire.Serialize(game)));
        }
    }
    public void SaveConnection(AccountConnection value)
    {
        lock (gate) { value.UpdatedAt = DateTimeOffset.UtcNow; using var db = Open(); Execute(db, null, "INSERT INTO connections VALUES($id,$json) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload", ("$id", value.Id), ("$json", Wire.Serialize(value))); }
    }
    public void SaveJob(SyncJob value)
    {
        lock (gate) { using var db = Open(); WriteJob(db, null, value); }
    }
    private static void WriteJob(SqliteConnection db, SqliteTransaction? tx, SyncJob value) => Execute(db, tx,
        "INSERT INTO jobs VALUES($id,$account,$status,$json) ON CONFLICT(id) DO UPDATE SET status=excluded.status,payload=excluded.payload",
        ("$id", value.Id), ("$account", value.AccountId), ("$status", value.Status), ("$json", Wire.Serialize(value)));
    public (SyncJob Job, bool Created) CreateJob(AccountConnection connection)
    {
        lock (gate)
        {
            if (connection.Status != "ready" || connection.AccountId is null) throw new InvalidOperationException("계정 연결을 먼저 완료하세요.");
            var active = Jobs().FirstOrDefault(x => x.AccountId == connection.AccountId && x.Status is "queued" or "running" or "cancelling");
            if (active is not null) return (active, false);
            var job = new SyncJob { ConnectionId = connection.Id, AccountId = connection.AccountId }; SaveJob(job); return (job, true);
        }
    }
    public void RecoverInterrupted()
    {
        foreach (var job in Jobs().Where(x => x.Status is "queued" or "running" or "cancelling"))
        { job.Status = "interrupted"; job.ErrorCode = "process_interrupted"; job.Message = "백엔드가 종료되어 동기화가 중단되었습니다. 다시 동기화하세요."; job.FinishedAt = DateTimeOffset.UtcNow; SaveJob(job); }
        foreach (var connection in Connections().Where(x => x.Status == "awaiting_login"))
        { connection.Status = "reauth_required"; connection.Message = "로그인 연결이 중단되었습니다."; SaveConnection(connection); }
    }
    public AccountSnapshot? Current(string accountId)
    {
        lock (gate) { using var db = Open(); return Current(db, null, accountId); }
    }
    private static AccountSnapshot? Current(SqliteConnection db, SqliteTransaction? tx, string accountId)
    {
        var json = Scalar(db, tx, "SELECT s.payload FROM accounts a JOIN snapshots s ON s.id=a.current_id WHERE a.id=$id", accountId);
        return json is null ? null : Wire.Read<AccountSnapshot>(json);
    }
    public string SaveRaw(string jobId, RawEnvelope raw, GameSnapshot game)
    {
        if (!Guid.TryParseExact(jobId, "N", out _)) throw new ArgumentException("Invalid job ID");
        var dir = Path.Combine(Root, "raw", jobId); Directory.CreateDirectory(dir);
        var content = Wire.Serialize(raw); var hash = Wire.Hash(content);
        var existing = Path.Combine(dir, "envelope.json");
        if (File.Exists(existing) && Wire.Hash(File.ReadAllText(existing)) != hash) throw new InvalidDataException("동일한 원천 ID의 내용을 덮어쓸 수 없습니다.");
        AtomicWrite(Path.Combine(dir, "envelope.json"), content);
        AtomicWrite(Path.Combine(dir, "manifest.json"), Wire.Serialize(new { schemaVersion = 1, id = jobId, raw.CollectorVersion,
            raw.Source, raw.StartedAt, raw.CompletedAt, raw.OpenId, raw.Area, gameSnapshotId = game.Id, envelopeHash = hash,
            endpoints = raw.Responses.Select(x => new { route = x?["route"]?.ToString(), hash = Wire.Hash(Wire.Canonical(x?["response"])), observedAt = x?["observedAt"]?.ToString() }) }));
        return jobId;
    }
    public RawEnvelope Raw(string manifestId)
    {
        if (!Guid.TryParseExact(manifestId, "N", out _)) throw new ArgumentException("Invalid manifest ID");
        var dir = Path.Combine(Root, "raw", manifestId); var content = File.ReadAllText(Path.Combine(dir, "envelope.json"));
        var manifest = JsonNode.Parse(File.ReadAllText(Path.Combine(dir, "manifest.json")))!;
        if (manifest["envelopeHash"]?.ToString() != Wire.Hash(content)) throw new InvalidDataException("원천 파일 hash가 일치하지 않습니다.");
        return Wire.Read<RawEnvelope>(content);
    }
    public static void AtomicWrite(string path, string content)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        File.WriteAllText(temporary, content, new System.Text.UTF8Encoding(false));
        File.Move(temporary, path, true);
    }
    public AccountSnapshot Commit(AccountSnapshot snapshot, SyncJob? job = null, string? expectedId = null, CancellationToken cancellation = default)
    {
        lock (gate)
        {
            if (!snapshot.Valid) throw new InvalidOperationException("검증 오류가 있는 snapshot은 적용할 수 없습니다.");
            // Verify referenced files before publishing. Current and job completion commit together.
            _ = Raw(snapshot.RawManifestId);
            if (Game(snapshot.GameSnapshotId) is null) throw new InvalidDataException("Game snapshot missing");
            using var db = Open(); using var tx = db.BeginTransaction();
            var previous = Current(db, tx, snapshot.AccountId);
            if (expectedId is not null && previous?.Id != expectedId) throw new InvalidOperationException("스펙이 갱신되었습니다. 다시 확인하고 저장하세요.");
            if (job is not null && previous is not null) CarryOverrides(previous, snapshot);
            snapshot.PreviousId = previous?.Id; snapshot.Revision = (previous?.Revision ?? 0) + 1;
            snapshot.SavedAt = DateTimeOffset.UtcNow;
            snapshot.ContentHash = Wire.Hash(Wire.Canonical(JsonNode.Parse(Wire.Serialize(new { snapshot.Characters, snapshot.Consoles, snapshot.SynchroLevel, snapshot.GameSnapshotId }))));
            snapshot.Changes = Changes(previous, snapshot);
            Execute(db, tx, "INSERT INTO snapshots VALUES($id,$account,$revision,$json)", ("$id", snapshot.Id), ("$account", snapshot.AccountId), ("$revision", snapshot.Revision), ("$json", Wire.Serialize(snapshot)));
            Execute(db, tx, "INSERT INTO accounts VALUES($id,$snapshot) ON CONFLICT(id) DO UPDATE SET current_id=excluded.current_id", ("$id", snapshot.AccountId), ("$snapshot", snapshot.Id));
            cancellation.ThrowIfCancellationRequested();
            if (job is not null) { job.Status = "succeeded"; job.Stage = "complete"; job.SnapshotId = snapshot.Id; job.FinishedAt = DateTimeOffset.UtcNow; job.Issues = snapshot.Issues; WriteJob(db, tx, job); }
            tx.Commit(); return snapshot;
        }
    }
    private static void CarryOverrides(AccountSnapshot old, AccountSnapshot next)
    {
        foreach (var manual in old.ManualOverrides)
        {
            var equip = next.Characters.FirstOrDefault(x => x.CharacterId == manual.CharacterId)?.Equipment.FirstOrDefault(x => x.Slot == manual.Slot);
            var line = equip?.Lines.FirstOrDefault(x => x.LineIndex == manual.LineIndex);
            if (equip?.Fingerprint == manual.Fingerprint && line?.Presence == "present")
            { line.LockState = manual.LockState; line.Source = "api+manual"; next.ManualOverrides.Add(manual); }
            else next.Issues.Add(new("warning", "stale_override", manual.CharacterId + "." + manual.Slot, "장비가 바뀌어 잠금 보완을 해제했습니다. 다시 확인하세요."));
        }
        foreach (var (field, source) in old.AccountStatSources.Where(x => x.Value == "manual"))
        {
            if (next.AccountStatSources.ContainsKey(field)) continue;
            if (field == "synchro") next.SynchroLevel = old.SynchroLevel;
            else if (field.StartsWith("console:") && old.Consoles?.TryGetValue(field[8..], out var level) == true)
            { next.Consoles ??= []; next.Consoles[field[8..]] = level; }
            next.AccountStatSources[field] = source; next.AccountStatsSource = "api+manual";
        }
    }
    public AccountSnapshot ApplyOverride(string accountId, OverrideRequest request)
    {
        lock (gate)
        {
            var current = Current(accountId) ?? throw new KeyNotFoundException("저장된 스펙이 없습니다.");
            if (current.Id != request.ExpectedSnapshotId) throw new InvalidOperationException("스펙이 갱신되었습니다. 다시 확인하세요.");
            var next = Wire.Read<AccountSnapshot>(Wire.Serialize(current)); next.Id = Guid.NewGuid().ToString("N");
            if (request.CharacterId is not null)
            {
                var equip = next.Characters.FirstOrDefault(x => x.CharacterId == request.CharacterId)?.Equipment.FirstOrDefault(x => x.Slot == request.Slot);
                var line = equip?.Lines.FirstOrDefault(x => x.LineIndex == request.LineIndex);
                if (equip is null || line?.Presence != "present" || equip.Fingerprint != request.Fingerprint || request.LockState is not ("locked" or "unlocked" or "unknown")) throw new ArgumentException("장비·옵션·잠금 선택을 확인하세요.");
                line.LockState = request.LockState; line.Source = "api+manual";
                next.ManualOverrides.RemoveAll(x => x.CharacterId == request.CharacterId && x.Slot == request.Slot && x.LineIndex == request.LineIndex);
                next.ManualOverrides.Add(new(request.CharacterId, request.Slot!, request.LineIndex!.Value, request.LockState, equip.Fingerprint, DateTimeOffset.UtcNow));
            }
            else
            {
                if (request.SynchroLevel is null && request.Consoles is null) throw new ArgumentException("보완 값을 입력하세요.");
                if (request.SynchroLevel is < 1 or > 10000 || request.Consoles?.Any(x => x.Value < 0 || x.Value > 10000 || !new[] { "1001", "1101", "1102", "1103", "1201", "1202", "1203", "1204", "1205" }.Contains(x.Key)) == true) throw new ArgumentException("계정 스탯 범위를 확인하세요.");
                if (request.SynchroLevel.HasValue && request.SynchroLevel != next.SynchroLevel)
                { next.SynchroLevel = request.SynchroLevel; next.AccountStatSources["synchro"] = "manual"; }
                if (request.Consoles is not null) foreach (var (id, level) in request.Consoles)
                {
                    if (next.Consoles?.TryGetValue(id, out var prior) == true && prior == level) continue;
                    next.Consoles ??= []; next.Consoles[id] = level; next.AccountStatSources["console:" + id] = "manual";
                }
                next.AccountStatsSource = next.AccountStatSources.Values.Contains("manual") ? "api+manual" : "api";
                if (next.SynchroLevel is not null) next.Issues.RemoveAll(x => x.Code == "unknown_synchro");
                if (next.Consoles?.Count == 9) next.Issues.RemoveAll(x => x.Code == "unknown_consoles");
            }
            return Commit(next, expectedId: current.Id);
        }
    }
    private static List<string> Changes(AccountSnapshot? previous, AccountSnapshot next)
    {
        var changes = new List<string>();
        if (previous is null) return [$"최초 수집: {next.Characters.Count}명"];
        foreach (var c in next.Characters)
        {
            var old = previous.Characters.FirstOrDefault(x => x.CharacterId == c.CharacterId);
            if (old is null) changes.Add($"{c.Name}: 신규 수집");
            else if (Wire.Serialize(c) != Wire.Serialize(old))
            {
                changes.Add($"{c.Name}: 스펙 변경");
                foreach (var e in c.Equipment)
                    if (Wire.Serialize(e) != Wire.Serialize(old.Equipment.FirstOrDefault(x => x.Slot == e.Slot))) changes.Add($"{c.Name}: {e.Slot} 장비/잠금 변경");
            }
        }
        foreach (var removed in previous.Characters.Where(x => next.Characters.All(n => n.CharacterId != x.CharacterId))) changes.Add($"{removed.Name}: 로스터에서 제외");
        if (previous.SynchroLevel != next.SynchroLevel || Wire.Serialize(previous.Consoles) != Wire.Serialize(next.Consoles)) changes.Add("계정 스탯 변경");
        if (changes.Count == 0) changes.Add("스펙 변경 없음");
        return changes;
    }
}

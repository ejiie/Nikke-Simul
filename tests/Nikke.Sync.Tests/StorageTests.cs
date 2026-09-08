using Nikke.Contracts;
using Nikke.Data;
using Nikke.Storage;

namespace Nikke.Sync.Tests;

public class StorageTests : IDisposable
{
    private readonly string root = Path.Combine(Path.GetTempPath(), "nikke-sync-tests", Guid.NewGuid().ToString("N"));
    private readonly SnapshotStore store;
    public StorageTests() { store = new(root); store.SaveGame(Fixtures.Game()); }
    private AccountSnapshot Prepared(RawEnvelope? raw = null)
    {
        raw ??= Fixtures.Raw(); var manifest = store.SaveRaw(Guid.NewGuid().ToString("N"), raw, Fixtures.Game());
        return new SnapshotNormalizer().Normalize(raw, Fixtures.Game(), "account", "synthetic-account", 83, manifest);
    }
    private AccountConnection Connected() => new() { Id = "connection", Status = "ready", AccountId = "account", OpenId = "synthetic-account", Area = 83 };
    [Fact] public void Invalid_snapshot_does_not_overwrite_current()
    {
        var first = store.Commit(Prepared()); var invalid = Prepared(); invalid.Issues.Add(new("error", "test", "", "bad"));
        Assert.Throws<InvalidOperationException>(() => store.Commit(invalid)); Assert.Equal(first.Id, store.Current("account")!.Id);
    }
    [Fact] public void Cancelled_commit_rolls_back_pointer_snapshot_and_job()
    {
        var first = store.Commit(Prepared()); var next = Prepared(); var job = store.CreateJob(Connected()).Job;
        Assert.Throws<OperationCanceledException>(() => store.Commit(next, job, cancellation: new(true)));
        Assert.Equal(first.Id, store.Current("account")!.Id); Assert.Null(store.Snapshot(next.Id)); Assert.Equal("queued", store.Job(job.Id)!.Status);
    }
    [Fact] public void Duplicate_start_returns_active_job_and_restart_recovers_it()
    {
        var a = store.CreateJob(Connected()); var b = store.CreateJob(Connected()); Assert.True(a.Created); Assert.False(b.Created); Assert.Equal(a.Job.Id, b.Job.Id);
        store.RecoverInterrupted(); Assert.Equal("interrupted", store.Job(a.Job.Id)!.Status); Assert.True(store.CreateJob(Connected()).Created);
    }
    [Fact] public void Publishing_keeps_old_snapshot_readable_and_completes_job()
    {
        var first = store.Commit(Prepared()); var job = store.CreateJob(Connected()).Job;
        var next = store.Commit(Prepared(), job); Assert.Equal(2, next.Revision); Assert.Equal(first.Id, next.PreviousId);
        Assert.Equal(first.Id, store.Snapshot(first.Id)!.Id); Assert.Equal(next.Id, store.Job(job.Id)!.SnapshotId);
        Assert.Equal("succeeded", store.Job(job.Id)!.Status);
    }
    [Fact] public void Revision_conflict_prevents_lost_manual_update()
    {
        var first = store.Commit(Prepared()); store.Commit(Prepared());
        Assert.Throws<InvalidOperationException>(() => store.ApplyOverride("account", new(first.Id, null, null, null, null, null, 450)));
    }
    [Fact] public void Lock_override_carries_only_while_equipment_fingerprint_matches()
    {
        var first = store.Commit(Prepared()); var fingerprint = first.Characters[0].Equipment[0].Fingerprint;
        store.ApplyOverride("account", new(first.Id, "101", "head", 1, "locked", fingerprint));
        var job = store.CreateJob(Connected()).Job; var same = store.Commit(Prepared(), job);
        Assert.Equal("locked", same.Characters[0].Equipment[0].Lines[0].LockState);
        var raw = Fixtures.Raw(); raw.Details[0]!["head_equip_lv"] = 4;
        var changed = store.Commit(Prepared(raw), store.CreateJob(Connected()).Job);
        Assert.Equal("unknown", changed.Characters[0].Equipment[0].Lines[0].LockState);
        Assert.Empty(changed.ManualOverrides); Assert.Contains(changed.Issues, x => x.Code == "stale_override");
    }
    [Fact] public void Raw_tampering_prevents_publication()
    {
        var snapshot = Prepared(); File.AppendAllText(Path.Combine(root, "raw", snapshot.RawManifestId, "envelope.json"), " ");
        Assert.Throws<InvalidDataException>(() => store.Commit(snapshot)); Assert.Null(store.Current("account"));
    }
    [Fact] public void Account_stores_are_isolated()
    {
        store.Commit(Prepared()); Assert.Null(store.Current("another-account"));
    }
    [Fact] public void Raw_manifest_and_game_snapshot_ids_are_immutable()
    {
        var id = Guid.NewGuid().ToString("N"); var raw = Fixtures.Raw(); store.SaveRaw(id, raw, Fixtures.Game());
        raw.Details[0]!["attractive_lv"] = 30;
        Assert.Throws<InvalidDataException>(() => store.SaveRaw(id, raw, Fixtures.Game()));
        Assert.Throws<InvalidDataException>(() => store.SaveGame(Fixtures.Game() with { Source = "changed" }));
    }
    [Fact] public void Only_actually_manual_account_fields_survive_missing_api_data()
    {
        var first = store.Commit(Prepared());
        store.ApplyOverride("account", new(first.Id, null, null, null, null, null, 450, new() { ["1001"] = 150 }));
        var next = store.Commit(Prepared(Fixtures.Raw() with { Outpost = null }), store.CreateJob(Connected()).Job);
        Assert.Equal(450, next.SynchroLevel); Assert.Equal("manual", next.AccountStatSources["synchro"]);
        Assert.Null(next.Consoles); // Unchanged API value was not silently promoted to manual.
    }
    public void Dispose()
    {
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        var expected = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "nikke-sync-tests")) + Path.DirectorySeparatorChar;
        if (!Path.GetFullPath(root).StartsWith(expected, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("Unsafe test cleanup path");
        Directory.Delete(root, true);
    }
}

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
    [Fact] public void Tactic_storage_is_separate_and_checks_snapshot_and_formation_preconditions()
    {
        var first = store.Commit(Prepared());
        var slots = new string?[] { first.Characters[0].CharacterId, null, null, null, null };
        store.SaveFormation("account", slots);
        var formationJson = Wire.Serialize(store.Formation("account"));
        var request = new SaveBurstTactic(first.Id, slots, new BurstTacticSettings());
        var saved = store.SaveBurstTactic("account", request);
        Assert.Equal(Wire.Serialize(saved), Wire.Serialize(new SnapshotStore(root).BurstTactic("account")));
        Assert.Equal(formationJson, Wire.Serialize(store.Formation("account")));
        Assert.Equal(Wire.Serialize(first), Wire.Serialize(store.Snapshot(first.Id)));
        store.SaveFormation("account", new string?[5]);
        Assert.Throws<InvalidOperationException>(() => store.SaveBurstTactic("account", request));
        Assert.Equal(slots, store.BurstTactic("account")!.FormationSlots);
        store.SaveFormation("account", slots);
        store.Commit(Prepared());
        Assert.Throws<InvalidOperationException>(() => store.SaveBurstTactic("account", request));
        store.Commit(Prepared() with { AccountId = "other" });
        Assert.Null(store.BurstTactic("other"));
    }
    [Fact] public void Failed_new_login_removes_placeholder_and_only_its_temporary_files()
    {
        var failed = new AccountConnection { Status="reauth_required", ErrorCode="network_access_denied", Message="연결 실패" };
        store.SaveConnection(failed);
        foreach (var file in new[] { $"staging/{failed.Id}.json", $"staging/{failed.Id}.json.tmp", $"sessions/{failed.Id}.bin", $"sessions/{failed.Id}.tmp", "sessions/unrelated.bin" })
        { var path=Path.Combine(root,file);Directory.CreateDirectory(Path.GetDirectoryName(path)!);File.WriteAllText(path,"synthetic"); }
        Assert.Equal(1, store.PruneFailedConnections()); Assert.Null(store.Connection(failed.Id));
        Assert.Empty(Directory.GetFiles(Path.Combine(root,"staging")));
        Assert.Equal(new[]{Path.Combine(root,"sessions","unrelated.bin")},Directory.GetFiles(Path.Combine(root,"sessions")));
        Assert.Equal("network_access_denied",store.LastConnectionFailure()!.Code);
        Assert.Equal(0,store.PruneFailedConnections());
    }
    [Fact] public void Failed_initial_collection_removes_job_and_unpublished_raw_but_keeps_saved_accounts()
    {
        var failed=new AccountConnection { Status="ready",AccountId="empty" };store.SaveConnection(failed);
        var job=store.CreateJob(failed).Job;job.Status="failed";job.FinishedAt=DateTimeOffset.UtcNow;store.SaveJob(job);
        store.SaveRaw(job.Id,Fixtures.Raw(),Fixtures.Game());
        var saved=store.Commit(Prepared());var connection=Connected() with { Status="reauth_required" };store.SaveConnection(connection);
        Assert.Equal(1,store.PruneFailedConnections());Assert.Null(store.Connection(failed.Id));Assert.Null(store.Job(job.Id));
        Assert.False(Directory.Exists(Path.Combine(root,"raw",job.Id)));
        Assert.NotNull(store.Connection(connection.Id));Assert.Equal(saved.Id,store.Current("account")!.Id);
        Assert.NotNull(store.Raw(saved.RawManifestId));
    }
    [Fact] public void Cleanup_preserves_active_login_server_selection_and_active_collection()
    {
        foreach(var status in new[]{"awaiting_login","select_account"})store.SaveConnection(new(){Status=status});
        var collecting=new AccountConnection {Status="ready",AccountId="pending"};store.SaveConnection(collecting);store.CreateJob(collecting);
        Assert.Equal(0,store.PruneFailedConnections());Assert.Equal(3,store.Connections().Count);
        store.RecoverInterrupted();Assert.Equal(2,store.PruneFailedConnections());
        Assert.Equal("select_account",Assert.Single(store.Connections()).Status);
    }
    [Fact] public void Malformed_connection_id_cannot_delete_files_outside_attempt_directories()
    {
        var target=Path.Combine(root,"keep.bin");File.WriteAllText(target,"keep");
        store.SaveConnection(new(){Id="../keep",Status="reauth_required"});
        Assert.Equal(1,store.PruneFailedConnections());Assert.Equal("keep",File.ReadAllText(target));
    }
    [Fact] public void Formation_preserves_slots_across_restart_and_snapshot_updates_and_isolates_accounts()
    {
        var first = store.Commit(Prepared());
        Assert.Equal(new string?[5], store.Formation("account").Slots);
        var slots = new string?[] { null, first.Characters[0].CharacterId, null, null, null };
        store.SaveFormation("account", slots);
        store.Commit(Prepared());
        Assert.Equal(slots, new SnapshotStore(root).Formation("account").Slots);
        Assert.NotNull(store.Formation("account").SavedAt);
        var other = Prepared() with { AccountId = "other" }; store.Commit(other);
        Assert.Equal(new string?[5], store.Formation("other").Slots);
        store.SaveFormation("account", new string?[5]);
        Assert.Equal(new string?[5], new SnapshotStore(root).Formation("account").Slots);
        Assert.Equal(Wire.Serialize(first.Characters), Wire.Serialize(store.Snapshot(first.Id)!.Characters));
    }
    [Fact] public void Invalid_formation_does_not_overwrite_saved_team()
    {
        var first = store.Commit(Prepared()); var id = first.Characters[0].CharacterId;
        var slots = new string?[] { id, null, null, null, null }; store.SaveFormation("account", slots);
        foreach (var invalid in new string?[]?[] { null, [], new string?[6], [id,id,null,null,null], ["unknown",null,null,null,null], ["",null,null,null,null] })
            Assert.Throws<ArgumentException>(() => store.SaveFormation("account", invalid));
        Assert.Throws<KeyNotFoundException>(() => store.SaveFormation("missing", slots));
        Assert.Equal(slots, store.Formation("account").Slots);
    }
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
    [Fact] public void Cube_level_is_shared_and_revisioned_without_changing_source_snapshot()
    {
        var prepared=Prepared();
        prepared.Characters.Add(prepared.Characters[0] with {CharacterId="102"});
        var first=store.Commit(prepared);
        var next=store.ApplyOverride("account",new(first.Id,null,null,null,null,null,CubeLevels:new(){["5"]=10}));
        Assert.All(next.Characters,c=>Assert.Equal(10,c.CubeLevel));
        Assert.Equal(10,next.CubeLevels["5"]);
        Assert.All(store.Snapshot(first.Id)!.Characters,c=>Assert.Equal(7,c.CubeLevel));
        Assert.NotEqual(first.ContentHash,next.ContentHash);
        Assert.Equal("manual",next.AccountStatSources["cube:5"]);
        Assert.Throws<ArgumentException>(()=>store.ApplyOverride("account",new(next.Id,null,null,null,null,null,CubeLevels:new(){["5"]=16})));
    }
    [Fact] public void Fresh_cube_observation_replaces_manual_level_on_sync()
    {
        var first=store.Commit(Prepared());
        store.ApplyOverride("account",new(first.Id,null,null,null,null,null,CubeLevels:new(){["5"]=10}));
        var next=store.Commit(Prepared(),store.CreateJob(Connected()).Job);
        Assert.Equal(7,next.CubeLevels["5"]);Assert.Equal(7,next.Characters[0].CubeLevel);
        Assert.Equal("api",next.AccountStatSources["cube:5"]);
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
    [Fact] public void Character_edit_publishes_a_revision_and_sync_restores_observed_build()
    {
        var first=store.Commit(Prepared());
        var edited=CharacterEditService.Preview(first,"101",new(first.Id,first.Characters[0] with {Level=500}),CharacterEditTests.Catalog());
        edited.Id=Guid.NewGuid().ToString("N");
        var next=store.Commit(edited,expectedId:first.Id);
        Assert.Equal(first.Id,next.PreviousId);Assert.Equal(500,next.Characters[0].Level);
        Assert.Equal("manual",next.Characters[0].BuildSource);
        Assert.Equal(400,store.Snapshot(first.Id)!.Characters[0].Level);
        Assert.Equal(first.RawManifestId,next.RawManifestId);
        Assert.Throws<InvalidOperationException>(()=>store.Commit(Prepared(),expectedId:first.Id));
        var synced=store.Commit(Prepared(),store.CreateJob(Connected()).Job);
        Assert.Equal(400,synced.Characters[0].Level);Assert.Equal("api",synced.Characters[0].BuildSource);
        Assert.Equal(500,store.Snapshot(next.Id)!.Characters[0].Level);
    }
    public void Dispose()
    {
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        var expected = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "nikke-sync-tests")) + Path.DirectorySeparatorChar;
        if (!Path.GetFullPath(root).StartsWith(expected, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("Unsafe test cleanup path");
        Directory.Delete(root, true);
    }
}

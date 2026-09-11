using Nikke.Contracts;

namespace Nikke.Storage;

public sealed partial class SnapshotStore
{
    public SavedBurstTactic? BurstTactic(string accountId)
    {
        lock (gate)
        {
            _ = Current(accountId) ?? throw new KeyNotFoundException();
            return Get<SavedBurstTactic>("solo_burst_tactics", accountId);
        }
    }

    // API validates stage semantics against pinned runtime data before this atomic precondition check.
    public SavedBurstTactic SaveBurstTactic(string accountId, SaveBurstTactic request)
    {
        lock (gate)
        {
            var current = Current(accountId) ?? throw new KeyNotFoundException();
            var slots = Formation(accountId).Slots;
            if (request.SnapshotId != current.Id || request.FormationSlots is null || !slots.SequenceEqual(request.FormationSlots))
                throw new InvalidOperationException("Snapshot or formation changed; reload before saving the tactic.");
            var saved = new SavedBurstTactic(accountId, current.Id, slots.ToArray(), request.Tactic, DateTimeOffset.UtcNow);
            using var db = Open();
            Execute(db, null, "INSERT INTO solo_burst_tactics VALUES($id,$json) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                ("$id", accountId), ("$json", Wire.Serialize(saved)));
            return saved;
        }
    }
}

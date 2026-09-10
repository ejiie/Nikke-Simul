namespace Nikke.Contracts;

// Slot positions are stable, including empty slots. Independent of spec snapshots.
public sealed record Formation(string AccountId, string?[] Slots, DateTimeOffset? SavedAt = null);
public sealed record SaveFormation(string?[]? Slots);

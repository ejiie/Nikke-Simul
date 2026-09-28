using Nikke.Contracts;

namespace Nikke.Data;

// Invalid server-side catalog state, not a defaultable member value or a client input error.
public sealed class CombatProfileException(string field, string reason, string? characterId = null)
    : InvalidOperationException($"combat_profile_invalid: {field}: {reason}")
{
    public CombatProfileError Error { get; } = new("combat_profile_invalid",
        $"combat_profile_invalid: {field}: {reason}", characterId, field, reason);
}

using Nikke.Contracts;

namespace Nikke.Data;

public static class BurstTacticValidation
{
    // Malformed candidates are never saved. Missing stages may be saved as a draft.
    public static IReadOnlyList<string> Validate(BurstTacticSettings? tactic, IReadOnlyDictionary<string, int> formationStages)
    {
        if (tactic is null) return []; // Legacy semantics, including incomplete formations.
        if (tactic.SchemaVersion != 1 || tactic.UnavailablePolicy is not ("next_ready" or "wait_preferred"))
            throw new ArgumentException("Unsupported burst tactic version or unavailable policy.");
        var lists = new[] { tactic.AllowedCharacterIds, tactic.Stage1Priority, tactic.Stage2Priority, tactic.Stage3Priority, tactic.Burst3Rotation };
        if (lists.Any(list => list is null || list.Length > 5 || list.Any(string.IsNullOrWhiteSpace) || list.Distinct(StringComparer.Ordinal).Count() != list.Length))
            throw new ArgumentException("Burst tactic lists must contain distinct character IDs.");
        if (tactic.AllowedCharacterIds.Any(id => !formationStages.ContainsKey(id) || formationStages[id] is < 1 or > 3))
            throw new ArgumentException("Burst tactic candidate is absent from the formation or unsupported.");
        var issues = new List<string>();
        for (int step = 1; step <= 3; step++)
        {
            var expected = tactic.AllowedCharacterIds.Where(id => formationStages[id] == step).ToHashSet(StringComparer.Ordinal);
            if (!expected.SetEquals(lists[step])) throw new ArgumentException($"Stage {step} priority must be the exact permutation of allowed candidates.");
            if (expected.Count == 0) issues.Add($"missing_stage_{step}");
        }
        if (tactic.Burst3Rotation.Any(id => !tactic.Stage3Priority.Contains(id, StringComparer.Ordinal))
            || tactic.Stage3Priority.Length > 0 && tactic.Burst3Rotation.Length == 0
            || tactic.FirstBurst3CharacterId is not null && !tactic.Burst3Rotation.Contains(tactic.FirstBurst3CharacterId, StringComparer.Ordinal))
            throw new ArgumentException("Burst III rotation and first caster must be allowed stage III candidates.");
        return issues;
    }
}

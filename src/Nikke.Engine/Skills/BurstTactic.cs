namespace Nikke.Engine.Skills;

public sealed record BurstTactic
{
    public int SchemaVersion { get; init; } = 1;
    public IReadOnlyList<string> AllowedCharacterIds { get; init; } = [];
    public IReadOnlyList<string> Stage1Priority { get; init; } = [];
    public IReadOnlyList<string> Stage2Priority { get; init; } = [];
    public IReadOnlyList<string> Stage3Priority { get; init; } = [];
    public IReadOnlyList<string> Burst3Rotation { get; init; } = [];
    public string FirstBurst3CharacterId { get; init; }
    public string UnavailablePolicy { get; init; } = "next_ready";

    public IReadOnlyList<string> Priority(int step) => step switch
    {
        1 => Stage1Priority, 2 => Stage2Priority, 3 => Stage3Priority,
        _ => throw new ArgumentOutOfRangeException(nameof(step))
    };

    public void ValidateForExecution(IReadOnlyList<SkillReplayMember> members)
    {
        var lists = new[] { AllowedCharacterIds, Stage1Priority, Stage2Priority, Stage3Priority, Burst3Rotation };
        if (SchemaVersion != 1 || UnavailablePolicy is not ("next_ready" or "wait_preferred")
            || lists.Any(xs => xs is null || xs.Count is < 1 or > 5
                || xs.Any(string.IsNullOrWhiteSpace) || xs.Distinct().Count() != xs.Count))
            throw new ArgumentException("Invalid tactic version, policy or candidate lists.");
        var byId = members.ToDictionary(m => m.Weapon.CharacterId);
        if (AllowedCharacterIds.Any(id => !byId.TryGetValue(id, out var m)
                || m.Skills.BurstConnection is null || m.Skills.Slots["burst"].Skill is null))
            throw new ArgumentException("Tactic candidates must be castable members of the current formation.");
        for (int step = 1; step <= 3; step++)
        {
            var expected = AllowedCharacterIds.Where(id => byId[id].Skills.BurstConnection.Step == step).ToHashSet();
            if (!expected.SetEquals(Priority(step)))
                throw new ArgumentException("Each stage priority must contain exactly its allowed candidates.");
        }
        if (Burst3Rotation.Any(id => !Stage3Priority.Contains(id))
            || FirstBurst3CharacterId is not null && !Burst3Rotation.Contains(FirstBurst3CharacterId))
            throw new ArgumentException("Rotation and first caster must belong to the allowed third-stage candidates.");
    }
}

namespace Nikke.Engine;

public static class DefenseMode
{
    public const string Fixed = "fixed";
    public const string TeamDamageThreshold = "team_damage_threshold";
    public const double InitialDefense = 30925;
    public const double SwitchedDefense = 31784;
    public const double DamageThreshold = 2_000_000_000;

    internal static void Validate(string mode)
    {
        if (mode is not (Fixed or TeamDamageThreshold))
            throw new ArgumentException("defense_mode_invalid");
    }
}

// The crossing hit still uses PreviousDefense. NewDefense applies to the next resolved hit,
// including another member, pellet or triggered skill in the same frame (provisional boundary).
public sealed record DefenseSwitch(int Frame, long HitTraceId, long HitOrdinal, string CharacterId,
    string Effect, double CumulativeDamage, double PreviousDefense, double NewDefense);
public sealed record DefenseRunSummary(string Mode, double InitialDefense, double FinalDefense,
    double? DamageThreshold, DefenseSwitch SwitchAfterHit);

internal sealed class BattleDefense
{
    private readonly string mode;
    private readonly double initial;
    private double cumulative;
    private long hits;
    public double Current { get; private set; }
    private DefenseSwitch transition;

    public BattleDefense(WeaponReplayConditions conditions)
    {
        mode = conditions.DefenseMode;
        initial = Current = mode == DefenseMode.Fixed ? conditions.EnemyDefense : DefenseMode.InitialDefense;
    }

    public DefenseSwitch Commit(double damage, int frame, long hitTraceId, string characterId, string effect)
    {
        if (mode == DefenseMode.Fixed || transition is not null) return null;
        cumulative += damage;
        hits++;
        if (cumulative <= DefenseMode.DamageThreshold) return null;
        transition = new(frame, hitTraceId, hits, characterId, effect, cumulative, Current, DefenseMode.SwitchedDefense);
        Current = DefenseMode.SwitchedDefense;
        return transition;
    }

    public DefenseRunSummary Summary() => new(mode, initial, Current,
        mode == DefenseMode.Fixed ? null : DefenseMode.DamageThreshold, transition);
}

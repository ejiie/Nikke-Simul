using Nikke.Simulator.Core.Stats;
namespace Nikke.Engine.Skills;

public sealed record TeamBurstOptions
{
    public BurstTactic Tactic { get; init; }
    public string GaugeModel { get; init; } = "source_full_charge_v2";
    public bool StageTarget { get; init; } = true;
    // Explicit timing candidates inherited from the user's legacy T02 observations.
    public int StageDelayMinFrames { get; init; } = 1;
    public int StageDelayMaxFrames { get; init; } = 10;
    public int FullBurstEntryDelayFrames { get; init; } = 28;
    public IReadOnlyList<string> Burst3Rotation { get; init; } = [];
    public string UnavailablePolicy { get; init; } = "next_ready";
    public int TimelineLimit { get; init; } = 20000;
}
public sealed record TeamBurstTrace(int Frame, string Kind, int Step, long GaugeRaw,
    string CharacterId = null, long? CauseTraceId = null, long RequestedRaw = 0, long AppliedRaw = 0,
    int? ReadyAtFrame = null, string Reason = null);
public sealed record TeamBurstWindow(int Cycle, string Caster, int StartFrame, int? EndFrame,
    int PlannedEndFrame, IReadOnlyDictionary<string, double> MemberDamage);
public sealed record TeamBurstSummary(string RulesVersion, string GaugeFormulaStatus, bool GameVerified,
    TeamBurstOptions Options, GaugeSourceConstants SourceConstants, int Step, long GaugeRaw,
    long TimelineEventCount, bool TimelineTruncated, IReadOnlyList<TeamBurstTrace> Timeline,
    IReadOnlyDictionary<string, long> GeneratedGaugeByMember, IReadOnlyDictionary<string, long> AcceptedGaugeByMember,
    IReadOnlyList<TeamBurstWindow> FullBursts, int FullBurstFrames, string WaitingReason);

// Newly authored controller. Mathematical reference and unapplied raw fields: docs/p04-team-burst.ko.md.
// It consumes execution events, never saved damage logs. No fixed charging-time shortcut.
public sealed class TeamBurstController : ICombatEventSink, ISkillBattleDriver
{
    public const string Version = "p04.team.2";
    private readonly IReadOnlyList<SkillReplayMember> members;
    private readonly Dictionary<string, SkillReplayMember> byId;
    private readonly TeamBurstOptions options;
    private readonly GaugeSourceConstants constants;
    private readonly IRandomSource random;
    private readonly ICombatEventSink observer;
    private readonly List<TeamBurstTrace> timeline = [];
    private readonly List<TeamBurstWindow> windows = [];
    private readonly Dictionary<string, long> generated = [], accepted = [];
    private long gauge, eventCount;
    private int step, readyFrame, stageDeadline = int.MaxValue, duration, frame;
    private string caster, waitingReason;
    private long? castTrace;
    private bool fullBurst;
    private int rotationIndex;

    public TeamBurstController(IReadOnlyList<SkillReplayMember> members, SkillGraph graph,
        SkillReplayConditions conditions, IRandomSource random, ICombatEventSink observer = null)
    {
        this.members = members; byId = members.ToDictionary(m => m.Weapon.CharacterId);
        options = conditions.AutoBurst; constants = graph.GaugeConstants;
        this.random = random; this.observer = observer;
        if (options is null || constants is null || constants.CapacityRaw <= 0 || constants.CapacityRaw > 1_000_000_000
            || options.GaugeModel != "source_full_charge_v2" || options.StageDelayMinFrames < 1
            || options.StageDelayMaxFrames < options.StageDelayMinFrames || options.StageDelayMaxFrames > 600
            || options.FullBurstEntryDelayFrames is < 1 or > 600 || options.TimelineLimit is < 0 or > 20000
            || options.UnavailablePolicy is not ("next_ready" or "wait_preferred")
            || options.Burst3Rotation is null || options.Burst3Rotation.Count > 5
            || options.Burst3Rotation.Distinct().Count() != options.Burst3Rotation.Count)
            throw new ArgumentException("자동 버스트 모델·지연·우선순위·원천 게이지 상수를 확인하세요.");
        foreach (var member in members)
        {
            var p = member.Skills.BurstConnection;
            if (p is null || p.Step is < 1 or > 3 || p.NextStep != p.Step + 1
                || p.EnergyPerShotRaw < 0 || p.TargetEnergyPerShotRaw < 0
                || p.EnergyPerShotRaw > 1_000_000_000 || p.TargetEnergyPerShotRaw > 1_000_000_000)
                throw new ArgumentException("이번 자동 사이클은 원천 프로파일이 있는 I→II→III 대상만 지원합니다.");
            if (member.Weapon.Weapon.isChargeWeapon && p.FullChargeEnergyRaw is <= 0 or > 1_000_000_000)
                throw new ArgumentException("차지 무기의 full_charge_burst_energy 원천 배율이 필요합니다.");
            generated[member.Weapon.CharacterId] = accepted[member.Weapon.CharacterId] = 0;
        }
        if (options.Burst3Rotation.Any(id => !byId.TryGetValue(id, out var m) || m.Skills.BurstConnection.Step != 3))
            throw new ArgumentException("버스트 III 순서는 편성된 III 니케로 지정하세요.");
        if (options.Tactic is { } tactic)
        {
            if (options.Burst3Rotation.Count != 0 || options.UnavailablePolicy != "next_ready")
                throw new ArgumentException("Do not mix legacy selection options and a versioned tactic.");
            tactic.ValidateForExecution(members);
            rotationIndex = tactic.FirstBurst3CharacterId is null ? 0
                : tactic.Burst3Rotation.ToList().IndexOf(tactic.FirstBurst3CharacterId);
        }
        Record("charging");
    }
    private void Record(string kind, string id = null, long? cause = null, long requested = 0,
        long applied = 0, int? ready = null, string reason = null)
    {
        eventCount++;
        if (timeline.Count < options.TimelineLimit)
            timeline.Add(new(frame, kind, step, gauge, id, cause, requested, applied, ready, reason));
    }
    private int StageDelay() => options.StageDelayMinFrames == options.StageDelayMaxFrames
        ? options.StageDelayMinFrames
        : options.StageDelayMinFrames + (int)(random.NextDouble() * (options.StageDelayMaxFrames - options.StageDelayMinFrames + 1));
    private void Wait(string reason)
    {
        if (waitingReason == reason) return;
        waitingReason = reason; Record("waiting", reason: reason);
    }
    public void OnEvent(CombatEvent e)
    {
        frame = e.Frame;
        if (e.Kind == CombatEventKind.FullBurstEntered)
        {
            fullBurst = true; waitingReason = null;
            windows.Add(new(windows.Count + 1, caster, frame, null, e.FullBurst.EndFrame!.Value,
                members.ToDictionary(m => m.Weapon.CharacterId, _ => 0d)));
            Record("full_burst_entered", caster, castTrace);
        }
        else if (e.Kind == CombatEventKind.FullBurstExited)
        {
            fullBurst = false;
            windows[^1] = windows[^1] with { EndFrame = frame };
            step = 0; gauge = 0; stageDeadline = int.MaxValue; waitingReason = null;
            Record("full_burst_exited", caster, castTrace);
        }
        if (fullBurst && e.Hit is { } damage)
            ((Dictionary<string, double>)windows[^1].MemberDamage)[e.Source] += damage.Damage;
        if (step == 0 && e.Kind == CombatEventKind.NormalHit && e.Hit is { } hit)
        {
            var member = byId[e.Source]; var p = member.Skills.BurstConnection;
            if (hit.WeaponShotId != p.ShotId)
                throw new InvalidOperationException("충전 구간에 미확인 교체 무기가 있습니다. 기본 무기 충전값으로 대체하지 않습니다.");
            // Each event already represents one pellet and one target.
            long basis = options.StageTarget ? p.TargetEnergyPerShotRaw : p.EnergyPerShotRaw;
            // User-confirmed 2026-09-11: full-charge field is the total multiplier in 1/10000 units.
            // Applies to automatic and manual full-charge hits alike; no invented partial-charge interpolation.
            long multiplier = member.Weapon.Weapon.isChargeWeapon && hit.FullCharge ? p.FullChargeEnergyRaw : 10000;
            long amount = (long)Math.Round((decimal)basis * multiplier / 10000m, MidpointRounding.AwayFromZero);
            long applied = Math.Min(constants.CapacityRaw - gauge, amount);
            gauge += applied; generated[e.Source] = checked(generated[e.Source] + amount);
            accepted[e.Source] = checked(accepted[e.Source] + applied);
            Record("gauge", e.Source, e.TraceId, amount, applied);
            if (gauge == constants.CapacityRaw)
            {
                step = 1; gauge = 0; readyFrame = frame + StageDelay();
                Record("gauge_ready", ready: readyFrame);
            }
        }
        observer?.OnEvent(e);
    }
    public void OnPhase(ISkillBattleControl battle, BattlePhase phase)
    {
        frame = battle.Frame;
        if (phase == BattlePhase.FullBurstExit && step is 2 or 3 && frame >= stageDeadline)
        {
            Record("stage_expired", reason: waitingReason);
            step = 0; gauge = 0; stageDeadline = int.MaxValue; waitingReason = null;
        }
        if (phase == BattlePhase.FullBurstEntry && step == 4 && !fullBurst && frame >= readyFrame)
        {
            if (battle.TryEnterFullBurst(duration, castTrace) != BattleCommandStatus.Applied)
                throw new InvalidOperationException("풀버스트 진입 상태가 일치하지 않습니다.");
        }
        if (phase != BattlePhase.CastSkills || step is < 1 or > 3 || frame < readyFrame) return;
        var eligible = options.Tactic?.Priority(step).ToList() ?? members.Where(m => m.Skills.BurstConnection.Step == step)
            .Select(m => m.Weapon.CharacterId).ToList();
        if (eligible.Count == 0) { Wait("missing_stage_" + step); return; }
        var rotation = options.Tactic?.Burst3Rotation ?? options.Burst3Rotation;
        if (step == 3 && rotation.Count > 0)
        {
            string preferred = rotation[(options.Tactic is null ? windows.Count : rotationIndex) % rotation.Count];
            eligible.Remove(preferred); eligible.Insert(0, preferred);
        }
        string chosen = (options.Tactic?.UnavailablePolicy ?? options.UnavailablePolicy) == "wait_preferred"
            ? (battle.GetCooldown(eligible[0]).IsReady ? eligible[0] : null)
            : eligible.FirstOrDefault(id => battle.GetCooldown(id).IsReady);
        if (chosen is null) { Wait("cooldown_stage_" + step); return; }
        var result = battle.TryCast(chosen);
        if (result.Status != BattleCommandStatus.Applied)
            throw new InvalidOperationException("버스트 준비 조회와 시전 상태가 일치하지 않습니다.");
        waitingReason = null; caster = chosen; castTrace = result.CastTraceId;
        Record("burst_cast", chosen, castTrace, ready: battle.GetCooldown(chosen).ReadyAtFrame);
        if (step == 3 && options.Tactic is not null)
            rotationIndex = (rotationIndex + 1) % rotation.Count;
        var profile = battle.GetBurstProfile(chosen);
        step = profile.NextStep;
        int applicationDelay = SkillUnits.ReadyFrame((long)profile.ApplyDelayCs * SkillUnits.TicksPerCs);
        readyFrame = frame + (step == 4 ? Math.Max(applicationDelay, options.FullBurstEntryDelayFrames)
            : Math.Max(applicationDelay, StageDelay()));
        duration = result.DurationRequest?.DurationFrames ?? throw new InvalidOperationException("풀버스트 지속시간이 없습니다.");
        stageDeadline = step == 4 ? int.MaxValue : frame + duration;
        Record("stage_entered", chosen, castTrace, ready: readyFrame);
    }
    public TeamBurstSummary Summary(int lastFrame) => new(Version, "reference_candidate", false, options, constants,
        step, gauge, eventCount, eventCount > timeline.Count, timeline.ToArray(),
        new Dictionary<string, long>(generated), new Dictionary<string, long>(accepted),
        windows.Select(w => w with { MemberDamage = new Dictionary<string, double>(w.MemberDamage) }).ToArray(),
        windows.Sum(w => Math.Max(0, Math.Min(w.EndFrame ?? w.PlannedEndFrame, lastFrame + 1) - w.StartFrame)), waitingReason);
}

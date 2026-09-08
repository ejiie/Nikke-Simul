using Nikke.Core.Combat;
using Nikke.Core.Stats;
using Nikke.Simulator.Core.Data.Dto;
using Nikke.Simulator.Core.Stats;
using Nikke.Simulator.Engine;

namespace Nikke.Engine;

public record FrameWindow(int StartFrame, int EndFrame)
{
    public bool Contains(int frame) => StartFrame <= frame && frame < EndFrame;
}
public record AttackBuffWindow(string CharacterId, StatRateBuff Buff, int StartFrame, int EndFrame);
public sealed record WeaponReplayConditions
{
    public int DurationFrames { get; init; } = 10800;
    public string PelletCoefficientPolicy { get; init; } = ""; // explicit for SG: per_trigger / per_pellet
    public string CritMode { get; init; } = "off"; // controlled measurement, or sample
    public bool Core { get; init; }
    public bool ProperDistance { get; init; }
    public bool ElementAdvantage { get; init; }
    public double EnemyDefense { get; init; }
    public string TargetLabel { get; init; } = "fixed_target";
    public string Notes { get; init; } = "";
    public string ManualCharacterId { get; init; } = "";
    public string ManualStyle { get; init; } = "full_charge";
    public IReadOnlyList<FrameWindow> FullBurstWindows { get; init; } = [];
    public IReadOnlyList<AttackBuffWindow> AttackBuffWindows { get; init; } = [];
    public bool Trace { get; init; }
    public int TraceLimit { get; init; } = 2000;
}
public record WeaponReplayMember(string CharacterId, WeaponDto Weapon, HitContext Hit, StatBuffSet Buffs);
public record ReplayEvent(long Id, long? ParentId, int Frame, string Kind, string CharacterId, string EffectId,
    int Ammo, bool FullCharge = false, bool Crit = false, bool Core = false, bool FullBurst = false,
    double EffectiveAttack = 0, IReadOnlyDictionary<string, double> Damage = null,
    IReadOnlyList<StatRateBuff> AttackBuffs = null);
public record WeaponMemberResult(string CharacterId, int Shots, int Hits, int CriticalHits, int FullChargeShots,
    int ReloadCompletions, int RemainingAmmo, IReadOnlyDictionary<string, double> Damage,
    IReadOnlyDictionary<string, IReadOnlyDictionary<string, double>> Effects);
public record WeaponReplayResult(string RulesVersion, string Status, string SkillExecutionStatus,
    WeaponReplayConditions Conditions, IReadOnlyList<WeaponMemberResult> Members,
    IReadOnlyDictionary<string, double> TotalDamage, IReadOnlyList<ReplayEvent> Events,
    long EventCount, bool TraceTruncated, IReadOnlyList<string> Limitations);

// A weapon-only reference replay. Prescribed condition windows are never labelled automatic skills or burst cycles.
public static class WeaponReplay
{
    public const string Version = "p03.weapon-reference.1";
    private static readonly string[] Policies = ["legacy_term_floor", "final_round_even", "nested_floor"];
    private static Dictionary<string, double> ZeroDamage() => Policies.ToDictionary(p => p, _ => 0d);
    private sealed class MemberState
    {
        public WeaponReplayMember Input;
        public FiringModel Firing;
        public int Shots, Hits, CriticalHits, FullChargeShots, ReloadCompletions;
        public Dictionary<string, double> Damage = ZeroDamage();
    }

    public static WeaponReplayResult Run(IReadOnlyList<WeaponReplayMember> members, WeaponReplayConditions c,
        IRandomSource random = null)
    {
        Validate(members, c);
        random ??= SystemRandomSource.Instance;
        var states = members.Select(m => new MemberState { Input = m,
            Firing = new(new WeaponProfile(m.Weapon), checked((int)StatBuffCalculator.Apply(m.Weapon.maxAmmo, m.Buffs.Ammo)),
                new FiringControl { Mode = m.CharacterId == c.ManualCharacterId ? ControlMode.Manual : ControlMode.Auto,
                    Style = c.ManualStyle == "tap" ? FireStyle.Tap : FireStyle.FullCharge }, random,
                Rates(m.Buffs.ReloadSpeed), Rates(m.Buffs.ChargeSpeed)) }).ToArray();
        var events = new List<ReplayEvent>(); long eventCount = 0;
        long Emit(int frame, string kind, string member, int ammo, long? parent = null, bool fullCharge = false,
            bool crit = false, bool core = false, bool burst = false, double atk = 0,
            IReadOnlyDictionary<string, double> damage = null, IReadOnlyList<StatRateBuff> buffs = null)
        {
            long id = ++eventCount;
            if (c.Trace && events.Count < c.TraceLimit)
                events.Add(new(id, parent, frame, kind, member, kind == "hit" ? "normal_attack" : "", ammo,
                    fullCharge, crit, core, burst, atk, damage, buffs));
            return id;
        }
        // Frame 1 is the first completed 1/60-second step, matching the imported model.
        for (int frame = 1; frame <= c.DurationFrames; frame++)
        {
            foreach (var window in c.FullBurstWindows.Where(w => w.EndFrame == frame)) Emit(frame, "prescribed_full_burst_end", "team", 0);
            foreach (var window in c.AttackBuffWindows.Where(w => w.EndFrame == frame)) Emit(frame, "prescribed_buff_end", window.CharacterId, 0, buffs: [window.Buff]);
            foreach (var window in c.FullBurstWindows.Where(w => w.StartFrame == frame)) Emit(frame, "prescribed_full_burst_start", "team", 0);
            foreach (var window in c.AttackBuffWindows.Where(w => w.StartFrame == frame)) Emit(frame, "prescribed_buff_start", window.CharacterId, 0, buffs: [window.Buff]);
            foreach (var s in states)
            {
                int beforeAmmo = s.Firing.CurrentAmmo;
                var step = s.Firing.AdvanceFrame();
                if (step.CurrentAmmo > beforeAmmo)
                {
                    s.ReloadCompletions++;
                    Emit(frame, "reload_completed", s.Input.CharacterId, step.CurrentAmmo);
                }
                if (!step.Fired) continue;
                s.Shots++; if (step.IsFullCharge) s.FullChargeShots++;
                long shotId = Emit(frame, "shot", s.Input.CharacterId, step.CurrentAmmo, fullCharge: step.IsFullCharge);
                var scheduled = c.AttackBuffWindows.Where(w => w.CharacterId == s.Input.CharacterId && w.StartFrame <= frame && frame < w.EndFrame)
                    .Select(w => w.Buff).ToArray();
                bool burst = c.FullBurstWindows.Any(w => w.Contains(frame));
                int pellets = checked(step.PelletsPerShot * s.Input.Weapon.muzzleCount);
                double coefficient = s.Input.Hit.Coefficient / (s.Input.Weapon.weaponType == "SG" && c.PelletCoefficientPolicy == "per_trigger" ? pellets : 1);
                double critChance = Math.Clamp(.15 + Rates(s.Input.Buffs.CriticalChance).Sum(), 0, 1);
                for (int pellet = 0; pellet < pellets; pellet++)
                {
                    bool crit = c.CritMode == "on" || c.CritMode == "sample" && CritSampler.RollCrit(random, critChance);
                    var hit = s.Input.Hit with { RuntimeAttackBuffs = s.Input.Hit.RuntimeAttackBuffs.Concat(scheduled).ToArray(),
                        Coefficient = coefficient, FullCharge = step.IsFullCharge, Crit = crit, Core = c.Core,
                        FullBurst = burst, ProperDistance = c.ProperDistance, ElementAdvantage = c.ElementAdvantage, Defense = c.EnemyDefense };
                    var comparison = HitCalculator.Compare(hit);
                    var damage = comparison.Candidates.ToDictionary(d => d.Policy, d => d.Damage);
                    s.Hits++; if (crit) s.CriticalHits++;
                    foreach (var d in damage) s.Damage[d.Key] += d.Value;
                    Emit(frame, "hit", s.Input.CharacterId, step.CurrentAmmo, shotId, step.IsFullCharge, crit, c.Core,
                        burst, comparison.EffectiveAttack, damage, hit.AttackBuffs.Concat(hit.RuntimeAttackBuffs).ToArray());
                }
            }
        }
        var results = states.Select(s => new WeaponMemberResult(s.Input.CharacterId, s.Shots, s.Hits, s.CriticalHits,
            s.FullChargeShots, s.ReloadCompletions, s.Firing.CurrentAmmo, s.Damage,
            new Dictionary<string, IReadOnlyDictionary<string, double>> { ["normal_attack"] = s.Damage })).ToArray();
        var total = Policies.ToDictionary(p => p, p => results.Sum(r => r.Damage[p]));
        return new(Version, "weapon_reference_only", "not_connected", c, results, total, events, eventCount,
            c.Trace && eventCount > events.Count,
            ["Character skills, conditional cubes and favorites are not executed; this is not a full team simulation.",
             "Full burst and attack buff windows are prescribed measurement conditions, not generated by team gauge or skills.",
             "Every pellet hits one fixed target. Core/distance/element flags are prescribed; geometry and piercing extra targets are not modelled.",
             "Legacy timing is a reference candidate: SG clip refill/shot coefficient, spot_last scope and MG decay units need measurement.",
             "Hit quantization is provisional. Do not mix these replays into raid recommendation samples."]);
    }

    private static double[] Rates(IReadOnlyList<StatRateBuff> buffs) => buffs.SelectMany(b => Enumerable.Repeat(b.Rate, b.Stacks)).ToArray();
    internal static void Validate(IReadOnlyList<WeaponReplayMember> members, WeaponReplayConditions c)
    {
        if (c is null || members is null || members.Count is < 1 or > 5 || members.Any(m => m is null)
            || members.Select(m => m.CharacterId).Distinct().Count() != members.Count || c.DurationFrames is < 1 or > 10800
            || c.CritMode is not ("off" or "on" or "sample") || c.ManualStyle is not ("full_charge" or "tap")
            || c.TraceLimit is < 1 or > 20000 || !double.IsFinite(c.EnemyDefense) || c.EnemyDefense is < 0 or > 1e12
            || string.IsNullOrWhiteSpace(c.TargetLabel) || c.TargetLabel.Length > 300 || c.Notes is null || c.Notes.Length > 4000
            || c.FullBurstWindows is null || c.AttackBuffWindows is null || c.FullBurstWindows.Count > 100 || c.AttackBuffWindows.Count > 200)
            throw new ArgumentException("평타 시간축 검산 입력을 확인하세요.");
        if (c.ManualCharacterId != "" && !members.Any(m => m.CharacterId == c.ManualCharacterId))
            throw new ArgumentException("수동 조작 캐릭터가 편성에 없습니다.");
        foreach (var m in members)
        {
            var w = m.Weapon;
            if (m.Hit is null || m.Buffs is null || w is null || string.IsNullOrWhiteSpace(m.CharacterId)
                || w.weaponType is not ("SMG" or "AR" or "SG" or "SR" or "MG") || w.fireType != "Instant"
                || w.maxAmmo is < 1 or > 100000 || w.shotCount is < 1 or > 20 || w.muzzleCount is < 1 or > 2
                || w.fireRate <= 0 || !double.IsFinite(w.fireRate) || w.fireRate > 1000
                || !double.IsFinite(w.endFireRate) || w.endFireRate < w.fireRate || w.endFireRate > 1000
                || !double.IsFinite(w.fireRateRampPerShot) || w.fireRateRampPerShot is < 0 or > 1000
                || !double.IsFinite(w.fireRateResetTimeSec) || w.fireRateResetTimeSec is < 0 or > 1000
                || !double.IsFinite(w.reloadTimeSec) || w.reloadTimeSec is < 0 or > 1000
                || !double.IsFinite(w.chargeTimeSec) || w.chargeTimeSec is < 0 or > 1000
                || !double.IsFinite(w.spotFirstDelaySec) || w.spotFirstDelaySec is < 0 or > 1000
                || !double.IsFinite(w.spotLastDelaySec) || w.spotLastDelaySec is < 0 or > 1000
                || !double.IsFinite(w.reloadBulletRate) || w.reloadBulletRate is <= 0 or > 1)
                throw new ArgumentException("이 검산에서 지원하는 무기 입력이 아닙니다.");
            if (w.weaponType == "SG" && c.PelletCoefficientPolicy is not ("per_trigger" or "per_pellet"))
                throw new ArgumentException("SG 계수를 한 발 전체 또는 펠릿당 기준 중 명시하세요.");
            HitCalculator.Compare(m.Hit);
            foreach (var buffs in new[] { m.Buffs.Ammo, m.Buffs.ChargeSpeed, m.Buffs.ReloadSpeed, m.Buffs.CriticalChance })
                StatBuffCalculator.Apply(0, buffs); // shared validation before expanding stack terms
            if (StatBuffCalculator.Apply(w.maxAmmo, m.Buffs.Ammo) is < 1 or > 100000)
                throw new ArgumentException("유효 장탄 수 범위를 확인하세요.");
            if (w.isChargeWeapon && !m.Hit.ChargeApplicable)
                throw new ArgumentException("차지 무기와 타격 입력이 일치하지 않습니다.");
        }
        bool BadWindow(int a, int b) => a < 1 || b <= a || b > c.DurationFrames + 1;
        if (c.FullBurstWindows.Any(w => w is null || BadWindow(w.StartFrame, w.EndFrame))
            || c.AttackBuffWindows.Any(w => w is null || BadWindow(w.StartFrame, w.EndFrame) || !members.Any(m => m.CharacterId == w.CharacterId)))
            throw new ArgumentException("조건 구간은 시작 프레임 이상·종료 프레임 미만이며 실행 범위 안이어야 합니다.");
        var windows = c.FullBurstWindows.OrderBy(w => w.StartFrame).ToArray();
        if (windows.Zip(windows.Skip(1)).Any(p => p.First.EndFrame > p.Second.StartFrame))
            throw new ArgumentException("풀버스트 조건 구간이 겹칩니다.");
        foreach (var window in c.AttackBuffWindows) StatBuffCalculator.Apply(0, new StatRateBuff[] { window.Buff });
    }
}

using Nikke.Core.Combat;
using Nikke.Core.Stats;
using Nikke.Simulator.Core.Stats;
using Nikke.Simulator.Engine;

namespace Nikke.Engine.Skills;

// P03: a prescribed battle context drives real skill effects. Team gauge and enemy AI belong to P04/P05.
public static class SkillReplay
{
    public const string Version = "p03.skills.1";
    public static SkillReplayResult Run(IReadOnlyList<SkillReplayMember> members, SkillGraph graph,
        SkillReplayConditions conditions, IRandomSource random = null)
    {
        Validate(members, graph, conditions);
        return new Battle(members, graph, conditions, random ?? SystemRandomSource.Instance).Run();
    }

    public static IReadOnlyList<string> CheckSupport(SkillLoadout loadout, SkillGraph graph)
    {
        var issues = new SortedSet<string>(); var seen = new HashSet<int>(); var skills = new HashSet<int>();
        void VisitFunction(int id)
        {
            if (id == 0 || !seen.Add(id)) return;
            if (!graph.Functions.TryGetValue(id, out var f)) { issues.Add($"missing_function:{id}"); return; }
            if (f.FunctionType is not (0 or 1 or 2 or 3 or 5 or 8 or 11 or 14 or 27 or 40 or 42 or 51 or 54 or 61 or 62 or 72 or 75 or 83 or 94 or 96))
                issues.Add($"function:{id}:type:{f.FunctionType}");
            if (f.TimingTriggerType is not (0 or 1 or 3 or 15 or 16 or 22 or 30 or 31 or 43)) issues.Add($"function:{id}:timing:{f.TimingTriggerType}");
            foreach (var st in new[] { f.StatusTriggerType, f.StatusTrigger2Type })
                if (st is not (0 or 9 or 11 or 12 or 13 or 15 or 18 or 31)) issues.Add($"function:{id}:status:{st}");
            if (f.FunctionTarget is < 1 or > 4 || f.FunctionStandard is < 0 or > 2
                || f.StatusTriggerStandard is < 0 or > 2 || f.StatusTrigger2Standard is < 0 or > 2
                || f.DurationType is not (0 or 1 or 3) || f.KeepingType is not (2 or 3)
                || f.DelayValue != 0 || f.DelayType != 0 || f.IsCancel || f.LimitValue != 0
                || f.FullCount is < 1 or > 100 || f.DurationValue < 0)
                issues.Add($"function:{id}:unreviewed_metadata");
            foreach (var next in f.ConnectedFunction) VisitFunction(next);
            if (f.FunctionType == 72)
            {
                if (graph.CharacterSkills.TryGetValue(checked((int)f.FunctionValue), out var nested)) VisitSkill(nested);
                else issues.Add($"missing_skill:{f.FunctionValue}");
            }
        }
        void VisitSkill(SkillDefinition sk)
        {
            if (!skills.Add(sk.SkillId)) return;
            foreach (var id in sk.FunctionIds) VisitFunction(id);
            foreach (var (phase, ids) in sk.FunctionPhases)
            {
                if (phase is not ("before_use" or "before_hurt" or "after_use" or "after_hurt")) issues.Add($"skill:{sk.SkillId}:phase:{phase}");
                foreach (var id in ids) VisitFunction(id);
            }
            if (sk.Skill is { } body)
            {
                if (body.SkillType is not (1 or 6 or 7 or 8) || body.SkillValueData.Count != 5
                    || body.DurationType is not (0 or 1) || body.DurationValue < 0 || body.SkillCooltime < 0
                    || body.PreferTarget is not (11 or 15 or 17 or 47) || body.PreferTargetCondition is < 0 or > 1)
                    issues.Add($"skill:{sk.SkillId}:unreviewed_body");
            }
        }
        foreach (var sk in loadout.Slots.Values) VisitSkill(sk);
        return issues.ToArray();
    }

    private static void Validate(IReadOnlyList<SkillReplayMember> members, SkillGraph graph, SkillReplayConditions c)
    {
        if (members is null || members.Count is < 1 or > 5 || members.Any(m => m is null || m.Weapon is null || m.Skills is null
            || !double.IsFinite(m.NativeHp) || m.NativeHp <= 0 || m.NativeHp > 1e12)
            || graph?.Functions is null || graph.CharacterSkills is null || c?.Combat is null
            || c.RoundingPolicy is not ("legacy_term_floor" or "final_round_even" or "nested_floor")
            || c.Casts is null || c.HpObservations is null || c.InitialHpRatios is null || c.InitialCovers is null
            || c.LowestHpTargetBasis is not ("ratio" or "absolute") || c.LowestCoverTargetBasis is not ("ratio" or "absolute")
            || c.Casts.Count > 200 || c.HpObservations.Count > 500)
            throw new ArgumentException("스킬 검산 입력과 정수화 후보를 명시하세요.");
        // Reuse the weapon contract validation without executing a reference replay.
        WeaponReplay.Validate(members.Select(m => m.Weapon).ToArray(), c.Combat);
        var ids = members.Select(m => m.Weapon.CharacterId).ToHashSet();
        bool FrameOk(int f) => f >= 1 && f <= c.Combat.DurationFrames;
        bool RatioOk(double r) => double.IsFinite(r) && r > 0 && r <= 1;
        if (c.Casts.Any(s => s is null || !FrameOk(s.Frame) || !ids.Contains(s.CharacterId) || s.Slot != "burst")
            || c.Casts.GroupBy(s => (s.Frame, s.CharacterId)).Any(g => g.Count() > 1)
            || c.HpObservations.Any(s => s is null || !FrameOk(s.Frame) || !ids.Contains(s.CharacterId) || !RatioOk(s.Ratio))
            || c.HpObservations.GroupBy(s => (s.Frame, s.CharacterId)).Any(g => g.Count() > 1)
            || c.InitialHpRatios.Any(p => !ids.Contains(p.Key) || !RatioOk(p.Value))
            || c.InitialCovers.Any(p=>!ids.Contains(p.Key) || p.Value is null || !double.IsFinite(p.Value.MaxHp) || !double.IsFinite(p.Value.CurrentHp)
                || p.Value.MaxHp<=0 || p.Value.MaxHp>1e12 || p.Value.CurrentHp<0 || p.Value.CurrentHp>p.Value.MaxHp)
            || c.InitialCovers.Count!=0 && c.InitialCovers.Count!=members.Count)
            throw new ArgumentException("시전·HP 관측의 캐릭터, 프레임, 중복과 생존 HP 비율을 확인하세요.");
        foreach (var m in members)
        {
            if (!double.IsFinite(m.Weapon.Buffs.NormalAttackMultiplier) || m.Weapon.Buffs.NormalAttackMultiplier is <= -1 or > 1e6)
                throw new ArgumentException("일반 공격 계수 증가량을 확인하세요.");
            StatBuffCalculator.Apply(0,m.Weapon.Buffs.Accuracy);
            if (m.Skills.Slots.Count != 3 || new[] { "skill1", "skill2", "burst" }.Any(s => !m.Skills.Slots.ContainsKey(s)
                || !m.Skills.Levels.TryGetValue(s, out int lv) || lv is < 1 or > 10))
                throw new ArgumentException("실제 3슬롯 스킬 레벨이 필요합니다. 최고 레벨로 대체하지 않습니다.");
            var unsupported = CheckSupport(m.Skills, graph);
            if (unsupported.Count != 0) throw new ArgumentException("미지원 공식 스킬: " + string.Join(", ", unsupported.Take(12)));
        }
    }

    private sealed class Actor
    {
        public SkillReplayMember Input;
        public string Id => Input.Weapon.CharacterId;
        public SkillFiringModel Gun;
        public double Hp, CoverRatio = 1, CoverMaxHp = 1;
        public int Shots, Hits, Crits, AmmoConsumed;
        public Dictionary<string, double> Damage = new();
        public Dictionary<string, long> Ready = new();
    }
    private sealed class Effect
    {
        public Actor Source, Target;
        public SkillFunction Function;
        public int Stacks = 1;
        public int? Expires;
        public int NextTick;
        public double Value;
        public string Basis;
        public long EventId;
    }
    private sealed record Listener(Actor Owner, SkillFunction Function, string Slot)
    {
        public int Counter;
    }
    private sealed record WeaponMode(int SkillId, int Expires, double Coefficient, double Rate, long EventId, int ShotId);

    private sealed class Battle
    {
        private readonly SkillGraph graph;
        private readonly SkillReplayConditions input;
        private WeaponReplayConditions C => input.Combat;
        private readonly IRandomSource random;
        private readonly List<Actor> team;
        private readonly List<Listener> listeners = [];
        private readonly List<Effect> effects = [];
        private readonly Dictionary<string, WeaponMode> modes = new();
        private readonly Dictionary<string, SharedShieldView> shields = new();
        private readonly List<SkillTrace> trace = [];
        private long eventCount;
        private int frame, operations;
        private bool fullBurst;

        public Battle(IReadOnlyList<SkillReplayMember> members, SkillGraph graph, SkillReplayConditions conditions, IRandomSource random)
        {
            this.graph = graph; input = conditions; this.random = random;
            team = members.Select(m => new Actor { Input = m,
                Gun = new(new WeaponProfile(m.Weapon.Weapon), m.Weapon.Weapon.maxAmmo,
                    new FiringControl { Mode = C.ManualCharacterId == m.Weapon.CharacterId ? ControlMode.Manual : ControlMode.Auto,
                        Style = C.ManualStyle == "tap" ? FireStyle.Tap : FireStyle.FullCharge }, random),
                Ready = m.Skills.Slots.ToDictionary(p => p.Key, p => p.Key == "burst" ? 0L : (long)(p.Value.Skill?.SkillCooltime ?? 0)*SkillUnits.TicksPerCs)
            }).ToList();
            foreach (var a in team)
            {
                a.Hp = MaxHp(a) * input.InitialHpRatios.GetValueOrDefault(a.Id, 1);
                if (input.InitialCovers.TryGetValue(a.Id,out var cover))
                { a.CoverMaxHp=cover.MaxHp; a.CoverRatio=cover.CurrentHp/cover.MaxHp; }
                foreach (var (slot, sk) in a.Input.Skills.Slots)
                    if (sk.Skill is null) foreach (var id in sk.FunctionIds.Where(id => id != 0))
                        listeners.Add(new(a, graph.Functions[id], slot));
                SyncGun(a);
                a.Gun.RefillFull();
            }
        }

        private long Log(string kind, string source, string target = null, string effect = null, long? parent = null,
            int? fid = null, int? sid = null, double? value = null, int? stacks = null, string basis = null,
            int? expires = null, HitContext hit = null)
        {
            long id = ++eventCount;
            if (C.Trace && trace.Count < C.TraceLimit)
                trace.Add(new(id, parent, frame, kind, source, target, effect, fid, sid, value, stacks, basis, expires, hit));
            return id;
        }
        private void Guard(int depth)
        {
            if (depth > 32 || ++operations > 20000) throw new ArgumentException("스킬 연쇄가 실행 한도를 넘었습니다. 해당 그래프를 검토하세요.");
        }
        private IEnumerable<Effect> On(Actor a, int type) => effects.Where(e => e.Target == a && e.Function.FunctionType == type);
        private static string Key(Effect e) => $"skill:{e.Source.Id}:{e.Function.Id}";
        private IReadOnlyList<StatRateBuff> Rates(Actor a, int type) => On(a, type).Select(e => new StatRateBuff(Key(e), e.Value, e.Stacks)).ToArray();
        private double MaxHp(Actor a) => StatBuffCalculator.Apply(a.Input.NativeHp, a.Input.Weapon.Buffs.HP, Rates(a, 94));
        private double Ratio(Actor a) => a.Hp / MaxHp(a);
        private IEnumerable<Actor> Targets(Actor owner, SkillFunction f, IReadOnlyList<Actor> selected) => f.FunctionTarget switch
        {
            1 => new[] { owner }, 2 => team, 3 => new Actor[] { null }, 4 => selected, _ => throw new ArgumentException("Unknown target")
        };
        private bool Status(Actor owner, Actor target, int type, int standard, long value)
        {
            var a = standard == 2 ? target : owner;
            if (type == 0) return true;
            if (a is null) return false;
            return type switch
            {
                9 => team.Count(t => t.Input.Skills.Squad == a.Input.Skills.Squad) == value,
                11 => team.Count(t => t.Input.Skills.Squad == a.Input.Skills.Squad) >= value,
                12 => Ratio(a) < SkillUnits.Rate(value),
                13 => Ratio(a) > SkillUnits.Rate(value),
                15 => On(a, checked((int)value)).Any(e => e.Function.Buff == 0 && e.Value > 0)
                    || value == 8 && a.Input.Weapon.Buffs.Accuracy.Any(b=>b.Rate>0),
                18 => effects.Any(e => e.Target == a && e.Function.GroupId == value),
                31 => value == 5 && a.Input.Weapon.Weapon.weaponType == "SG",
                _ => throw new ArgumentException("Unknown status")
            };
        }
        private bool Pass(Actor o, Actor t, SkillFunction f) => Status(o,t,f.StatusTriggerType,f.StatusTriggerStandard,f.StatusTriggerValue)
            && Status(o,t,f.StatusTrigger2Type,f.StatusTrigger2Standard,f.StatusTrigger2Value);

        private void Dispatch(int timing, Actor owner, long parent, int value = 0)
        {
            foreach (var l in listeners)
            {
                var f = l.Function;
                if (f.TimingTriggerType != timing || owner is not null && l.Owner != owner) continue;
                if (timing == 22 && f.TimingTriggerValue != value) continue;
                // OnSkillUse's value is a skill group ID, not an N-use threshold.
                if (timing == 30 && f.TimingTriggerValue != value) continue;
                if (timing is 3 or 31)
                {
                    l.Counter++;
                    if (l.Counter < Math.Max(1, f.TimingTriggerValue)) continue;
                    l.Counter = 0;
                }
                Apply(l.Owner, f, new Actor[] { null }, parent, 0);
            }
        }

        private void RefreshConditions(long? parent = null)
        {
            foreach (var l in listeners.Where(l => l.Function.TimingTriggerType is 15 or 16))
            {
                var f = l.Function;
                bool enabled = Pass(l.Owner, l.Owner, f);
                bool present = effects.Any(e => e.Source == l.Owner && e.Function.Id == f.Id);
                if (enabled && !present) Apply(l.Owner, f, [l.Owner], parent, 0);
                else if (!enabled && present)
                    foreach (var e in effects.Where(e => e.Source == l.Owner && e.Function.Id == f.Id).ToArray()) Remove(e, "condition_off");
            }
        }

        private void Apply(Actor owner, SkillFunction f, IReadOnlyList<Actor> selected, long? parent, int depth)
        {
            Guard(depth);
            var targets = Targets(owner, f, selected).Where(t => Pass(owner,t,f)).ToArray();
            if (targets.Length == 0) return;
            long call = Log("function", owner.Id, effect:$"function:{f.Id}", parent:parent, fid:f.Id);
            if (f.FunctionType == 72)
                ExecuteSkill(owner, graph.CharacterSkills[checked((int)f.FunctionValue)], call, depth + 1);
            else foreach (var target in targets)
            {
                switch (f.FunctionType)
                {
                    case 75:
                        Damage(owner, f.Rate, $"function:{f.Id}", call, false, false);
                        break;
                    case 27:
                        SyncGun(target);
                        int count = f.FunctionValueType == 2 ? checked((int)Math.Round(target.Gun.MaxAmmo * f.Rate, MidpointRounding.AwayFromZero)) : checked((int)f.FunctionValue);
                        int before = target.Gun.CurrentAmmo; target.Gun.AddAmmo(count);
                        Log("ammo_gain", owner.Id, target.Id, $"function:{f.Id}", call, f.Id, value:target.Gun.CurrentAmmo-before);
                        break;
                    case 83:
                        long old = target.Ready["burst"], now = (long)frame*SkillUnits.TicksPerFrame;
                        long delta = checked(f.FunctionValue*SkillUnits.TicksPerCs);
                        target.Ready["burst"] = delta<0 && old<=now ? old : Math.Max(now,Math.Max(now,old)+delta);
                        Log("cooldown_change",owner.Id,target.Id,$"function:{f.Id}",call,f.Id,
                            value:(target.Ready["burst"]-old)/(double)SkillUnits.TicksPerCs,basis:"centiseconds");
                        break;
                    case 3:
                        double oldCover = target.CoverRatio; target.CoverRatio = Math.Min(1, oldCover + f.Rate);
                        Log("cover_heal",owner.Id,target.Id,$"function:{f.Id}",call,f.Id,value:target.CoverRatio-oldCover,basis:"prescribed_cover_fraction");
                        break;
                    default: AddEffect(owner,target,f,call); break;
                }
            }
            // A connected function is called once with the same selected targets, not once per recipient.
            foreach (var next in f.ConnectedFunction.Where(id => id != 0)) Apply(owner,graph.Functions[next],selected,call,depth+1);
        }

        private void AddEffect(Actor owner, Actor target, SkillFunction f, long parent)
        {
            double oldMax = target is null ? 0 : MaxHp(target);
            var existing = effects.SingleOrDefault(e => e.Source == owner && e.Target == target && e.Function.GroupId == f.GroupId);
            double value = f.FunctionType switch
            {
                0 or 5 or 40 or 54 => f.FunctionValue,
                14 when f.FunctionValueType == 1 => f.FunctionValue,
                8 or 42 or 61 => -f.Rate,
                _ => f.Rate
            };
            string basis = f.FunctionStandard == 1 ? "native_caster" : "native_recipient";
            if (f.FunctionType == 1 && f.FunctionStandard == 1 && target != owner)
            {
                value = StatBuffCalculator.Apply(owner.Input.Weapon.Hit.StatAttack, new StatRateBuff[] { new($"function:{f.Id}",f.Rate) }) - owner.Input.Weapon.Hit.StatAttack;
                basis = "native_caster_flat_at_application";
            }
            if (f.FunctionType == 61 && f.FunctionStandard == 1 && target != owner)
            {
                var casterCs = SkillUnits.Cs(owner.Input.Weapon.Weapon.chargeTimeSec);
                var targetCs = SkillUnits.Cs(target.Input.Weapon.Weapon.chargeTimeSec);
                // Store a fixed centisecond grant. Avoid rescaling through a rounded recipient rate.
                value = casterCs - OverloadProcessor.ReduceTimeCs(casterCs, new[] { -f.Rate });
                basis = "caster_charge_centiseconds";
                if (targetCs == 0) value = 0;
            }
            if (f.FunctionType == 2) { value = MaxHp(owner) * f.Rate; basis = "caster_final_max_hp_at_application"; }
            var e = existing ?? new Effect { Source=owner, Target=target, Function=f };
            if (existing is null) effects.Add(e); else e.Stacks = Math.Min(f.FullCount, e.Stacks+1);
            e.Expires = f.DurationType == 3 ? null : frame + Math.Max(1,SkillUnits.Frames(f.DurationValue));
            e.Value=value; e.Basis=basis; e.Function=f;
            e.NextTick = frame + 60;
            e.EventId=Log(existing is null ? "buff_on" : "buff_refresh",owner.Id,target?.Id ?? "boss",$"function:{f.Id}",parent,f.Id,
                value:value,stacks:e.Stacks,basis:basis,expires:e.Expires);
            if (f.FunctionType == 94 && target is not null)
                target.Hp = Math.Min(MaxHp(target), target.Hp + MaxHp(target)-oldMax);
            if (target is not null && f.FunctionType is 5 or 14 or 61) SyncGun(target);
        }

        private void Remove(Effect e, string reason)
        {
            effects.Remove(e);
            if (e.Target is not null)
            {
                e.Target.Hp = Math.Min(e.Target.Hp, MaxHp(e.Target));
                if (e.Function.FunctionType is 5 or 14 or 61) SyncGun(e.Target);
            }
            Log(reason,e.Source.Id,e.Target?.Id ?? "boss",$"function:{e.Function.Id}",e.EventId,e.Function.Id,stacks:e.Stacks);
        }

        private void ExecuteSkill(Actor owner, SkillDefinition sk, long? parent, int depth)
        {
            Guard(depth);
            long cast = Log("skill_execute",owner.Id,effect:$"skill:{sk.SkillId}",parent:parent,sid:sk.SkillId);
            var body = sk.Skill;
            var selected = Select(owner, body);
            void Phase(string phase)
            {
                if (!sk.FunctionPhases.TryGetValue(phase,out var ids)) return;
                foreach (int id in ids.Where(id => id != 0)) Apply(owner,graph.Functions[id],selected,cast,depth+1);
            }
            foreach (int id in sk.FunctionIds.Where(id => id != 0)) Apply(owner,graph.Functions[id],selected,cast,depth+1);
            Phase("before_use"); Phase("before_hurt");
            if (body is not null)
            {
                var values=body.SkillValueData;
                switch (body.SkillType)
                {
                    case 1: Damage(owner,SkillUnits.Rate(values[0].SkillValue),$"skill:{sk.SkillId}",cast,false,false); break;
                    case 6:
                        // Shared shield, single pool. Enemy damage consumption is a P05 integration.
                        double shieldHp=MaxHp(owner)*SkillUnits.Rate(values[1].SkillValue);
                        int end=frame+SkillUnits.Frames(body.DurationValue);
                        long shieldEvent=Log("shared_shield",owner.Id,"team",$"skill:{sk.SkillId}",cast,sid:sk.SkillId,
                            value:shieldHp,basis:"caster_final_max_hp_at_application",expires:end);
                        shields[owner.Id]=new(owner.Id,sk.SkillId,shieldHp,end,shieldEvent);
                        break;
                    case 7:
                        modes[owner.Id]=new(sk.SkillId,frame+SkillUnits.Frames(body.DurationValue),SkillUnits.Rate(values[0].SkillValue),
                            values[1].SkillValue/60d,cast,checked((int)values[2].SkillValue));
                        Log("weapon_change",owner.Id,owner.Id,$"skill:{sk.SkillId}",cast,sid:sk.SkillId,value:values[2].SkillValue,
                            basis:"official_coefficient_rpm_shot_id",expires:modes[owner.Id].Expires);
                        break;
                    case 8: break; // Function-only ally-target skill body.
                    default: throw new ArgumentException("Unsupported skill body");
                }
            }
            Phase("after_hurt"); Phase("after_use");
        }

        private Actor[] Select(Actor owner, SkillBody body)
        {
            if (body is null) return [owner];
            int count = body.SkillValueData.Count > 1 ? Math.Clamp(checked((int)body.SkillValueData[1].SkillValue),1,5) : 1;
            if (body.SkillType is 1 or 7) return [null];
            if (body.SkillType == 6) return team.ToArray();
            if (body.AttackType == 4 && body.SkillValueData[2].SkillValue == 1) return [owner];
            IEnumerable<Actor> available = body.PreferTargetCondition == 1 ? team.Where(a=>a!=owner) : team;
            return (body.PreferTarget switch
            {
                17 => available.OrderByDescending(a=>EffectiveAttack(a)),
                47 => available.OrderBy(a=>input.LowestCoverTargetBasis=="ratio" ? a.CoverRatio : a.CoverRatio*a.CoverMaxHp),
                11 => available.OrderBy(a=>input.LowestHpTargetBasis=="ratio" ? Ratio(a) : a.Hp),
                15 => available,
                _ => throw new ArgumentException("Unsupported preferred target")
            }).Take(count).ToArray();
        }

        private void Cast(Actor owner, string slot, long? parent = null)
        {
            var sk = owner.Input.Skills.Slots[slot];
            if (sk.Skill is null || (long)frame*SkillUnits.TicksPerFrame < owner.Ready[slot]) throw new ArgumentException($"{owner.Id} {slot}: 쿨다운 중이거나 시전형 스킬이 아닙니다.");
            owner.Ready[slot]=(long)frame*SkillUnits.TicksPerFrame+(long)sk.Skill.SkillCooltime*SkillUnits.TicksPerCs;
            long ev=Log("skill_cast",owner.Id,effect:slot,parent:parent,sid:sk.SkillId);
            if (slot=="burst") Log("full_burst_duration_request",owner.Id,"team",slot,ev,sid:sk.SkillId,
                value:owner.Input.Skills.FullBurstDurationFrames,basis:"frames_for_P04_cycle");
            // Original passive order is significant: descending stage markers prevent one cast advancing three tiers.
            Dispatch(30,owner,ev,sk.SkillId/100);
            ExecuteSkill(owner,sk,ev,0);
        }

        private IReadOnlyList<StatRateBuff> AttackRates(Actor a) => On(a,1).Where(e=>e.Basis!="native_caster_flat_at_application")
            .Select(e=>new StatRateBuff(Key(e),e.Value,e.Stacks))
            .Concat(C.AttackBuffWindows.Where(w=>w.CharacterId==a.Id && w.StartFrame<=frame && frame<w.EndFrame).Select(w=>w.Buff)).ToArray();
        private IReadOnlyList<StatFlatBuff> AttackFlat(Actor a) => a.Input.Weapon.Hit.AttackFlatBuffs.Concat(On(a,1)
            .Where(e=>e.Basis=="native_caster_flat_at_application").Select(e=>new StatFlatBuff(Key(e),e.Value*e.Stacks))).ToArray();
        private double EffectiveAttack(Actor a) => StatBuffCalculator.AddFlat(StatBuffCalculator.Apply(a.Input.Weapon.Hit.StatAttack,
            a.Input.Weapon.Hit.AttackBuffs,a.Input.Weapon.Hit.RuntimeAttackBuffs,AttackRates(a)),AttackFlat(a));

        private void SyncGun(Actor a)
        {
            var w=a.Input.Weapon.Weapon; var b=a.Input.Weapon.Buffs;
            var ammoRates=On(a,14).Where(e=>e.Function.FunctionValueType==2).Select(e=>new StatRateBuff(Key(e),e.Value,e.Stacks)).ToArray();
            int maxAmmo=checked((int)StatBuffCalculator.Apply(w.maxAmmo,b.Ammo,ammoRates)
                + (int)On(a,14).Where(e=>e.Function.FunctionValueType==1).Sum(e=>e.Value*e.Stacks));
            var charge=On(a,61).Where(e=>e.Basis!="caster_charge_centiseconds").Select(e=>new StatRateBuff(Key(e),e.Value,e.Stacks));
            int chargeCs=OverloadProcessor.ReduceTimeCs(SkillUnits.Cs(w.chargeTimeSec),Terms(b.ChargeSpeed.Concat(charge)))
                - checked((int)On(a,61).Where(e=>e.Basis=="caster_charge_centiseconds").Sum(e=>e.Value*e.Stacks));
            int reloadCs=OverloadProcessor.ReduceTimeCs(SkillUnits.Cs(w.reloadTimeSec),Terms(b.ReloadSpeed));
            modes.TryGetValue(a.Id,out var mode);
            a.Gun.ApplyRuntime(Math.Max(1,maxAmmo),Math.Max(0,chargeCs),reloadCs,On(a,5).Any(),mode?.Rate);
        }
        private static double[] Terms(IEnumerable<StatRateBuff> buffs) => buffs.SelectMany(b=>Enumerable.Repeat(b.Rate,b.Stacks)).ToArray();

        private void Damage(Actor a, double coefficient, string effect, long parent, bool normal, bool charged)
        {
            bool crit=C.CritMode=="on" || C.CritMode=="sample" && CritSampler.RollCrit(random,
                Math.Clamp(.15+Terms(a.Input.Weapon.Buffs.CriticalChance).Sum(),0,1));
            var h=a.Input.Weapon.Hit with {
                Coefficient=coefficient, RuntimeAttackBuffs=a.Input.Weapon.Hit.RuntimeAttackBuffs.Concat(AttackRates(a)).ToArray(),
                AttackFlatBuffs=AttackFlat(a), Defense=C.EnemyDefense, DamageType=normal ? "normal" : "skill",
                AttackStatBasis="native_caster_with_shared_buffs_and_flat_grants", SnapshotTiming="damage_resolution",
                CanCrit=true, CanCore=normal, Crit=crit, Core=normal && C.Core,
                ChargeApplicable=normal && a.Input.Weapon.Hit.ChargeApplicable, FullCharge=normal && charged,
                ChargeAdd=a.Input.Weapon.Hit.ChargeAdd+On(a,11).Sum(e=>e.Value*e.Stacks),
                FullBurst=fullBurst, ProperDistance=normal && C.ProperDistance, ElementAdvantage=C.ElementAdvantage,
                CritBonus=a.Input.Weapon.Hit.CritBonus+On(a,51).Sum(e=>e.Value*e.Stacks),
                Pierce=normal && On(a,54).Any(),
                DamageTaken=a.Input.Weapon.Hit.DamageTaken+On(null,42).Sum(e=>e.Value*e.Stacks),
                AttackDamage=a.Input.Weapon.Hit.AttackDamage+(input.InterruptionTarget ? On(a,96).Sum(e=>e.Value*e.Stacks) : 0)
            };
            double damage=HitCalculator.Compare(h).Candidates.Single(p=>p.Policy==input.RoundingPolicy).Damage;
            a.Damage[effect]=a.Damage.GetValueOrDefault(effect)+damage;
            if (crit) a.Crits++;
            long ev=Log("damage",a.Id,"boss",effect,parent,value:damage,basis:h.AttackStatBasis,hit:h);
            foreach (var drain in On(a,62).ToArray()) Heal(a,a,damage*drain.Value*drain.Stacks,drain.EventId,drain.Function.Id);
            if (normal) { a.Hits++; Dispatch(31,a,ev); }
            // Skill damage never feeds normal-hit counters, so Modernia's extra hit cannot recurse.
        }
        private void Heal(Actor source, Actor target, double amount, long parent, int fid)
        {
            double before=target.Hp; target.Hp=Math.Min(MaxHp(target),target.Hp+amount);
            Log("heal",source.Id,target.Id,$"function:{fid}",parent,fid,value:target.Hp-before,basis:"hp");
        }

        public SkillReplayResult Run()
        {
            long start=Log("battle_start","team"); Dispatch(0,null,start); Dispatch(1,null,start); RefreshConditions(start);
            for (frame=1; frame<=C.DurationFrames; frame++)
            {
                operations=0;
                // A HoT's last tick is delivered at its end before removing the effect (5 seconds = 5 ticks).
                foreach (var e in effects.Where(e=>e.Function.FunctionType==2 && e.NextTick<=frame).ToArray())
                {
                    if (e.Expires is null || frame<=e.Expires) Heal(e.Source,e.Target,e.Value*e.Stacks,e.EventId,e.Function.Id);
                    e.NextTick+=60;
                }
                foreach (var e in effects.Where(e=>e.Expires<=frame).ToArray()) Remove(e,"buff_expired");
                foreach (var p in modes.Where(p=>p.Value.Expires<=frame).ToArray())
                { modes.Remove(p.Key); Log("weapon_restored",p.Key,p.Key,$"skill:{p.Value.SkillId}",p.Value.EventId); }
                foreach (var p in shields.Where(p=>p.Value.ExpiresAt<=frame).ToArray())
                { shields.Remove(p.Key); Log("shield_expired",p.Key,"team",$"skill:{p.Value.SkillId}",p.Value.EventId); }
                foreach (var o in input.HpObservations.Where(o=>o.Frame==frame))
                { var a=team.Single(a=>a.Id==o.CharacterId); a.Hp=MaxHp(a)*o.Ratio; Log("prescribed_hp",a.Id,a.Id,value:o.Ratio,basis:"max_hp_ratio"); }
                RefreshConditions();
                foreach (var window in C.FullBurstWindows.Where(w=>w.EndFrame==frame))
                { fullBurst=false; long ev=Log("prescribed_full_burst_end","team"); Dispatch(43,null,ev); }
                foreach (var a in team)
                    foreach (var slot in new[] { "skill1", "skill2" })
                        if (a.Input.Skills.Slots[slot].Skill is { SkillCooltime: > 0 } && a.Ready[slot]<=(long)frame*SkillUnits.TicksPerFrame) Cast(a,slot);
                foreach (var cast in input.Casts.Where(s=>s.Frame==frame)) Cast(team.Single(a=>a.Id==cast.CharacterId),cast.Slot);
                foreach (var window in C.FullBurstWindows.Where(w=>w.StartFrame==frame))
                { fullBurst=true; long ev=Log("prescribed_full_burst_start","team"); Dispatch(22,null,ev,4); }
                RefreshConditions();
                foreach (var a in team)
                {
                    SyncGun(a);
                    int before=a.Gun.CurrentAmmo;
                    var shot=a.Gun.AdvanceFrame();
                    if (!shot.Fired)
                    {
                        if (a.Gun.CurrentAmmo>before) Log("reload_completed",a.Id,a.Id,value:a.Gun.CurrentAmmo-before);
                        continue;
                    }
                    a.Shots++;
                    long shotId=Log("shot",a.Id,"boss","normal_attack",value:a.Gun.CurrentAmmo,basis:a.Gun.UnlimitedAmmo?"unlimited_ammo":"ammo_after_shot");
                    if (!a.Gun.UnlimitedAmmo) { a.AmmoConsumed++; Dispatch(3,a,shotId); }
                    modes.TryGetValue(a.Id,out var mode);
                    int pellets=shot.PelletsPerShot*a.Input.Weapon.Weapon.muzzleCount;
                    double coefficient=mode is null ? a.Input.Weapon.Hit.Coefficient : mode.Coefficient*(1+a.Input.Weapon.Buffs.NormalAttackMultiplier);
                    if (a.Input.Weapon.Weapon.weaponType=="SG" && C.PelletCoefficientPolicy=="per_trigger") coefficient/=pellets;
                    for (int pellet=0; pellet<pellets; pellet++)
                        Damage(a,coefficient,mode is null?"normal_attack":$"skill:{mode.SkillId}:weapon",shotId,true,shot.IsFullCharge);
                    RefreshConditions(shotId);
                }
            }
            var members=team.Select(a=>new SkillMemberResult(a.Id,a.Damage.Values.Sum(),a.Damage,a.Shots,a.Hits,a.Crits,a.AmmoConsumed,
                a.Gun.CurrentAmmo,a.Gun.MaxAmmo,a.Hp,MaxHp(a),a.CoverRatio,a.Ready.ToDictionary(p=>p.Key,p=>SkillUnits.ReadyFrame(p.Value)))).ToArray();
            return new(Version,"prescribed_context_provisional","selected_five_effects_connected",input,members.Sum(m=>m.Damage),members,
                trace,eventCount,C.Trace && eventCount>trace.Count,
                effects.Select(e=>new SkillEffectView(e.Source.Id,e.Target?.Id ?? "boss",e.Function.Id,e.Function.GroupId,e.Function.FunctionType,
                    e.Value,e.Stacks,e.Expires,e.Basis)).ToArray(),shields.Values.ToArray(),
                ["Burst casts and full-burst windows are prescribed; team gauge and step validation are P04 work.",
                 "Fixed surviving target and prescribed HP observations; enemy attacks, shield consumption, death and boss geometry are not simulated.",
                 "Pierce, accuracy and interruption bonuses are tracked; automatic aim, extra pierce targets and interruption mechanics remain P05 work.",
                 "Modernia mode consumes official coefficient/RPM/shot ID and unlimited-ammo duration; unextracted replacement-shot geometry uses the base weapon.",
                 "Rounding, same-frame ordering, HP threshold equality, skill critical rolls and changed-weapon timing await game observations.",
                 "Caster ATK grants use native caster ATK; healing snapshots final caster max HP at application. Snapshot timing remains a measurement target.",
                 "Cover HP must be supplied for real cover targeting; absent cover inputs mean equal undamaged unit-size cover fixtures.",
                 "Lowest HP/cover target basis is an explicit comparison policy; verify the actual skill recipient before selecting a game rule.",
                 "Conditional cube/favorite effects are not connected. These runs are not validated raid recommendation samples."]);
        }
    }
}

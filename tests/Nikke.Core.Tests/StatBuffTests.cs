using Nikke.Core.Combat;
using Nikke.Core.Stats;

namespace Nikke.Core.Tests;

public class StatBuffTests
{
    [Fact]
    public void Overload_and_skill_attack_share_native_basis_before_defense()
    {
        var hit = new HitContext { StatAttack = 100, Defense = 160,
            AttackBuffs = [new("overload:head:1", .2)], RuntimeAttackBuffs = [new("skill:attack", .5)] };
        var result = HitCalculator.Compare(hit);
        Assert.Equal(170, result.EffectiveAttack); // 100 * (1 + .2 + .5), never 120 * 1.5 = 180
        Assert.All(result.Candidates, candidate => Assert.Equal(10, candidate.Damage));
        Assert.Equal(100, result.Input.StatAttack);
    }

    [Fact]
    public void Equal_rates_group_across_overload_and_skill_sources()
    {
        var hit = new HitContext { StatAttack = 100,
            AttackBuffs = [new("overload", .014)], RuntimeAttackBuffs = [new("skill", .014)] };
        Assert.Equal(103, HitCalculator.Compare(hit).EffectiveAttack); // round(1.4 + 1.4) = 3
        Assert.Equal(102, HitCalculator.Compare(hit with { RuntimeAttackBuffs = [new("skill", .013)] }).EffectiveAttack);
    }

    [Fact]
    public void Stacks_expiry_and_repeated_hits_never_rebase_on_buffed_attack()
    {
        var hit = new HitContext { StatAttack = 100,
            AttackBuffs = [new("overload", .2)], RuntimeAttackBuffs = [new("skill", .3, 2)] };
        Assert.Equal(180, HitCalculator.Compare(hit).EffectiveAttack);
        Assert.Equal(180, HitCalculator.Compare(hit).EffectiveAttack);
        Assert.Equal(120, HitCalculator.Compare(hit with { RuntimeAttackBuffs = [] }).EffectiveAttack);
        Assert.Equal(100, hit.StatAttack);
    }

    [Fact]
    public void Attack_up_and_attack_damage_up_remain_different_brackets()
    {
        var hit = new HitContext { StatAttack = 100, Defense = 50,
            AttackBuffs = [new("overload", .2)], RuntimeAttackBuffs = [new("skill", .5)], AttackDamage = .5 };
        Assert.All(HitCalculator.Compare(hit).Candidates, candidate => Assert.Equal(180, candidate.Damage));
    }

    [Fact]
    public void Invalid_buff_input_is_rejected()
    {
        Assert.Throws<ArgumentException>(() => StatBuffCalculator.Apply(100, new StatRateBuff[] { new("bad", double.NaN) }));
        Assert.Throws<ArgumentException>(() => StatBuffCalculator.Apply(100, new StatRateBuff[] { new("bad", .5, 0) }));
        Assert.Throws<ArgumentException>(() => StatBuffCalculator.Apply(100, new StatRateBuff[] { new("bad", -2) }));
        Assert.Throws<ArgumentException>(() => HitCalculator.Compare(new() { StatAttack = 100, AttackBuffs = null! }));
    }
}

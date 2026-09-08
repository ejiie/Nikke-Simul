using Nikke.Core.Combat;

namespace Nikke.Core.Tests;

public class HitCalculatorTests
{
    [Theory]
    [InlineData(0, 0, 250)]
    [InlineData(.4, 0, 350)]
    [InlineData(0, .8, 330)]
    [InlineData(.4, .8, 430)]
    public void Charge_axes_follow_user_formula(double mult, double add, double expected)
    {
        var c = new HitContext { StatAttack = 100, ChargeApplicable = true, FullCharge = true, ChargeBase = 2.5, ChargeMultiplierBonus = mult, ChargeAdd = add };
        Assert.All(HitCalculator.Compare(c).Candidates, x => Assert.Equal(expected, x.Damage));
        Assert.All(HitCalculator.Compare(c with { FullCharge = false }).Candidates, x => Assert.Equal(100, x.Damage));
    }
    [Fact]
    public void Rounding_discriminator_and_half_even_are_visible()
    {
        var c = new HitContext { StatAttack = 1, Coefficient = 1.9, Crit = true, CritBonus = .5 };
        var result = HitCalculator.Compare(c, 2);
        Assert.Equal(1, result.Candidates[0].Damage); Assert.Equal(3, result.Candidates[1].Damage);
        Assert.Equal(-1, result.Candidates[0].Residual);
        Assert.Equal(2, HitCalculator.Compare(c with { Coefficient = 2.5, Crit = false }).Candidates[1].Damage);
        Assert.Equal(4, HitCalculator.Compare(c with { Coefficient = 3.5, Crit = false }).Candidates[1].Damage);
    }
    [Fact]
    public void Nested_floor_is_a_separate_candidate()
    {
        var r = HitCalculator.Compare(new() { StatAttack = 10, AttackDamage = .15, DamageTaken = .15 });
        Assert.Equal(13, r.Candidates[0].Damage); Assert.Equal(12, r.Candidates[2].Damage);
    }
    [Theory]
    [InlineData("normal", 100)] [InlineData("dot", 120)] [InlineData("sequential", 130)]
    [InlineData("distribution", 140)] [InlineData("true", 300)]
    public void Type_buffs_and_defense_are_gated(string type, double expected)
    {
        var c = new HitContext { StatAttack = 200, Defense = 100, DamageType = type, DotDamage = .2,
            SequentialDamage = .3, DistributionDamage = .4, TrueDamage = .5, PierceDamage = 1, PartsDamage = 1, ElementBonus = 1 };
        Assert.All(HitCalculator.Compare(c).Candidates, x => Assert.Equal(expected, x.Damage));
    }
    [Fact]
    public void Flags_activate_only_their_bonus()
    {
        var basis = new HitContext { StatAttack = 100, PierceDamage = .5, PartsDamage = .3, ElementBonus = .4 };
        Assert.Equal(150, HitCalculator.Compare(basis with { Pierce = true }).Candidates[0].Damage);
        Assert.Equal(130, HitCalculator.Compare(basis with { Parts = true }).Candidates[0].Damage);
        Assert.Equal(150, HitCalculator.Compare(basis with { ElementAdvantage = true }).Candidates[0].Damage);
    }
    [Fact]
    public void Unavailable_conditions_and_invalid_inputs_are_rejected()
    {
        Assert.Throws<ArgumentException>(() => HitCalculator.Compare(new() { StatAttack = 10, CanCrit = false, Crit = true }));
        Assert.Throws<ArgumentException>(() => HitCalculator.Compare(new() { StatAttack = 10, CanCore = false, Core = true }));
        Assert.Throws<ArgumentException>(() => HitCalculator.Compare(new() { StatAttack = 10, FullCharge = true }));
        Assert.Throws<ArgumentException>(() => HitCalculator.Compare(new() { StatAttack = double.NaN }));
        Assert.Throws<ArgumentException>(() => HitCalculator.Compare(new() { StatAttack = 10 }, 1.5));
    }
    [Fact]
    public void Defense_minimum_is_not_multiplied()
    {
        Assert.All(HitCalculator.Compare(new() { StatAttack = 10, Defense = 20, Coefficient = 50, AttackDamage = 50 }).Candidates,
            x => Assert.Equal(1, x.Damage));
    }
}

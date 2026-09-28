using System.Text.Json;
using Nikke.Engine;
using Nikke.Engine.Skills;
using static Nikke.Core.Tests.SkillReplayTests;

namespace Nikke.Core.Tests;

public class BossConditionTests
{
    private static readonly JsonSerializerOptions Json=new(JsonSerializerDefaults.Web);
    private static WeaponReplayMember Meta(string id="a",int min=25,int max=45,string element="Fire",string weapon="AR")
    {
        var member=Member(id).Weapon with { BonusRangeMin=min,BonusRangeMax=max,Element=element };
        member.Weapon.weaponType=weapon;
        return member;
    }

    [Theory]
    [InlineData(24,false)] [InlineData(25,true)] [InlineData(45,true)] [InlineData(46,false)]
    public void Inclusive_character_range_boundaries(int distance,bool expected)
    {
        var c=new WeaponReplayConditions { BossDistance=distance };
        Assert.Equal(expected,BossConditionResolver.Resolve(Meta(),c,true).ProperDistance);
        Assert.False(BossConditionResolver.Resolve(Meta(),c,false).ProperDistance);
    }

    [Theory]
    [InlineData(0)] [InlineData(1)] [InlineData(100)]
    public void Rl_zero_zero_has_no_bonus_without_enabling_rl_simulation(int distance)
    {
        var member=Meta(min:0,max:0,weapon:"RL");
        Assert.False(BossConditionResolver.Resolve(member,new() { BossDistance=distance },true).ProperDistance);
    }

    [Fact]
    public void Sr_character_exception_overrides_weapon_family_reference()
    {
        var regular=Meta("regular",45,100,weapon:"SR");
        var exception=Meta("exception",25,45,weapon:"SR");
        Assert.True(BossConditionResolver.Resolve(exception,new() { BossDistance=25 },true).ProperDistance);
        Assert.False(BossConditionResolver.Resolve(regular,new() { BossDistance=25 },true).ProperDistance);
        Assert.True(BossConditionResolver.Resolve(regular,new() { BossDistance=100 },true).ProperDistance);
        Assert.False(BossConditionResolver.Resolve(exception,new() { BossDistance=100 },true).ProperDistance);
        Assert.True(BossConditionResolver.Resolve(Meta(min:0,max:25,weapon:"SG"),new() { BossDistance=0 },true).ProperDistance);
    }

    [Theory]
    [InlineData("Fire")] [InlineData("Water")] [InlineData("Wind")] [InlineData("Iron")] [InlineData("Electronic")]
    public void Weakness_is_direct_member_element_equality_for_normal_and_skill(string element)
    {
        var member=Meta(element:element);
        Assert.True(BossConditionResolver.Resolve(member,new() { BossWeakElement=element },true).ElementAdvantage);
        Assert.True(BossConditionResolver.Resolve(member,new() { BossWeakElement=element },false).ElementAdvantage);
        Assert.False(BossConditionResolver.Resolve(member,new() { BossWeakElement=element=="Fire"?"Water":"Fire" },true).ElementAdvantage);
    }

    [Fact]
    public void Unset_conditions_need_no_member_metadata_and_apply_no_bonus()
    {
        var c=new WeaponReplayConditions { BossDistance=null,BossWeakElement=null };
        Assert.Equal(new MemberHitBonuses(false,false),BossConditionResolver.Resolve(Member().Weapon,c,true));
        var prepared=PreparedSkillReplay.Create([Member()],Graph(),new() { Combat=c with { DurationFrames=60 } });
        Assert.Equal(SkillReplay.Run([Member()],Graph(),new() { Combat=c with { DurationFrames=60 } }).TotalDamage,prepared.Run().TeamDamage);
    }

    [Fact]
    public void Unknown_or_invalid_required_metadata_is_an_error_instead_of_a_guess()
    {
        Assert.Contains("member_bonus_range_unknown",Assert.Throws<ArgumentException>(()=>
            BossConditionResolver.Resolve(Member().Weapon,new() { BossDistance=30 },true)).Message);
        Assert.Contains("member_element_unknown",Assert.Throws<ArgumentException>(()=>
            BossConditionResolver.Resolve(Member().Weapon,new() { BossWeakElement="Fire" },true)).Message);
        Assert.Throws<ArgumentException>(()=>BossConditionResolver.Resolve(Meta(min:45,max:25),new() { BossDistance=30 },true));
        Assert.Throws<ArgumentException>(()=>BossConditionResolver.Resolve(Meta(min:-1),new() { BossDistance=30 },true));
        Assert.Throws<ArgumentException>(()=>BossConditionResolver.Resolve(Meta(max:101),new() { BossDistance=30 },true));
        Assert.Throws<ArgumentException>(()=>BossConditionResolver.Resolve(Meta(element:"Electric"),new() { BossWeakElement="Electronic" },true));
        Assert.Throws<ArgumentException>(()=>PreparedSkillReplay.Create([Member()],Graph(),new() { Combat=new() { BossDistance=30 } }));
        Assert.Throws<ArgumentException>(()=>WeaponReplay.Run([Member().Weapon],new() { BossWeakElement="Fire" }));
        // Unused metadata is not inferred or required.
        Assert.True(BossConditionResolver.Resolve(Meta() with { Element=null },new() { BossDistance=30 },true).ProperDistance);
        Assert.True(BossConditionResolver.Resolve(Meta() with { BonusRangeMin=null,BonusRangeMax=null },new() { BossWeakElement="Fire" },true).ElementAdvantage);
    }

    [Theory]
    [InlineData("{\"bossDistance\":-1}")] [InlineData("{\"bossDistance\":101}")]
    [InlineData("{\"bossWeakElement\":\"Electric\"}")] [InlineData("{\"bossWeakElement\":\"\"}")]
    [InlineData("{\"bossDistance\":35,\"properDistance\":false}")]
    [InlineData("{\"bossWeakElement\":\"Fire\",\"elementAdvantage\":true}")]
    [InlineData("{\"bossDistance\":35,\"elementAdvantage\":false}")]
    [InlineData("{\"bossDistance\":null,\"properDistance\":true}")]
    public void Reject_invalid_and_mixed_json_even_explicit_false_or_null(string json)
    {
        var c=JsonSerializer.Deserialize<WeaponReplayConditions>(json,Json)!;
        Assert.Throws<ArgumentException>(()=>BossConditionResolver.Validate(c));
    }

    [Fact]
    public void Fractional_distance_fails_integer_deserialization()
    {
        Assert.Throws<JsonException>(()=>JsonSerializer.Deserialize<WeaponReplayConditions>("{\"bossDistance\":25.5}",Json));
        Assert.Throws<ArgumentException>(()=>BossConditionResolver.Validate(new() { BossDistance=35,ProperDistance=false }));
    }

    [Fact]
    public void Legacy_json_bool_values_survive_roundtrip_and_new_json_omits_legacy_bools()
    {
        var legacy=JsonSerializer.Deserialize<WeaponReplayConditions>("{\"properDistance\":true,\"elementAdvantage\":false}",Json)!;
        var copy=JsonSerializer.Deserialize<WeaponReplayConditions>(JsonSerializer.Serialize(legacy,Json),Json)!;
        Assert.True(copy.ProperDistance); Assert.False(copy.ElementAdvantage); Assert.False(copy.BossFieldsSpecified);
        Assert.Equal(false,copy.LegacyElementAdvantage);
        Assert.Equal(new MemberHitBonuses(true,false),BossConditionResolver.Resolve(Member().Weapon,copy,true));
        using var fresh=JsonDocument.Parse(JsonSerializer.Serialize(new WeaponReplayConditions { BossDistance=35,BossWeakElement="Fire" },Json));
        Assert.False(fresh.RootElement.TryGetProperty("properDistance",out _));
        Assert.False(fresh.RootElement.TryGetProperty("elementAdvantage",out _));
        Assert.Equal(35,fresh.RootElement.GetProperty("bossDistance").GetInt32());
    }

    [Fact]
    public void Mixed_team_replay_summary_and_weapon_reference_use_member_bonuses()
    {
        var members=new[] { Member("a") with { Weapon=Meta("a",25,45,"Fire") },
            Member("b") with { Weapon=Meta("b",45,100,"Water") } };
        var c=new SkillReplayConditions { Combat=new() { DurationFrames=60,BossDistance=35,BossWeakElement="Fire",Trace=true } };
        var replay=SkillReplay.Run(members,Graph(),c);
        Assert.Equal(143*replay.Members[0].Hits,replay.Members[0].Damage);
        Assert.Equal(100*replay.Members[1].Hits,replay.Members[1].Damage);
        Assert.Equal(replay.Members.Sum(m=>m.Damage),replay.TotalDamage);
        Assert.All(replay.Events.Where(e=>e.Kind=="damage"),e=> {
            Assert.Equal(e.Source=="a",e.Hit.ProperDistance); Assert.Equal(e.Source=="a",e.Hit.ElementAdvantage); });
        var prepared=PreparedSkillReplay.Create(members,Graph(),c);
        Parallel.For(0,4,_=>Assert.Equal(replay.TotalDamage,prepared.Run().TeamDamage));
        var weapon=WeaponReplay.Run(members.Select(m=>m.Weapon).ToArray(),c.Combat);
        Assert.Equal(replay.TotalDamage,weapon.TotalDamage["client_f32"]);
        var legacy=SkillReplay.Run(members,Graph(),new() { Combat=new() { DurationFrames=60,ProperDistance=true,ElementAdvantage=true } });
        Assert.All(legacy.Members,m=>Assert.Equal(143*m.Hits,m.Damage));
        Assert.Equal(legacy.TotalDamage,PreparedSkillReplay.Create(members,Graph(),legacy.Conditions).Run().TeamDamage);
    }

    [Fact]
    public void Skill_damage_receives_element_but_never_normal_distance_bonus()
    {
        var member=Member("a",[10]) with { Weapon=Meta() };
        var c=new SkillReplayConditions { Combat=new() { DurationFrames=1,BossDistance=35,BossWeakElement="Fire",Trace=true } };
        var result=SkillReplay.Run([member],Graph(F(10,75,value:10000)),c);
        var skill=Assert.Single(result.Events,e=>e.Kind=="damage" && e.Effect=="function:10");
        Assert.False(skill.Hit.ProperDistance); Assert.True(skill.Hit.ElementAdvantage); Assert.Equal(110,skill.Value);
        var normal=Assert.Single(result.Events,e=>e.Kind=="damage" && e.Effect!="function:10");
        Assert.True(normal.Hit.ProperDistance); Assert.True(normal.Hit.ElementAdvantage); Assert.Equal(143,normal.Value);
    }
}

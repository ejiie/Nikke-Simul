using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Data;

namespace Nikke.Sync.Tests;

public class CombatProfileCatalogTests
{
    private static JsonObject Catalog()
    {
        var source=new CombatProfileSource("fixture",new string('a',64),"sha256:"+new string('a',64),"synthetic","en");
        var entries=new[]{new CombatMemberProfile("a","normal1","SR",45,100,"Fire"),new("b","normal2","SR",45,100,"Water"),
            new("c","exception","SR",25,45,"Electronic"),new("d","launcher","RL",0,0,"Iron")};
        return JsonNode.Parse(Wire.Serialize(new {schemaVersion=1,source,characters=entries.ToDictionary(p=>p.CharacterId)}))!.AsObject();
    }
    [Fact] public void Groups_are_aggregated_from_characters_and_exceptions_are_visible()
    {
        var catalog=new CombatProfileCatalog(Catalog());var response=catalog.Describe("runtime");
        var sr=response.WeaponRanges.Single(g=>g.WeaponType=="SR");
        Assert.Equal(3,sr.CharacterCount);Assert.Equal("c",Assert.Single(sr.Exceptions).CharacterId);
        Assert.Equal(45,sr.Ranges.Single(r=>r.IsTypical).Min);
        Assert.False(catalog.Member("d").RangeBonusAvailable);
        Assert.Equal("rl_zero_range_no_bonus_unverified",catalog.Member("d").Diagnostic);
        Assert.Equal("/editor/assets/ui/code-electric.png",response.Elements.Single(e=>e.Value=="Electronic").IconUrl);
        Assert.False(response.GameVerified);
    }
    [Fact] public void Missing_catalog_or_profile_is_never_replaced_with_weapon_defaults()
    {
        Assert.Throws<InvalidOperationException>(()=>new CombatProfileCatalog(null));
        var catalog=new CombatProfileCatalog(Catalog());
        Assert.Throws<ArgumentException>(()=>catalog.Member("unknown"));
        var bad=Catalog();bad["characters"]!["a"]!["element"]="Electric";
        var error=Assert.Throws<CombatProfileException>(()=>new CombatProfileCatalog(bad)).Error;
        Assert.Equal("combatProfiles.characters.a.element",error.Field);
        Assert.Equal("unsupported_value",error.Reason);
    }

    public static IEnumerable<object[]> MalformedFields()
    {
        foreach(var field in new[]{"bonusRangeMin","bonusRangeMax","element"})
        {
            yield return new object[]{field,"missing","null"};
            yield return new object[]{field,"null","null"};
            foreach(var json in new[]{"false","{}","[]","0.5",field=="element"?"0":"\"0\"","2147483648"})
                yield return new object[]{field,"wrong_type",json};
        }
    }
    [Theory,MemberData(nameof(MalformedFields))]
    public void Missing_null_and_wrong_types_remain_distinct_before_DTO_construction(string field,string reason,string json)
    {
        var node=Catalog();var member=node["characters"]!["a"]!.AsObject();
        if(reason=="missing")member.Remove(field);else member[field]=JsonNode.Parse(json);
        var error=Assert.Throws<CombatProfileException>(()=>new CombatProfileCatalog(node)).Error;
        Assert.Equal("combat_profile_invalid",error.Code);
        Assert.Equal("a",error.CharacterId);
        Assert.Equal("combatProfiles.characters.a."+field,error.Field);
        Assert.Equal(reason,error.Reason);
        Assert.Contains(error.Field,error.Message);
    }
    [Theory]
    [InlineData("SG",0,25)]
    [InlineData("RL",0,0)]
    [InlineData("SR",25,45)]
    [InlineData("SR",45,100)]
    public void Explicit_zero_and_character_specific_ranges_are_preserved(string weapon,int min,int max)
    {
        var node=Catalog();var member=node["characters"]!["a"]!;
        member["weaponType"]=weapon;member["bonusRangeMin"]=min;member["bonusRangeMax"]=max;
        var actual=new CombatProfileCatalog(node).Member("a");
        Assert.Equal(min,actual.BonusRangeMin);Assert.Equal(max,actual.BonusRangeMax);
        Assert.Equal(weapon!="RL",actual.RangeBonusAvailable);
    }
    [Theory]
    [InlineData(-1,100,"bonusRangeMin")]
    [InlineData(101,100,"bonusRangeMin")]
    [InlineData(45,101,"bonusRangeMax")]
    [InlineData(45,-1,"bonusRangeMax")]
    [InlineData(45,25,"bonusRangeMax")]
    public void Invalid_range_values_report_the_bad_field(int min,int max,string field)
    {
        var node=Catalog();node["characters"]!["a"]!["bonusRangeMin"]=min;node["characters"]!["a"]!["bonusRangeMax"]=max;
        var error=Assert.Throws<CombatProfileException>(()=>new CombatProfileCatalog(node)).Error;
        Assert.Equal("combatProfiles.characters.a."+field,error.Field);Assert.Equal("out_of_range",error.Reason);
    }
    [Theory]
    [InlineData("source")]
    [InlineData("characters")]
    [InlineData("schemaVersion")]
    public void Malformed_catalog_container_has_a_diagnostic_instead_of_a_deserialization_exception(string field)
    {
        var node=Catalog();node.Remove(field);
        var error=Assert.Throws<CombatProfileException>(()=>new CombatProfileCatalog(node)).Error;
        Assert.Equal("combatProfiles."+field,error.Field);Assert.Equal("missing",error.Reason);
        Assert.Null(error.CharacterId);
    }
}

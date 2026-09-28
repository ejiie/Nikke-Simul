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
        Assert.Throws<InvalidDataException>(()=>new CombatProfileCatalog(bad));
    }
}

using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Data;
using Nikke.Storage;

namespace Nikke.Sync.Tests;

public class CharacterEditTests
{
    internal static JsonNode Catalog() => JsonNode.Parse("""
        {"characters":[{"characterUid":"101","rarityCode":"ssr","manufacturerCode":"pilgrim","combatClassCode":"attacker","weaponCode":"sniper_rifle"}],
         "supportDefinitions":[
           {"definitionUid":"1000","rawSlot":"head","combatClassCode":"attacker","tier":10},
           {"definitionUid":"9000","rawSlot":"head","combatClassCode":"attacker","tier":9},
           {"definitionUid":"900","kindCode":"favorite","rarityCode":"ssr","weaponCode":"sniper_rifle","favoriteCharacterUid":"101","levels":[{"level":1},{"level":2},{"level":3}]},
           {"definitionUid":"901","kindCode":"collection","rarityCode":"sr","weaponCode":"assault_rifle","levels":[{"level":15}]}],
         "overloadOptions":[
           {"definitionUid":"StatAtk","sign":1,"legalValues":[{"unscaledValue":1181},{"unscaledValue":1463}]},
           {"definitionUid":"StatChargeTime","sign":-1,"legalValues":[{"unscaledValue":140},{"unscaledValue":609}]}],
         "cubes":[{"definitionUid":"5","levels":[{"level":7},{"level":8}]}]}
        """)!;

    private static AccountSnapshot Snapshot()
    {
        var snapshot=new SnapshotNormalizer().Normalize(Fixtures.Raw(),Fixtures.Game(),"account","synthetic-account",83,"raw");
        snapshot.Characters[0]=snapshot.Characters[0] with {CollectionId="0",CollectionGrade="none",CollectionLevel=0,FavoriteStage=0};
        return snapshot;
    }
    private static AccountSnapshot Edit(AccountSnapshot snapshot,CharacterBuild build) =>
        CharacterEditService.Preview(snapshot,"101",new(snapshot.Id,build),Catalog());
    private static CharacterBuild WithLine(CharacterBuild build,int index,decimal value)
    {
        var copy=Wire.Read<CharacterBuild>(Wire.Serialize(build));
        copy.Equipment[0].Lines[index]=copy.Equipment[0].Lines[index] with {NormalizedValue=value};
        return copy;
    }

    [Fact] public void Preview_keeps_observation_identity_and_original_snapshot()
    {
        var original=Snapshot();var before=Wire.Serialize(original);
        var next=Edit(original,original.Characters[0] with {Level=500,Name="forged name",CatalogKnown=false,NativeLevel=9999,CombatSupport="forged"});
        Assert.Equal(before,Wire.Serialize(original));
        Assert.Equal(500,next.Characters[0].Level);
        Assert.Equal("manual",next.Characters[0].BuildSource);
        Assert.Equal(original.Characters[0].Name,next.Characters[0].Name);
        Assert.Equal(original.Characters[0].NativeLevel,next.Characters[0].NativeLevel);
        Assert.Equal(original.Characters[0].CombatSupport,next.Characters[0].CombatSupport);
        Assert.Equal(original.RawManifestId,next.RawManifestId);
    }
    [Fact] public void Changed_overload_value_is_signed_and_no_longer_claims_raw_provenance()
    {
        var original=Snapshot();var old=original.Characters[0].Equipment[0];
        original.ManualOverrides.Add(new("101","head",2,"locked",old.Fingerprint,DateTimeOffset.UtcNow));
        var next=Edit(original,WithLine(original.Characters[0],1,-.0609m));
        var changed=next.Characters[0].Equipment[0];var line=changed.Lines[1];
        Assert.Equal(-.0609m,line.NormalizedValue);Assert.Equal(2,line.ValueTier);
        Assert.Equal("manual",line.Source);Assert.Null(line.RawValue);Assert.Null(line.OptionId);
        Assert.Equal("unknown",line.LockState);Assert.NotEqual(old.Fingerprint,changed.Fingerprint);
        Assert.Equal(Wire.Serialize(old.Lines[0]),Wire.Serialize(changed.Lines[0]));
        Assert.Empty(next.ManualOverrides);Assert.Single(original.ManualOverrides);
    }
    [Theory]
    [InlineData(.0609)] // Display magnitude must not be submitted as positive charge-time change.
    [InlineData(-.0608)] // No invented value between legal tiers.
    public void Illegal_overload_value_is_rejected(decimal value)
    {
        var snapshot=Snapshot();Assert.Throws<ArgumentException>(()=>Edit(snapshot,WithLine(snapshot.Characters[0],1,value)));
    }
    [Fact] public void Duplicate_options_and_overloads_on_T9_are_rejected()
    {
        var snapshot=Snapshot();var build=Wire.Read<CharacterBuild>(Wire.Serialize(snapshot.Characters[0]));
        build.Equipment[0].Lines[1]=build.Equipment[0].Lines[0] with {LineIndex=2};
        Assert.Throws<ArgumentException>(()=>Edit(snapshot,build));
        build=Wire.Read<CharacterBuild>(Wire.Serialize(snapshot.Characters[0]));
        build.Equipment[0]=build.Equipment[0] with {ItemId="9000",Tier=9};
        Assert.Throws<ArgumentException>(()=>Edit(snapshot,build));
        build.Equipment[0]=build.Equipment[0] with {Lines=Enumerable.Range(1,3).Select(i=>new EquipmentLine {LineIndex=i,Presence="absent"}).ToList()};
        Assert.Equal(9,Edit(snapshot,build).Characters[0].Equipment[0].Tier);
    }
    [Fact] public void Growth_and_skill_boundaries_are_enforced()
    {
        var snapshot=Snapshot();var build=snapshot.Characters[0];
        Assert.Throws<ArgumentException>(()=>Edit(snapshot,build with {LimitBreak=2,Core=1}));
        Assert.Throws<ArgumentException>(()=>Edit(snapshot,build with {Core=8}));
        Assert.Throws<ArgumentException>(()=>Edit(snapshot,build with {Bond=41}));
        Assert.Throws<ArgumentException>(()=>Edit(snapshot,build with {Skills=new() { ["1"]=11,["2"]=8,["3"]=9 }}));
        Assert.Equal(7,Edit(snapshot,build with {Core=7}).Characters[0].Core);
        Assert.Equal(0,Edit(snapshot,build with {LimitBreak=0,Core=0,Bond=10}).Characters[0].Core);
    }
    [Fact] public void Core_and_limit_break_edits_preserve_bond_40_for_an_Elysion_build()
    {
        var snapshot=Snapshot();var catalog=Catalog();
        catalog["characters"]![0]!["manufacturerCode"]="elysion";
        catalog["characters"]![0]!["maximumBondLevel"]=40;
        snapshot.Characters[0]=snapshot.Characters[0] with {Core=7,Bond=40};
        foreach(var (limit,core) in new[]{(3,6),(3,0),(2,0)})
        {
            var next=CharacterEditService.Preview(snapshot,"101",new(snapshot.Id,snapshot.Characters[0] with {LimitBreak=limit,Core=core}),catalog);
            Assert.Equal(40,next.Characters[0].Bond);
        }
    }
    [Fact] public void Normal_catalog_bond_cap_rejects_31_but_accepts_30()
    {
        var snapshot=Snapshot();var catalog=Catalog();
        catalog["characters"]![0]!["manufacturerCode"]="elysion";
        catalog["characters"]![0]!["maximumBondLevel"]=30;
        Assert.Throws<ArgumentException>(()=>CharacterEditService.Preview(snapshot,"101",new(snapshot.Id,snapshot.Characters[0] with {Bond=31}),catalog));
        Assert.Equal(30,CharacterEditService.Preview(snapshot,"101",new(snapshot.Id,snapshot.Characters[0] with {Bond=30}),catalog).Characters[0].Bond);
    }
    [Fact] public void Favorite_requires_owner_weapon_and_growth_conditions()
    {
        var snapshot=Snapshot();var build=snapshot.Characters[0];
        Assert.Throws<ArgumentException>(()=>Edit(snapshot,build with {CollectionId="900",CollectionGrade="SSR",CollectionLevel=2,FavoriteStage=3,Bond=20}));
        Assert.Throws<ArgumentException>(()=>Edit(snapshot,build with {CollectionId="901",CollectionGrade="SR",CollectionLevel=15}));
        var favorite=build with {CollectionId="900",CollectionGrade="SSR",CollectionLevel=2,FavoriteStage=3,Bond=30};
        Assert.Equal(3,Edit(snapshot,favorite).Characters[0].FavoriteStage);
        Assert.Throws<ArgumentException>(()=>Edit(snapshot,favorite with {FavoriteStage=2}));
    }
    [Fact] public void Cube_level_is_shared_without_mutating_the_previous_builds()
    {
        var snapshot=Snapshot();snapshot.Characters.Add(snapshot.Characters[0] with {CharacterId="102"});
        var next=Edit(snapshot,snapshot.Characters[0] with {CubeLevel=8});
        Assert.All(next.Characters,c=>Assert.Equal(8,c.CubeLevel));
        Assert.All(snapshot.Characters,c=>Assert.Equal(7,c.CubeLevel));
        Assert.Equal(8,next.CubeLevels["5"]);Assert.Equal("manual",next.AccountStatSources["cube:5"]);
        Assert.Throws<ArgumentException>(()=>Edit(snapshot,snapshot.Characters[0] with {CubeId="unknown"}));
    }
    [Fact] public void Stale_snapshot_and_wrong_character_are_rejected()
    {
        var snapshot=Snapshot();
        Assert.Throws<InvalidOperationException>(()=>CharacterEditService.Preview(snapshot,"101",new("stale",snapshot.Characters[0]),Catalog()));
        Assert.Throws<ArgumentException>(()=>Edit(snapshot,snapshot.Characters[0] with {CharacterId="102"}));
    }
}

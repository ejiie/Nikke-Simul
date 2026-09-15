using Nikke.Contracts;
using Nikke.Data;

namespace Nikke.Compute.Tests;

public sealed class OverloadAdapterTests
{
    [Fact] public void Catalog_preserves_signed_tiers_slots_and_excludes_unmodeled_effects()
    {
        var ids=new[]{"a","b","c","d","e"};var snapshot=new AccountSnapshot{GameSnapshotId="game",Characters=ids.Select(id=>new CharacterBuild {
            CharacterId=id,Equipment=id=="a"?[new(){Slot="head",Tier=10,Lines=[new(){LineIndex=2,Presence="present",OptionType="StatAtk",NormalizedValue=.1m}]}]:[]}).ToList()};
        var game=new GameSnapshot{Id="game",OptionSteps=new(){["atk_pct"]=[.1m,.2m],["charge_speed_pct"]=[.1m,.2m],["accuracy_pct"]=[.1m],["element_bonus"]=[.1m]}};
        var before=Wire.Serialize(snapshot);var charge=ids.ToDictionary(id=>id,id=>id=="a");
        var space=ComputeOverloadCatalog.Generate(snapshot,game,ids,charge,new());
        Assert.Equal(before,Wire.Serialize(snapshot));Assert.Equal(3,space.Candidates.Length);
        Assert.All(space.Candidates,c=>{Assert.Equal("a",c.After.CharacterId);Assert.Equal("head",c.After.Slot);Assert.Equal(2,c.After.Line);});
        Assert.Equal(new[]{-.2,-.1},space.Candidates.Where(c=>c.After.Option=="StatChargeTime").Select(c=>c.After.Value));
        Assert.DoesNotContain(space.Candidates,c=>c.After.Option is "StatAccuracyCircle" or "IncElementDmg");
        charge["a"]=false;Assert.Single(ComputeOverloadCatalog.Generate(snapshot,game,ids,charge,new()).Candidates);
    }
}

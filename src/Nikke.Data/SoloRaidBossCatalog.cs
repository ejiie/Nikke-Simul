using Nikke.Contracts;

namespace Nikke.Data;

public sealed class SoloRaidBossCatalogService(string presentationRoot)
{
    private static readonly SoloRaidBoss Dummy=new("dummy","더미 보스",null);
    public SoloRaidBossCatalog Read()
    {
        var path=Path.Combine(presentationRoot,"solo-raid-bosses.json");
        if(!File.Exists(path))return new(1,"dummy",[Dummy],[new("catalog",null,"boss_catalog_not_prepared",false,"보스 목록 준비 필요")],false);
        try
        {
            var catalog=Wire.Read<SoloRaidBossCatalog>(File.ReadAllText(path));
            if(catalog is null || catalog.SchemaVersion!=1 || catalog.DefaultBossId!="dummy" || catalog.Bosses is null || catalog.Diagnostics is null || catalog.Bosses.Count==0
                || catalog.Bosses.Any(b=>b is null) || catalog.Bosses.Select(b=>b.Id).Distinct().Count()!=catalog.Bosses.Count
                || catalog.Bosses[0]!=Dummy)throw new InvalidOperationException("boss_catalog_invalid");
            foreach(var boss in catalog.Bosses.Skip(1))
                if(string.IsNullOrWhiteSpace(boss.Name) || !System.Text.RegularExpressions.Regex.IsMatch(boss.Name,"[가-힣]") || boss.Season is null or <1 || boss.Id!="solo-raid-"+boss.Season
                    || boss.ImageUrl is null || !System.Text.RegularExpressions.Regex.IsMatch(boss.ImageUrl,@"^/editor/assets/bosses/[a-f0-9]{32}\.png$"))
                    throw new InvalidOperationException("boss_catalog_invalid");
            return catalog;
        }
        catch(System.Text.Json.JsonException ex){throw new InvalidOperationException("boss_catalog_invalid",ex);}
    }
    public SoloRaidBoss Resolve(string? id) => id is null or "dummy"?Dummy:
        Read().Bosses.SingleOrDefault(b=>b.Id==id)??throw new ArgumentException("boss_id_unknown");
}

public sealed class SoloRaidBossAttributeCatalogService(string presentationRoot)
{
    public SoloRaidBossAttributeCatalog Read()
    {
        var path=Path.Combine(presentationRoot,"solo-raid-boss-attributes.json");
        if(!File.Exists(path))return new(1,"solo_raid_boss_static_attributes",[],[],
            [new("catalog",null,"boss_attributes_not_prepared",false,"보스 속성 준비 필요")],false,null);
        try
        {
            var catalog=Wire.Read<SoloRaidBossAttributeCatalog>(File.ReadAllText(path));
            if(catalog.SchemaVersion!=1 || catalog.Kind!="solo_raid_boss_static_attributes" || catalog.Bosses is null || catalog.Diagnostics is null || catalog.Fields is null
                || catalog.Bosses.Any(b=>b is null || b.Id!="solo-raid-"+b.Season) || catalog.Bosses.Select(b=>b.Id).Distinct().Count()!=catalog.Bosses.Count)
                throw new InvalidOperationException("boss_attributes_invalid");
            foreach(var boss in catalog.Bosses)
            {
                var available=boss.Status=="available";
                if(!available && (boss.Status!="unavailable" || boss.Reason is null || boss.Challenge is not null || boss.Element is not null))
                    throw new InvalidOperationException("boss_attributes_invalid");
                if(available && (boss.Challenge?.Stats is null || boss.Parts is null || boss.Core is null || boss.Ladder is null || boss.Unconfirmed is null
                    || boss.DefenceRatio is null || boss.DefenceRatioRate is null || boss.HpRatio is null))
                    throw new InvalidOperationException("boss_attributes_invalid");
            }
            return catalog;
        }
        catch(System.Text.Json.JsonException ex){throw new InvalidOperationException("boss_attributes_invalid",ex);}
    }
}

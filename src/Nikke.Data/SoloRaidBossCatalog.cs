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
    private const string Invalid="boss_attributes_invalid";
    // Strict: every non-defaulted constructor member must be present and non-null, numbers are never read from
    // strings, and StrictGraph rejects null collection elements and any non-nullable member at any depth.
    // A null on a nullable member is accepted only when Validate() can explain it (declared in "unconfirmed" or
    // implied by another field); anything else is a corrupt file, never an unconfirmed value.
    private static readonly System.Text.Json.JsonSerializerOptions Strict=new(Wire.Json){RespectRequiredConstructorParameters=true,NumberHandling=System.Text.Json.Serialization.JsonNumberHandling.Strict,RespectNullableAnnotations=true};
    public SoloRaidBossAttributeCatalog Read()
    {
        var path=Path.Combine(presentationRoot,"solo-raid-boss-attributes.json");
        if(!File.Exists(path))return new(1,"solo_raid_boss_static_attributes",[],[],
            [new("catalog",null,"boss_attributes_not_prepared",false,"보스 속성 준비 필요")],false,null);
        try
        {
            var catalog=System.Text.Json.JsonSerializer.Deserialize<SoloRaidBossAttributeCatalog>(File.ReadAllText(path),Strict)
                ?? throw new InvalidOperationException(Invalid);
            StrictGraph.RequireNoNullViolations(catalog,Invalid);
            Validate(catalog);
            return catalog;
        }
        catch(System.Text.Json.JsonException ex){throw new InvalidOperationException(Invalid,ex);}
    }
    private static void Require(bool condition,string why)
    {
        if(!condition)throw new InvalidOperationException(Invalid,new InvalidDataException(why));
    }
    private static void Validate(SoloRaidBossAttributeCatalog catalog)
    {
        Require(catalog.SchemaVersion==1 && catalog.Kind=="solo_raid_boss_static_attributes","header");
        Require(catalog.Source is not null,"source");
        Require(catalog.Diagnostics.All(d=>d.Season is not null),"diagnostic season");
        Require(catalog.Bosses.Select(b=>b.Id).Distinct().Count()==catalog.Bosses.Count && catalog.Bosses.All(b=>b.Season>=1 && b.Id=="solo-raid-"+b.Season),"boss ids");
        foreach(var boss in catalog.Bosses)
            if(boss.Status=="unavailable")ValidateUnavailable(boss);
            else{Require(boss.Status=="available","status "+boss.Id);ValidateAvailable(boss);}
    }
    private static void ValidateUnavailable(BossAttributes boss)
    {
        Require(!string.IsNullOrWhiteSpace(boss.Reason),"reason "+boss.Id);
        Require(boss.ImageResource is null && boss.MonsterId is null && boss.MonsterModelId is null && boss.ModelPrefab is null
            && boss.StatEnhanceGroup is null && boss.Element is null && boss.HpRatio is null && boss.DefenceRatio is null
            && boss.DefenceRatioRate is null && boss.AttackRatio is null && boss.Challenge is null && boss.Ladder is null
            && boss.Parts is null && boss.Core is null && boss.Unconfirmed is null,"unavailable carries attributes "+boss.Id);
    }
    private static void ValidateAvailable(BossAttributes boss)
    {
        var id=boss.Id;
        Require(boss.Reason is null,"reason on available "+id);
        Require(boss.ImageResource is not null && boss.MonsterId is not null && boss.MonsterModelId is not null && boss.StatEnhanceGroup is not null
            && boss.HpRatio is not null && boss.DefenceRatio is not null && boss.DefenceRatioRate is not null && boss.AttackRatio is not null
            && boss.Challenge is not null && boss.Ladder is not null && boss.Parts is not null && boss.Core is not null && boss.Unconfirmed is not null,"required attribute "+id);
        var declared=boss.Unconfirmed!.ToHashSet();
        // Explicit nulls are legitimate only when the preparer declared them unconfirmed.
        void Declared(bool isNull,string code,string where){if(isNull)Require(declared.Contains(code),$"undeclared null {where} ({code}) {id}");}
        Declared(boss.ModelPrefab is null,"model_prefab","modelPrefab");
        Declared(boss.Element is null,"element","element");
        if(boss.Element is not null)Declared(boss.Element.WeakKey is null,"weak_element","element.weakKey");
        var challenge=boss.Challenge!;
        Declared(challenge.Stats is null,"challenge_level_stats","challenge.stats");
        Require(challenge.LevelChangeGroupId>=0,"levelChangeGroupId "+id);
        if(challenge.LevelChangeGroupId==0)Require(challenge.LevelChange is null,"levelChange without group "+id);
        else if(challenge.LevelChange is null)Declared(true,"level_change_rows","challenge.levelChange");
        else
        {
            Require(challenge.LevelChange.GroupId==challenge.LevelChangeGroupId,"levelChange group "+id);
            var steps=challenge.LevelChange.Steps;
            Require(steps.Count>0 && steps.Select(s=>s.Step).Distinct().Count()==steps.Count,"levelChange steps "+id);
            var last=steps.Max(s=>s.Step);
            foreach(var step in steps)
            {
                Declared(step.Stats is null,$"level_change_step_{step.Step}_stats",$"levelChange.steps[{step.Step}].stats");
                // A null upper bound means "no limit" and only the last step can be open-ended.
                Require(step.RangeTo is not null || step.Step==last,$"open-ended step {step.Step} is not last {id}");
            }
        }
        var core=boss.Core!;
        if(core.Kind=="unconfirmed")
        {
            Require(core.Evidence is null && core.PartIds.Count==0,"unconfirmed core carries data "+id);
            Require(declared.Contains("core_position"),"undeclared unconfirmed core "+id);
        }
        else Require(core.Evidence is not null && core.PartIds.Count>0,"core without evidence "+id);
    }
}

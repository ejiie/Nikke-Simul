using System.Text.Json;
using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Engine;

namespace Nikke.Data;

public sealed class CombatProfileCatalog
{
    public static readonly IReadOnlyList<string> Elements = Array.AsReadOnly(new[] { "Fire", "Water", "Wind", "Iron", "Electronic" });
    private readonly Dictionary<string,CombatMemberProfile> members;
    private readonly CombatProfileSource source;
    public CombatProfileCatalog(JsonObject? node)
    {
        if(node is null) throw new InvalidOperationException("combat_profile_catalog_missing: prepare pinned public roster catalog");
        const string root="combatProfiles";
        if(Integer(node,"schemaVersion",root)!=1)throw new CombatProfileException(root+".schemaVersion","unsupported_value");
        var sourceNode=Object(node,"source",root);
        source=new(Text(sourceNode,"path",root+".source"),Text(sourceNode,"sha256",root+".source"),
            Text(sourceNode,"version",root+".source"),Text(sourceNode,"origin",root+".source"),Text(sourceNode,"locale",root+".source"));
        if(source.Sha256.Length!=64 || source.Sha256.Any(c=>!Uri.IsHexDigit(c)) || source.Version!="sha256:"+source.Sha256)
            throw new CombatProfileException(root+".source","hash_mismatch");
        var characters=Object(node,"characters",root);
        members=new(StringComparer.Ordinal);
        foreach(var (id,_) in characters)
        {
            var member=Object(characters,id,root+".characters",id);
            var path=root+".characters."+id;
            // Preserve missing/null/type errors before a non-nullable DTO can turn them into zero.
            var min=Integer(member,"bonusRangeMin",path,id);
            var max=Integer(member,"bonusRangeMax",path,id);
            var element=Text(member,"element",path,id);
            var characterId=Text(member,"characterId",path,id);
            var name=Text(member,"name",path,id);
            var weaponType=Text(member,"weaponType",path,id);
            if(min is <0 or >100)throw new CombatProfileException(path+".bonusRangeMin","out_of_range",id);
            if(max is <0 or >100 || max<min)throw new CombatProfileException(path+".bonusRangeMax","out_of_range",id);
            if(!Elements.Contains(element))throw new CombatProfileException(path+".element","unsupported_value",id);
            if(characterId!=id)throw new CombatProfileException(path+".characterId","id_mismatch",id);
            if(weaponType is not ("AR" or "SMG" or "SG" or "SR" or "MG" or "RL"))
                throw new CombatProfileException(path+".weaponType","unsupported_value",id);
            members.Add(id,new(characterId,name,weaponType,min,max,element));
        }
    }
    private static JsonNode Required(JsonObject parent,string key,string path,string? id)
    {
        if(!parent.TryGetPropertyValue(key,out var value))throw new CombatProfileException(path+"."+key,"missing",id);
        return value??throw new CombatProfileException(path+"."+key,"null",id);
    }
    private static JsonObject Object(JsonObject parent,string key,string path,string? id=null) =>
        Required(parent,key,path,id) as JsonObject??throw new CombatProfileException(path+"."+key,"wrong_type",id);
    private static int Integer(JsonObject parent,string key,string path,string? id=null)
    {
        var value=Required(parent,key,path,id);
        if(value is JsonValue scalar && scalar.GetValueKind()==JsonValueKind.Number && scalar.TryGetValue<int>(out var number))return number;
        throw new CombatProfileException(path+"."+key,"wrong_type",id);
    }
    private static string Text(JsonObject parent,string key,string path,string? id=null)
    {
        var value=Required(parent,key,path,id);
        if(value is not JsonValue scalar || scalar.GetValueKind()!=JsonValueKind.String)
            throw new CombatProfileException(path+"."+key,"wrong_type",id);
        var text=scalar.GetValue<string>();
        if(string.IsNullOrWhiteSpace(text))throw new CombatProfileException(path+"."+key,"unsupported_value",id);
        return text;
    }
    public CombatMemberProfile Member(string id) => members.GetValueOrDefault(id)
        ?? throw new ArgumentException("combat_member_profile_missing:"+id);
    public CombatConditionCatalog Describe(string runtimeId)
    {
        var groups=members.Values.GroupBy(p=>p.WeaponType).OrderBy(g=>g.Key,StringComparer.Ordinal).Select(g=> {
            var ranges=g.GroupBy(p=>(p.BonusRangeMin,p.BonusRangeMax)).OrderByDescending(r=>r.Count())
                .ThenBy(r=>r.Key.BonusRangeMin).ThenBy(r=>r.Key.BonusRangeMax).ToArray();
            var typical=ranges[0].Key;
            return new WeaponRangeGroup(g.Key,g.Count(),ranges.Select(r=>new WeaponRangeVariant(r.Key.BonusRangeMin,r.Key.BonusRangeMax,
                r.Count(),r.Key==typical,r.Select(p=>p.CharacterId).Order(StringComparer.Ordinal).ToArray())).ToArray(),
                g.Where(p=>(p.BonusRangeMin,p.BonusRangeMax)!=typical).OrderBy(p=>p.CharacterId,StringComparer.Ordinal).ToArray(),
                g.Any(p=>p.RangeBonusAvailable),g.Select(p=>p.Diagnostic).OfType<string>().Distinct().ToArray());
        }).ToArray();
        return new(runtimeId,1,source,groups,Elements.Select(e=>new CombatElementChoice(e,
            "/editor/assets/ui/code-"+(e=="Electronic"?"electric":e.ToLowerInvariant())+".png")).ToArray());
    }
}

public sealed partial class RuntimeReplayService
{
    private CombatProfileCatalog Profiles() => catalog["combatProfiles"] is {} node && node is not JsonObject
        ? throw new CombatProfileException("combatProfiles","wrong_type") : new(catalog["combatProfiles"] as JsonObject);
    private CombatProfileCatalog? ProfilesForConditions(WeaponReplayConditions conditions)
    {
        BossConditionResolver.Validate(conditions);
        // Historical catalogs still support explicit legacy replays. A requested new condition requires its source.
        if(catalog["combatProfiles"] is null && conditions.BossDistance is null && conditions.BossWeakElement is null)
            return null;
        return Profiles();
    }
    private static WeaponReplayMember WithCombatProfile(WeaponReplayMember member,CombatProfileCatalog? profiles)
    {
        if(profiles is null)return member;
        var profile=profiles.Member(member.CharacterId);
        if(profile.WeaponType!=member.Weapon.weaponType)
            throw new CombatProfileException("combatProfiles.characters."+member.CharacterId+".weaponType","weapon_mismatch",member.CharacterId);
        return member with {BonusRangeMin=profile.BonusRangeMin,BonusRangeMax=profile.BonusRangeMax,Element=profile.Element};
    }
    public CombatConditionCatalog CombatConditions() => Profiles().Describe(runtimeId);
    public DeckCombatProfiles DeckConditions(AccountSnapshot snapshot,IReadOnlyList<string> ids)
    {
        if(ids.Count is <1 or >5 || ids.Distinct().Count()!=ids.Count || ids.Any(id=>!snapshot.Characters.Any(c=>c.CharacterId==id)))
            throw new ArgumentException("combat_profiles_require_owned_unique_one_to_five_members");
        var profiles=Profiles();
        return new(runtimeId,snapshot.Id,ids.Select(profiles.Member).ToArray());
    }
}

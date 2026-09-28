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
        if(node["schemaVersion"]?.GetValue<int>() != 1) throw new InvalidDataException("unsupported_combat_profile_schema");
        source=node["source"]!.Deserialize<CombatProfileSource>(Wire.Json) ?? throw new InvalidDataException("combat_profile_source_missing");
        if(source.Sha256.Length!=64 || source.Sha256.Any(c=>!Uri.IsHexDigit(c)) || source.Version!="sha256:"+source.Sha256)
            throw new InvalidDataException("invalid_combat_profile_source");
        members=node["characters"]!.AsObject().ToDictionary(p=>p.Key,p=>p.Value!.Deserialize<CombatMemberProfile>(Wire.Json)!);
        foreach(var (id,p) in members)
            if(p is null || id!=p.CharacterId || string.IsNullOrWhiteSpace(p.Name)
                || p.WeaponType is not ("AR" or "SMG" or "SG" or "SR" or "MG" or "RL")
                || !Elements.Contains(p.Element) || p.BonusRangeMin<0 || p.BonusRangeMax>100 || p.BonusRangeMin>p.BonusRangeMax)
                throw new InvalidDataException("invalid_combat_profile:"+id);
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
    private CombatProfileCatalog Profiles() => new(catalog["combatProfiles"] as JsonObject);
    private WeaponReplayMember WithCombatProfile(WeaponReplayMember member,WeaponReplayConditions conditions)
    {
        BossConditionResolver.Validate(conditions);
        // Historical catalogs still support explicit legacy replays. A requested new condition requires its source.
        if(catalog["combatProfiles"] is null && conditions.BossDistance is null && conditions.BossWeakElement is null)
            return member;
        var profile=Profiles().Member(member.CharacterId);
        if(profile.WeaponType!=member.Weapon.weaponType)throw new InvalidDataException("combat_profile_weapon_mismatch:"+member.CharacterId);
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

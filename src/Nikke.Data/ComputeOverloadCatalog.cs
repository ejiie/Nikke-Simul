using System.Collections.Immutable;
using System.Text.Json;
using Nikke.Analysis;
using Nikke.Contracts;
using Nikke.Engine;
using Nikke.Engine.Skills;

namespace Nikke.Data;

public static class ComputeOverloadCatalog
{
    public static CandidateSpace Generate(AccountSnapshot snapshot,GameSnapshot game,IReadOnlyList<string> ids,
        IReadOnlyDictionary<string,bool> chargeWeapons,WeaponReplayConditions combat)
    {
        if(snapshot.GameSnapshotId!=game.Id || ids.Count!=5 || ids.Distinct().Count()!=5)
            throw new ArgumentException("invalid_ol_catalog_input");
        var lines=new List<Nikke.Analysis.EquipmentLine>();var options=new List<AllowedOption>();
        foreach(var id in ids)
        {
            var character=snapshot.Characters.SingleOrDefault(c=>c.CharacterId==id)??throw new ArgumentException("character_missing");
            if(!chargeWeapons.TryGetValue(id,out var charge))throw new ArgumentException("unsupported_character");
            foreach(var gear in character.Equipment.Where(e=>e.Tier==10))
            {
                if(!SnapshotNormalizer.Parts.Contains(gear.Slot))throw new ArgumentException("invalid_ol_slot");
                foreach(var line in gear.Lines.Where(l=>l.Presence=="present"))
                {
                    if(line.OptionType is not {} option || line.NormalizedValue is not {} value)
                        throw new ArgumentException("incomplete_ol_line");
                    VirtualOverload.Apply(snapshot,game,[new(id,gear.Slot,line.LineIndex,option,value)]);
                    // Canonicalize aliases for duplicate-on-equipment checks, preserving the physical line.
                    var canonical=SnapshotNormalizer.OptionKeys.First(p=>p.Value==SnapshotNormalizer.OptionKeys[option]).Key;
                    lines.Add(new(id,gear.Slot,line.LineIndex,canonical,(double)value));
                }
                foreach(var definition in SnapshotNormalizer.OptionKeys.DistinctBy(p=>p.Value))
                {
                    if(!game.OptionSteps.TryGetValue(definition.Value,out var tiers) || tiers.Length==0)continue;
                    if(tiers.Any(v=>v<=0))throw new ArgumentException("invalid_authoritative_ol_tiers");
                    var option=definition.Key;bool negative=option is "StatChargeTime" or "StatAccuracyCircle";
                    bool effect=option switch {
                        "StatAtk" or "StatAmmoLoad"=>true,
                        "StatChargeTime" or "StatChargeDamage"=>charge,
                        "StatCritical" or "StatCriticalDamage"=>combat.CritMode=="sample",
                        "IncElementDmg"=>combat.ElementAdvantage,
                        _=>false // Accuracy/misses and survival/defense do not affect this damage model.
                    };
                    options.Add(new(id,gear.Slot,option,tiers.Select(v=>(double)(negative?-v:v)).ToImmutableArray(),effect,effect,
                        option is "StatAmmoLoad" or "StatChargeTime"));
                }
            }
        }
        return OverloadCandidates.Generate(game.Id,lines,options);
    }
}

public sealed partial class RuntimeReplayService
{
    public CandidateSpace ComputeCandidates(AccountSnapshot original,GameSnapshot game,ExperimentRequest request)
    {
        var snapshot=VirtualOverload.Apply(original,game,request.OlChanges??[]);
        var conditions=request.Conditions.Deserialize<SkillReplayConditions>(Wire.Json)??throw new ArgumentException("missing_conditions");
        var charge=request.CharacterIds.ToDictionary(id=>id,id=>catalog["characters"]?[id]?["weapon"]?["isChargeWeapon"]?.GetValue<bool>()
            ??throw new ArgumentException("unsupported_character"));
        return ComputeOverloadCatalog.Generate(snapshot,game,request.CharacterIds,charge,conditions.Combat);
    }
}

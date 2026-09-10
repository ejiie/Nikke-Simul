using System.Text.Json.Nodes;
using Nikke.Contracts;

namespace Nikke.Data;

// Validates local simulation edits; raw observations and identity fields are never replaced.
public static class CharacterEditService
{
    public static AccountSnapshot Preview(AccountSnapshot snapshot, string characterId, CharacterEditRequest request, JsonNode presentation)
    {
        if(snapshot.Id!=request.ExpectedSnapshotId)throw new InvalidOperationException("스펙이 갱신되었습니다. 다시 열고 저장하세요.");
        var current=snapshot.Characters.SingleOrDefault(c=>c.CharacterId==characterId)??throw new KeyNotFoundException();
        var edited=request.Build??throw new ArgumentException("편집할 스펙이 없습니다.");
        if(edited.CharacterId!=characterId)throw new ArgumentException("캐릭터가 일치하지 않습니다.");
        var character=presentation["characters"]?.AsArray().SingleOrDefault(c=>c?["characterUid"]?.ToString()==characterId)
            ??throw new ArgumentException("캐릭터 카탈로그를 확인하세요.");
        var rarity=character["rarityCode"]?.ToString();var maxLimit=rarity=="ssr"?3:rarity=="sr"?2:0;
        if(edited.Level is null or <1 or >10000 || edited.LimitBreak is null or <0 || edited.LimitBreak>maxLimit
            || edited.Core is null or <0 or >7 || edited.Core>0&&(rarity!="ssr"||edited.LimitBreak!=3)
            || edited.Bond is null or <0 or >40)throw new ArgumentException("레벨·돌파·코어·호감도 범위를 확인하세요.");
        // Growth controls do not mutate bond. Apply the catalog cap, including Overspec.
        var bondMax=character["maximumBondLevel"]?.GetValue<int>()??40;
        if(edited.Bond>bondMax)throw new ArgumentException($"이 캐릭터의 호감도 상한은 {bondMax}입니다.");
        if(edited.Skills is null||edited.Skills.Count!=3||new[]{"1","2","3"}.Any(k=>!edited.Skills.TryGetValue(k,out var n)||n is null or <1 or >10))throw new ArgumentException("스킬 레벨은 1~10입니다.");
        var supports=(presentation["supportDefinitions"]?.AsArray()??[]).OfType<JsonObject>().ToArray();
        var options=(presentation["overloadOptions"]?.AsArray()??[]).OfType<JsonObject>().ToArray();
        var cubes=(presentation["cubes"]?.AsArray()??[]).OfType<JsonObject>().ToArray();
        if(edited.CubeId!=current.CubeId||edited.CubeLevel!=current.CubeLevel)
        {
            if(edited.CubeId=="0") { if(edited.CubeLevel!=0)throw new ArgumentException("미장착 큐브 레벨은 0입니다."); }
            else if(edited.CubeId is null || edited.CubeLevel is null or <1 or >15 || !cubes.Any(c=>c["definitionUid"]?.ToString()==edited.CubeId&&c["levels"]!.AsArray().Any(l=>l?["level"]?.GetValue<int>()==edited.CubeLevel)))throw new ArgumentException("큐브 종류·레벨을 확인하세요.");
        }
        if(edited.CollectionId!=current.CollectionId||edited.CollectionLevel!=current.CollectionLevel||edited.FavoriteStage!=current.FavoriteStage||edited.CollectionGrade!=current.CollectionGrade || edited.CollectionGrade=="SSR"&&(edited.Bond!=current.Bond||edited.LimitBreak!=current.LimitBreak))
        {
            if(edited.CollectionId=="0")
            { if(edited.CollectionLevel!=0||edited.FavoriteStage!=0||edited.CollectionGrade!="none")throw new ArgumentException("소장품 미장착 값을 확인하세요."); }
            else
            {
                var def=supports.SingleOrDefault(c=>c["definitionUid"]?.ToString()==edited.CollectionId && c["kindCode"]?.ToString() is "collection" or "favorite")??throw new ArgumentException("소장품 종류를 확인하세요.");
                var favorite=def["kindCode"]!.ToString()=="favorite";
                if(def["weaponCode"]?.ToString()!=character["weaponCode"]?.ToString() || edited.CollectionGrade!=def["rarityCode"]?.ToString().ToUpperInvariant()
                    || favorite && (def["favoriteCharacterUid"]?.ToString()!=characterId || edited.Bond<30 || edited.LimitBreak<2)
                    || edited.FavoriteStage!=(favorite?edited.CollectionLevel+1:0)
                    || !def["levels"]!.AsArray().Any(l=>l?["level"]?.GetValue<int>()==(favorite?edited.FavoriteStage:edited.CollectionLevel)))throw new ArgumentException("소장품의 무기·단계·호감도 조건을 확인하세요.");
            }
        }
        if(edited.Equipment is null || edited.Equipment.Count!=4 || !SnapshotNormalizer.Parts.ToHashSet().SetEquals(edited.Equipment.Select(e=>e.Slot)))throw new ArgumentException("장비 4부위를 확인하세요.");
        var equipment=new List<Equipment>();
        foreach(var item in edited.Equipment)
        {
            var old=current.Equipment.Single(e=>e.Slot==item.Slot);
            if(Wire.Serialize(item)==Wire.Serialize(old)){equipment.Add(old);continue;}
            if(item.Tier is null or <0 or >10 || item.Level is null or <0 or >5 || !new int?[]{0,1,2,3,4,7}.Contains(item.Manufacturer))throw new ArgumentException("장비 티어·강화·기업을 확인하세요.");
            if(item.Tier==0) { if(item.Level!=0||item.ItemId!="0")throw new ArgumentException("장비 미장착 값을 확인하세요."); }
            else if(!supports.Any(d=>d["definitionUid"]?.ToString()==item.ItemId&&d["rawSlot"]?.ToString()==item.Slot&&d["combatClassCode"]?.ToString()==character["combatClassCode"]?.ToString()&&d["tier"]?.GetValue<int>()==item.Tier))throw new ArgumentException("장비의 클래스·부위·종류가 일치하지 않습니다.");
            if(item.Lines is null || item.Lines.Count!=3 || !new[]{1,2,3}.ToHashSet().SetEquals(item.Lines.Select(l=>l.LineIndex)))throw new ArgumentException("옵션 3줄을 확인하세요.");
            var lines=new List<EquipmentLine>();
            foreach(var line in item.Lines)
            {
                var prior=old.Lines.Single(l=>l.LineIndex==line.LineIndex);
                if(Wire.Serialize(line)==Wire.Serialize(prior)&&item.ItemId==old.ItemId&&item.Tier==old.Tier){lines.Add(prior);continue;}
                if(line.Presence=="absent"){lines.Add(new(){LineIndex=line.LineIndex,Presence="absent",OptionId="0",LockState="not_applicable",Source="manual"});continue;}
                var type=line.OptionType=="StatDef"?"IncHurtDef":line.OptionType;
                var option=options.SingleOrDefault(o=>o?["definitionUid"]?.ToString()==type);
                if(item.Tier!=10||line.Presence!="present"||option is null||line.NormalizedValue is null||line.Unit!="ratio")throw new ArgumentException("T10 오버로드 옵션을 확인하세요.");
                var signed=option["sign"]!.GetValue<int>();
                var legal=option["legalValues"]!.AsArray().Select(v=>v!["unscaledValue"]!.GetValue<decimal>()/10000m).ToArray();
                var tier=Array.IndexOf(legal,line.NormalizedValue.Value*signed)+1;
                if(tier==0)throw new ArgumentException("오버로드 단계표에 없는 수치입니다.");
                lines.Add(new(){LineIndex=line.LineIndex,Presence="present",OptionType=type,NormalizedValue=line.NormalizedValue,Unit="ratio",ValueTier=tier,Source="manual",LockState="unknown"});
            }
            if(item.Tier!=10&&lines.Any(l=>l.Presence!="absent"))throw new ArgumentException("T10 이외 장비에는 오버로드를 설정할 수 없습니다.");
            if(lines.Where(l=>l.Presence=="present").GroupBy(l=>l.OptionType=="StatDef"?"IncHurtDef":l.OptionType).Any(g=>g.Count()>1))throw new ArgumentException("같은 장비에 동일한 오버로드 옵션을 중복 설정할 수 없습니다.");
            var replacement=item with { Lines=lines,Fingerprint="" };
            replacement.Fingerprint=Wire.Hash(Wire.Canonical(JsonNode.Parse(Wire.Serialize(replacement))));equipment.Add(replacement);
        }
        var build=current with {BuildSource="manual",Level=edited.Level,LimitBreak=edited.LimitBreak,Core=edited.Core,Bond=edited.Bond,Skills=edited.Skills,
            CubeId=edited.CubeId,CubeLevel=edited.CubeLevel,CollectionId=edited.CollectionId,CollectionGrade=edited.CollectionGrade,CollectionLevel=edited.CollectionLevel,FavoriteStage=edited.FavoriteStage,Equipment=equipment};
        var next=Wire.Read<AccountSnapshot>(Wire.Serialize(snapshot));
        next.Characters[next.Characters.FindIndex(c=>c.CharacterId==characterId)]=build;
        if(build.CubeId is not null and not "0" && build.CubeLevel is >=1 && (build.CubeId!=current.CubeId||build.CubeLevel!=current.CubeLevel))
        {
            next.CubeLevels[build.CubeId]=build.CubeLevel.Value;next.AccountStatSources["cube:"+build.CubeId]="manual";
            for(var i=0;i<next.Characters.Count;i++)if(next.Characters[i].CubeId==build.CubeId)next.Characters[i]=next.Characters[i] with {CubeLevel=build.CubeLevel};
        }
        next.ManualOverrides.RemoveAll(m=>m.CharacterId==characterId&&build.Equipment.Any(e=>e.Slot==m.Slot&&e.Fingerprint!=m.Fingerprint));
        return next;
    }
}

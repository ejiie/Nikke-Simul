using System.Security.Cryptography;
using System.Text.Json.Nodes;
using Nikke.Contracts;
using Nikke.Data;

namespace Nikke.Sync.Tests;

public sealed class CalculationTests : IDisposable
{
    private readonly string folder = Path.Combine(Path.GetTempPath(), "nikke-p02-test-" + Guid.NewGuid().ToString("N"));
    private readonly CalculationService service;
    public CalculationTests()
    {
        var row = Enumerable.Repeat("0", 37).ToArray(); row[0] = "1";
        foreach (var start in new[] { 1, 9, 17 }) { row[start] = "100"; row[start+1] = "100"; for (int w=0; w<6; w++) row[start+2+w]="100"; }
        row[26]="1"; row[27]="1"; foreach (var start in new[] {28,31,34}) { row[start]="10"; row[start+1]="10"; row[start+2]="10"; }
        var files = new Dictionary<string,string> {
            ["stat_table.csv"] = string.Join(',', row),
            ["equip_stat_table.json"] = """{"Attacker":{"10":{"head":{"HP":100,"ATK":100,"DEF":0}}}}""",
            ["cube_base_table.json"] = """{"1":{"HP":10,"ATK":20,"DEF":30}}""",
            ["cube_effect_table.json"] = """{"5":{"effects":[{"type":"MaxHp","values":[10]},{"type":"PartsDamage","values":[20],"conditional":true}]}}""",
            ["roledata_clean.json"] = """{"101":{"class":"Attacker","manufacturer":"Pilgrim","weapon":"Sniper Rifle","basicAttack":{"multiplier":50,"chargeDamage":2.5,"coreHitBonus":1},"weaponData":{"isChargeWeapon":true}}}""",
            ["name_codes.json"] = """{"101":"테스트"}""",
            ["parsed_nikke.json"] = """{"테스트":{"rarity":"SSR"}}""",
            ["collection.json"] = """{"_stat_table":{"R0":{"hp":1,"atk":2,"def":3,"skill_lv":1},"SR0":{"hp":10,"atk":20,"def":30,"skill_lv":1},"SR15":{"hp":100,"atk":200,"def":300,"skill_lv":4}},"common":{"def_pct":{"buff_type":"def_pct","R":[10,10,10,10],"SR":[20,20,20,20]}},"SR":{"buff_type":"charge_dmg_mag_pct","R":[1,2,3,4],"SR":[5,6,7,8]}}"""
        };
        var hashes = new JsonObject(); foreach (var pair in files) hashes[pair.Key] = Convert.ToHexStringLower(SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(pair.Value)));
        var id = Wire.Hash(Wire.Canonical(hashes)); Directory.CreateDirectory(Path.Combine(folder,id));
        foreach (var pair in files) File.WriteAllText(Path.Combine(folder,id,pair.Key),pair.Value);
        File.WriteAllText(Path.Combine(folder,"current.json"), new JsonObject { ["id"] = id, ["fileHashes"] = hashes }.ToJsonString());
        service = new(folder);
    }
    private static AccountSnapshot Snapshot(string grade = "none", int level = 0) => new() {
        Id="synthetic-snapshot", GameSnapshotId="synthetic-mapping", Consoles = new() { ["1001"]=0,["1101"]=0,["1204"]=0 },
        Characters = [new() { CharacterId="101", Name="테스트", Level=1, LimitBreak=0, Core=0, Bond=1,
            CubeId="0", CubeLevel=0, CollectionId=grade=="none"?"0":"900", CollectionGrade=grade, CollectionLevel=level,
            Equipment = new[] { "head","torso","arm","leg" }.Select(slot => new Equipment { Slot=slot,Tier=0,Level=0,Manufacturer=0,
                Lines=Enumerable.Range(1,3).Select(i=>new EquipmentLine { LineIndex=i, Presence="absent" }).ToList() }).ToList() }] };
    [Theory]
    [InlineData("none",0,0)] [InlineData("R",0,2)] [InlineData("SR",0,20)] [InlineData("SSR",0,200)] [InlineData("SSR",2,200)]
    public void Collection_grade_and_zero_based_level_are_preserved(string grade,int level,double addedAttack)
    {
        var r=service.Calculate(Snapshot(grade,level),"101"); Assert.Empty(r.Issues);
        Assert.Equal(110+addedAttack,r.Total!.ATK);
        Assert.Equal(grade=="SSR"?.08:grade=="SR"?.05:grade=="R"?.01:0,r.BasicHit!.ChargeMultiplierBonus);
        Assert.Equal(.5,r.BasicHit.Coefficient); // percent-number converted exactly once
    }
    [Fact]
    public void Missing_inputs_are_not_silently_filled_with_defaults()
    {
        var s=Snapshot(); s.Consoles=null;
        Assert.Null(service.Calculate(s,"101").Total);
        Assert.Null(service.Calculate(Snapshot(),"101",400).Total);
        var invalid=Snapshot("R",16); Assert.Null(service.Calculate(invalid,"101").Total);
        var cube=Snapshot() with { Characters=[Snapshot().Characters[0] with {CubeId="5",CubeLevel=15}] };
        Assert.Null(service.Calculate(cube,"101").Total);
    }
    [Fact]
    public void Normalized_charge_is_not_divided_again_and_equal_attack_lines_group()
    {
        var s=Snapshot(); var c=s.Characters[0]; var eq=c.Equipment[0];
        eq.Lines.Clear(); eq.Lines.AddRange([
            new() {Presence="present",OptionType="StatAtk",Unit="ratio",NormalizedValue=.014m},
            new() {Presence="present",OptionType="StatAtk",Unit="ratio",NormalizedValue=.014m},
            new() {Presence="present",OptionType="StatChargeDamage",Unit="ratio",RawUnit="Integer",RawValue=8705,NormalizedValue=.8705m}]);
        var r=service.Calculate(s,"101"); Assert.Equal(113,r.Total!.ATK); Assert.Equal(.8705,r.BasicHit!.ChargeAdd);
        Assert.Equal(r.Total.ATK,r.Steps.Sum(x=>x.Value.ATK));
    }
    [Fact]
    public void Conditional_cube_effect_is_not_applied_as_passive()
    {
        var s=Snapshot() with {Characters=[Snapshot().Characters[0] with {CubeId="5",CubeLevel=1}]};
        var r=service.Calculate(s,"101"); Assert.Equal(132,r.Total!.HP); Assert.Equal(130,r.Total.ATK);
        Assert.Equal(0,r.BasicHit!.PartsDamage); Assert.Contains("cube:PartsDamage:conditional",r.DeferredEffects);
    }
    [Fact]
    public void Accuracy_option_is_known_but_not_a_damage_multiplier()
    {
        var s=Snapshot(); s.Characters[0].Equipment[0].Lines.Add(new() { Presence="present",OptionType="StatAccuracyCircle",Unit="ratio",NormalizedValue=-.1m });
        var r=service.Calculate(s,"101"); Assert.Empty(r.Issues); Assert.Equal(110,r.Total!.ATK);
        Assert.Contains("overload:StatAccuracyCircle:weapon_runtime_or_rng:P03",r.DeferredEffects);
    }
    [Fact]
    public void Calculation_data_hash_detects_tampering()
    {
        var sub=Directory.GetDirectories(folder).Single(); File.AppendAllText(Path.Combine(sub,"cube_base_table.json")," ");
        Assert.Throws<InvalidDataException>(()=>new CalculationService(folder));
    }
    public void Dispose() => Directory.Delete(folder,true);
}

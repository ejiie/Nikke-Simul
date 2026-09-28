using System.Globalization;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using Nikke.Contracts;
using Nikke.Core.Combat;
using Nikke.Core.Stats;

namespace Nikke.Data;

// Wire migration and persistence only. All arithmetic remains owned by Core.
public sealed class HitCalculationService(string archiveRoot)
{
    private static readonly JsonSerializerOptions Strict = new(Wire.Json) { UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow };
    public static HitContext ReadInput(JsonObject input, int schemaVersion)
    {
        if (schemaVersion is not (2 or 3)) throw new ArgumentException("unsupported_hit_schema: expected 2 or 3");
        if (input is null || !input.ContainsKey("statAttack")) throw new ArgumentException("statAttack_required");
        var copy = (JsonObject)input.DeepClone();
        // Canonical property spelling prevents duplicate case variants from winning by order.
        var names = typeof(HitContext).GetProperties().Select(p => JsonNamingPolicy.CamelCase.ConvertName(p.Name)).ToHashSet();
        if (copy.Any(p => !names.Contains(p.Key))) throw new ArgumentException("unknown_hit_field: use canonical camelCase names");
        if (schemaVersion == 2)
        {
            if (copy.ContainsKey("statDamageRatio") || copy.ContainsKey("defenceRatioRate"))
                throw new ArgumentException("schema2_cannot_contain_schema3_rates");
            copy["statDamageRatio"] = 1; copy["defenceRatioRate"] = 0;
        }
        try
        {
            static void RequireGrid(JsonNode node, string field, int places)
            {
                // Check the JSON lexeme before double/decimal can round or underflow it.
                string text = node.ToJsonString();
                var parts = text.ToLowerInvariant().Split('e');
                if (text.Length > 256 || text[0] == '"' || parts.Length > 2
                    || !int.TryParse(parts.Length == 2 ? parts[1] : "0", NumberStyles.AllowLeadingSign,
                        CultureInfo.InvariantCulture, out var exponent)) throw new ArgumentException(field + "_invalid_number");
                int dot = parts[0].IndexOf('.'), decimals = dot < 0 ? 0 : parts[0].Length-dot-1;
                string digits = parts[0].Replace(".", "").TrimStart('-','0');
                if (digits.Length == 0) return;
                int trailing = digits.Length-digits.TrimEnd('0').Length;
                if ((long)exponent-decimals+trailing+places < 0)
                    throw new ArgumentException(field + (places == 0 ? "_must_be_integer_never_truncated" : "_requires_exact_1_per_10000_units"));
            }
            foreach (var key in new[] { "statAttack", "defense" })
                if (copy[key] is {} value) RequireGrid(value,key,0);
            foreach (var key in new[] { "attackBuffs", "runtimeAttackBuffs", "attackFlatBuffs" })
            {
                if (!copy.ContainsKey(key)) continue;
                if (copy[key] is not JsonArray buffs) throw new ArgumentException(key + "_must_be_array");
                foreach (var node in buffs)
                {
                    if (node is not JsonObject buff) throw new ArgumentException("invalid_attack_buff");
                    bool flat = key == "attackFlatBuffs";
                    var allowed = flat ? new[] { "source", "amount", "exactAmount" } : new[] { "source", "rate", "stacks", "rawRate10000" };
                    if (buff.Any(p => !allowed.Contains(p.Key))) throw new ArgumentException("unknown_attack_buff_field");
                    string exactKey = flat ? "exactAmount" : "rawRate10000", valueKey = flat ? "amount" : "rate";
                    if (buff[exactKey] is {} raw)
                    {
                        long value = JsonSerializer.Deserialize<long?>(raw.ToJsonString(), new JsonSerializerOptions {
                            Converters = { new HitWire.ExactIntegerConverter() } })!.Value;
                        if (!buff.ContainsKey(valueKey)) buff[valueKey] = flat ? (double)value : (double)((decimal)value / 10000);
                    }
                    if (!buff.ContainsKey(valueKey)) throw new ArgumentException(valueKey + "_required");
                    if (buff[valueKey] is not {} supplied) throw new ArgumentException(valueKey + "_required");
                    RequireGrid(supplied,valueKey,flat ? 0 : 4);
                }
            }
            return copy.Deserialize<HitContext>(Strict) ?? throw new ArgumentException("missing_hit_input");
        }
        catch (JsonException ex) { throw new ArgumentException("invalid_hit_json: " + ex.Message, ex); }
    }

    public static HitContext ApplyExperimentOverrides(HitContext input, JsonObject? overrides)
    {
        if (overrides is null) return input;
        if (overrides.Any(p => p.Key is not ("statDamageRatio" or "defenceRatioRate" or "runtimeAttackBuffs" or "attackFlatBuffs")))
            throw new ArgumentException("unsupported_hit_override");
        var node = JsonSerializer.SerializeToNode(input, Wire.Json)!.AsObject();
        foreach (var field in overrides) node[field.Key] = field.Value?.DeepClone();
        return ReadInput(node, 3);
    }

    public static HitCalculationResponse Evaluate(HitCalculationRequest request, JsonObject? sourceArtifact = null)
    {
        if (!HitWire.Policies.Contains(request.RoundingPolicy)) throw new ArgumentException("unknown_rounding_policy");
        if (request.ObservedDamage is {} observed && (!double.IsFinite(observed) || observed < 1
            || observed != Math.Truncate(observed) || observed > 9007199254740991d)) throw new ArgumentException("invalid_observed_damage");
        var input = ReadInput(request.Input, request.InputSchemaVersion);
        ClientFloatResult client;
        try { client = HitCalculator.CalculateClient(input); }
        catch (OverflowException ex) { throw new ArgumentException("hit_integer_overflow: " + ex.Message, ex); }
        catch (ArgumentException ex) { throw new ArgumentException("invalid_client_f32_input: " + ex.Message, ex); }
        var candidates = HitWire.Policies.Select(policy => {
            try
            {
                var result = HitCalculator.Evaluate(input, policy, request.ObservedDamage);
                return new HitCandidate(policy, result.Damage, result.Residual, result.RelativeError,
                    result.Terms.Select(t => new HitAuditTerm(t.Name,t.Before,t.After,t.Operation)).ToArray(), "available",
                    ExactDamage: policy == HitWire.DefaultPolicy ? client.Damage.ToString(CultureInfo.InvariantCulture) : null);
            }
            catch (Exception ex) when (ex is ArgumentException or OverflowException)
            { return new HitCandidate(policy,null,null,null,[],"unavailable",ex.Message); }
        }).ToArray();
        var selected = candidates.Single(c => c.Policy == request.RoundingPolicy);
        if (selected.Status != "available") throw new ArgumentException("selected_policy_unavailable: " + selected.ErrorCode);
        var converted = request.InputSchemaVersion == 2;
        return new(Guid.NewGuid().ToString("N"), DateTimeOffset.UtcNow, HitWire.SchemaVersion, HitCalculator.Version,
            "provisional_rounding", JsonSerializer.SerializeToNode(input, Wire.Json)!.AsObject(), (JsonObject)request.Input.DeepClone(),
            new(request.InputSchemaVersion, 3, converted, converted ? "v2_to_v3_neutral_rates" : "none",
                converted ? new JsonObject { ["statDamageRatio"]=1, ["defenceRatioRate"]=0 } : new()),
            client.Attack, client.Attack.ToString(CultureInfo.InvariantCulture), request.ObservedDamage,
            request.RoundingPolicy, selected, candidates,
            ["experimental_source_mapping", "historical_policies_ignore_statDamageRatio_and_defenceRatioRate",
             "audit_terms_are_binary64_display_values_use_exact_fields_for_integers"], sourceArtifact?.DeepClone().AsObject());
    }

    public HitCalculationResponse Calculate(HitCalculationRequest request)
    { var result = Evaluate(request); Save(result); return result; }
    public HitCalculationResponse Import(JsonObject artifact)
    {
        try
        {
            var comparison = artifact["comparison"] as JsonObject ?? artifact;
            int schema = artifact["inputSchemaVersion"]?.GetValue<int>() ?? throw new ArgumentException("saved_input_schema_required");
            var input = comparison["input"]?.AsObject() ?? throw new ArgumentException("saved_input_required");
            var request = new HitCalculationRequest(input, comparison["observedDamage"]?.GetValue<double>(), schema,
                comparison["selectedPolicy"]?.GetValue<string>() ?? artifact["roundingPolicy"]?.GetValue<string>() ?? HitWire.DefaultPolicy);
            var result = Evaluate(request, artifact); Save(result); return result;
        }
        catch (InvalidOperationException ex) { throw new ArgumentException("invalid_saved_hit_artifact", ex); }
    }
    private void Save(HitCalculationResponse result)
    { Directory.CreateDirectory(archiveRoot); File.WriteAllText(Path.Combine(archiveRoot,result.Id+".json"),Wire.Serialize(result)); }
    public HitCalculationResponse Read(string id)
    {
        if (!Guid.TryParseExact(id,"N",out _)) throw new ArgumentException("invalid_hit_record_id");
        var path = Path.Combine(archiveRoot,id+".json");
        return File.Exists(path) ? Wire.Read<HitCalculationResponse>(File.ReadAllText(path)) : throw new KeyNotFoundException();
    }
}

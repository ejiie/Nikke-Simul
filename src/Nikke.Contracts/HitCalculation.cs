using System.Globalization;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using System.Text.Json.Serialization.Metadata;

namespace Nikke.Contracts;

public static class HitWire
{
    public const int SchemaVersion = 3;
    public const string DefaultPolicy = "client_f32";
    public static readonly IReadOnlyList<string> Policies = Array.AsReadOnly(
        new[] { DefaultPolicy, "legacy_term_floor", "final_round_even", "nested_floor" });
    public static DefaultJsonTypeInfoResolver Resolver()
    {
        var resolver = new DefaultJsonTypeInfoResolver();
        resolver.Modifiers.Add(type => {
            foreach (var property in type.Properties)
                if (property.PropertyType == typeof(long?) && property.Name is "rawRate10000" or "exactAmount")
                    property.CustomConverter = new ExactIntegerConverter();
        });
        return resolver;
    }
    // New exact integer fields are strings on output. Old safe numeric inputs remain readable.
    public sealed class ExactIntegerConverter : JsonConverter<long?>
    {
        public override long? Read(ref Utf8JsonReader reader, Type type, JsonSerializerOptions options)
        {
            if (reader.TokenType == JsonTokenType.Null) return null;
            if (reader.TokenType == JsonTokenType.String && long.TryParse(reader.GetString(),
                NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out long exact)) return exact;
            if (reader.TokenType == JsonTokenType.Number && reader.TryGetInt64(out long safe)
                && safe is >= -9007199254740991L and <= 9007199254740991L) return safe;
            throw new JsonException("exact_integer_requires_decimal_string_or_safe_integer_number");
        }
        public override void Write(Utf8JsonWriter writer, long? value, JsonSerializerOptions options)
        { if (value is {} integer) writer.WriteStringValue(integer.ToString(CultureInfo.InvariantCulture)); else writer.WriteNullValue(); }
    }
}

public record HitCalculationRequest(JsonObject Input, double? ObservedDamage, int InputSchemaVersion,
    string RoundingPolicy = HitWire.DefaultPolicy);
public record HitConversion(int OriginalSchemaVersion, int TargetSchemaVersion, bool Converted,
    string Method, JsonObject AppliedDefaults);
public record HitAuditTerm(string Name, double Before, double After, string Operation);
public record HitCandidate(string Policy, double? Damage, double? Residual, double? RelativeError,
    IReadOnlyList<HitAuditTerm> Terms, string Status, string? ErrorCode = null, string? ExactDamage = null);
public record HitCalculationResponse(string Id, DateTimeOffset CreatedAt, int InputSchemaVersion,
    string RulesVersion, string Status, JsonObject Input, JsonObject OriginalInput,
    HitConversion Conversion, double EffectiveAttack, string ExactEffectiveAttack, double? ObservedDamage,
    string SelectedPolicy, HitCandidate SelectedCandidate, IReadOnlyList<HitCandidate> Candidates,
    IReadOnlyList<string> Limitations, JsonObject? SourceArtifact = null);

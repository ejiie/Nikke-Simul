using System.Text;
using System.Text.Json.Nodes;

namespace Nikke.Data;

// E1 contract d7ce350. Reads captured data only; never reconstructs hits from trace.
public static class DamageLogExport
{
    public static JsonObject Read(string replayJson)
    {
        var replay = JsonNode.Parse(replayJson)!.AsObject();
        var log = replay["result"]?["damageLog"];
        return new JsonObject
        {
            ["exportSchemaVersion"] = 1,
            ["collectionStatus"] = log is null ? "not_collected" : log["status"]?.DeepClone(),
            ["replay"] = replay
        };
    }

    public static string Csv(string replayJson)
    {
        var envelope = Read(replayJson);
        var replay = envelope["replay"]!;
        var log = replay["result"]?["damageLog"];
        if (log is not null && log["schemaVersion"]?.GetValue<int>() != 1)
            throw new InvalidOperationException("Unsupported damage log schema; use JSON export.");
        var entries = log?["entries"]?.AsArray();
        if (log is not null && entries is null) throw new InvalidOperationException("Damage log entries are missing.");
        // Metadata survives even a zero-hit or historical replay. Full contexts remain JSON cells.
        var metadata = envelope.DeepClone();
        metadata["replay"]!["result"]?["damageLog"]?.AsObject().Remove("entries");
        var output = new StringBuilder("recordType,frame,seconds,hitId,shotId,damage,cumulativeDamage,entryJson,metadataJson\r\n");
        output.Append("metadata,,,,,,,,").Append(Cell(metadata.ToJsonString())).Append("\r\n");
        if (entries is not null)
            foreach (var entry in entries)
            {
                if (entry is null) throw new InvalidOperationException("Damage log entry is null.");
                output.Append("hit,");
                foreach (var field in new[] { "frame", "seconds", "hitId", "shotId", "damage", "cumulativeDamage" })
                    output.Append(Cell(entry[field]?.ToJsonString() ?? "")).Append(',');
                output.Append(Cell(entry.ToJsonString())).Append(",\r\n");
            }
        return output.ToString();
    }

    private static string Cell(string value) => "\"" + value.Replace("\"", "\"\"") + "\"";
}

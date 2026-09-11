using System.Text;
using System.Text.Json;

namespace Nikke.Data;

// Persistence only: never interpret or regenerate combat results on read/export.
public sealed class SkillReplayArchive(string root)
{
    private readonly string root = Path.GetFullPath(root);

    private string FilePath(string id)
    {
        if (!Guid.TryParseExact(id, "N", out _)) throw new ArgumentException("Invalid skill replay ID");
        return Path.Combine(root, id + ".json");
    }

    private static void ValidateIdentity(string id, string json)
    {
        using var document = JsonDocument.Parse(json);
        if (document.RootElement.ValueKind != JsonValueKind.Object
            || !document.RootElement.TryGetProperty("id", out var storedId)
            || storedId.ValueKind != JsonValueKind.String || storedId.GetString() != id)
            throw new InvalidDataException("Skill replay identity mismatch");
    }

    public void Save(string id, string json)
    {
        var path = FilePath(id);
        ValidateIdentity(id, json);
        Directory.CreateDirectory(root);
        var temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                stream.Write(Encoding.UTF8.GetBytes(json));
                stream.Flush(flushToDisk: true);
            }
            File.Move(temporary, path, overwrite: false);
        }
        finally
        {
            if (File.Exists(temporary)) File.Delete(temporary);
        }
    }

    public string ReadJson(string id)
    {
        var path = FilePath(id);
        if (!File.Exists(path)) throw new KeyNotFoundException();
        var json = File.ReadAllText(path, Encoding.UTF8);
        ValidateIdentity(id, json);
        return json;
    }
}

"""Prepare a local, pinned mapping snapshot from the P00 reference; no account access."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]

def main():
    lock = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8-sig"))
    reference = ROOT / lock["upstream"]["checkout"]
    head = subprocess.check_output(["git", "-c", f"safe.directory={reference.as_posix()}", "-C", str(reference), "rev-parse", "HEAD"], text=True).strip()
    if head != lock["upstream"]["commit"]:
        raise RuntimeError("Upstream commit mismatch")
    changed = subprocess.check_output(["git", "-c", f"safe.directory={reference.as_posix()}", "-C", str(reference), "diff", "--name-only", "HEAD"], text=True).strip()
    if changed:
        raise RuntimeError("Upstream tracked files changed")
    paths = ["data/name_codes.json", "data/base_stat_tables/equipment_skills.json", "site/public/settings.json"]
    data = {p: json.loads((reference / p).read_text(encoding="utf-8-sig")) for p in paths}
    hashes = {p: hashlib.sha256((reference / p).read_bytes()).hexdigest() for p in paths}
    catalog = {"schemaVersion": 1, "source": f"Moris-kr/nikke-calc@{head}; P01 mapping subset",
               "fileHashes": hashes, "names": {k: v for k, v in data[paths[0]].items() if k.isdigit()},
               "optionSteps": {k: v["values"] for k, v in data[paths[1]].items() if isinstance(v, dict) and "values" in v},
               "favoriteGrades": data[paths[2]]["favoriteItems"]}
    catalog["id"] = hashlib.sha256(json.dumps(catalog, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    output = ROOT / "data/local/game-catalog.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Game mapping snapshot prepared: {len(catalog['names'])} character IDs, {len(catalog['favoriteGrades'])} favorite IDs")

if __name__ == "__main__":
    main()

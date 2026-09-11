"""Run only on a Director-approved integrated checkout; never substitute mock engine output."""
import argparse
from contextlib import closing
import copy
import csv
import io
import json
import math
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
import uuid


def verify_exports(saved, retrieved, envelope, csv_text):
    assert saved == retrieved == envelope["replay"], "stored result changed"
    assert envelope["exportSchemaVersion"] == 1 and envelope["collectionStatus"] == "complete"
    result = saved["result"]
    log = result["damageLog"]
    assert log["schemaVersion"] == 1 and log["status"] == "complete"
    assert log["truncated"] is False and log.get("truncationReason") is None
    entries = log["entries"]
    assert entries and len(entries) == log["eventCount"], "missing captured hits"
    assert result["conditions"]["combat"]["durationFrames"] == 10800
    assert len({e["hitId"] for e in entries}) == len(entries)
    assert [e["frame"] for e in entries] == sorted(e["frame"] for e in entries)
    cumulative = 0
    for entry in entries:
        assert entry["source"] == log["characterId"]
        assert 1 <= entry["frame"] <= 10800 and math.isclose(entry["seconds"], entry["frame"] / 60)
        cumulative += entry["damage"]
        assert math.isclose(cumulative, entry["cumulativeDamage"], rel_tol=1e-12, abs_tol=1e-6)
    member = next(m for m in result["members"] if m["characterId"] == log["characterId"])
    assert math.isclose(cumulative, log["totalDamage"], rel_tol=1e-12)
    assert math.isclose(cumulative, member["damage"], rel_tol=1e-12)
    # Real replay metadata contains full skill inputs and exceeds Python's 128 KiB default.
    # This validates the already-loaded response without truncating any field.
    previous_limit = csv.field_size_limit()
    try:
        csv.field_size_limit(max(previous_limit, len(csv_text)))
        rows = list(csv.DictReader(io.StringIO(csv_text)))
    finally:
        csv.field_size_limit(previous_limit)
    assert rows[0]["recordType"] == "metadata" and all(r["recordType"] == "hit" for r in rows[1:])
    expected_metadata = copy.deepcopy(envelope)
    del expected_metadata["replay"]["result"]["damageLog"]["entries"]
    assert json.loads(rows[0]["metadataJson"]) == expected_metadata
    assert [json.loads(r["entryJson"]) for r in rows[1:]] == entries
    assert math.isclose(sum(float(r["damage"]) for r in rows[1:]), cumulative, rel_tol=1e-12)
    for row, entry in zip(rows[1:], entries):
        for field in ("frame", "seconds", "hitId", "shotId", "damage", "cumulativeDamage"):
            assert (None if row[field] == "" else json.loads(row[field])) == entry[field]
    for field in ("accountSnapshotId", "gameSnapshotId", "calculationDataId", "runtimeDataId", "statRulesVersion", "hitRulesVersion"):
        assert saved[field], f"missing {field}"
    return {"hits": len(entries), "distinctShots": len({e["shotId"] for e in entries if e["shotId"] is not None}), "damage": cumulative}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dotnet", required=True)
    parser.add_argument("--source-data", type=Path, required=True, help="Prepared dataRoot, read-only source")
    parser.add_argument("--request", type=Path, required=True, help="Supported snapshot/formation and complete tactic request")
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    expected = subprocess.check_output(["git", "rev-parse", args.expected_commit], cwd=root, text=True).strip()
    assert head == expected, "Checkout must match Director's integrated commit"
    assert not subprocess.check_output(["git", "diff", "HEAD", "--", "src"], cwd=root, text=True).strip(), "Tracked product changes are not allowed for this verification"
    output = root / "artifacts" / "b2" / ("integration-" + uuid.uuid4().hex)
    output.mkdir(parents=True)
    data = output / "data"
    data.mkdir()
    report = {"commit": head, "kind": "actual_engine_http_with_supplied_conditions_not_game_measurement", "status": "failed", "checks": []}
    try:
        # Rebuild the checked-out product so a stale binary cannot satisfy this check.
        subprocess.run([args.dotnet, "build", "src/Nikke.Api/Nikke.Api.csproj", "-c", "Release", "--no-restore"], cwd=root, check=True,
                       stdout=(output / "build.log").open("w"), stderr=subprocess.STDOUT)
        source = args.source_data.resolve()
        for folder in ("runtime", "calculation"):
            shutil.copytree(source / folder, data / folder)
        shutil.copyfile(source / "game-catalog.json", data / "game-catalog.json")
        with closing(sqlite3.connect((source / "accounts.db").as_uri() + "?mode=ro", uri=True)) as original:
            with closing(sqlite3.connect(data / "accounts.db")) as isolated:
                original.backup(isolated)
                # No login/session/raw files are copied. Avoid recovering source jobs in this test.
                isolated.execute("DELETE FROM jobs")
                isolated.execute("DELETE FROM connections")
                isolated.commit()
        request_body = json.loads(args.request.read_text(encoding="utf-8-sig"))
        conditions = request_body["conditions"]
        assert conditions["combat"]["durationFrames"] == 10800
        assert conditions["damageLog"]["characterId"] == "5004"
        assert conditions["combat"].get("critMode", "off") == "off", "Use deterministic conditions"
        assert not conditions["combat"].get("manualCharacterId"), "Manual reclick timing samples RNG; use auto firing for exact replay equality"
        auto = conditions["autoBurst"]
        assert auto["stageDelayMinFrames"] == auto["stageDelayMaxFrames"], "Fix sampled timing for replay comparison"
        tactic = auto["tactic"]
        assert tactic["schemaVersion"] == 1
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = dict(os.environ, NIKKE_DATA_ROOT=str(data), NIKKE_GAME_CATALOG=str(data / "game-catalog.json"), NIKKE_TEST_FIXTURE="1", NIKKE_PORT=str(port), NIKKE_PROJECT_ROOT=str(root))
        token = ""

        def call(path, body=None, method="GET", status=200):
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/{path}", data=None if body is None else json.dumps(body).encode(), method=method,
                                         headers={"Content-Type": "application/json", "X-Nikke-Token": token})
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    code, text = response.status, response.read().decode("utf-8")
            except urllib.error.HTTPError as error:
                code, text = error.code, error.read().decode("utf-8")
            assert code == status, f"{path}: expected {status}, got {code}: {text[:300]}"
            return text

        with (output / "server.log").open("w") as server_log:
            process = subprocess.Popen([args.dotnet, str(root / "src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll")], cwd=root, env=env,
                                       stdout=server_log, stderr=server_log, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                for _ in range(100):
                    try:
                        token = json.loads(call("bootstrap"))["token"]
                        break
                    except urllib.error.URLError:
                        time.sleep(.2)
                else:
                    raise RuntimeError("API startup timeout")
                snapshot = json.loads(call("snapshots/" + request_body["snapshotId"]))
                account = snapshot["accountId"]
                slots = request_body["characterIds"] + [None] * (5 - len(request_body["characterIds"]))
                call(f"accounts/{account}/formation", {"slots": slots}, "PUT")
                saved_tactic = json.loads(call(f"accounts/{account}/burst-tactic", {"snapshotId": snapshot["id"], "formationSlots": slots, "tactic": tactic}, "PUT"))
                restored = json.loads(call(f"accounts/{account}/burst-tactic"))
                assert restored["saved"] == saved_tactic["saved"] and not restored["stale"]
                auto["tactic"] = restored["saved"]["tactic"]
                saved = json.loads(call("runtime/skill-replays", request_body, "POST"))
                base = "runtime/skill-replays/" + saved["id"]
                raw = call(base)
                assert raw == (data / "skill-replays" / (saved["id"] + ".json")).read_text(encoding="utf-8")
                assert call(base + "/export.json") == raw
                envelope = json.loads(call(base + "/damage-log/export.json"))
                report["log"] = verify_exports(saved, json.loads(raw), envelope, call(base + "/damage-log/export.csv"))
                assert saved["result"]["conditions"]["autoBurst"]["tactic"] == auto["tactic"]
                report["checks"].append("180s actual engine -> immutable file -> JSON/CSV and restored tactic")
                repeated = json.loads(call("runtime/skill-replays", request_body, "POST"))
                assert repeated["result"] == saved["result"], "deterministic restored tactic replay changed"
                no_log = copy.deepcopy(request_body)
                no_log["conditions"].pop("damageLog")
                off = json.loads(call("runtime/skill-replays", no_log, "POST"))
                assert off["result"]["members"] == saved["result"]["members"]
                assert json.loads(call("runtime/skill-replays/" + off["id"] + "/damage-log"))["collectionStatus"] == "not_collected"
                report["checks"].append("log off preserves member damage/shots and not_collected")
                legacy = copy.deepcopy(no_log)
                legacy["conditions"]["autoBurst"].pop("tactic")
                old = json.loads(call("runtime/skill-replays", legacy, "POST"))
                explicit_null = copy.deepcopy(legacy)
                explicit_null["conditions"]["autoBurst"]["tactic"] = None
                assert json.loads(call("runtime/skill-replays", explicit_null, "POST"))["result"] == old["result"]
                # Explicit synthetic historical fixture; not presented as a new engine run.
                old["id"] = uuid.uuid4().hex
                old["result"].pop("damageLog", None)
                (data / "skill-replays" / (old["id"] + ".json")).write_text(json.dumps(old))
                assert json.loads(call("runtime/skill-replays/" + old["id"] + "/damage-log"))["collectionStatus"] == "not_collected"
                report["checks"].append("legacy null tactic compatibility and synthetic historical missing field")
                for mutation in ("wrong_log_target", "duplicate", "wrong_stage", "incomplete", "mixed_legacy"):
                    bad = copy.deepcopy(request_body)
                    t = bad["conditions"]["autoBurst"]["tactic"]
                    if mutation == "wrong_log_target": bad["conditions"]["damageLog"]["characterId"] = "absent"
                    if mutation == "duplicate": t["allowedCharacterIds"].append(t["allowedCharacterIds"][0])
                    if mutation == "wrong_stage": t["stage1Priority"] = t["stage3Priority"]
                    if mutation == "incomplete": t["stage1Priority"] = []
                    if mutation == "mixed_legacy": bad["conditions"]["autoBurst"]["burst3Rotation"] = t["burst3Rotation"]
                    call("runtime/skill-replays", bad, "POST", status=400)
                call(f"accounts/{account}/formation", {"slots": [None] * 5}, "PUT")
                assert json.loads(call(f"accounts/{account}/burst-tactic"))["stale"] is True
                report["checks"].append("invalid execution inputs rejected and changed formation stale")
                report["status"] = "passed"
            finally:
                process.terminate()
                process.wait(timeout=10)
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        (output / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(output)


if __name__ == "__main__":
    main()

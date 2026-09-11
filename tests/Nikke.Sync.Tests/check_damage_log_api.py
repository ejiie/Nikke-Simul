"""Isolated HTTP/storage checks with synthetic E1-shaped data, not engine/game validation."""
import argparse
from contextlib import closing
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid

parser = argparse.ArgumentParser()
parser.add_argument("--dotnet", required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
checks = []
run_root = root / "artifacts" / "b2" / ("http-" + uuid.uuid4().hex)
run_root.mkdir(parents=True)
with tempfile.TemporaryDirectory(prefix="store-", dir=run_root) as folder:
    data = Path(folder)
    (data / "game.json").write_text(json.dumps({"id": "synthetic-game", "source": "synthetic", "names": {}}))
    catalog = json.dumps({"schemaVersion": 1, "characters": {k: {"burstConnection": {"step": v}} for k, v in {"i": 1, "ii": 2, "5004": 3}.items()}}).encode()
    runtime_id = hashlib.sha256(catalog).hexdigest()
    (data / "runtime" / runtime_id).mkdir(parents=True)
    (data / "runtime" / runtime_id / "catalog.json").write_bytes(catalog)
    (data / "runtime" / "current.json").write_text(json.dumps({"id": runtime_id}))
    replay_id = uuid.uuid4().hex
    replay = {"id": replay_id, "accountSnapshotId": "synthetic-snapshot", "result": {"damageLog": {"schemaVersion": 1, "status": "complete", "truncated": False, "totalDamage": 3.75, "entries": [
        {"frame": 60, "seconds": 1, "hitId": 9, "shotId": 7, "damage": 1.25, "cumulativeDamage": 1.25},
        {"frame": 60, "seconds": 1, "hitId": 10, "shotId": 7, "damage": 2.5, "cumulativeDamage": 3.75}]}}}
    source = json.dumps(replay)
    (data / "skill-replays").mkdir()
    (data / "skill-replays" / f"{replay_id}.json").write_text(source)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, NIKKE_DATA_ROOT=str(data), NIKKE_GAME_CATALOG=str(data / "game.json"), NIKKE_TEST_FIXTURE="1", NIKKE_PORT=str(port), NIKKE_PROJECT_ROOT=str(root))
    token = ""

    def request(path, payload=None, method="GET"):
        body = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/{path}", data=body, method=method, headers={"Content-Type": "application/json", "X-Nikke-Token": token})
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status, response.read().decode("utf-8"), response.headers
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8"), error.headers

    with (data / "server.log").open("w") as log:
        process = subprocess.Popen([args.dotnet, str(root / "src/Nikke.Api/bin/Release/net10.0/Nikke.Api.dll")], cwd=root, env=env, stdout=log, stderr=log, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            for attempt in range(100):
                try:
                    status, body, _ = request("bootstrap")
                    if status == 200:
                        token = json.loads(body)["token"]
                        break
                except (OSError, urllib.error.URLError):
                    pass
                if process.poll() is not None:
                    raise RuntimeError((data / "server.log").read_text())
                time.sleep(.2)
            else:
                raise RuntimeError("API startup timed out")
            base = f"runtime/skill-replays/{replay_id}"
            assert request(base)[1] == source
            assert request(base + "/export.json")[1] == source
            checks.append("raw read/export exact")
            exported = json.loads(request(base + "/damage-log/export.json")[1])
            assert exported["replay"] == replay and exported["collectionStatus"] == "complete"
            rows = list(csv.DictReader(io.StringIO(request(base + "/damage-log/export.csv")[1])))
            hits = [r for r in rows if r["recordType"] == "hit"]
            assert [r["hitId"] for r in hits] == ["9", "10"]
            assert sum(float(r["damage"]) for r in hits) == 3.75
            assert all(r["seconds"] == "1" for r in hits)
            assert json.loads(rows[0]["metadataJson"])["replay"]["accountSnapshotId"] == "synthetic-snapshot"
            checks.append("JSON/CSV order units sum metadata")
            # Saved reads continue without the runtime catalog.
            (data / "runtime" / "current.json").rename(data / "runtime" / "saved-current.json")
            assert request(base)[1] == source
            (data / "runtime" / "saved-current.json").rename(data / "runtime" / "current.json")
            legacy_id = uuid.uuid4().hex
            (data / "skill-replays" / f"{legacy_id}.json").write_text(json.dumps({"id": legacy_id, "result": {}}))
            assert json.loads(request(f"runtime/skill-replays/{legacy_id}/damage-log")[1])["collectionStatus"] == "not_collected"
            checks.append("historical missing log and catalog independence")
            assert request("runtime/skill-replays/bad")[0] == 400
            assert request("runtime/skill-replays/" + uuid.uuid4().hex)[0] == 404
            checks.append("invalid and missing IDs")
            for conditions in [{"damageLog": {}}, {"autoBurst": {"tactic": {}}}]:
                assert request("runtime/skill-replays", {"conditions": conditions}, "POST")[0] == 409
            checks.append("unintegrated engine features rejected")
            assert request("runtime/skill-replays", {"conditions": {"autoBurst": {"tactics": {"version": 2}}}}, "POST")[0] == 400
            assert request("runtime/skill-replays", {"conditions": []}, "POST")[0] == 400
            with closing(sqlite3.connect(data / "accounts.db")) as db:
                snapshot = {"id": "synthetic-snapshot", "accountId": "synthetic", "characters": [{"characterId": k} for k in ["i", "ii", "5004"]]}
                db.execute("INSERT INTO snapshots VALUES(?,?,?,?)", (snapshot["id"], "synthetic", 1, json.dumps(snapshot)))
                db.execute("INSERT INTO accounts VALUES(?,?)", ("synthetic", snapshot["id"]))
                db.commit()
            slots = ["i", "ii", "5004", None, None]
            assert request("accounts/synthetic/formation", {"slots": slots}, "PUT")[0] == 200
            tactic = {"schemaVersion": 1, "allowedCharacterIds": ["i", "ii", "5004"], "stage1Priority": ["i"], "stage2Priority": ["ii"], "stage3Priority": ["5004"], "burst3Rotation": ["5004"]}
            payload = {"snapshotId": "synthetic-snapshot", "formationSlots": slots, "tactic": tactic}
            draft = dict(payload, tactic={"schemaVersion": 1})
            assert request("accounts/synthetic/burst-tactic", draft, "PUT")[0] == 200
            restored_draft = json.loads(request("accounts/synthetic/burst-tactic")[1])
            assert restored_draft["executionStatus"] == "draft_incomplete"
            assert restored_draft["issues"] == ["missing_stage_1", "missing_stage_2", "missing_stage_3"]
            assert request("accounts/synthetic/burst-tactic", dict(payload, tactic={"version": 2, "allowlist": {}}), "PUT")[0] == 400
            checks.append("draft restoration and unmapped UI model rejection")
            status, body, _ = request("accounts/synthetic/burst-tactic", payload, "PUT")
            assert status == 200, body
            saved = json.loads(body)["saved"]
            assert json.loads(request("accounts/synthetic/burst-tactic")[1])["saved"] == saved
            bad = dict(payload, tactic=dict(tactic, burst3Rotation=["excluded"]))
            assert request("accounts/synthetic/burst-tactic", bad, "PUT")[0] == 400
            assert request("accounts/synthetic/formation", {"slots": [None] * 5}, "PUT")[0] == 200
            assert json.loads(request("accounts/synthetic/burst-tactic")[1])["stale"] is True
            checks.append("tactic save restore candidate rejection stale detection")
        finally:
            process.terminate()
            process.wait(timeout=10)
summary = {"kind": "synthetic_http_storage_not_engine_integration", "passed": checks}
(run_root / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(dict(summary, evidence=str(run_root)), indent=2))

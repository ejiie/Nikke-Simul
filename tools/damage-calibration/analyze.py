"""Read-only S3 analysis of native results, SavedSkillReplay and export envelopes.

No engine execution, account access, calibration or game-accuracy assertion.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import uuid


E2_HASHES = {
    "input.json": "e14a48955bdbc42f15b6e361ef2ab54a5dc66b5c3df46484346b5a3d2cf40f9b",
    "result.json": "461f3e0e9a2038c3891753eb34635f7ed48c5c3dd661287928a305889f8e7114",
    "manifest.json": "dce19030539f74bf0f80b275d5c82befc9956567b7ec87737dca87fe83baf184",
}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def adapt(data):
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object")
    envelope = None
    shape = "native_result"
    if "replay" in data:
        if data.get("exportSchemaVersion") != 1:
            raise ValueError("Unsupported exportSchemaVersion")
        envelope, data = data, data["replay"]
        shape = "damage_log_export"
    metadata = {}
    if "result" in data:
        metadata = {k: v for k, v in data.items() if k not in ("result", "inputs")}
        data = data["result"]
        if shape == "native_result":
            shape = "saved_skill_replay"
    if not isinstance(data, dict) or "rulesVersion" not in data or "conditions" not in data:
        raise ValueError("Not a native SkillReplayResult or SavedSkillReplay")
    log = data.get("damageLog")
    if envelope is not None:
        expected = "not_collected" if log is None else log.get("status")
        if envelope.get("collectionStatus") != expected:
            raise ValueError("collectionStatus disagrees with captured log")
    return shape, metadata, data, log


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def formula(hit, policy):
    """Independent arithmetic of documented p02.3, using captured HitContext."""
    if policy not in ("legacy_term_floor", "final_round_even", "nested_floor"):
        raise ValueError("Unsupported rounding policy: " + str(policy))
    counts = Counter()
    for buff in hit["attackBuffs"] + hit["runtimeAttackBuffs"]:
        counts[buff["rate"]] += buff["stacks"]
    def away(x):
        return math.copysign(math.floor(abs(x) + .5), x)
    attack = hit["statAttack"] + sum(away(hit["statAttack"] * (rate * n)) for rate, n in counts.items())
    attack += sum(b["amount"] for b in hit["attackFlatBuffs"])
    defense = 0 if hit["damageType"] == "true" else hit["defense"]
    charge = hit["chargeBase"] * (1 + hit["chargeMultiplierBonus"]) + hit["chargeAdd"] if hit["fullCharge"] else 1
    p = (attack - defense) * hit["coefficient"] * charge
    bonuses = [hit[b] if hit[a] else 0 for a, b in (
        ("properDistance", "distanceBonus"), ("fullBurst", "burstBonus"),
        ("crit", "critBonus"), ("core", "coreBonus"))]
    if defense >= attack:
        return 1
    damage = p * (1 + sum(bonuses)) if policy == "final_round_even" else math.floor(p) + sum(math.floor(p * b) for b in bonuses)
    b3 = 1 + hit["attackDamage"] + (hit["pierceDamage"] if hit["pierce"] else 0) + (hit["partsDamage"] if hit["parts"] else 0)
    b3 += hit[hit["damageType"] + "Damage"] if hit["damageType"] in ("dot", "sequential", "true") else 0
    b4 = 1 + hit["damageTaken"] + (hit["distributionDamage"] if hit["damageType"] == "distribution" else 0)
    b5 = 1 + hit["elementBase"] + hit["elementBonus"] if hit["elementAdvantage"] else 1
    for factor in (b3, b4, b5):
        damage *= factor
        if policy == "nested_floor":
            damage = math.floor(damage)
    return max(1, round(damage)) if policy == "final_round_even" else math.floor(damage)


def compare(entries, observations):
    base = {"status": "not_provided", "matched": [], "unmatchedObservations": [],
            "missingDamage": [], "ambiguous": [], "unobservedHitIds": [],
            "meanAbsoluteError": None, "meanAbsoluteRelativeError": None}
    if observations is None:
        return base
    if not isinstance(observations, dict) or observations.get("schemaVersion") != 1 or not isinstance(observations.get("entries"), list):
        raise ValueError("Observation input requires schemaVersion=1 and entries array")
    base["status"] = "provided"
    base["evidence"] = observations.get("evidence", "unspecified")
    # Explicit hitId mapping, or exact frame/source/target/kind/effect/pelletIndex.
    # Ambiguous same-frame hits are never paired by arbitrary order or nearest time.
    fields = ("frame", "source", "target", "kind", "effect", "pelletIndex")
    candidates = []
    for i, row in enumerate(observations["entries"]):
        if not isinstance(row, dict):
            raise ValueError("Observation row must be an object")
        if row.get("hitId") is not None:
            found = [e for e in entries if e["hitId"] == row["hitId"] and all(e.get(k) == row[k] for k in fields if k in row)]
        else:
            found = [e for e in entries if all(k in row and row[k] == e.get(k) for k in fields)]
        candidates.append((i, row, found))
    claims = Counter(e["hitId"] for _, _, found in candidates if len(found) == 1 for e in found)
    used = set()
    for i, row, found in candidates:
        if not found:
            base["unmatchedObservations"].append(i)
            continue
        if len(found) != 1 or claims[found[0]["hitId"]] != 1:
            base["ambiguous"].append(i)
            continue
        e = found[0]
        if row.get("damage") is None:
            base["missingDamage"].append(i)
            continue
        observed = row["damage"]
        if not number(observed) or observed < 0:
            raise ValueError("Observed damage must be finite and nonnegative")
        used.add(e["hitId"])
        error = e["damage"] - observed
        base["matched"].append({"observationIndex": i, "hitId": e["hitId"],
            "simulated": e["damage"], "observed": observed, "signedError": error,
            "absoluteError": abs(error), "relativeError": error / observed if observed else None,
            "absoluteRelativeError": abs(error) / observed if observed else None,
            "zeroDenominator": observed == 0, "exact": error == 0})
    base["unobservedHitIds"] = [e["hitId"] for e in entries if e["hitId"] not in used]
    matched = base["matched"]
    relatives = [m["absoluteRelativeError"] for m in matched if not m["zeroDenominator"]]
    base["meanAbsoluteError"] = sum(m["absoluteError"] for m in matched) / len(matched) if matched else None
    base["meanAbsoluteRelativeError"] = sum(relatives) / len(relatives) if relatives else None
    base["exactCount"] = sum(m["exact"] for m in matched)
    base["zeroDenominatorCount"] = sum(m["zeroDenominator"] for m in matched)
    return base


def analyze(data, observations=None):
    shape, metadata, result, log = adapt(data)
    report = {"analysisSchemaVersion": 1, "inputShape": shape, "metadata": metadata,
              "rulesVersion": result["rulesVersion"], "gameVerified": False,
              "formulaRules": metadata.get("hitRulesVersion", "p02.3"),
              "formulaRulesSource": "saved_metadata" if "hitRulesVersion" in metadata else "assumed_from_pinned_contract_native_result_has_no_hit_rules_version",
              "issues": [], "observationComparison": {"status": "not_analyzed"}}
    if log is None:
        report["collectionState"] = "not_collected"
        return report
    if log.get("schemaVersion") != 1:
        report["collectionState"] = "unsupported_version"
        return report
    if not isinstance(log.get("entries"), list):
        raise ValueError("Captured entries missing (not a zero-hit log)")
    state = "truncated" if log.get("truncated") or log.get("status") == "truncated" else "complete"
    if log.get("status") not in ("complete", "truncated") or type(log.get("truncated")) is not bool:
        state = "unknown_completeness"
    report.update(collectionState=state, truncationReason=log.get("truncationReason"), characterId=log["characterId"])
    entries = log["entries"]
    issues = report["issues"]
    required = ("hitId", "shotId", "frame", "seconds", "source", "target", "effect", "kind", "damage", "cumulativeDamage",
                "fullCharge", "chargeRatioRaw", "actualChargeFrames", "effectiveChargeFrames", "ownBurstEffectActive", "hit", "calculation", "shot")
    for e in entries:
        if not isinstance(e, dict) or any(k not in e for k in required):
            raise ValueError("Damage entry is missing required v1 fields")
        if not all(number(e[k]) for k in ("damage", "cumulativeDamage", "seconds", "frame", "hitId")):
            raise ValueError("Invalid numeric damage entry")
        if type(e["kind"]) is not int or e["kind"] not in (2, 3, 4):
            raise ValueError("Unsupported numeric damage kind")
    if len({e["hitId"] for e in entries}) != len(entries):
        raise ValueError("Duplicate simulation hitId")
    cumulative, previous = 0, -1
    groups = defaultdict(list)
    checks = []
    shots = {}
    for e in entries:
        cumulative += e["damage"]
        if e["frame"] < previous or not math.isclose(e["seconds"], e["frame"] / 60, abs_tol=1e-9):
            issues.append({"hitId": e["hitId"], "code": "time_or_order"})
        previous = e["frame"]
        if not math.isclose(cumulative, e["cumulativeDamage"], abs_tol=1e-7):
            issues.append({"hitId": e["hitId"], "code": "cumulative_mismatch"})
        if e["source"] != log["characterId"]:
            issues.append({"hitId": e["hitId"], "code": "wrong_character"})
        h = e["hit"]
        key = (e["kind"], e["chargeRatioRaw"], e["fullCharge"], h["crit"], h["core"], e["ownBurstEffectActive"], h["fullBurst"])
        groups[key].append(e)
        if e["kind"] == 2 and e["shotId"] is not None:
            shots.setdefault(e["shotId"], e)
        try:
            if report["formulaRules"] != "p02.3":
                raise ValueError("Unsupported hitRulesVersion")
            predicted = formula(h, e["calculation"]["policy"])
            checks.append({"hitId": e["hitId"], "predicted": predicted,
                           "logged": e["damage"], "difference": predicted - e["damage"]})
            if predicted != e["damage"] or e["calculation"]["damage"] != e["damage"]:
                issues.append({"hitId": e["hitId"], "code": "formula_mismatch"})
        except (KeyError, TypeError, ValueError) as exc:
            issues.append({"hitId": e["hitId"], "code": "formula_unavailable", "detail": str(exc)})
    if log.get("eventCount") != len(entries) or not math.isclose(log["totalDamage"], cumulative, abs_tol=1e-7):
        issues.append({"code": "summary_mismatch_or_missing_rows"})
    member = next((m for m in result.get("members", []) if m["characterId"] == log["characterId"]), None)
    if member and member["damage"] != log["totalDamage"]:
        issues.append({"code": "member_total_mismatch"})
    duration = result["conditions"]["combat"]["durationFrames"]
    # SkillReplay.Run steps damage frames from 1 through DurationFrames inclusive.
    if any(e["frame"] < 1 or e["frame"] > duration for e in entries):
        issues.append({"code": "outside_duration"})
    shot_rows = sorted(shots.values(), key=lambda e: (e["frame"], e["hitId"]))
    intervals = []
    for a, b in zip(shot_rows, shot_rows[1:]):
        gap = b["frame"] - a["frame"]
        intervals.append({"shotId": a["shotId"], "nextShotId": b["shotId"], "frame": a["frame"],
            "nextFrame": b["frame"], "shotGapFrames": gap,
            "nextActualChargeFrames": b["actualChargeFrames"], "nextEffectiveChargeFrames": b["effectiveChargeFrames"],
            "gapMinusNextChargeFrames": gap - b["actualChargeFrames"] if b["actualChargeFrames"] is not None else None,
            "emptyAmmoBeforeGap": a["shot"]["ammoAfter"] == 0 and not a["shot"]["unlimitedAmmo"],
            "ammoIncreased": b["shot"]["ammoBefore"] > a["shot"]["ammoAfter"]})
    team = result.get("teamBurst") or {}
    cycles = []
    for cycle in team.get("fullBursts", []):
        selected = [e for e in entries if cycle["startFrame"] <= e["frame"] < cycle["endFrame"]]
        total = sum(e["damage"] for e in selected)
        expected = cycle.get("memberDamage", {}).get(log["characterId"])
        cycles.append({**{k: cycle[k] for k in ("cycle", "caster", "startFrame", "endFrame", "plannedEndFrame")},
                       "hits": len(selected), "damage": total, "memberDamage": expected})
        if expected is not None and expected != total:
            issues.append({"code": "cycle_damage_mismatch", "cycle": cycle["cycle"]})
    last = cycles[-1] if cycles else None
    report.update(hitCount=len(entries), uniqueReferencedShots=len({e["shotId"] for e in entries if e["shotId"] is not None}),
        normalShotsWithHits=len(shots), shotlessHits=sum(e["shotId"] is None for e in entries),
        memberShots=member["shots"] if member else None, totalDamage=cumulative, reportedTotalDamage=log["totalDamage"],
        durationFrames=duration, lastHitFrame=entries[-1]["frame"] if entries else None,
        tailFrames=duration - entries[-1]["frame"] if entries else None,
        formulaChecks=checks, groups=[dict(zip(("kind", "chargeRatioRaw", "fullCharge", "crit", "core", "ownBurstEffectActive", "teamFullBurst"), k),
            hits=len(v), shots=len({e["shotId"] for e in v if e["shotId"] is not None}),
            damage=sum(e["damage"] for e in v), minDamage=min(e["damage"] for e in v), maxDamage=max(e["damage"] for e in v)) for k, v in groups.items()],
        timing={"intervals": intervals, "meaning": "Intervals between normal shots with logged hits; gap minus charge is not measured reload duration.",
                "traceEnabled": result["conditions"]["combat"].get("trace"),
                "reloadCompletedFrames": [e["frame"] for e in (result.get("connection") or {}).get("timeline", []) if e["kind"] == 5 and e["source"] == log["characterId"]],
                "connectionTimelineTruncated": (result.get("connection") or {}).get("timelineTruncated")},
        cycles=cycles, lastCycle=last,
        afterLastCycle={"hits": sum(e["frame"] >= last["endFrame"] for e in entries),
                        "damage": sum(e["damage"] for e in entries if e["frame"] >= last["endFrame"])} if last else None,
        endState={k: team.get(k) for k in ("step", "gaugeRaw", "waitingReason", "timelineTruncated")},
        observationComparison=compare(entries, observations))
    return report


def verify_e2(path):
    actual = {name: sha(Path(path).parent / name) for name in E2_HASHES}
    if actual != E2_HASHES:
        raise ValueError("E2 input/result/manifest SHA-256 mismatch")
    manifest = read(Path(path).parent / "manifest.json")
    if manifest["gameVerified"] is not False or manifest["evidence"] != "synthetic_input_actual_engine_execution":
        raise ValueError("Unexpected E2 evidence provenance")
    result = read(path)
    log = result["damageLog"]
    expected = {"eventCount": len(log["entries"]), "totalDamage": log["totalDamage"],
                "lastHitFrame": log["entries"][-1]["frame"], "durationFrames": result["conditions"]["combat"]["durationFrames"],
                "fullBurstCount": len(result["teamBurst"]["fullBursts"]), "replayRules": result["rulesVersion"]}
    if any(manifest[k] != v for k, v in expected.items()):
        raise ValueError("E2 manifest/result mismatch")
    return {"hashes": actual, "manifest": manifest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--observations", type=Path)
    parser.add_argument("--verify-e2", action="store_true", help="Verify pinned E2 three-file hashes and manifest")
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/s3"))
    args = parser.parse_args()
    root = args.output_root.resolve()
    workspace = Path(__file__).resolve().parents[2]
    if not root.is_relative_to(workspace):
        parser.error("Output must stay in this workspace")
    out = root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex)
    out.mkdir(parents=True, exist_ok=False)
    provenance = {"inputPath": str(args.input.resolve()), "inputSha256": sha(args.input),
                  "toolSha256": sha(__file__), "gitHead": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=workspace, text=True).strip()}
    try:
        if args.verify_e2:
            provenance["e2"] = verify_e2(args.input)
        if args.observations:
            provenance["observationsSha256"] = sha(args.observations)
        report = analyze(read(args.input), read(args.observations) if args.observations else None)
        report["provenance"] = provenance
        code = 0 if report["collectionState"] == "complete" and not report["issues"] else 2
    except (ValueError, KeyError, TypeError, OSError) as exc:
        report = {"status": "invalid_input", "error": str(exc), "provenance": provenance}
        code = 2
    (out / "analysis.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    # ASCII JSON on stdout survives Windows cp949/UTF-8 parent process differences.
    print(json.dumps({"output": str(out / "analysis.json"), "exitCode": code}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

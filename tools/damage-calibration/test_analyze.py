import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from analyze import analyze, compare, formula, verify_e2


def hit_context():
    h = dict.fromkeys(("chargeMultiplierBonus", "chargeAdd", "attackDamage", "pierceDamage", "partsDamage",
                      "dotDamage", "sequentialDamage", "trueDamage", "damageTaken", "distributionDamage", "elementBonus"), 0)
    h.update(dict.fromkeys(("properDistance", "fullBurst", "crit", "core", "pierce", "parts", "elementAdvantage"), False))
    h.update(statAttack=100, attackBuffs=[], runtimeAttackBuffs=[], attackFlatBuffs=[], defense=10,
             coefficient=1, damageType="normal", fullCharge=True, chargeBase=3.5,
             distanceBonus=.3, burstBonus=.5, critBonus=.5, coreBonus=1, elementBase=.1)
    return h


def fixture():
    h = hit_context()
    e = dict(hitId=2, shotId=1, frame=60, seconds=1, source="5004", target="boss", kind=2,
             effect="normal_attack", pelletIndex=0, damage=315, cumulativeDamage=315,
             fullCharge=True, chargeRatioRaw=10000, actualChargeFrames=60, effectiveChargeFrames=60,
             ownBurstEffectActive=False, hit=h, calculation={"policy": "legacy_term_floor", "damage": 315},
             shot={"ammoBefore": 1, "ammoAfter": 0, "unlimitedAmmo": False})
    return dict(rulesVersion="p04.team.2", conditions={"combat": {"durationFrames": 10800}},
                members=[dict(characterId="5004", damage=315, shots=1)],
                damageLog=dict(schemaVersion=1, characterId="5004", status="complete", truncated=False,
                               entries=[e], eventCount=1, totalDamage=315))


def obs(*entries):
    return dict(schemaVersion=1, evidence="synthetic_test", entries=list(entries))


class AnalysisTests(unittest.TestCase):
    def test_native_saved_export_equivalence(self):
        native = fixture()
        saved = dict(id="synthetic", accountSnapshotId="synthetic", result=native)
        export = dict(exportSchemaVersion=1, collectionStatus="complete", replay=saved)
        reports = [analyze(x) for x in (native, saved, export)]
        self.assertEqual([r["totalDamage"] for r in reports], [315] * 3)
        self.assertEqual([r["inputShape"] for r in reports], ["native_result", "saved_skill_replay", "damage_log_export"])
        self.assertEqual(reports[2]["metadata"]["accountSnapshotId"], "synthetic")
        self.assertFalse(reports[0]["issues"])

    def test_missing_observations_not_zero_error(self):
        self.assertIsNone(analyze(fixture())["observationComparison"].get("meanAbsoluteError"))
        self.assertEqual(analyze(fixture())["observationComparison"]["status"], "not_provided")

    def test_known_error_and_exact(self):
        entries = fixture()["damageLog"]["entries"]
        r = compare(entries, obs(dict(hitId=2, damage=300)))
        self.assertEqual(r["meanAbsoluteError"], 15)
        self.assertEqual(r["matched"][0]["relativeError"], .05)
        r = compare(entries, obs(dict(hitId=2, damage=315)))
        self.assertEqual(r["exactCount"], 1)
        self.assertEqual(r["meanAbsoluteRelativeError"], 0)

    def test_zero_denominator_even_exact_zero(self):
        entries = fixture()["damageLog"]["entries"]
        for damage in (315, 0):
            entries[0]["damage"] = damage
            r = compare(entries, obs(dict(hitId=2, damage=0)))
            self.assertEqual(r["zeroDenominatorCount"], 1)
            self.assertIsNone(r["meanAbsoluteRelativeError"])
            self.assertEqual(r["meanAbsoluteError"], damage)

    def test_missing_unmatched_ambiguous_are_separate(self):
        entries = fixture()["damageLog"]["entries"]
        r = compare(entries, obs(dict(hitId=2), dict(hitId=999, damage=3)))
        self.assertEqual(r["missingDamage"], [0])
        self.assertEqual(r["unmatchedObservations"], [1])
        self.assertEqual(r["unobservedHitIds"], [2])
        r = compare(entries, obs(dict(hitId=2, damage=3), dict(hitId=2, damage=3)))
        self.assertEqual(r["ambiguous"], [0, 1])
        self.assertFalse(r["matched"])

    def test_exact_composite_match_and_context_conflict(self):
        e = fixture()["damageLog"]["entries"][0]
        row = {k: e[k] for k in ("frame", "source", "target", "kind", "effect", "pelletIndex", "damage")}
        self.assertEqual(compare([e], obs(row))["exactCount"], 1)
        row["frame"] = 61
        row["hitId"] = 2
        self.assertEqual(compare([e], obs(row))["unmatchedObservations"], [0])

    def test_shotless_skill_additional_and_pellet_no_new_shots(self):
        r = fixture()
        entries = r["damageLog"]["entries"]
        for hid, sid, kind in ((3, 1, 2), (4, 1, 4), (5, None, 3)):
            e = copy.deepcopy(entries[0])
            e.update(hitId=hid, shotId=sid, kind=kind, cumulativeDamage=315 * len(entries + [e]))
            if kind != 2:
                e.update(fullCharge=None, chargeRatioRaw=None, actualChargeFrames=None, effectiveChargeFrames=None)
            entries.append(e)
        r["damageLog"].update(eventCount=4, totalDamage=1260)
        r["members"][0]["damage"] = 1260
        report = analyze(r)
        self.assertEqual(report["hitCount"], 4)
        self.assertEqual(report["uniqueReferencedShots"], 1)
        self.assertEqual(report["normalShotsWithHits"], 1)
        self.assertEqual(report["shotlessHits"], 1)
        self.assertEqual(report["timing"]["intervals"], [])

    def test_collection_states(self):
        r = fixture()
        r["damageLog"] = None
        self.assertEqual(analyze(r)["collectionState"], "not_collected")
        del r["damageLog"]
        self.assertEqual(analyze(r)["collectionState"], "not_collected")
        r = fixture()
        r["damageLog"].update(entries=[], eventCount=0, totalDamage=0)
        r["members"][0].update(damage=0, shots=0)
        self.assertEqual(analyze(r)["collectionState"], "complete")
        self.assertEqual(analyze(r)["totalDamage"], 0)
        r["damageLog"]["schemaVersion"] = 99
        self.assertEqual(analyze(r)["collectionState"], "unsupported_version")
        r["damageLog"].update(schemaVersion=1, truncated=True)
        self.assertEqual(analyze(r)["collectionState"], "truncated")

    def test_missing_rows_and_invalid_entries(self):
        r = fixture()
        r["damageLog"]["entries"] = []
        self.assertIn("summary_mismatch_or_missing_rows", [x["code"] for x in analyze(r)["issues"]])
        del r["damageLog"]["entries"]
        with self.assertRaises(ValueError):
            analyze(r)
        r = fixture()
        r["damageLog"]["entries"][0]["kind"] = "NormalHit"
        with self.assertRaises(ValueError):
            analyze(r)

    def test_numeric_and_envelope_errors(self):
        with self.assertRaises(ValueError):
            analyze(dict(exportSchemaVersion=2, replay=fixture()))
        with self.assertRaises(ValueError):
            analyze(dict(exportSchemaVersion=1, collectionStatus="not_collected", replay={"result": fixture()}))
        for value in (float("nan"), float("inf"), -1, True):
            with self.assertRaises(ValueError):
                compare(fixture()["damageLog"]["entries"], obs(dict(hitId=2, damage=value)))

    def test_formula_crit_core_fullburst_and_own_buff(self):
        h = hit_context()
        for crit, core, expected in ((False, False, 315), (True, False, 472), (False, True, 630), (True, True, 787)):
            h.update(crit=crit, core=core)
            self.assertEqual(formula(h, "legacy_term_floor"), expected)
        h.update(crit=False, core=False, fullBurst=True)
        self.assertEqual(formula(h, "legacy_term_floor"), 472)
        h["runtimeAttackBuffs"] = [dict(rate=.5, stacks=1)]
        self.assertEqual(formula(h, "legacy_term_floor"), 735)
        h["fullCharge"] = False
        self.assertEqual(formula(h, "legacy_term_floor"), 210)

    def test_rounding_policies_minimum_and_grouping(self):
        h = hit_context()
        h["crit"] = True
        self.assertEqual(formula(h, "final_round_even"), 472)
        self.assertEqual(formula(h, "nested_floor"), 472)
        h.update(crit=False, fullCharge=False, defense=0, statAttack=1,
                 attackBuffs=[dict(rate=.25, stacks=1)], runtimeAttackBuffs=[dict(rate=.25, stacks=1)])
        self.assertEqual(formula(h, "legacy_term_floor"), 2)
        h["defense"] = 999
        self.assertEqual(formula(h, "legacy_term_floor"), 1)

    def test_timing_and_last_cycle(self):
        r = fixture()
        e = copy.deepcopy(r["damageLog"]["entries"][0])
        e.update(hitId=4, shotId=3, frame=180, seconds=3, cumulativeDamage=630)
        r["damageLog"]["entries"].append(e)
        r["damageLog"].update(eventCount=2, totalDamage=630)
        r["members"][0].update(damage=630, shots=2)
        r["teamBurst"] = dict(fullBursts=[dict(cycle=1, caster="5004", startFrame=60, endFrame=180, plannedEndFrame=180, memberDamage={"5004":315})])
        report = analyze(r)
        gap = report["timing"]["intervals"][0]
        self.assertEqual(gap["shotGapFrames"], 120)
        self.assertEqual(gap["gapMinusNextChargeFrames"], 60)
        self.assertTrue(gap["emptyAmmoBeforeGap"])
        self.assertEqual(report["lastCycle"]["damage"], 315)
        self.assertEqual(report["afterLastCycle"]["hits"], 1)

    def test_corruption_is_detected(self):
        r = fixture()
        e = r["damageLog"]["entries"][0]
        e.update(seconds=2, cumulativeDamage=99, damage=20)
        codes = {x["code"] for x in analyze(r)["issues"]}
        self.assertTrue({"time_or_order", "cumulative_mismatch", "formula_mismatch", "summary_mismatch_or_missing_rows"} <= codes)
        r["damageLog"]["entries"].append(copy.deepcopy(e))
        with self.assertRaises(ValueError):
            analyze(r)

    def test_e2_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            for name in ("input.json", "result.json", "manifest.json"):
                (Path(directory) / name).write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                verify_e2(Path(directory) / "result.json")

    def test_unsupported_hit_rules_not_recomputed(self):
        report = analyze(dict(result=fixture(), hitRulesVersion="future"))
        self.assertEqual(report["formulaChecks"], [])
        self.assertEqual(report["issues"][0]["code"], "formula_unavailable")

    def test_rounding_candidates_can_diverge(self):
        h = hit_context()
        h.update(fullCharge=False, coefficient=.015, attackDamage=.5, damageTaken=.5)
        self.assertEqual(formula(h, "legacy_term_floor"), 2)
        self.assertEqual(formula(h, "nested_floor"), 1)
        self.assertEqual(formula(h, "final_round_even"), 3)

    def test_cli_unique_outputs_and_saved_wrapper(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "saved.json"
            path.write_text(json.dumps(dict(id="synthetic", result=fixture())), encoding="utf-8")
            outputs = []
            for _ in range(2):
                process = subprocess.run([sys.executable, str(Path(__file__).with_name("analyze.py")), str(path),
                                          "--output-root", directory], capture_output=True, text=True)
                self.assertEqual(process.returncode, 0, process.stderr)
                outputs.append(json.loads(process.stdout)["output"])
            self.assertNotEqual(*outputs)
            self.assertTrue(all(Path(p).is_file() for p in outputs))


if __name__ == "__main__":
    unittest.main(verbosity=2)

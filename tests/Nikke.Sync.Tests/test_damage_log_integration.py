"""Independent tests of integration assertions; synthetic fixtures only."""
import copy
import csv
import io
import json
import unittest

from check_damage_log_integration import verify_exports


def fixture():
    entries = [dict(frame=60, seconds=1, hitId=9, shotId=7, source="5004", damage=1.25, cumulativeDamage=1.25),
               dict(frame=60, seconds=1, hitId=10, shotId=7, source="5004", damage=2.5, cumulativeDamage=3.75)]
    saved = dict(id="synthetic", accountSnapshotId="snapshot", gameSnapshotId="game", calculationDataId="calculation",
                 runtimeDataId="runtime", statRulesVersion="stat", hitRulesVersion="hit",
                 result=dict(conditions=dict(combat=dict(durationFrames=10800)), members=[dict(characterId="5004", damage=3.75)],
                             damageLog=dict(schemaVersion=1, status="complete", truncated=False, truncationReason=None,
                                            characterId="5004", eventCount=2, totalDamage=3.75, entries=entries)))
    envelope = dict(exportSchemaVersion=1, collectionStatus="complete", replay=copy.deepcopy(saved))
    metadata = copy.deepcopy(envelope)
    del metadata["replay"]["result"]["damageLog"]["entries"]
    output = io.StringIO(newline="")
    columns = ["recordType", "frame", "seconds", "hitId", "shotId", "damage", "cumulativeDamage", "entryJson", "metadataJson"]
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerow(dict(recordType="metadata", metadataJson=json.dumps(metadata)))
    for entry in entries:
        row = {field: entry[field] for field in columns[1:7]}
        writer.writerow(dict(row, recordType="hit", entryJson=json.dumps(entry)))
    return saved, copy.deepcopy(saved), envelope, output.getvalue()


class IntegrationAssertions(unittest.TestCase):
    def test_valid_multihit_preserves_distinct_shot_count(self):
        self.assertEqual(dict(hits=2, distinctShots=1, damage=3.75), verify_exports(*fixture()))

    def test_truncation_is_not_success(self):
        args = fixture()
        for value in (args[0], args[1], args[2]["replay"]):
            value["result"]["damageLog"]["truncated"] = True
        with self.assertRaises(AssertionError): verify_exports(*args)

    def test_missing_csv_row_is_detected(self):
        a, b, c, text = fixture()
        with self.assertRaises(AssertionError): verify_exports(a, b, c, text.rsplit("\r\n", 2)[0] + "\r\n")

    def test_metadata_loss_is_detected(self):
        a, b, c, text = fixture()
        with self.assertRaises(AssertionError): verify_exports(a, b, c, text.replace("calculation", "lost"))

    def test_same_time_hit_order_change_is_detected(self):
        a, b, c, text = fixture()
        lines = text.splitlines()
        with self.assertRaises(AssertionError): verify_exports(a, b, c, "\r\n".join(lines[:2] + lines[2:][::-1]) + "\r\n")

    def test_incorrect_seconds_are_detected(self):
        args = fixture()
        for value in (args[0], args[1], args[2]["replay"]):
            value["result"]["damageLog"]["entries"][0]["seconds"] = 60
        with self.assertRaises(AssertionError): verify_exports(*args)


if __name__ == "__main__":
    unittest.main()

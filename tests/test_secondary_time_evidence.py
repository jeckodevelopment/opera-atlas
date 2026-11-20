"""Verified secondary time evidence enriches existing recite, never their identity."""
import copy
import json
import unittest

from scripts.build_verified_catalog import (
    MANIFEST, TIME_EVIDENCE, build, validate_time_evidence
)
from scripts.publish_catalog_v2 import REGISTRY, assemble, release_parts

class SecondaryTimeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.facts = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.evidence = json.loads(TIME_EVIDENCE.read_text(encoding="utf-8"))
        self.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_official_clocks_preserve_existing_recite_ids(self):
        data = build(self.facts, self.evidence)
        events = {x["id"]: x for x in data["performances"]}
        self.assertEqual(len(events), sum(len(p["dates"]) for p in self.facts["productions"]))
        self.assertEqual(sum(x["time_known"] for x in events.values()), len(events)-2)
        self.assertEqual(sum(not x["time_known"] for x in events.values()), 2)
        for key, evidence in self.evidence["times"].items():
            staging, day = key.split("|")
            event = events["curated:" + staging + ":" + day]
            self.assertEqual(event["time_label"], evidence["time"])
            self.assertEqual(event["starts_at"][11:16], evidence["time"])
            self.assertEqual(len(event["sources"]), 2)
            self.assertEqual(event["sources"][1], evidence["url"])
        for e in events.values():
            if not e["time_known"]:
                self.assertIsNone(e["starts_at"])
                self.assertEqual(e["time_label"], "Orario da confermare")

    def test_v2_preserves_canonical_ids_and_time_provenance(self):
        canonical = assemble(self.facts, self.registry)
        by_key = {x["legacy_id"]: x for x in canonical["performances"]}
        for key, item in self.evidence["times"].items():
            staging, day = key.split("|")
            replica = by_key["curated:" + staging + ":" + day]
            self.assertEqual(replica["id"], self.registry["performances"][key]["id"])
            self.assertEqual(replica["starts_at"][11:16], item["time"])
            self.assertEqual(replica["sources"][1], item["url"])
        _, manifest = release_parts(self.facts, self.registry)
        self.assertEqual(manifest["files"]["performances"]["count"], sum(len(p["dates"]) for p in self.facts["productions"]))

    def test_unauthorized_or_unrelated_secondary_source_fails(self):
        bad = copy.deepcopy(self.evidence)
        next(iter(bad["times"].values()))["url"] = "https://example.invalid/show"
        with self.assertRaisesRegex(ValueError, "unreviewed evidence URL"):
            build(self.facts, bad)

    def test_time_attached_to_wrong_recita_fails(self):
        bad = copy.deepcopy(self.evidence)
        bad["times"]["lombardia-italiana-brescia|2026-11-26"] = bad["times"].pop(
            "lombardia-italiana-pavia|2026-11-20"
        )
        with self.assertRaisesRegex(ValueError, "unreviewed evidence URL"):
            build(self.facts, bad)

    def test_new_date_cannot_silently_reuse_time_evidence(self):
        bad = copy.deepcopy(self.evidence)
        bad["times"]["lombardia-italiana-pavia|2027-03-01"] = {
            "time":"20:00",
            "url":"https://www.teatrofraschini.it/programma/litaliana-in-algeri/"
        }
        with self.assertRaisesRegex(ValueError, "one known replica"):
            build(self.facts, bad)

    def test_malformed_or_conflicting_hour_fails(self):
        bad = copy.deepcopy(self.evidence)
        bad["times"]["lombardia-italiana-pavia|2026-11-20"]["time"] = "24:72"
        with self.assertRaises(ValueError):
            build(self.facts, bad)
        conflict = copy.deepcopy(self.facts)
        for p in conflict["productions"]:
            if p["key"] == "lombardia-italiana-pavia":
                p["dates"][0][1] = "21:00"
        with self.assertRaisesRegex(ValueError, "contradictory"):
            validate_time_evidence(conflict, self.evidence)

if __name__ == "__main__":
    unittest.main()

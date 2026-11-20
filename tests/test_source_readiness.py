"""Regio and OperaLombardia live-source readiness quality gates.

The two official pages are publicly viewable for editorial checks, but their
robots.txt could not be verified from the research environment on 2026-11-20.
Thus the daily-access flags remain pending and must not be auto-promoted.
"""
import json
import unittest
from datetime import datetime
from pathlib import Path

from scripts.build_verified_catalog import official_local_time
from scripts.daily_ingest import CONFIG, validate_source_config
from scripts.publish_catalog_v2 import REGISTRY, assemble
from scripts.build_verified_catalog import MANIFEST


class SourceReadinessTests(unittest.TestCase):
    def test_production_sources_are_conditionally_authorized_and_runtime_robots_gated(self):
        config=json.loads(CONFIG.read_text(encoding="utf-8"))
        items=validate_source_config(config)
        self.assertEqual(len(items),4)
        self.assertEqual({i["access_status"] for i in items},{"approved"})
        self.assertTrue(all("runtime" in i["approval_evidence"] for i in items))
        self.assertTrue(all("NOT verified" in i["approval_evidence"] for i in items))

    def test_timed_event_preserves_italian_summer_dst(self):
        self.assertEqual(official_local_time("2027-07-10","20:00"),
                         "2027-07-10T20:00:00+02:00")
        self.assertEqual(official_local_time("2027-02-26","20:00"),
                         "2027-02-26T20:00:00+01:00")

    def test_dst_gap_and_ambiguous_hour_are_not_fabricated(self):
        with self.assertRaisesRegex(ValueError,"nonexistent"):
            official_local_time("2027-03-28","02:30")
        with self.assertRaisesRegex(ValueError,"ambiguous"):
            official_local_time("2027-10-31","02:30")

    def test_future_summer_replica_retains_id_and_offset(self):
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        product=facts["productions"][0]
        product["dates"].append(["2027-07-10","20:00"])
        registry["performances"][product["key"]+"|2027-07-10"]={
            "id":"oa-r-999998","staging_id":registry["stagings"][product["key"]]["id"],
            "original_date":"2027-07-10","source_url":product["source_url"]
        }
        data=assemble(facts,registry)
        result=[e for e in data["performances"] if e["id"]=="oa-r-999998"]
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["starts_at"],"2027-07-10T20:00:00+02:00")
        self.assertTrue(result[0]["time_known"])


if __name__=="__main__":
    unittest.main()

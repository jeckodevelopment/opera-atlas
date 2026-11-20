"""Truthful eight-source access and scan status, driven by factual data."""
import copy
import json
import unittest
from scripts.sync_source_registry import reconcile, INDEX_MAP
from scripts.source_coverage import SOURCES
from scripts.daily_ingest import CONFIG as DAILY
from scripts.discover_season_indexes import CONFIG as SEASONS

class SourceRegistrySyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources=json.loads(SOURCES.read_text(encoding="utf-8"))
        cls.daily=json.loads(DAILY.read_text(encoding="utf-8"))
        cls.seasons=json.loads(SEASONS.read_text(encoding="utf-8"))

    def test_all_eight_derived_from_real_approved_configs(self):
        health={"sources":[{"key":item["key"],"status":"success","links":5}
                           for item in self.seasons["sources"]]}
        daily={"sources":[{"key":"regio-traviata-2027","outcome":"success"},
                          {"key":"opera-lombardia-calendar-2026-27","outcome":"success"}]}
        result=reconcile(self.sources,self.daily,self.seasons,daily,health)
        by={x["key"]:x for x in result["sources"]}
        self.assertEqual(len(by),8)
        self.assertEqual(sum(x["access_status"]=="approved" for x in by.values()),7)
        self.assertEqual(sum(x["automated_index"] for x in by.values()),5)
        self.assertEqual(by["rossini-opera-festival"]["access_status"],"pending")
        self.assertEqual(by["rossini-opera-festival"]["monitoring_status"],"not_started")
        self.assertEqual(by["regio-torino"]["monitoring_status"],"detail_verified")
        self.assertEqual(by["teatro-alla-scala"]["monitoring_status"],"index_verified")
        self.assertFalse(any(x["autonomous_publication_verified"] for x in by.values()))
        self.assertEqual(reconcile(result,self.daily,self.seasons,daily,health),result)

    def test_failed_index_does_not_claim_live_coverage(self):
        health={"sources":[{"key":x["key"],"status":"unavailable_or_invalid"}
                           for x in self.seasons["sources"]]}
        result=reconcile(self.sources,self.daily,self.seasons,{"sources":[]},health)
        by={x["key"]:x for x in result["sources"]}
        self.assertEqual(by["teatro-la-fenice"]["access_status"],"approved")
        self.assertEqual(by["teatro-la-fenice"]["monitoring_status"],"configured_unverified")
        self.assertFalse(by["teatro-la-fenice"]["automated_index"])

    def test_unapproved_source_never_marked_approved(self):
        daily=copy.deepcopy(self.daily)
        season=copy.deepcopy(self.seasons)
        for row in daily["sources"]:row["access_status"]="pending"
        for row in season["sources"]:row["access_status"]="pending"
        result=reconcile(self.sources,daily,season,
                         {"sources":[]},{"sources":[]})
        self.assertTrue(all(x["access_status"]=="pending" for x in result["sources"]))

    def test_registry_must_have_exact_eight_sources(self):
        broken=copy.deepcopy(self.sources)
        broken["sources"].pop()
        with self.assertRaises(ValueError):
            reconcile(broken,self.daily,self.seasons,None,None)

if __name__=="__main__":
    unittest.main()

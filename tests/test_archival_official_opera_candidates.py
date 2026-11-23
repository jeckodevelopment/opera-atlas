"""Regression: archival opera links remain audited without hiding future performances."""
import unittest
from scripts.discover_season_indexes import (
    ARCHIVAL_OFFICIAL_EVENTS, classify, excluded_nonopera,
)
from scripts.reconcile_published_candidates import reconcile

class HistoricOperaCandidates(unittest.TestCase):
    def test_seven_exact_historic_urls_are_not_current_and_not_nonopera(self):
        self.assertEqual(len(ARCHIVAL_OFFICIAL_EVENTS), 7)
        for (source,url),year in ARCHIVAL_OFFICIAL_EVENTS.items():
            with self.subTest(url=url):
                self.assertLess(year,2026)
                self.assertFalse(excluded_nonopera(source,url))
                self.assertEqual(classify(source,url,set()),"not_in_official_season")
                queued={"schema_version":1,"candidates":[{
                    "id":"historic-test","source_key":source,"official_url":url,
                    "status":"needs_review","first_seen":"2026-11-22T00:00:00+00:00"}]}
                outcome,report=reconcile(queued,set())
                self.assertEqual(outcome["candidates"][0]["status"],"not_in_official_season")
                self.assertEqual(report["states"]["not_in_official_season"],1)

    def test_newer_mantova_page_not_archived(self):
        url="https://www.teatrosocialemantova.it/it-it/la-traviata-v3.aspx"
        source="mantova-sociale-rolling-opera"
        self.assertNotIn((source,url),ARCHIVAL_OFFICIAL_EVENTS)
        self.assertEqual(classify(source,url,set()),"needs_review")

    def test_same_title_different_source_is_not_archived(self):
        source="vicenza-olimpico-rolling-opera"
        url="https://www.vicenzainlirica.it/il-barbiere-di-siviglia-rossini/"
        self.assertEqual(classify(source,url,set()),"needs_review")

if __name__=="__main__":
    unittest.main()

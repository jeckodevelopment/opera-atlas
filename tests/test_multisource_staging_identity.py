"""Different official ticket pages can corroborate one physical staging."""
import copy
import json
import unittest
from datetime import date

from scripts.auto_catalogue import promote
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY

PRIMARY = "https://www.haydn.it/eventi/cronaca-di-un-amore-callas-e-pasolini"
SECONDARY = "https://www.haydn.it/eventi/cronaca-di-un-amore-callas-e-pasolini-2"
KEY = "auto-5fea5e594da012da"
CID = "oa-test-independent-haydn-source"


class MultisourceStagingIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def run_candidate(self, clock="2027-01-29T20:00:00+01:00", day="2027-01-29",
                      facts=None, registry=None):
        evidence = {"evidence": [{
            "candidate_id": CID, "source_key": "haydn-rolling-opera",
            "source_url": SECONDARY, "status": "needs_editorial_review",
            "event_facts": [{"event_title": "Cronaca di un amore. Callas e Pasolini",
                             "composer": "Davide Tramontano",
                             "venue": "Teatro Sociale", "date": day,
                             "starts_at": clock}]
        }]}
        candidates = {"candidates": [{
            "id": CID, "source_key": "haydn-rolling-opera",
            "official_url": SECONDARY, "status": "needs_review"
        }]}
        return promote(copy.deepcopy(facts or self.facts),
                       copy.deepcopy(registry or self.registry),
                       evidence, candidates, [], today=date(2026, 11, 22))

    def test_coincident_ticket_does_not_allocate_duplicate_staging_or_recita(self):
        facts, registry, urls, report = self.run_candidate()
        self.assertEqual(report["new_stagings"], 0, report)
        self.assertEqual(report["new_recite"], 0, report)
        self.assertEqual(len([p for p in facts["productions"] if p["key"] == KEY]), 1)
        self.assertEqual(registry["stagings"][KEY]["id"], "oa-s-000250")
        self.assertEqual(registry["stagings"][KEY]["supporting_source_urls"],
                         [PRIMARY, SECONDARY])
        self.assertIn(SECONDARY, urls)
        again, ids, _, next_report = self.run_candidate(facts=facts, registry=registry)
        self.assertEqual(next_report["new_stagings"], 0)
        self.assertEqual(again, facts)
        self.assertEqual(ids, registry)

    def test_different_time_same_day_is_not_silently_merged(self):
        facts, registry, _, report = self.run_candidate("2027-01-29T21:00:00+01:00")
        self.assertEqual(report["new_stagings"], 0)
        self.assertEqual(report["new_recite"], 0)
        self.assertEqual(report["auto_skipped"][0]["reason"],
                         "conflicting_multisource_showtime")
        self.assertEqual(facts, self.facts)
        self.assertEqual(registry, self.registry)


if __name__ == "__main__":
    unittest.main()

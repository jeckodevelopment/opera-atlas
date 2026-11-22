"""Haydn's two ticket URLs describe two recite of one canonical production."""
import copy
import json
import unittest
from datetime import date
from pathlib import Path

from scripts.auto_catalogue import promote
from scripts.reconcile_published_candidates import verified_haydn_cronaca_urls
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY

URLS={
    "https://www.haydn.it/eventi/cronaca-di-un-amore-callas-e-pasolini",
    "https://www.haydn.it/eventi/cronaca-di-un-amore-callas-e-pasolini-2",
}
TITLE="Cronaca di un amore. Callas e Pasolini"
COMPOSER="Davide Tramontano"

class HaydnSharedStagingTests(unittest.TestCase):
    def test_ticket_pages_share_one_staging_and_preserve_times(self):
        facts=json.loads(MANIFEST.read_text())
        registry=json.loads(REGISTRY.read_text())
        candidate_doc=json.loads(Path("data/season-index-candidates.json").read_text())
        evidence_doc=json.loads(Path("data/candidate-detail-evidence.json").read_text())
        selected=[{**x,"status":"needs_review"} for x in candidate_doc["candidates"]
                  if x.get("official_url") in URLS]
        evidence=[x for x in evidence_doc["evidence"] if x.get("source_url") in URLS]
        self.assertEqual(len(selected),2)
        self.assertEqual(len(evidence),2)
        for row in evidence:
            self.assertEqual(row["status"],"needs_editorial_review")
            self.assertEqual(len(row["event_facts"]),1)
        from scripts.consolidate_haydn_cronaca import consolidate
        facts,registry,migrated=consolidate(facts,registry)
        self.assertIn(migrated,(0,1))
        resulting,identity,approved,report=promote(
            facts,registry,{"schema_version":1,"evidence":evidence},
            {"schema_version":1,"candidates":selected},[],
            today=date(2026,11,22))
        stages=[p for p in resulting["productions"]
                if p["municipality"]=="Trento" and p["venue"]=="Teatro Sociale"
                and p["title"]==TITLE and p["composer"]==COMPOSER]
        self.assertEqual(len(stages),1,report)
        self.assertEqual(stages[0]["dates"],
                         [["2027-01-29","20:00"],["2027-01-31","16:00"]])
        self.assertEqual(verified_haydn_cronaca_urls(
            resulting,{"evidence":evidence}),URLS)
        after,identity2,_,replayed=promote(
            resulting,identity,{"schema_version":1,"evidence":evidence},
            {"schema_version":1,"candidates":selected},approved,
            today=date(2026,11,22))
        self.assertEqual(replayed["new_recite"],0)
        self.assertEqual(after,resulting)
        self.assertEqual(identity2,identity)
        altered=copy.deepcopy(evidence)
        altered[0]["event_facts"][0]["composer"]="Other composer"
        self.assertNotEqual(verified_haydn_cronaca_urls(
            resulting,{"evidence":altered}),URLS)

if __name__=="__main__":
    unittest.main()

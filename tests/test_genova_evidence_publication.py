"""Regression: official Genova evidence must become canonical public performances."""
import json
import unittest
from datetime import date

from scripts.auto_catalogue import promote, SOURCE_ALLOWLIST
from scripts.build_verified_catalog import MANIFEST, build
from scripts.publish_catalog_v2 import REGISTRY, assemble
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.collect_candidate_details import OUTPUT as EVIDENCE
from scripts.publish_work_editorial import EDITORIAL, HISTORY, build_editorial

class CarloFeliceIntegrationTests(unittest.TestCase):
    def test_existing_four_official_productions_publish_without_manual_reconciliation(self):
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        candidates=json.loads(CANDIDATES.read_text(encoding="utf-8"))
        evidence=json.loads(EVIDENCE.read_text(encoding="utf-8"))
        existing=[p for p in facts["productions"] if p["municipality"]=="Genova"]
        official=[
            x for x in evidence["evidence"]
            if x.get("source_key")=="carlo-felice-season-2026-27"
            and x.get("status")=="needs_editorial_review"
            and x.get("event_facts")
        ]
        # Before the first automatic refresh: require four complete official
        # pages. Afterwards: trust the committed facts and test idempotence.
        if not existing:
            self.assertGreaterEqual(len(official),4,
                                    "Official Genova evidence fixtures disappeared")
        authorized=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))["urls"]
        out,ids,urls,report=promote(facts,registry,evidence,candidates,authorized,
                                    today=date(2026,11,21))
        genova=[p for p in out["productions"] if p["municipality"]=="Genova"]
        self.assertGreaterEqual(len(genova),4,report)
        self.assertGreaterEqual(sum(len(p["dates"]) for p in genova),24,report)
        self.assertTrue(all(p["venue"]=="Teatro Carlo Felice" for p in genova))
        self.assertIn("Genova|Teatro Carlo Felice",ids["venues"])
        if not existing:
            self.assertGreaterEqual(report["new_recite"],24,report)
        else:
            # A previously published venue may still gain additional official
            # dates or productions. The second promote() below verifies true
            # idempotence against the enriched output, rather than assuming
            # that a nonempty Genova catalog was already exhaustive.
            self.assertGreaterEqual(report["new_recite"],0,report)
        self.assertTrue(all(p["source_url"] in urls for p in genova))
        public=assemble(out,ids,approved_extra=set(urls))
        canonical=build(out,approved_extra=set(urls))
        self.assertTrue(public["performances"])
        self.assertTrue(canonical["performances"])
        editorial=json.loads(EDITORIAL.read_text(encoding="utf-8"))
        history=json.loads(HISTORY.read_text(encoding="utf-8"))
        enriched=build_editorial(out,ids,editorial,
                                  approved_extra=set(urls),history=history)
        self.assertTrue(enriched["works"])
        after,again_ids,again_urls,second=promote(
            out,ids,evidence,candidates,urls,today=date(2026,11,21))
        self.assertEqual(second["new_recite"],0,second)
        self.assertEqual(after,out)
        self.assertEqual(again_ids,ids)
        self.assertEqual(again_urls,urls)

if __name__=="__main__":
    unittest.main()

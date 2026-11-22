"""Regression: real checkpoint may publish only verified public Parma recite."""
import json
import unittest
from datetime import date
from scripts.auto_catalogue import official_identity_candidates, promote_new_works
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY
from scripts.publish_work_editorial import EDITORIAL,HISTORY
from opera_atlas.parma_reviewed_historical_calendar import URL

class ParmaLiveCheckpointPublicationTests(unittest.TestCase):
    def test_existing_source_checkpoint_issues_one_work_and_two_public_recite(self):
        facts=json.loads(MANIFEST.read_text())
        ids=json.loads(REGISTRY.read_text())
        candidates=json.loads(CANDIDATES.read_text())
        detail=json.loads(DETAILS.read_text())
        selected=[{**c,"status":"needs_review"} for c in candidates["candidates"]
                  if c["official_url"]==URL]
        matched=[e for e in detail["evidence"]
                 if e.get("source_url")==URL]
        self.assertEqual(len(selected),1)
        self.assertEqual(len(matched),1)
        self.assertEqual(len(matched[0]["event_facts"]),2)
        source={"schema_version":1,"candidates":selected}
        evidence={"schema_version":1,"evidence":matched}
        intelligence=official_identity_candidates(
            evidence,source,{"schema_version":1,"works":[]})
        self.assertEqual(len(intelligence["works"]),1)
        out=promote_new_works(
            facts,ids,evidence,source,intelligence,
            json.loads(EDITORIAL.read_text()),[],
            today=date(2026,11,22),
            history=json.loads(HISTORY.read_text()),require_image=True)
        result,registry,_,_,_,health=out
        self.assertEqual(health["new_works"],1,health)
        self.assertEqual(health["new_recite"],2,health)
        p=[x for x in result["productions"] if x["source_url"]==URL]
        self.assertEqual(len(p),1)
        self.assertEqual(p[0]["dates"],[
            ["2026-12-05","15:00"],["2026-12-05","18:00"]])
        self.assertFalse(any(day=="2026-12-04" for day,_ in p[0]["dates"]))

if __name__=="__main__":
    unittest.main()

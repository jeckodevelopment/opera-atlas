"""An officially credited contemporary opera needs artwork and history before release."""
import json
import unittest
from datetime import date

from opera_atlas.verified_original_work_art import verified_original_art
from scripts.auto_catalogue import official_identity_candidates,promote_new_works
from scripts.build_verified_catalog import MANIFEST
from scripts.collect_candidate_details import OUTPUT as EVIDENCE
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.publish_catalog_v2 import REGISTRY
from scripts.publish_work_editorial import EDITORIAL,HISTORY

SOURCE="lecce-apollo-pinocchio-2026"
URL=("https://www.provincia.le.it/al-via-la-51-stagione-lirica-della-"
     "provincia-di-lecce-teatro-di-tradizione-si-inaugura-con-turandot-di-puccini/")

class PinocchioEditorialPromotionTests(unittest.TestCase):
    def test_complete_official_work_identity_premiere_art_and_representations(self):
        all_candidates=json.loads(CANDIDATES.read_text(encoding="utf-8"))
        all_details=json.loads(EVIDENCE.read_text(encoding="utf-8"))
        original=next(x for x in all_candidates["candidates"]
                      if x["source_key"]==SOURCE and x["official_url"]==URL)
        candidate={"schema_version":1,"candidates":[{**original,"status":"needs_review"}]}
        observed=next(x for x in all_details["evidence"]
                      if x["source_key"]==SOURCE and x["source_url"]==URL)
        evidence={"schema_version":1,"evidence":[observed]}
        self.assertEqual(observed["status"],"needs_editorial_review")
        self.assertEqual(observed["event_facts"],[{
            "event_title":"Le avventure di Pinocchio","composer":"Antonio Cericola",
            "venue":"Teatro Apollo","date":"2026-12-30",
            "starts_at":"2026-12-30T20:45:00+01:00"}])
        intelligence=official_identity_candidates(
            evidence,candidate,{"schema_version":1,"works":[]})
        work=next(x for x in intelligence["works"] if x["candidate_id"]==original["id"])
        self.assertEqual((work["title"],work["composer"]),
                         ("Le avventure di Pinocchio","Antonio Cericola"))
        self.assertEqual(work["history"]["premiere_year"],2003)
        self.assertEqual(work["history"]["premiere_venue"],"Teatro Marrucino")
        self.assertEqual(work["history"]["librettist"],"Sandro Bernabei")
        self.assertTrue(45<=len(work["synopsis"])<=300)
        self.assertNotIn("Consulta le rappresentazioni",work["synopsis"])
        artwork=verified_original_art(
            source_url=URL,title=work["title"],composer=work["composer"])
        self.assertIsNotNone(artwork)
        self.assertEqual(artwork["kind"],"official_original_work_artwork")
        self.assertIn("Locandina-PInocchio",artwork["image_url"])
        self.assertIsNone(verified_original_art(
            source_url=URL,title=work["title"],composer="Different composer"))
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        editorial=json.loads(EDITORIAL.read_text(encoding="utf-8"))
        history=json.loads(HISTORY.read_text(encoding="utf-8"))
        result,ids,urls,_,_,report=promote_new_works(
            facts,registry,evidence,candidate,intelligence,editorial,[],
            today=date(2026,11,22),history=history,require_image=True)
        published=[x for x in result["productions"] if x["source_url"]==URL
                   and x["title"]=="Le avventure di Pinocchio"]
        self.assertEqual(len(published),1,report)
        self.assertEqual(published[0]["venue"],"Teatro Apollo")
        self.assertEqual(published[0]["municipality"],"Lecce")
        self.assertEqual(published[0]["dates"],[["2026-12-30","20:45"]])
        existing=any(p.get("source_url")==URL for p in facts["productions"])
        self.assertEqual(report["new_recite"],0 if existing else 1,report)
        # Once the official production is already present, the cached
        # publisher does not repeat a URL authorization; its prior
        # provenance is instead carried in the immutable production.
        self.assertTrue(existing or URL in urls,report)
        again,again_ids,_,_,_,repeat=promote_new_works(
            result,ids,evidence,candidate,intelligence,editorial,urls,
            today=date(2026,11,22),history=history,require_image=True)
        self.assertEqual(repeat["new_recite"],0,repeat)
        self.assertEqual(again,result)
        self.assertEqual(again_ids,ids)

if __name__=="__main__":
    unittest.main()

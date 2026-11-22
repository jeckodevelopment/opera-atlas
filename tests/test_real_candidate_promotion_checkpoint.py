"""Regression: three source-backed, image-backed works publish atomically.

Uses the checked-in official performance evidence rather than synthetic
dates. All graph mutations are in memory and are never written to JSON.
"""
import json
import unittest
from datetime import date
from scripts.auto_catalogue import (
    official_identity_candidates,promote_new_works,SOURCE_ALLOWLIST)
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.discover_season_indexes import OUTPUT as INDEX
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.publish_work_editorial import EDITORIAL,HISTORY

REQUIRED={
 "oa-index-8bc8b40e1da92efab27d":("Il quinto moschettiere","Matteo Musumeci",9),
 "oa-index-d54e9b021b5167cfb735":("Le nozze dell’orso","Joe Schittino",9),
 "oa-index-a98083086627ce6e0225":("Veleno","Gaia Aloisi",2)
}

class ActualCandidatePublicationTests(unittest.TestCase):
    def test_publish_complete_source_verified_works_in_one_transaction(self):
        all_candidates=json.loads(INDEX.read_text(encoding="utf-8"))
        all_evidence=json.loads(DETAILS.read_text(encoding="utf-8"))
        candidates={"schema_version":1,"candidates":[x for x in all_candidates["candidates"]
                       if x["id"] in REQUIRED and x["status"]=="needs_review"]}
        evidence={"schema_version":1,"evidence":[x for x in all_evidence["evidence"]
                      if x.get("candidate_id") in {x["id"] for x in candidates["candidates"]}]}
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        ids=json.loads(REGISTRY.read_text(encoding="utf-8"))
        # Already published candidates should no longer require an insert.
        expected={cid:info for cid,info in REQUIRED.items()
                  if any(x["id"]==cid for x in candidates["candidates"])}
        if not expected:
            return
        self.assertEqual({x["candidate_id"] for x in evidence["evidence"]},
                         set(expected))
        for row in evidence["evidence"]:
            self.assertEqual(len(row["event_facts"]),expected[row["candidate_id"]][2])
        intel=official_identity_candidates(
            evidence,candidates,{"schema_version":1,"works":[]})
        self.assertEqual(set(x["candidate_id"] for x in intel["works"]),set(expected))
        for w in intel["works"]:
            expected_title,expected_composer,_=expected[w["candidate_id"]]
            self.assertEqual((w["title"],w["composer"]),(expected_title,expected_composer))
            self.assertTrue(w["history"]["sources"])
        published=promote_new_works(
            facts,ids,evidence,candidates,intel,
            json.loads(EDITORIAL.read_text(encoding="utf-8")),
            json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))["urls"],
            today=date(2026,11,22),
            history=json.loads(HISTORY.read_text(encoding="utf-8")),
            require_image=True)
        result_facts,result_ids,urls,_,_,report=published
        self.assertEqual(report["new_works"],len(expected),report)
        self.assertEqual(report["new_stagings"],len(expected),report)
        self.assertEqual(report["new_recite"],sum(x[2] for x in expected.values()),report)
        self.assertFalse(report["auto_skipped"],report)
        graph=assemble(result_facts,result_ids,approved_extra=set(urls))
        self.assertEqual(len(graph["performances"]),
                         len(ids["performances"])+sum(x[2] for x in expected.values()))
        for candidate in candidates["candidates"]:
            self.assertIn(candidate["official_url"],urls)

if __name__=="__main__":
    unittest.main()

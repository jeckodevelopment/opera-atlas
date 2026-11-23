"""Verified editorial identities must remain tied to exact official productions."""
import json
import unittest

from scripts.auto_catalogue import official_identity_candidates
from scripts.collect_candidate_details import OUTPUT as EVIDENCE
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.publish_catalog_v2 import ROOT,normalized

SEEDS=ROOT/"data/verified-work-authority-seeds.json"
CASES=(
 ("oa-index-52b35f0089c3663c7ddb","Ghost Cafè","Carlo Galante",
  "Teatro M° Tonino Pardo"),
 ("oa-index-d57d2a1cbc3f370f3da5","Il schiavo di sua moglie",
  "Francesco Provenzale","Chiostro del Carmine"),
)

class FirstPartyReviewedOperas(unittest.TestCase):
    def test_two_source_bound_works_match_live_evidence(self):
        read=lambda p:json.loads(p.read_text(encoding="utf-8"))
        candidates=read(CANDIDATES)
        evidence=read(EVIDENCE)
        seeds=read(SEEDS)["works"]
        ids={cid for cid,*_ in CASES}
        # Publication may have changed live candidate statuses by this point.
        # Verify source-bound promotion against a stable pending fixture.
        candidates={"schema_version":1,"candidates":[
            {**row,"status":"needs_review"} for row in candidates["candidates"]
            if row["id"] in ids]}
        evidence={"schema_version":1,"evidence":[
            {**row,"status":"needs_editorial_review"} for row in evidence["evidence"]
            if row["candidate_id"] in ids]}
        generated=official_identity_candidates(
            evidence,candidates,{"schema_version":1,"works":[]})
        byid={w["candidate_id"]:w for w in generated["works"]}
        for cid,title,composer,venue in CASES:
            with self.subTest(cid=cid):
                record=next(r for r in evidence["evidence"]
                            if r["candidate_id"]==cid)
                seed=next(s for s in seeds
                          if s["source_key"]==record["source_key"]
                          and s["source_url"]==record["source_url"])
                self.assertEqual((normalized(seed["title"]),
                                  normalized(seed["composer"])),
                                 (normalized(title),normalized(composer)))
                self.assertEqual({f["venue"] for f in record["event_facts"]},
                                 {venue})
                self.assertEqual(byid[cid]["synopsis"],seed["synopsis"])
                self.assertEqual(byid[cid]["history"],seed["history"])
                self.assertEqual(byid[cid]["official_authority_url"],
                                 record["source_url"])

    def test_wrong_composer_cannot_reuse_reviewed_seed(self):
        from copy import deepcopy
        read=lambda p:json.loads(p.read_text(encoding="utf-8"))
        evidence=deepcopy(read(EVIDENCE))
        row=next(r for r in evidence["evidence"]
                 if r["candidate_id"]==CASES[0][0])
        row["status"]="needs_editorial_review"
        candidates=read(CANDIDATES)
        candidates={"schema_version":1,"candidates":[
            {**r,"status":"needs_review"} for r in candidates["candidates"]
            if r["id"]==CASES[0][0]]}
        row["event_facts"][0]["composer"]="Other Composer"
        with self.assertRaisesRegex(ValueError,"contradicts"):
            official_identity_candidates(evidence,candidates,
                                         {"schema_version":1,"works":[]})

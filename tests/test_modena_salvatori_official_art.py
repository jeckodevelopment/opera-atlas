"""Source-bounded municipality art unblocks the original Modena opera."""
import json
import unittest
from datetime import date
from opera_atlas.verified_municipal_work_art import (
    SOURCE,PROVENANCE,IMAGE,TITLE,COMPOSER,
    verified_municipal_art,is_verified_municipal_art,
)
from scripts.auto_catalogue import (
    verified_candidate_image,official_identity_candidates,promote_new_works,
)
from scripts.publish_catalog_v2 import ROOT,REGISTRY
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_work_editorial import EDITORIAL,HISTORY

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

class ModenaSalvatoriArtTests(unittest.TestCase):
    def test_immutable_first_party_artwork_provenance(self):
        art=verified_municipal_art(source_url=SOURCE,title=TITLE,composer=COMPOSER)
        self.assertEqual(art["image_url"],IMAGE)
        self.assertEqual(art["provenance_url"],PROVENANCE)
        self.assertTrue(is_verified_municipal_art(art,title=TITLE,composer=COMPOSER))
        for kwargs in (
            {"source_url":SOURCE+"?ref=1","title":TITLE,"composer":COMPOSER},
            {"source_url":SOURCE,"title":"Un'altra opera","composer":COMPOSER},
            {"source_url":SOURCE,"title":TITLE,"composer":"Giuseppe Verdi"},
        ):
            self.assertIsNone(verified_municipal_art(**kwargs))
        for tampered in (
            {**art,"image_url":"https://example.org/fake.jpeg"},
            {**art,"source_url":"https://example.org/opera/"},
            {**art,"provenance_url":"https://example.org/event"},
            {**art,"credit":"Attribution uncertain"},
        ):
            self.assertFalse(is_verified_municipal_art(
                tampered,title=TITLE,composer=COMPOSER))

    def test_full_canonical_promotion_with_real_modena_clock(self):
        evidence=read(ROOT/"data/candidate-detail-evidence.json")["evidence"]
        matches=[x for x in evidence if x.get("source_url")==SOURCE]
        self.assertEqual(len(matches),1)
        detail=matches[0]
        self.assertEqual(detail["event_facts"],[{
            "event_title":TITLE,"composer":COMPOSER,
            "venue":"Teatro Comunale Pavarotti-Freni",
            "date":"2026-12-13",
            "starts_at":"2026-12-13T17:30:00+01:00",
        }])
        art=verified_candidate_image(detail,title=TITLE,url=SOURCE,
                                     composer=COMPOSER)
        self.assertEqual(art["image_url"],IMAGE)
        candidate={"id":detail["candidate_id"],
                   "source_key":detail["source_key"],
                   "official_url":SOURCE,"status":"needs_review"}
        rows={"schema_version":1,"evidence":[detail]}
        candidates={"schema_version":1,"candidates":[candidate]}
        intelligence=official_identity_candidates(
            rows,candidates,{"schema_version":1,"works":[]})
        self.assertEqual(
            len([w for w in intelligence["works"] if w.get("source_url")==SOURCE]),
            1)
        original=read(MANIFEST)
        registry=read(REGISTRY)
        if any(w["title"]==TITLE and w["composer"]==COMPOSER
               for w in registry["works"].values()):
            self.skipTest("work already published after current main refresh")
        after,ids,urls,editorial,history,report=promote_new_works(
            original,registry,rows,candidates,intelligence,
            read(EDITORIAL),[],today=date(2026,11,22),
            history=read(HISTORY),require_image=True)
        self.assertEqual(report["new_works"],1,report)
        self.assertEqual(report["new_recite"],1,report)
        work=next(p for p in after["productions"] if p["source_url"]==SOURCE)
        self.assertEqual(work["dates"],[["2026-12-13","17:30"]])
        self.assertEqual(work["title"],TITLE)
        self.assertTrue(any(x["title"]==TITLE and x["composer"]==COMPOSER
                            for x in ids["works"].values()))

if __name__=="__main__":
    unittest.main()

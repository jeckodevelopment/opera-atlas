"""Complete two verified Piacenza opera cards without bypassing final gates."""
import json
import unittest
from datetime import date
from scripts.auto_catalogue import (
    complete_cached_verified_work_cards,official_identity_candidates,
    promote_new_works,SOURCE_ALLOWLIST)
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY
from scripts.publish_work_editorial import EDITORIAL,HISTORY,validate_history
from scripts.publish_work_posters import load_archival_art
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.discover_season_indexes import OUTPUT as CANDIDATES

NEW={
 "Siberia":("Umberto Giordano","piacenza-opera-2026-27",
            "https://teatripiacenza.it/event/siberia/","2026-12-18"),
 "Simon Boccanegra":("Giuseppe Verdi","piacenza-opera-2026-27",
                     "https://teatripiacenza.it/event/simon-boccanegra/","2027-04-02"),
}

def read(path):return json.loads(path.read_text(encoding="utf-8"))

class PiacenzaCompletedCards(unittest.TestCase):
    def test_verified_two_source_bound_editorial_seeds(self):
        seeds=read(__import__("pathlib").Path(__file__).resolve().parents[1]/
                   "data/verified-work-authority-seeds.json")["works"]
        for title,(composer,key,url,day) in NEW.items():
            with self.subTest(title=title):
                found=[s for s in seeds if s["source_key"]==key and s["source_url"]==url]
                self.assertEqual(len(found),1)
                self.assertEqual(found[0]["title"],title)
                self.assertEqual(found[0]["composer"],composer)
                self.assertTrue(validate_history(found[0]["history"]))
                self.assertTrue(45<=len(found[0]["synopsis"])<=300)
                self.assertNotIn("Consulta le rappresentazioni",found[0]["synopsis"])
        artwork=load_archival_art({"siberia","simon-boccanegra"})
        self.assertEqual(set(artwork),{"siberia","simon-boccanegra"})
        self.assertTrue(all(x["kind"]=="archival_work_image" for x in artwork.values()))
        self.assertIn("Dudovich",artwork["siberia"]["credit"])
        self.assertIn("Simon_Boccanegra",artwork["simon-boccanegra"]["image_url"])

    def test_from_cached_evidence_to_publishable_new_compositions(self):
        import copy
        evidence=read(DETAILS)
        discovered=read(CANDIDATES)
        original_intelligence=read(__import__("pathlib").Path(__file__).resolve().parents[1]/
                                   "data/auto-work-intelligence.json")
        requested={}
        for title,(composer,key,url,day) in NEW.items():
            candidate=next((x for x in discovered["candidates"]
                            if x.get("source_key")==key and x.get("official_url")==url),None)
            detail=next((x for x in evidence["evidence"]
                         if x.get("source_key")==key and x.get("source_url")==url),None)
            self.assertIsNotNone(candidate,title)
            self.assertIsNotNone(detail,title)
            self.assertEqual(detail["status"],"needs_editorial_review")
            self.assertTrue(any(x["date"]==day for x in detail["event_facts"]))
            requested[(key,url)]=(candidate,detail)
        chosen={"schema_version":1,"candidates":[dict(c,status="needs_review")
                   for c,_ in requested.values()]}
        selected={"schema_version":1,"evidence":[d for _,d in requested.values()]}
        prepared=official_identity_candidates(
            selected,chosen,{"schema_version":1,"works":[x for x in original_intelligence["works"]
                if (x.get("source_key"),x.get("source_url")) in requested]})
        identities={(x["title"],x["composer"]):x for x in prepared["works"]}
        for title,(composer,_,_,_) in NEW.items():
            self.assertIn((title,composer),identities)
            self.assertTrue(validate_history(identities[(title,composer)]["history"]))
            self.assertEqual(identities[(title,composer)]["official_authority_url"],
                             NEW[title][2])
        registry=read(REGISTRY)
        present={(w["title"],w["composer"]) for w in registry["works"].values()}
        yet_missing={(t,c) for t,(c,_,_,_) in NEW.items()}-present
        if not yet_missing:
            return # Refresh may already have published both since fixture creation.
        selected={"schema_version":1,"evidence":[d for _,d in requested.values()
                  if (d["event_facts"][0]["event_title"],
                      d["event_facts"][0]["composer"].title()) in yet_missing
                  or d["source_url"] in {NEW[t][2] for t,c in yet_missing}]}
        chosen={"schema_version":1,"candidates":[c for c in chosen["candidates"]
                    if c["official_url"] in {NEW[t][2] for t,c in yet_missing}]}
        prepared={"schema_version":1,"works":[x for x in prepared["works"]
                  if (x["title"],x["composer"]) in yet_missing]}
        output=promote_new_works(
            read(MANIFEST),registry,selected,chosen,prepared,read(EDITORIAL),
            read(SOURCE_ALLOWLIST)["urls"],today=date(2026,11,22),
            history=read(HISTORY),require_image=True)
        self.assertEqual(output[-1]["new_works"],len(yet_missing),output[-1])
        self.assertGreaterEqual(output[-1]["new_recite"],len(yet_missing)*2)

if __name__=="__main__":unittest.main()

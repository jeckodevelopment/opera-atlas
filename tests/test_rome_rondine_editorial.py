"""First-party La rondine credit, editorial work and September 2027 recite."""
import json
import unittest
from datetime import date

from scripts.publish_catalog_v2 import ROOT,REGISTRY,normalized
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_work_editorial import EDITORIAL,HISTORY,build_editorial,validate_history
from scripts.publish_work_posters import load_archival_art
from scripts.auto_catalogue import official_identity_candidates,promote_new_works,SOURCE_ALLOWLIST
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.collect_candidate_details import OUTPUT as EVIDENCE
from scripts.auto_work_research import OUT as INTELLIGENCE

URL="https://www.operaroma.it/spettacoli/la-rondine/"
TITLE="La rondine"
COMPOSER="Giacomo Puccini"

def read(path):return json.loads(path.read_text(encoding="utf-8"))

class RomeLaRondineTests(unittest.TestCase):
    def test_complete_first_party_identity_and_1917_historical_poster(self):
        seeds=[w for w in read(ROOT/"data/verified-work-authority-seeds.json")["works"]
               if w.get("source_url")==URL]
        self.assertEqual(len(seeds),1)
        work=seeds[0]
        self.assertEqual((work["title"],work["composer"]),(TITLE,COMPOSER))
        self.assertEqual(work["source_key"],"opera-roma-season-2026-27")
        self.assertTrue(validate_history(work["history"]))
        self.assertTrue(45<=len(work["synopsis"])<=300)
        image=load_archival_art({"la-rondine"})["la-rondine"]
        self.assertEqual(image["kind"],"archival_work_image")
        self.assertIn("commons.wikimedia.org",image["source_url"])
        self.assertIn("1917",image["description"])
        evidence=[x for x in read(EVIDENCE)["evidence"] if x["source_url"]==URL]
        self.assertEqual(len(evidence),1)
        recite=evidence[0]["event_facts"]
        self.assertEqual(len(recite),6)
        self.assertEqual([x["date"] for x in recite],
            ["2027-09-18","2027-09-19","2027-09-21",
             "2027-09-22","2027-09-24","2027-09-26"])
        self.assertEqual({(x["event_title"],x["composer"]) for x in recite},
                         {(TITLE,COMPOSER)})
        self.assertEqual({x["venue"] for x in recite},{"Teatro dell'Opera di Roma"})

    def test_complete_new_work_promotion_or_idempotent_replay(self):
        facts,registry=read(MANIFEST),read(REGISTRY)
        evidence,candidates=read(EVIDENCE),read(CANDIDATES)
        intelligence=official_identity_candidates(evidence,candidates,read(INTELLIGENCE))
        chosen={"schema_version":1,"works":[x for x in intelligence["works"]
                if x.get("source_url")==URL]}
        already=any(normalized(x["title"])==normalized(TITLE)
                    and normalized(x["composer"])==normalized(COMPOSER)
                    for x in registry["works"].values())
        editorial,history=read(EDITORIAL),read(HISTORY)
        approved=read(SOURCE_ALLOWLIST)["urls"]
        new_facts,ids,urls,news,hist,report=promote_new_works(
            facts,registry,evidence,candidates,chosen,editorial,approved,
            today=date(2026,11,21),history=history,require_image=True)
        self.assertEqual(report["new_works"],0 if already else 1,report)
        self.assertEqual(report["new_recite"],0 if already else 6,report)
        published=build_editorial(new_facts,ids,news,approved_extra=set(urls),history=hist)
        self.assertEqual(len([w for w in published["works"]
                              if normalized(w["title"])==normalized(TITLE)
                              and normalized(w["composer"])==normalized(COMPOSER)]),1)
        roma=[p for p in new_facts["productions"] if p["source_url"]==URL]
        self.assertEqual(len(roma),1)
        self.assertEqual(len(roma[0]["dates"]),6)
        again=promote_new_works(new_facts,ids,evidence,candidates,chosen,news,
                                urls,today=date(2026,11,21),history=hist,
                                require_image=True)
        self.assertEqual(again[-1]["new_works"],0)
        self.assertEqual(again[-1]["new_recite"],0)

if __name__=="__main__":
    unittest.main()

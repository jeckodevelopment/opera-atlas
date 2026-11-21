"""Regression: official-source Scala cards need plot, premiere, archival image before publication."""
import json
import unittest
from scripts.publish_catalog_v2 import ROOT,REGISTRY,normalized
from scripts.publish_work_editorial import validate_history,EDITORIAL,HISTORY,build_editorial
from scripts.publish_work_posters import load_archival_art
from scripts.auto_catalogue import official_identity_candidates,promote_new_works,SOURCE_ALLOWLIST
from scripts.discover_season_indexes import OUTPUT as INDEX
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.auto_work_research import OUT as RESEARCH
from scripts.build_verified_catalog import MANIFEST
from datetime import date

SOURCES={
    "leonora":("Leonora","Ferdinando Paër",6),
    "les-pecheurs-de-perles":("Les Pêcheurs de perles","Georges Bizet",5),
    "dido-and-aeneas":("Dido and Æneas","Henry Purcell",7),
    "the-rake-s-progress":("The Rake's Progress","Igor' Stravinskij",6),
}

class ScalaEditorialReadyTests(unittest.TestCase):
    def test_four_new_canonical_works_have_verified_usable_cards(self):
        seeds=json.loads((ROOT/"data/verified-work-authority-seeds.json").read_text())
        candidates=json.loads(INDEX.read_text())
        evidence=json.loads(DETAILS.read_text())
        intelligence=json.loads(RESEARCH.read_text())
        resolved=official_identity_candidates(evidence,candidates,intelligence)
        artwork=load_archival_art(set(SOURCES))
        for slug,(title,composer,count) in SOURCES.items():
            with self.subTest(slug=slug):
                matches=[w for w in seeds["works"] if
                         w.get("source_url","").endswith("/"+slug+".html")]
                self.assertEqual(len(matches),1)
                seed=matches[0]
                self.assertEqual((seed["title"],seed["composer"]),(title,composer))
                self.assertTrue(validate_history(seed["history"]))
                self.assertTrue(55<=len(seed["synopsis"])<=300)
                self.assertNotIn("Consulta le rappresentazioni",seed["synopsis"])
                self.assertTrue(all(x.startswith("https://") for x in seed["history"]["sources"]))
                rows=[x for x in evidence["evidence"] if x["source_url"]==seed["source_url"]]
                self.assertEqual(len(rows),1)
                self.assertEqual(len(rows[0]["event_facts"]),count)
                self.assertTrue(all(x["event_title"]==title and x["composer"]==composer
                                    for x in rows[0]["event_facts"]))
                promoted=[x for x in resolved["works"]
                          if x.get("source_url")==seed["source_url"]]
                self.assertEqual(len(promoted),1)
                self.assertEqual(promoted[0]["synopsis"],seed["synopsis"])
                self.assertEqual(promoted[0]["history"],seed["history"])
                self.assertIn(slug,artwork)
                self.assertEqual(artwork[slug]["kind"],"archival_work_image")
                self.assertIn("commons.wikimedia.org",artwork[slug]["source_url"])

    def test_full_canonical_promotion_is_atomic_and_idempotent(self):
        read=lambda path:json.loads(path.read_text())
        facts,registry=read(MANIFEST),read(REGISTRY)
        detail,candidates=read(DETAILS),read(INDEX)
        editorial,history=read(EDITORIAL),read(HISTORY)
        urls=read(SOURCE_ALLOWLIST)["urls"]
        intelligence=official_identity_candidates(detail,candidates,read(RESEARCH))
        chosen={"schema_version":1,"works":[w for w in intelligence["works"]
                   if w.get("source_url","").endswith((
                     "/leonora.html","/les-pecheurs-de-perles.html"))]}
        self.assertEqual(len(chosen["works"]),4)
        prior={(normalized(w["title"]),normalized(w["composer"]))
               for w in registry["works"].values()}
        next_facts,ids,approved,news,hist,report=promote_new_works(
            facts,registry,detail,candidates,chosen,editorial,urls,
            today=date(2026,11,21),history=history,require_image=True)
        remaining={title:count for title,composer,count in SOURCES.values()
                   if (normalized(title),normalized(composer)) not in prior}
        self.assertEqual(report["new_works"],len(remaining),report)
        self.assertEqual(report["new_recite"],sum(remaining.values()),report)
        published=build_editorial(next_facts,ids,news,
                                  approved_extra=set(approved),history=hist)
        works={w["title"]:w for w in published["works"]}
        for name in SOURCES:
            title,composer,count=SOURCES[name]
            self.assertIn(title,works)
            self.assertEqual(len([x for x in next_facts["productions"]
                                  if normalized(x["title"])==normalized(title)
                                  and normalized(x["composer"])==normalized(composer)]),1)
        again=promote_new_works(next_facts,ids,detail,candidates,chosen,
                                news,approved,today=date(2026,11,21),
                                history=hist,require_image=True)
        self.assertEqual(again[-1]["new_works"],0)
        self.assertEqual(again[-1]["new_recite"],0)

if __name__=="__main__":
    unittest.main()

"""Regression: official-source Scala cards need plot, premiere, archival image before publication."""
import json
import unittest
from scripts.publish_catalog_v2 import ROOT
from scripts.publish_work_editorial import validate_history
from scripts.publish_work_posters import load_archival_art
from scripts.auto_catalogue import official_identity_candidates
from scripts.discover_season_indexes import OUTPUT as INDEX
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.auto_work_research import OUT as RESEARCH

SOURCES={
    "leonora":("Leonora","Ferdinando Paër",6),
    "les-pecheurs-de-perles":("Les Pêcheurs de perles","Georges Bizet",5),
}

class ScalaEditorialReadyTests(unittest.TestCase):
    def test_two_new_canonical_works_have_verified_usable_cards(self):
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

if __name__=="__main__":
    unittest.main()

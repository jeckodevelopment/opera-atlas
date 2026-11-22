"""Six San Carlo 2026/27 source-bound canonical work cards and archival art."""
import json
import unittest

from scripts.publish_catalog_v2 import ROOT, slugify
from scripts.publish_work_editorial import validate_history
from scripts.publish_work_posters import load_archival_art


class SanCarloEditorialCardsTests(unittest.TestCase):
    def test_six_exact_source_bound_editorial_cards_are_complete(self):
        document=json.loads((ROOT/"data/verified-work-authority-seeds.json").read_text())
        rows=[r for r in document["works"]
              if r["source_key"]=="napoli-san-carlo-rolling-opera"]
        expected={
            "Luisa Miller": "Giuseppe Verdi",
            "Peter Grimes": "Benjamin Britten",
            "Nina o sia La pazza per amore": "Giovanni Paisiello",
            "Otto mesi in due ore o sia Gli esiliati in Siberia": "Gaetano Donizetti",
            "La damnation de Faust": "Hector Berlioz",
            "La chute de la maison Usher": "Claude Debussy / Alessandro Solbiati"}
        self.assertEqual({r["title"]:r["composer"] for r in rows},expected)
        self.assertEqual(len({r["source_url"] for r in rows}),6)
        for row in rows:
            self.assertTrue(row["source_url"].startswith(
                "https://www.teatrosancarlo.it/spettacoli/"))
            self.assertTrue(validate_history(row["history"]),row["title"])
            self.assertTrue(45<=len(row["synopsis"])<=300,row["title"])
            self.assertNotIn("Consulta le rappresentazioni verificate",row["synopsis"])
        usher=next(r for r in rows if r["title"]=="La chute de la maison Usher")
        self.assertEqual(usher["history"]["premiere_year"],2027)
        self.assertIn("Solbiati",usher["history"]["premiere_venue"])

    def test_all_six_have_work_specific_attributed_archival_images(self):
        doc=json.loads((ROOT/"data/verified-work-authority-seeds.json").read_text())
        rows=[r for r in doc["works"]
              if r["source_key"]=="napoli-san-carlo-rolling-opera"]
        slugs={slugify(r["title"]) for r in rows}
        image=load_archival_art(slugs)
        self.assertEqual(set(image),slugs)
        for slug,entry in image.items():
            self.assertEqual(entry["kind"],"archival_work_image")
            self.assertIn("commons.wikimedia.org/",entry["source_url"])
            self.assertTrue(entry["credit"])
            self.assertTrue(entry["license"])
            self.assertTrue(entry["alt"])
            self.assertIn("non",entry["alt"].casefold())

    def test_existing_canonical_rossini_work_is_not_recreated(self):
        document=json.loads((ROOT/"data/verified-work-authority-seeds.json").read_text())
        self.assertFalse(any(r["source_key"]=="napoli-san-carlo-rolling-opera"
                             and r["title"]=="Il barbiere di Siviglia"
                             for r in document["works"]))


if __name__=="__main__":
    unittest.main()

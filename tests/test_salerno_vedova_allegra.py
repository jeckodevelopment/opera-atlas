"""Salerno official operetta: complete editorial identity before publication."""
import json
import unittest
from scripts.publish_catalog_v2 import ROOT
from scripts.publish_work_editorial import validate_history

SOURCE="https://cultura.comune.salerno.it/eventi/la-vedova-allegra-2026/"

class SalernoVedovaAllegraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read=lambda p:json.loads((ROOT/p).read_text(encoding="utf-8"))
        cls.seeds=read("data/verified-work-authority-seeds.json")["works"]
        cls.evidence=read("data/candidate-detail-evidence.json")["evidence"]
        cls.candidates=read("data/season-index-candidates.json")["candidates"]

    def test_only_one_first_party_verified_seed(self):
        matches=[s for s in self.seeds if s["source_url"]==SOURCE]
        self.assertEqual(len(matches),1)
        work=matches[0]
        self.assertEqual((work["title"],work["composer"]),
                         ("La vedova allegra","Franz Lehár"))
        self.assertEqual(work["source_key"],"salerno-verdi-opera-2026")
        self.assertTrue(validate_history(work["history"]))
        self.assertEqual(work["history"]["premiere_year"],1905)
        self.assertEqual(work["history"]["librettist"],"Victor Léon; Leo Stein")
        self.assertGreaterEqual(len(work["synopsis"]),45)

    def test_three_real_recite_and_an_authenticated_poster(self):
        detail=[x for x in self.evidence if x["source_url"]==SOURCE]
        self.assertEqual(len(detail),1)
        detail=detail[0]
        self.assertEqual(detail["status"],"needs_editorial_review")
        self.assertEqual([(x["date"],x["starts_at"]) for x in detail["event_facts"]],
                         [("2026-11-06","2026-11-06T21:00:00+01:00"),
                          ("2026-11-07","2026-11-07T21:00:00+01:00"),
                          ("2026-11-08","2026-11-08T18:00:00+01:00")])
        self.assertTrue(all(x["composer"]=="Franz Lehár" for x in detail["event_facts"]))
        poster=detail["poster_evidence"]
        self.assertEqual(poster["source_url"],SOURCE)
        self.assertEqual(poster["kind"],"official_production_image")
        self.assertIn("la-vedova-allegra",poster["image_url"])
        self.assertEqual(len([c for c in self.candidates if c["official_url"]==SOURCE]),1)

if __name__=="__main__":
    unittest.main()

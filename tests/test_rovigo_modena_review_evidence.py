"""Rovigo observations are review evidence, never canonical performances."""
import json
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/"data/rovigo-season-review-evidence.json"
SEEDS=ROOT/"data/verified-work-authority-seeds.json"
CANDIDATES=ROOT/"data/season-index-candidates.json"
CATALOG=ROOT/"data/verified-launch-catalog.json"
MODENA=("https://www.teatrocomunalemodena.it/spettacolo/"
        "daniele-furlati-i-salvatori-della-mezzanotte/")

class RovigoModenaCoverageTests(unittest.TestCase):
    def test_rovigo_observations_remain_review_only(self):
        doc=json.loads(REVIEW.read_text(encoding="utf-8"))
        self.assertEqual(doc["status"],"review_only_not_for_publication")
        self.assertEqual((doc["city"],doc["venue"]),("Rovigo","Teatro Sociale"))
        self.assertEqual(len(doc["programmes"]),6)
        sources=set()
        for item in doc["programmes"]:
            self.assertFalse(item["verified_official_performance_evidence"])
            self.assertTrue(item["performance_dates"])
            self.assertEqual(len(item["performance_dates"]),
                             len(set(item["performance_dates"])))
            if item["performance_times"] is not None:
                self.assertEqual(len(item["performance_times"]),
                                 len(item["performance_dates"]))
            for day in item["performance_dates"]:
                self.assertIn(date.fromisoformat(day).year,(2026,2027))
            link=urlsplit(item["secondary_source_url"])
            self.assertEqual(link.scheme,"https")
            self.assertTrue(link.hostname)
            sources.add(link.hostname)
        self.assertGreaterEqual(len(sources),2)
        paired=next(x for x in doc["programmes"]
                    if "Trouble in Tahiti" in x["title"])
        self.assertEqual(len(paired["performance_dates"]),3)
        self.assertIsNone(paired["composer"])
        # Never insert unverified secondary dates as first-party catalog facts.
        catalog=json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertFalse(any(x["municipality"]=="Rovigo"
                             for x in catalog["productions"]))

    def test_modena_new_opera_identity_is_prepared_not_falsely_published(self):
        seeds=json.loads(SEEDS.read_text(encoding="utf-8"))["works"]
        matched=[s for s in seeds if s["source_url"]==MODENA]
        self.assertEqual(len(matched),1)
        work=matched[0]
        self.assertEqual((work["title"],work["composer"]),
                         ("I salvatori della mezzanotte","Daniele Furlati"))
        self.assertEqual(work["history"]["premiere_date"],"2023-12-17")
        self.assertEqual(work["history"]["premiere_city"],"Modena")
        candidates=json.loads(CANDIDATES.read_text(encoding="utf-8"))
        self.assertEqual(len([c for c in candidates["candidates"]
                              if c["official_url"]==MODENA]),1)

if __name__=="__main__":
    unittest.main()

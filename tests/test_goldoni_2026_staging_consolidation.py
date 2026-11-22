"""Regression: one canonical production per Goldoni 2026/27 opera."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SEASON="https://www.goldoniteatro.it/notizie/la-stagione-lirica/"
EXPECTED={
    "Dido and Æneas": {"2026-11-06":"20:00","2026-11-08":"16:00"},
    "Otello": {"2027-01-29":"20:00","2027-01-31":"16:00"},
    "L’elisir d’amore": {"2027-04-16":"20:00","2027-04-18":"16:00"},
}

class GoldoniSingleStagingTests(unittest.TestCase):
    def test_exactly_one_staging_and_two_recite_per_opera(self):
        facts=json.loads((ROOT/"data/verified-launch-catalog.json").read_text())
        registry=json.loads((ROOT/"data/identity-registry.json").read_text())
        for title,dates in EXPECTED.items():
            with self.subTest(title=title):
                matches=[p for p in facts["productions"]
                         if p["municipality"]=="Livorno"
                         and p["venue"]=="Teatro Goldoni"
                         and p["title"]==title]
                self.assertEqual(len(matches),1)
                production=matches[0]
                self.assertEqual(production["source_url"],SEASON)
                self.assertEqual(dict(production["dates"]),dates)
                staging=registry["stagings"][production["key"]]
                recite=[p for p in registry["performances"].values()
                        if p["staging_id"]==staging["id"]]
                self.assertEqual(len(recite),2)
                self.assertEqual({r["original_date"] for r in recite},set(dates))
        self.assertEqual(
            len([p for p in facts["productions"]
                 if p["municipality"]=="Livorno" and p["venue"]=="Teatro Goldoni"]),3)

    def test_mascagni_outdoor_staging_kept_separate(self):
        facts=json.loads((ROOT/"data/verified-launch-catalog.json").read_text())
        outdoor=[p for p in facts["productions"]
                 if p["municipality"]=="Livorno" and p["venue"]=="Piazza Goldoni"
                 and p["title"]=="Cavalleria rusticana"]
        self.assertEqual(len(outdoor),1)
        self.assertEqual(dict(outdoor[0]["dates"]),
                         {"2026-08-19":"21:30","2026-08-20":"21:30"})

if __name__=="__main__":
    unittest.main()

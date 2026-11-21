"""Editorial stories for the theatres and compact directions layout."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"

class TheatreEditorialHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles=json.loads((SITE/"theatre-profiles.json").read_text(encoding="utf-8"))["venues"]

    def test_all_current_venues_have_sourced_original_histories(self):
        self.assertEqual(len(self.profiles),52)
        for key,venue in self.profiles.items():
            self.assertTrue(80<=len(venue["history"])<=550,key)
            self.assertTrue(venue["source"].startswith("https://"),key)
            self.assertIn(venue["city"],key)
            if "opening_year" in venue:
                self.assertTrue(1600<=venue["opening_year"]<=2026,key)
                self.assertIn(str(venue["opening_year"]),venue["history"],key)

    def test_torino_uses_two_historically_distinct_dates(self):
        theatre=self.profiles["Torino|Teatro Regio"]["history"]
        for item in ("1740","1936","1973","Carlo Mollino"):
            self.assertIn(item,theatre)
        self.assertIn("1913",self.profiles["Verona|Arena di Verona"]["history"])

    def test_history_is_rendered_separately_from_address(self):
        script=(SITE/"detail.js").read_text(encoding="utf-8")
        self.assertIn('node("section","theatre-history")',script)
        self.assertIn('node("h2",null,"La storia del teatro")',script)
        self.assertIn('node("p","theatre-history-text",profile.history)',script)
        self.assertIn('node("div","theatre-location")',script)
        self.assertIn('link("Come arrivare"',script)

    def test_directions_card_uses_intrinsic_size_not_full_row(self):
        css=(SITE/"styles.css").read_text(encoding="utf-8")
        self.assertIn('.theatre-location{display:inline-flex;',css)
        self.assertIn('width:fit-content;max-width:100%;',css)
        self.assertIn('.theatre-history .theatre-history-text{max-width:67ch;',css)

if __name__=="__main__":
    unittest.main()

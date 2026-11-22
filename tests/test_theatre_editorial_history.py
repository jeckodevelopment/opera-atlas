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
        census=json.loads((ROOT/"data/venue-directory.json").read_text(encoding="utf-8"))["venues"]
        self.assertGreaterEqual(len(self.profiles),len(census))
        for key,venue in self.profiles.items():
            self.assertTrue(80<=len(venue["history"])<=550,key)
            self.assertTrue(venue["source"].startswith("https://"),key)
            self.assertIn(venue["city"],key)
            if "opening_year" in venue:
                self.assertTrue(1600<=venue["opening_year"]<=2026,key)
                self.assertIn(str(venue["opening_year"]),venue["history"],key)

    def test_florence_goldoni_is_distinct_from_livorno_goldoni(self):
        profile=self.profiles["Firenze|Teatro Goldoni"]
        self.assertIn("1817",profile["history"])
        self.assertEqual(profile["address"],"Via Santa Maria 15")
        self.assertIn("maggiofiorentino.com",profile["source"])
        census=json.loads((ROOT/"data/venue-directory.json").read_text(encoding="utf-8"))
        florence=next(x for x in census["venues"] if x["name"]=="Teatro Goldoni" and x["city"]=="Firenze")
        livorno=next(x for x in census["venues"] if x["name"]=="Teatro Goldoni" and x["city"]=="Livorno")
        self.assertEqual(florence["profile_key"],"Firenze|Teatro Goldoni")
        self.assertEqual(florence["photo_license"],"CC BY-SA 3.0")
        self.assertNotEqual(florence["id"],livorno["id"])
        self.assertNotEqual(profile,self.profiles["Livorno|Teatro Goldoni"])

    def test_new_malibran_venue_is_not_conflated_with_fenice(self):
        profile=self.profiles["Venezia|Teatro Malibran"]
        self.assertIn("1678",profile["history"])
        self.assertIn("Cannaregio 5873",profile["address"])
        self.assertIn("teatrolafenice.it",profile["source"])
        census=json.loads((ROOT/"data/venue-directory.json").read_text(encoding="utf-8"))
        item=next(x for x in census["venues"] if x["name"]=="Teatro Malibran")
        self.assertEqual(item["canonical_venue_id"],"oa-v-000021")
        self.assertEqual(item["profile_key"],"Venezia|Teatro Malibran")
        self.assertEqual(item["photo_license"],"CC0 1.0")
        self.assertNotEqual(profile,self.profiles["Venezia|Teatro La Fenice"])

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

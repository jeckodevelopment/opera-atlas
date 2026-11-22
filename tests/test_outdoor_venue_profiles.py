"""Outdoor opera venues have public-facing copy and verified location photographs."""
import json
import unittest
from pathlib import Path

PROFILES=Path(__file__).resolve().parents[1]/"site"/"theatre-profiles.json"

class OutdoorVenueProfileTests(unittest.TestCase):
    def test_forte_and_piazza_have_editorial_photographs(self):
        venues=json.loads(PROFILES.read_text(encoding="utf-8"))["venues"]
        expected={
            "Alghero|Forte della Maddalena":("Alghero, forte-bastione della maddalena 04.JPG","Sailko"),
            "Livorno|Piazza Goldoni":("Teatro Goldoni a Livorno.JPG","Luca Aless"),
        }
        for key,(filename,author) in expected.items():
            with self.subTest(venue=key):
                profile=venues[key]
                self.assertEqual(profile["photo_file"],filename)
                self.assertIn(author,profile["photo_credit"])
                self.assertTrue(profile["photo_source_url"].startswith(
                    "https://commons.wikimedia.org/wiki/File:"))
                self.assertTrue(profile["photo_license"].startswith("CC BY"))
                self.assertGreaterEqual(len(profile["history"]),120)
                self.assertLessEqual(len(profile["description"]),260)
                self.assertNotEqual(profile["description"],profile["history"])
                for field in ("description","history"):
                    for internal in ("pipeline","censita","è stata acquisita","il sistema",
                                     "nella scheda","verificata la fonte"):
                        self.assertNotIn(internal,profile[field].casefold())

if __name__=="__main__":
    unittest.main()

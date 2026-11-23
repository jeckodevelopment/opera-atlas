"""Regression: La mère coupable must have complete, QID-bound source material."""
import unittest

from scripts.auto_work_research import preverified_work_material
from scripts.publish_work_posters import load_archival_art
from scripts.publish_catalog_v2 import slugify
from scripts.publish_work_editorial import validate_history


class MereCoupableResearchTests(unittest.TestCase):
    def test_source_bound_opera_card_and_licensed_cover(self):
        slug=slugify("La mère coupable")
        self.assertEqual(slug,"la-mere-coupable")
        card=preverified_work_material()[slug]
        self.assertEqual(card["attribution"]["wikidata_id"],"Q3210943")
        self.assertEqual(card["attribution"]["composer"],"Darius Milhaud")
        self.assertIn("Bégearss",card["synopsis"])
        self.assertTrue(validate_history(card["history"]))
        self.assertEqual(card["history"]["premiere_year"],1966)
        self.assertEqual(card["history"]["librettist"],"Madeleine Milhaud")
        art=load_archival_art({slug})[slug]
        self.assertEqual(art["kind"],"archival_work_image")
        self.assertIn("Ricordi",art["credit"])
        self.assertIn("CC BY-SA 4.0",art["license"])
        self.assertIn("commons.wikimedia.org",art["image_url"])


if __name__=="__main__":
    unittest.main()

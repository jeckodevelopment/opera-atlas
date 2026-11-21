"""Artwork specifically approved for the 2027 Nicola Sani premiere."""
import unittest

from opera_atlas.verified_ticketing_art import (
    verified_ticketing_image,is_verified_ticketing_poster)
from scripts.auto_catalogue import verified_candidate_image

SOURCE="https://www.operaroma.it/spettacoli/code-unknown/"
IMG="https://www.ticketone.it/obj/media/IT-eventim/teaser/evo/artwork/2027/code-unknow-biglietti.jpg"

class TicketingArtworkTests(unittest.TestCase):
    def test_code_unknown_ticketone_image_bound_to_exact_work(self):
        proof=verified_ticketing_image(
            source_url=SOURCE,title="Code: Unknown",composer="Nicola Sani")
        self.assertIsNotNone(proof)
        self.assertEqual(proof["image_url"],IMG)
        self.assertEqual(proof["kind"],"ticketing_event_artwork")
        self.assertIn("/artist/",proof["ticketing_page_url"])
        self.assertTrue(is_verified_ticketing_poster(
            proof,title="Code: Unknown",composer="Nicola Sani"))
        self.assertEqual(verified_candidate_image(
            {},title="Code: Unknown",composer="Nicola Sani",url=SOURCE),proof)
    def test_never_confuse_homonyms_other_composers_or_sources(self):
        self.assertIsNone(verified_ticketing_image(
            source_url=SOURCE,title="Code: Unknown",composer="Giacomo Puccini"))
        self.assertIsNone(verified_ticketing_image(
            source_url=SOURCE,title="Code Unknown Film",composer="Nicola Sani"))
        self.assertIsNone(verified_ticketing_image(
            source_url="https://www.operaroma.it/spettacoli/falstaff/",
            title="Code: Unknown",composer="Nicola Sani"))
        correct=verified_ticketing_image(
            source_url=SOURCE,title="Code: Unknown",composer="Nicola Sani")
        self.assertFalse(is_verified_ticketing_poster(
            {**correct,"image_url":"https://www.ticketone.it/img/other.jpg"},
            title="Code: Unknown",composer="Nicola Sani"))
        self.assertFalse(is_verified_ticketing_poster(
            {**correct,"ticketing_page_url":"https://example.com"},
            title="Code: Unknown",composer="Nicola Sani"))

if __name__=="__main__":
    unittest.main()

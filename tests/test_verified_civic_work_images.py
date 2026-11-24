"""A work-specific municipal image must not be confused with invented poster art."""
import unittest
from opera_atlas.verified_civic_work_images import (
    verified_civic_image,is_verified_civic_image,SOURCE,TITLE,COMPOSER,IMAGE,PROVENANCE)
from scripts.auto_catalogue import verified_candidate_image


class VerifiedCivicImageTests(unittest.TestCase):
    def test_exact_official_municipal_photo_enables_real_new_opera(self):
        proof=verified_civic_image(source_url=SOURCE,title=TITLE,composer=COMPOSER)
        self.assertIsNotNone(proof)
        self.assertEqual(proof["image_url"],IMAGE)
        self.assertEqual(proof["provenance_url"],PROVENANCE)
        self.assertEqual(proof["kind"],"official_civic_production_image")
        self.assertTrue(is_verified_civic_image(proof,title=TITLE,composer=COMPOSER))
        self.assertEqual(
            verified_candidate_image({},title=TITLE,composer=COMPOSER,url=SOURCE),proof)

    def test_pisa_poster_photo_is_source_scoped_with_explicit_press_caption(self):
        from opera_atlas.verified_civic_work_images import (
            PISA_SOURCE,PISA_IMAGE,PISA_PROVENANCE,PISA_TITLE,PISA_COMPOSER)
        proof=verified_civic_image(source_url=PISA_SOURCE,
                                   title=PISA_TITLE,composer=PISA_COMPOSER)
        self.assertIsNotNone(proof)
        self.assertEqual(PISA_IMAGE,proof["image_url"])
        self.assertEqual(PISA_PROVENANCE,proof["provenance_url"])
        self.assertIn("conferenza stampa",proof["credit"])
        self.assertTrue(is_verified_civic_image(proof,title=PISA_TITLE,composer=PISA_COMPOSER))
        for corrupt in (
            {"image_url":"https://different.example/random.jpg"},
            {"provenance_url":"https://www.comune.pisa.it/other"},
            {"source_url":"https://teatrodipisa.it/spettacolo/carmen/"},
        ):
            self.assertFalse(is_verified_civic_image({**proof,**corrupt},
                title=PISA_TITLE,composer=PISA_COMPOSER))
        self.assertIsNone(verified_civic_image(source_url=PISA_SOURCE,
                                    title=PISA_TITLE,composer="Another Britten"))
        self.assertIsNone(verified_civic_image(source_url=PISA_SOURCE,
                                    title="Death in Venice",composer=PISA_COMPOSER))

    def test_no_authorization_by_title_only_or_other_venue(self):
        self.assertIsNone(verified_civic_image(
            source_url=SOURCE,title=TITLE,composer="Another Composer"))
        self.assertIsNone(verified_civic_image(
            source_url="https://www.teatrocomunalemodena.it/spettacolo/other/",
            title=TITLE,composer=COMPOSER))
        self.assertIsNone(verified_civic_image(
            source_url=SOURCE,title="L'anno che verrà",composer=COMPOSER))
        proof=verified_civic_image(source_url=SOURCE,title=TITLE,composer=COMPOSER)
        self.assertFalse(is_verified_civic_image({**proof,"image_url":
            "https://www.comune.modena.it/another-photo.jpeg"},
            title=TITLE,composer=COMPOSER))

if __name__=="__main__":
    unittest.main()

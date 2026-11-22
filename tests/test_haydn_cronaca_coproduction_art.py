"""Official illustration from the original Piacenza coproductor for Trento shows."""
import unittest
from opera_atlas.verified_coproduction_posters import (
    verified_coproduction_poster, is_verified_coproduction_poster)
from scripts.auto_catalogue import verified_candidate_image

TITLE="Cronaca di un amore. Callas e Pasolini"
COMPOSER="Davide Tramontano"
IMAGE="https://teatripiacenza.it/wp-content/uploads/2025/05/Callas-e-Pasolini.jpg"
URLS=(
    "https://www.haydn.it/eventi/cronaca-di-un-amore-callas-e-pasolini",
    "https://www.haydn.it/eventi/cronaca-di-un-amore-callas-e-pasolini-2",
)

class HaydnCoproductionArtTests(unittest.TestCase):
    def test_original_illustration_is_source_bound_to_both_recite(self):
        for source_url in URLS:
            with self.subTest(source_url=source_url):
                poster=verified_coproduction_poster(
                    source_url=source_url,title=TITLE,composer=COMPOSER)
                self.assertIsNotNone(poster)
                self.assertEqual(poster["image_url"],IMAGE)
                self.assertTrue(is_verified_coproduction_poster(
                    poster,title=TITLE,composer=COMPOSER))
                self.assertEqual(verified_candidate_image(
                    {"source_key":"haydn-rolling-opera","source_url":source_url},
                    title=TITLE,composer=COMPOSER,url=source_url)["image_url"],IMAGE)

    def test_never_reuse_art_for_different_opera_or_composer(self):
        for source_url in URLS:
            self.assertIsNone(verified_coproduction_poster(
                source_url=source_url,title="La bohème",composer=COMPOSER))
            self.assertIsNone(verified_coproduction_poster(
                source_url=source_url,title=TITLE,composer="Giacomo Puccini"))
        self.assertIsNone(verified_coproduction_poster(
            source_url="https://www.haydn.it/eventi/anna-a",
            title=TITLE,composer=COMPOSER))

if __name__=="__main__":
    unittest.main()

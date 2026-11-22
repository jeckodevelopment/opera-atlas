"""Pop-opera productions must not enter the lyric-opera catalogue."""
import unittest
from scripts.discover_season_indexes import eligible, classify


class LyricOperaOnlyTests(unittest.TestCase):
    def test_dalla_pop_opera_excluded_at_each_official_venue(self):
        candidates = (
            ("modena-teatro-opera-2026-27",
             "https://www.teatrocomunalemodena.it/spettacolo/lanno-che-verra/"),
            ("giglio-lucca-opera-2026-27",
             "https://www.teatrodelgigliogiacomopuccini.it/it/cartellone/lirica/stagione-2026-2027/lanno-che-verra/"),
            ("piacenza-opera-2026-27",
             "https://teatripiacenza.it/event/lanno-che-verra/"),
        )
        for key, url in candidates:
            with self.subTest(source=key):
                self.assertFalse(eligible(key, url))
                self.assertEqual(classify(key, url, set()), "excluded_nonopera")
                self.assertEqual(classify(key, url, {url}), "excluded_nonopera")

    def test_other_real_lyric_opera_candidates_remain_eligible(self):
        for key, url in (
            ("modena-teatro-opera-2026-27",
             "https://www.teatrocomunalemodena.it/spettacolo/umberto-giordano-siberia/"),
            ("piacenza-opera-2026-27",
             "https://teatripiacenza.it/event/la-clemenza-di-tito/"),
        ):
            with self.subTest(source=key):
                self.assertTrue(eligible(key, url))
                self.assertEqual(classify(key, url, set()), "needs_review")


if __name__ == "__main__":
    unittest.main()

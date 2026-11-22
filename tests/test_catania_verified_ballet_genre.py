"""Official genre evidence excludes one ballet, not neighboring chamber operas."""
import unittest
from scripts.discover_season_indexes import excluded_nonopera, classify

SOURCE="bellini-catania-opera-2026-27"
HOST="https://www.teatromassimobellini.it/eventi/"

class BelliniOperaGenreTests(unittest.TestCase):
    def test_sleeping_beauty_ballet_is_not_queued_as_an_opera(self):
        self.assertTrue(excluded_nonopera(SOURCE,HOST+"la-bella-addormentata-5/"))
        self.assertEqual(classify(SOURCE,HOST+"la-bella-addormentata-5/",set()),
                         "excluded_nonopera")

    def test_two_first_party_chamber_operas_remain_candidates(self):
        for slug in ("il-quinto-moschettiere-2","le-nozze-dellorso"):
            with self.subTest(slug=slug):
                self.assertFalse(excluded_nonopera(SOURCE,HOST+slug+"/"))
                self.assertEqual(classify(SOURCE,HOST+slug+"/",set()),
                                 "needs_review")

    def test_only_same_source_and_exact_url_leaf_is_excluded(self):
        self.assertFalse(excluded_nonopera("reggio-valli-opera-2026-27",
                                          HOST+"la-bella-addormentata-5/"))
        self.assertFalse(excluded_nonopera(SOURCE,HOST+"la-bella-addormentata-6/"))


if __name__=="__main__":
    unittest.main()

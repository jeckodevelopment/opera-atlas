"""Exact mixed-festival exclusions never suppress actual operas."""
import unittest
from scripts.discover_season_indexes import excluded_nonopera, classify

BASE_ROF="https://www.rossinioperafestival.it/archivio/stagione-2026/"
BASE_TRAPANI="https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/"

class MixedFestivalExclusionsTests(unittest.TestCase):
    def test_rof_concert_sections_only(self):
        for slug in ("concerti-di-belcanto","festival-giovane",
                     "incontri","rossinimania","stabat-mater"):
            self.assertTrue(excluded_nonopera("pesaro-rof-2026",BASE_ROF+slug+"/"))
        for slug in ("le-siege-de-corinthe","il-viaggio-a-reims",
                     "la-scala-di-seta","loccasione-fa-il-ladro"):
            with self.subTest(slug=slug):
                self.assertFalse(excluded_nonopera("pesaro-rof-2026",BASE_ROF+slug+"/"))

    def test_trapani_instrumental_and_pop_events_not_operas(self):
        for slug in ("new-saxophone-orchestra","duo-resonans",
                     "duo-monica-leone-michele-campanella",
                     "quartetto-vocale-faraualla","concerto-di-natale",
                     "concerto-di-capodanno","bruno-canino",
                     "sicily-jazz-concert"):
            with self.subTest(slug=slug):
                url=BASE_TRAPANI+slug+"/"
                self.assertTrue(excluded_nonopera("trapani-luglio-musicale-2026",url))
                self.assertEqual(classify("trapani-luglio-musicale-2026",url,set()),
                                 "excluded_nonopera")
        for slug in ("l-elisir-d-amore","i-capuleti-e-i-montecchi",
                     "l-opera-forse-di-francesco-filidei-infinito-nero-di-salvatore-sciarrino"):
            self.assertFalse(excluded_nonopera("trapani-luglio-musicale-2026",
                                              BASE_TRAPANI+slug+"/"))

if __name__=="__main__":
    unittest.main()

"""Explicit official genres: concerts/dance excluded, actual operas retained."""
import unittest
from scripts.discover_season_indexes import excluded_nonopera, classify

ROF="https://www.rossinioperafestival.it/archivio/stagione-2026/"
TRAPANI="https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/"
MARTINA="https://www.festivaldellavalleditria.it/spettacolo/"

class FestivalGenreBoundaryTests(unittest.TestCase):
    def test_rof_recital_is_not_opera(self):
        self.assertTrue(excluded_nonopera("pesaro-rof-2026",ROF+"florez-30/"))
        self.assertFalse(excluded_nonopera("pesaro-rof-2026",ROF+"il-viaggio-a-reims/"))

    def test_trapani_dance_and_concert_vs_real_chamber_opera(self):
        for slug in ("romeo-e-giulietta","food-ensemble","quintetto-sospeso"):
            with self.subTest(slug=slug):
                url=TRAPANI+slug+"/"
                self.assertEqual(classify("trapani-luglio-musicale-2026",url,set()),
                                 "excluded_nonopera")
        for slug in ("ghost-cafe","magic-words-circus","fuori-fuoco",
                     "l-opera-forse-di-francesco-filidei-infinito-nero-di-salvatore-sciarrino"):
            self.assertFalse(excluded_nonopera("trapani-luglio-musicale-2026",
                                               TRAPANI+slug+"/"))

    def test_martina_dated_event_urls_not_shared_date_slug(self):
        for slug,date in (("approfondimenti","2026-07-18"),
                          ("in-orbita-naufragi","2026-07-10")):
            self.assertTrue(excluded_nonopera(
                "martina-valle-itria-2026",MARTINA+slug+"/"+date))
        for slug,date in (("carmen","2026-07-25"),
                          ("il-schiavo-di-sua-moglie","2026-07-24")):
            self.assertFalse(excluded_nonopera(
                "martina-valle-itria-2026",MARTINA+slug+"/"+date))

if __name__=="__main__":
    unittest.main()

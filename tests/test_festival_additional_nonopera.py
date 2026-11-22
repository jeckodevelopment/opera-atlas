"""Source-confirmed excluded 2026 festival concerts, no opera hiding."""
import unittest
from scripts.discover_season_indexes import excluded_nonopera

class FestivalConcertBoundaryTests(unittest.TestCase):
    def test_trapani_nonopera_concerts(self):
        base="https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/"
        for slug in ("american-dream","requiem-k-626",
                     "verdi-sogno-e-passione","passantino-incontra-brioschi"):
            self.assertTrue(excluded_nonopera(
                "trapani-luglio-musicale-2026",base+slug+"/"))
        for slug in ("nabucco","l-elisir-d-amore",
                     "magic-words-circus","ghost-cafe","fuori-fuoco"):
            self.assertFalse(excluded_nonopera(
                "trapani-luglio-musicale-2026",base+slug+"/"))

    def test_martina_concert_not_opera(self):
        base="https://www.festivaldellavalleditria.it/spettacolo/"
        self.assertTrue(excluded_nonopera("martina-valle-itria-2026",
                                          base+"vennero-da-ogni-dove/2026-07-20"))
        for path in ("carmen/2026-07-25","il-schiavo-di-sua-moglie/2026-07-24",
                     "pulcinella-la-favola-di-orfeo/2026-07-14"):
            self.assertFalse(excluded_nonopera("martina-valle-itria-2026",base+path))

if __name__=="__main__":
    unittest.main()

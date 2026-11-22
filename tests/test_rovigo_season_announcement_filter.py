"""Regional season announcement must not masquerade as one opera."""
import unittest
from scripts.discover_season_indexes import classify, excluded_nonopera, eligible

REGIONAL="https://www.culturaveneto.it/spettacoli/musica/3563a671-d9b2-46bf-a10d-776af9ab17bc"

class RovigoRegionalAnnouncementTests(unittest.TestCase):
    def test_regional_season_program_is_not_a_ticketed_work(self):
        key="rovigo-regione-programma-2026-27"
        self.assertFalse(eligible(key,REGIONAL))
        self.assertTrue(excluded_nonopera(key,REGIONAL))
        self.assertEqual(classify(key,REGIONAL,set()),"excluded_nonopera")
        self.assertEqual(classify(key,REGIONAL,{REGIONAL}),"excluded_nonopera")

    def test_actual_rovigo_production_urls_stay_eligible(self):
        url="https://www.comune.rovigo.it/teatrosociale/dettaglio-teatro/eventi/aida"
        self.assertTrue(eligible("rovigo-sociale-opera-2026-27",url))
        self.assertFalse(excluded_nonopera("rovigo-sociale-opera-2026-27",url))

if __name__=="__main__":
    unittest.main()

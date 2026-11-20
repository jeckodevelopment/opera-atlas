"""Genre isolation must not silently turn dance, concerts or previews into opera."""
import unittest
from scripts.discover_season_indexes import excluded_nonopera,classify,EXCLUDED_PATHS

class SourceGenreFilteringTests(unittest.TestCase):
    def test_only_exact_checked_paths_are_excluded(self):
        examples=[
            ("arena-festival-2027","https://www.arena.it/arena-opera-festival/romeo-e-giulietta/"),
            ("scala-season-2026-27","https://www.teatroallascala.org/it/stagione/2026-2027/opera/otello-anteprima-under30.html"),
            ("parma-opera-2027","https://teatroregioparma.it/spettacolo/concerto-di-capodanno-27/"),
            ("parma-opera-2027","https://teatroregioparma.it/spettacolo/verdi-off-los-angeles/"),
            ("massimo-season-2026-27","https://www.teatromassimo.it/event/nuovo-cinema-paradiso/"),
            ("massimo-season-2026-27","https://www.teatromassimo.it/event/lo-schiaccianoci-4/"),
            ("massimo-season-2026-27","https://www.teatromassimo.it/event/non-dirmi-che-hai-paura/"),
        ]
        for key,url in examples:
            with self.subTest(url=url):
                self.assertTrue(excluded_nonopera(key,url))
                self.assertEqual(classify(key,url,set()),"excluded_nonopera")

    def test_real_opera_titles_and_variant_slugs_remain_pending(self):
        titles=[
            ("scala-season-2026-27","https://www.teatroallascala.org/it/stagione/2026-2027/opera/anna-bolena.html"),
            ("scala-season-2026-27","https://www.teatroallascala.org/it/stagione/2026-2027/opera/otello.html"),
            ("arena-festival-2027","https://www.arena.it/arena-opera-festival/aida-ed-stefano-poda/"),
            ("parma-opera-2027","https://teatroregioparma.it/spettacolo/boris-godunov/"),
            ("parma-opera-2027","https://teatroregioparma.it/spettacolo/piccolo-orso-e-la-montagna-di-ghiaccio/"),
            ("fenice-opera-2026-27","https://www.teatrolafenice.it/event/adriana-lecouvreur/"),
            ("massimo-season-2026-27","https://www.teatromassimo.it/event/falstaff-2/"),
            ("massimo-season-2026-27","https://www.teatromassimo.it/event/ernani-2/"),
        ]
        for key,url in titles:
            with self.subTest(url=url):
                self.assertFalse(excluded_nonopera(key,url))
                self.assertEqual(classify(key,url,set()),"needs_review")
        self.assertGreaterEqual(sum(len(v) for v in EXCLUDED_PATHS.values()),50)

    def test_verified_canonical_source_is_never_lost_for_opera(self):
        key="massimo-season-2026-27"
        url="https://www.teatromassimo.it/event/carmen-3/"
        self.assertEqual(classify(key,url,{url}),"already_catalogued")

if __name__=="__main__":
    unittest.main()

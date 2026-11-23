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
            ("petruzzelli-opera-2026","https://www.fondazionepetruzzelli.it/eventi/le-lac-des-cygnes-il-lago-dei-cigni-12-15-novembre/"),
            ("petruzzelli-opera-2027","https://www.fondazionepetruzzelli.it/eventi/lo-schiaccianoci-di-petr-ilic-cajkovskij-11-14-febbraio/"),
            ("modena-teatro-opera-2026-27","https://www.teatrocomunalemodena.it/spettacolo/lanno-che-verra/"),
            ("coccia-novara-rolling-opera","https://www.fondazioneteatrococcia.it/stagione-27-la-bella-addormentata.html"),
            ("coccia-novara-rolling-opera","https://www.fondazioneteatrococcia.it/stagione-27-il-lago-dei-cigni.html"),
            ("coccia-novara-rolling-opera","https://www.fondazioneteatrococcia.it/stagione-27-beethoven-200.html"),
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
            ("modena-teatro-opera-2026-27","https://www.teatrocomunalemodena.it/spettacolo/daniele-furlati-i-salvatori-della-mezzanotte/"),
            ("massimo-season-2026-27","https://www.teatromassimo.it/event/falstaff-2/"),
            ("massimo-season-2026-27","https://www.teatromassimo.it/event/ernani-2/"),
            ("coccia-novara-rolling-opera","https://www.fondazioneteatrococcia.it/stagione-27-il-noce-di-benevento.html"),
            ("coccia-novara-rolling-opera","https://www.fondazioneteatrococcia.it/stagione-27-l-amor-mio.html"),
            ("coccia-novara-rolling-opera","https://www.fondazioneteatrococcia.it/stagione-27-dove-nasce-il-melograno.html"),
        ]
        for key,url in titles:
            with self.subTest(url=url):
                self.assertFalse(excluded_nonopera(key,url))
                self.assertEqual(classify(key,url,set()),"needs_review")
        self.assertGreaterEqual(sum(len(v) for v in EXCLUDED_PATHS.values()),50)

    def test_utility_navigation_is_not_an_opera_candidate(self):
        # These exact pages were accidentally imported from mixed site menus.
        exclusions=[
            ("mantova-sociale-rolling-opera","https://www.teatrosocialemantova.it/it-it/contatti.aspx"),
            ("mantova-sociale-rolling-opera","https://www.teatrosocialemantova.it/it-it/privacy-policy.aspx"),
            ("mantova-sociale-rolling-opera","https://www.teatrosocialemantova.it/it-it/biglietteria.aspx"),
            ("vicenza-olimpico-rolling-opera","https://www.vicenzainlirica.it/sponsor/"),
            ("vicenza-olimpico-rolling-opera","https://www.vicenzainlirica.it/privacy-policy/"),
        ]
        for key,url in exclusions:
            with self.subTest(url=url):
                self.assertTrue(excluded_nonopera(key,url))
                self.assertEqual(classify(key,url,set()),"excluded_nonopera")
        # Performance pages and new season URLs must remain reviewable.
        eligible=[
            ("mantova-sociale-rolling-opera","https://www.teatrosocialemantova.it/it-it/tosca.aspx"),
            ("mantova-sociale-rolling-opera","https://www.teatrosocialemantova.it/it-it/cavalleria-rusticana-la-serva-padrona.aspx"),
            ("vicenza-olimpico-rolling-opera","https://www.vicenzainlirica.it/le-nozze-di-figaro-mozart/"),
            ("vicenza-olimpico-rolling-opera","https://www.vicenzainlirica.it/lorfeo-monteverdi/"),
        ]
        for key,url in eligible:
            with self.subTest(url=url):
                self.assertFalse(excluded_nonopera(key,url))
                self.assertEqual(classify(key,url,set()),"needs_review")

    def test_residual_nonopera_pages_are_exactly_scoped(self):
        excluded=[
            ("mantova-sociale-rolling-opera","https://www.teatrosocialemantova.it/it-it/annullato-gala-lirico.aspx"),
            ("mantova-sociale-rolling-opera","https://www.teatrosocialemantova.it/it-it/lirica-nel-foyer-aperitivo-in-musica.aspx"),
            ("mantova-sociale-rolling-opera","https://www.teatrosocialemantova.it/it-it/opera-domani-aida-amore-e-coraggio.aspx"),
            ("vicenza-olimpico-rolling-opera","https://www.vicenzainlirica.it/vetrine-vestono-lirica/"),
            ("vicenza-olimpico-rolling-opera","https://www.vicenzainlirica.it/olimpichetto-il-ritorno-di-un-ambasciatore/"),
            ("sabbioneta-antica-rolling-opera","https://sabbionetaoperafestival.it/evento/gran-concerto-di-natale/"),
        ]
        for key,url in excluded:
            with self.subTest(url=url):
                self.assertTrue(excluded_nonopera(key,url))
                self.assertEqual(classify(key,url,set()),"excluded_nonopera")
        still_eligible=[
            ("mantova-sociale-rolling-opera","https://www.teatrosocialemantova.it/it-it/madama-butterfly.aspx"),
            ("vicenza-olimpico-rolling-opera","https://www.vicenzainlirica.it/il-filosofo-di-campagna-galuppi/"),
            ("sabbioneta-antica-rolling-opera","https://sabbionetaoperafestival.it/evento/nuova-opera/"),
            ("trapani-luglio-musicale-2026","https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/magic-words-circus/"),
        ]
        for key,url in still_eligible:
            with self.subTest(url=url):
                self.assertFalse(excluded_nonopera(key,url))
                self.assertEqual(classify(key,url,set()),"needs_review")

    def test_verified_canonical_source_is_never_lost_for_opera(self):
        key="massimo-season-2026-27"
        url="https://www.teatromassimo.it/event/carmen-3/"
        self.assertEqual(classify(key,url,{url}),"already_catalogued")

if __name__=="__main__":
    unittest.main()

"""Asti official mixed calendar -> genre-scoped canonical evidence, future-proof."""
import json
import unittest
from scripts.discover_season_indexes import CONFIG,eligible,extract,validate_config
from scripts.collect_candidate_details import parse_source_credited_opera_detail
from scripts.source_automation import INDEX_VENUES
from scripts.auto_catalogue import VENUE_BY_SOURCE
from opera_atlas.asti_alfieri_parser import INDEX,parse_detail

KEY="asti-alfieri-rolling-opera"
AIDA="https://www.teatroalfieriasti.it/event/aida/"
CONCERT="https://www.teatroalfieriasti.it/event/concerto-di-capodanno/"
def detail(year=2027,kind="opera"):
    if kind=="opera":
        return (f'<main><h1>Aida</h1><p>06/02/{year} @ 21:00</p>'
                '<h2>Aida</h2><p>di Giuseppe Verdi Regia Renato Bonajuto '
                'Produzione Lirica Tamagno Fuori abbonamento '
                'Opera ambientata nell’antico Egitto</p>'
                '<h2>Dettagli</h2><p>Data</p><h2>Luogo</h2>'
                '<p>Teatro Alfieri Via al teatro, 2 Asti (AT)</p></main>')
    return (f'<main><h1>Concerto di Capodanno</h1><p>01/01/{year} @ 17:00</p>'
            '<p>di Giuseppe Verdi Regia Renato Bonajuto Concerto</p>'
            '<h2>Luogo</h2><p>Teatro Alfieri Via al teatro, 2 Asti</p></main>')

class AstiAlfieriRollingTests(unittest.TestCase):
    def test_evergreen_config_and_exact_target_venue(self):
        config=json.loads(CONFIG.read_text(encoding="utf-8"))
        source=next(s for s in validate_config(config) if s["key"]==KEY)
        self.assertEqual(source["url"],INDEX)
        self.assertEqual(INDEX_VENUES[KEY],("Asti|Teatro Alfieri",))
        self.assertEqual(VENUE_BY_SOURCE[KEY],("Asti","Teatro Alfieri"))
        policy=json.loads(open("data/season-lifecycle-policy.json",encoding="utf-8").read())
        self.assertEqual(policy["sources"][KEY]["strategy"],"evergreen_index")

    def test_index_lists_mixed_events_but_details_are_strict(self):
        html=f'<a href="/event/concerto-di-capodanno/">Concerto</a><a href="{AIDA}">Aida</a>'
        self.assertEqual(extract(KEY,INDEX,html,1),[AIDA,CONCERT])
        self.assertTrue(eligible(KEY,AIDA))
        for url in ("https://example.org/event/aida/",
                    "http://www.teatroalfieriasti.it/event/aida/",
                    AIDA+"?source=other",
                    "https://www.teatroalfieriasti.it/events/elenco/"):
            self.assertFalse(eligible(KEY,url))
        self.assertEqual(parse_detail(detail(),url=AIDA),
                         ("Aida","Giuseppe Verdi","Teatro Alfieri",[("2027-02-06","21:00")]))
        self.assertEqual(parse_source_credited_opera_detail(KEY,AIDA,detail()),
                         [{"event_title":"Aida","composer":"Giuseppe Verdi",
                           "venue":"Teatro Alfieri","date":"2027-02-06",
                           "starts_at":"2027-02-06T21:00:00+01:00"}])
        with self.assertRaisesRegex(ValueError,"not verified as an opera"):
            parse_detail(detail(kind="concert"),url=CONCERT)

    def test_aida_composer_in_separate_official_production_header(self):
        # The live Asti page has separate H1, event clock, H2 work heading,
        # composer line and direction credit. It must not require the
        # composer to be in a single paragraph with the director.
        html=('<main><h1>Aida</h1><p>06/02/2027 @ 21:00</p>'
              '<h2>Aida</h2><p>di Giuseppe Verdi</p>'
              '<p>Regia Renato Bonajuto</p><p>Produzione Lirica Tamagno</p>'
              '<p>Fuori abbonamento</p><p>Opera ambientata in Egitto</p>'
              '<h2>Dettagli</h2><p>Data: 06/02/2027</p>'
              '<h2>Luogo</h2><p>Teatro Alfieri Via al teatro, 2 Asti (AT)</p>'
              '</main>')
        self.assertEqual(parse_detail(html,url=AIDA),
                         ("Aida","Giuseppe Verdi","Teatro Alfieri",
                          [("2027-02-06","21:00")]))
        # Multiple conflicting production headings or a different source
        # credit cannot establish the identity.
        for broken in (
            html.replace('<p>di Giuseppe Verdi</p>','<p>di Altro Autore</p>'),
            html.replace('<h2>Aida</h2>','<h2>Aida</h2><h2>Aida</h2>'),
            html.replace('<p>Regia Renato Bonajuto</p>','<p>Direttore</p>'),
            html.replace('<p>Opera ambientata','<p>Prosa ambientata'),
        ):
            with self.subTest(broken=broken[:130]),self.assertRaises(ValueError):
                parse_detail(broken,url=AIDA)

    def test_future_year_is_from_official_event_not_current_year(self):
        title,composer,venue,dates=parse_detail(detail(2029),url=AIDA)
        self.assertEqual((title,composer,venue),("Aida","Giuseppe Verdi","Teatro Alfieri"))
        self.assertEqual(dates,[("2029-02-06","21:00")])

    def test_no_missing_genre_composer_clock_or_venue(self):
        base=detail()
        for bad in (
            base.replace("Opera ambientata","Dramma di prosa ambientato"),
            base.replace("di Giuseppe Verdi",""),
            base.replace("06/02/2027 @ 21:00",""),
            base.replace("Teatro Alfieri Via al teatro, 2 Asti","Teatro Altrove Via al teatro, 2 Asti")
        ):
            with self.subTest(bad=bad[-100:]),self.assertRaises(ValueError):
                parse_detail(bad,url=AIDA)

if __name__=="__main__":
    unittest.main()

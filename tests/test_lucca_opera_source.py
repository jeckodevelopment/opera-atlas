"""Lucca Teatro del Giglio 2026/27 direct production source regressions."""
import json
import unittest
from opera_atlas.lucca_opera_parser import parse_detail
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract
from scripts.collect_candidate_details import parse_source_credited_opera_detail

KEY="giglio-lucca-opera-2026-27"
INDEX="https://www.teatrodelgigliogiacomopuccini.it/it/cartellone/lirica/stagione-2026-2027/"
DETAIL=INDEX+"il-barbiere-di-siviglia/"

def page(*,theatre="Teatro del Giglio",kind="Lirica",credit="GIOACHINO ROSSINI",
         dates=None):
    dates = ('Il 22 gennaio 2027 Ore 20:30 '
             'Il 24 gennaio 2027 Ore 16:00') if dates is None else dates
    return ('<html><header>I prossimi spettacoli: '
            'Il 11 ottobre 2026 Ore 11:30 Teatro San Girolamo '
            'Il 12 ottobre 2026 Ore 21:00</header>'
            '<p>MENU</p><div>TEATRO DEL GIGLIO Il barbiere di Siviglia '
            f'{theatre} {kind} {dates} Biglietto non ancora disponibile</div>'
            '<main><h1>Il barbiere di Siviglia</h1>'
            '<h2>Commedia in due atti</h2>'
            f'<p>Musica di {credit}</p>'
            '<p>Il Conte di Almaviva Paolo Nevi</p>'
            '</main><footer><h3>Segui tutte le novità</h3>'
            'Il 1 novembre 2026 Ore 20:00</footer></html>')

class LuccaOperaTests(unittest.TestCase):
    def test_exact_official_index_and_production_scope(self):
        sources=validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
        x=next(v for v in sources if v["key"]==KEY)
        self.assertEqual(x["url"],INDEX)
        self.assertEqual(len(sources),36)
        self.assertTrue(eligible(KEY,DETAIL))
        self.assertFalse(eligible(KEY,"https://www.teatrodelgigliogiacomopuccini.it/it/cartellone/prosa/stagione-2026-2027/foo/"))
        html="".join(f'<a href="{slug}/">Lirica</a>' for slug in
            ["il-barbiere-di-siviglia","otello","l-anno-che-verra","aida"])
        html+='<a href="https://evil.example/it/cartellone/lirica/stagione-2026-2027/bogus/">External</a>'
        self.assertEqual(len(extract(KEY,INDEX,html,4)),4)

    def test_two_barbiere_recitals_only(self):
        title,composer,venue,dates=parse_detail(page(),url=DETAIL)
        self.assertEqual((title,composer,venue),
                         ("Il barbiere di Siviglia","GIOACHINO ROSSINI",
                          "Teatro del Giglio Giacomo Puccini"))
        self.assertEqual(dates,[("2027-01-22","20:30"),("2027-01-24","16:00")])
        facts=parse_source_credited_opera_detail(KEY,DETAIL,page())
        self.assertEqual(len(facts),2)
        self.assertEqual(facts[0]["starts_at"],"2027-01-22T20:30:00+01:00")

    def test_mismatched_venue_genre_composer_or_partial_date_fail(self):
        for fixture in [
            page(theatre="Teatro San Girolamo"),
            page(kind="Prosa"),
            page(credit=""),
            page(dates="Il 22 gennaio 2027 Ore 20:30 Il 24 gennaio 2027"),
        ]:
            with self.subTest(fixture=fixture[-120:]):
                with self.assertRaises(ValueError):
                    parse_detail(fixture,url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(page(),url=DETAIL.replace("www.teatrodelgigliogiacomopuccini.it","bad.invalid"))

if __name__=="__main__":
    unittest.main()

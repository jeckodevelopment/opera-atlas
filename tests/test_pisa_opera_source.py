"""Pisa official opera 2026/27: exact five titles and date scope."""
import unittest
from opera_atlas.pisa_opera_parser import parse_detail
from scripts.discover_season_indexes import eligible,extract
BASE="https://teatrodipisa.it"
URL=BASE+"/spettacolo/la-clemenza-di-tito/"
HTML="""<h1>La clemenza di Tito</h1><p>Musica di Wolfgang Amadeus Mozart</p>
<p>Nuovo allestimento del Teatro Alighieri di Ravenna in coproduzione con Teatro Verdi di Pisa.</p>
<h3>Date:</h3><h4>16 Aprile 2027 20:30</h4><h4>18 Aprile 2027 15:30</h4>
<a>Acquista biglietto</a><h3>Allegati:</h3>"""
class PisaOperaTests(unittest.TestCase):
    def test_index_allowlist(self):
        self.assertTrue(eligible("pisa-verdi-opera-2026-27",URL))
        self.assertFalse(eligible("pisa-verdi-opera-2026-27",BASE+"/spettacolo/carmen/"))
        self.assertFalse(eligible("pisa-verdi-opera-2026-27",BASE+"/spettacolo/otello/?ref=1"))
        slugs=("dido-and-aeneas","loccasione-fa-il-ladro-ossia-il-cambio-della-valigia",
               "otello","aida","la-clemenza-di-tito")
        html="".join(f'<a href="/spettacolo/{s}/">Opera</a>' for s in slugs)
        html+='<a href="/spettacolo/carmen/">Older season</a>'
        self.assertEqual(len(extract("pisa-verdi-opera-2026-27",BASE+"/tipologia-spettacolo/opera/",html,5)),5)
    def test_exact_dates_and_credit(self):
        self.assertEqual(parse_detail(HTML,url=URL),
            ("La clemenza di Tito","Wolfgang Amadeus Mozart","Teatro Verdi",
             [("2027-04-16","20:30"),("2027-04-18","15:30")]))
        for bad in [HTML.replace("Wolfgang Amadeus Mozart","Antonio Vivaldi"),
                    HTML.replace("16 Aprile 2027","16 Aprile 2026"),
                    HTML.replace("18 Aprile 2027 15:30",""),
                    HTML.replace("Teatro Verdi di Pisa","Teatro Comunale di Bologna")]:
            with self.assertRaises(ValueError):parse_detail(bad,url=URL)
        with self.assertRaises(ValueError):parse_detail(HTML,url="https://fake.example/spettacolo/la-clemenza-di-tito/")
if __name__=="__main__":unittest.main()

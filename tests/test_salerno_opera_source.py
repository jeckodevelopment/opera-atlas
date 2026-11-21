"""Salerno 2026: reject ballet, foreign URLs and unverified dates."""
import unittest
from opera_atlas.salerno_opera_parser import parse_detail
from scripts.discover_season_indexes import eligible,extract

BASE="https://cultura.comune.salerno.it"
URL=BASE+"/eventi/turandot-2026/"
HTML="""<h1>Turandot | 2026</h1><div>Teatro Municipale Giuseppe Verdi</div>
<p>Opera in tre atti e cinque quadri di Giacomo Puccini</p>
<h3>APPUNTAMENTI</h3><p>Lunedì 21 dicembre, ore 21.00 FUORI ABBONAMENTO</p>
<p>Mercoledì 23 dicembre, ore 21.00 TURNO A</p>
<p>Sabato 26 dicembre, ore 18.00 TURNO B</p><h4>Luoghi collegati</h4>"""

class SalernoOperaTests(unittest.TestCase):
    def test_exact_source_links(self):
        self.assertTrue(eligible("salerno-verdi-opera-2026",URL))
        self.assertFalse(eligible("salerno-verdi-opera-2026",BASE+"/eventi/carmen-2026/"))
        self.assertFalse(eligible("salerno-verdi-opera-2026",BASE+"/eventi/la-vie-en-rose-bolero-2026/"))
        self.assertFalse(eligible("salerno-verdi-opera-2026",URL+"?test=1"))
        slugs=("trovatore-2026","il-signor-bruschino-2026","il-barbiere-di-siviglia-2026",
               "macbeth-2026","la-vedova-allegra-2026","turandot-2026")
        html="".join(f'<a href="/eventi/{slug}/">opera</a>' for slug in slugs)
        html+='<a href="/eventi/carmen-2026/">balletto</a>'
        self.assertEqual(len(extract("salerno-verdi-opera-2026",BASE+"/teatro-verdi/la-stagione/",html,6)),6)
    def test_verified_turandot(self):
        title,composer,venue,dates=parse_detail(HTML,url=URL)
        self.assertEqual((title,composer,venue),("Turandot","Giacomo Puccini","Teatro Municipale Giuseppe Verdi"))
        self.assertEqual(dates,[("2026-12-21","21:00"),("2026-12-23","21:00"),("2026-12-26","18:00")])
        for invalid in [HTML.replace("Lunedì 21","Martedì 21"),HTML.replace("Sabato 26 dicembre, ore 18.00",""),
                        HTML.replace("Giacomo Puccini","Giuseppe Verdi"),HTML.replace("Teatro Municipale Giuseppe Verdi","Altro teatro")]:
            with self.assertRaises(ValueError):parse_detail(invalid,url=URL)
        with self.assertRaises(ValueError):parse_detail(HTML,url="https://fake.example/eventi/turandot-2026/")
if __name__=="__main__":unittest.main()

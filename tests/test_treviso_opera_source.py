"""Treviso: only official public ticketed performances, never school previews."""
import unittest
from opera_atlas.treviso_opera_parser import parse_program
from scripts.discover_season_indexes import eligible,extract

URL="https://risorse.teatrostabileveneto.it/treviso-teatro-del-monaco-stagione-lirica-concertistica-26-27"
HTML="""<h2>PROGRAMMA STAGIONE LIRICA 26/27</h2>
<h2>21, 23, 25 ottobre 2026</h2><p>LA TRAVIATA / Giuseppe Verdi</p>
<h2>1, 4, 6 dicembre 2026</h2><p>PAGLIACCI / Ruggero Leoncavallo</p>
<h2>7 febbraio 2027 (Evento speciale fuori abbonamento)</h2>
<p>IL PIPISTRELLO / Johann Strauss</p>
<h2>3, 5, 7 marzo 2027</h2>
<p>IL CAPPELLO DI PAGLIA DI FIRENZE / Nino Rota</p>
<h3>ANTEPRIMA PER SCUOLE</h3><p>Mercoledì ore 18.00</p>
<p>(per Pagliacci martedì)</p>
<h3>TURNO A</h3><p>Venerdì ore 20.00</p>
<h3>TURNO C</h3><p>Domenica ore 16.00</p>
<h3>PREZZI ABBONAMENTI LIRICA</h3>
<h2>PROGRAMMA STAGIONE CONCERTISTICA 26/27</h2>
<p>19 gennaio 2027 concerto d'archi</p>"""

class TrevisoSourceTests(unittest.TestCase):
    def test_reuse_only_first_party_exact_season_page(self):
        self.assertTrue(eligible("treviso-del-monaco-opera-2026-27",URL))
        self.assertFalse(eligible("treviso-del-monaco-opera-2026-27",URL+"/more"))
        self.assertFalse(eligible("treviso-del-monaco-opera-2026-27",URL+"?utm=1"))
        self.assertEqual(extract("treviso-del-monaco-opera-2026-27",URL,HTML,1),[URL])
    def test_six_public_recite_not_school_or_concert(self):
        result=parse_program(HTML,url=URL)
        self.assertEqual(result,[
            ("La traviata","Giuseppe Verdi","Teatro Comunale Mario del Monaco","2026-10-23","20:00"),
            ("La traviata","Giuseppe Verdi","Teatro Comunale Mario del Monaco","2026-10-25","16:00"),
            ("Pagliacci","Ruggero Leoncavallo","Teatro Comunale Mario del Monaco","2026-12-04","20:00"),
            ("Pagliacci","Ruggero Leoncavallo","Teatro Comunale Mario del Monaco","2026-12-06","16:00"),
            ("Il cappello di paglia di Firenze","Nino Rota","Teatro Comunale Mario del Monaco","2027-03-05","20:00"),
            ("Il cappello di paglia di Firenze","Nino Rota","Teatro Comunale Mario del Monaco","2027-03-07","16:00"),
        ])
        self.assertFalse(any("2026-12-01" in row or "2027-02-07" in row for x in result for row in x))
    def test_fail_closed_on_attribution_and_turns(self):
        for bad in (HTML.replace("Giuseppe Verdi","Pietro Mascagni"),
                    HTML.replace("Venerdì ore 20.00","Venerdì ore 17.00"),
                    HTML.replace("3, 5, 7 marzo 2027","3, 5, 8 marzo 2027"),
                    HTML.replace("PREZZI ABBONAMENTI LIRICA","LISTINO"),
                    HTML.replace("ANTEPRIMA PER SCUOLE","RECITE APERTE AL PUBBLICO")):
            with self.assertRaises(ValueError):
                parse_program(bad,url=URL)
        with self.assertRaises(ValueError):
            parse_program(HTML,url="https://evil.example"+URL.split("it",1)[-1])
if __name__=="__main__":
    unittest.main()

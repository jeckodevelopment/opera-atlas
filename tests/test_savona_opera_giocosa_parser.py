"""Regression tests for the official Opera Giocosa homepage evidence."""
import unittest
from opera_atlas.savona_opera_giocosa_parser import parse_homepage,URL

def fixture(year=2026):
    return f"""<h2>Stagione lirica autunnale {year}</h2>
    <div>Teatro Chiabrera</div>
    <p>Opera 23 Ottobre - ore 20:00 25 Ottobre - ore 15:30
       Teatro Chiabrera Savona La traviata di Giuseppe Verdi</p>
    <p>Opera 7 Novembre - ore 18:00 Teatro Chiabrera Savona
       I salvatori della mezzanotte di Daniele Furlati</p>
    <p>Concerto 13 Dicembre - ore 21:00 Teatro Chiabrera Savona
       Te Deum di Marc-Antoine Charpentier</p>
    <h2>Stagione lirica estiva {year}</h2>
    <p>Opera 6 Giugno - ore 18:00 Teatro Chiabrera Savona
       L’arca di Noè di Benjamin Britten</p>
    <p>Opera 25 Giugno - ore 21:15 Fortezza del Priàmar Savona
       Nabucco di Giuseppe Verdi</p>"""

class SavonaOperaGiocosaTests(unittest.TestCase):
    def test_only_issuer_credited_operas_at_chiabrera(self):
        rows=parse_homepage(fixture())
        self.assertEqual(
            [(x["title"],x["date"],x["time"]) for x in rows],
            [("L’arca di Noè","2026-06-06","18:00"),
             ("La traviata","2026-10-23","20:00"),
             ("La traviata","2026-10-25","15:30"),
             ("I salvatori della mezzanotte","2026-11-07","18:00")])
        self.assertTrue(all(x["venue"]=="Teatro Chiabrera" for x in rows))
        self.assertTrue(all(x["organizer"]=="Teatro dell'Opera Giocosa" for x in rows))

    def test_future_season_rollover_uses_issuer_heading(self):
        rows=parse_homepage(fixture(2028))
        self.assertEqual(len(rows),4)
        self.assertEqual(sorted(set(x["date"][:4] for x in rows)),["2028"])

    def test_unknown_venue_and_concert_are_not_opera(self):
        html=fixture().replace("Teatro Chiabrera Savona La traviata",
                               "Altro teatro Savona La traviata")
        self.assertFalse(any(x["title"]=="La traviata" for x in
                             parse_homepage(html)))
        self.assertFalse(any(x["title"]=="Te Deum" for x in
                             parse_homepage(fixture())))

    def test_untrusted_url_rejected(self):
        for url in ("http://operagiocosa.it/",
                    "https://operagiocosa.it/?q=node/15",
                    "https://other.example/"):
            with self.subTest(url=url),self.assertRaises(ValueError):
                parse_homepage(fixture(),url=url)

    def test_no_unsourced_dates_and_conflicting_clocks(self):
        self.assertEqual(parse_homepage("<h2>Stagione lirica autunnale 2027</h2>"
                                        "<p>Opera Teatro Chiabrera Savona "
                                        "La traviata di Giuseppe Verdi</p>"),[])
        with self.assertRaises(ValueError):
            parse_homepage(fixture()+"<h2>Stagione lirica autunnale 2026</h2>"
                           "<p>Opera 23 Ottobre - ore 21:00 Teatro Chiabrera "
                           "Savona La traviata di Giuseppe Verdi</p>")

if __name__=="__main__":
    unittest.main()

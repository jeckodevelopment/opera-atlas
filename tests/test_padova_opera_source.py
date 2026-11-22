"""Comune di Padova: exact 2026 Teatro Verdi opera times, no concerts."""
import unittest
from opera_atlas.padova_opera_parser import parse_program
from scripts.discover_season_indexes import eligible,extract

URL="https://padovacultura.padovanet.it/it/attivita-culturali/stagione-lirica-di-padova-2026"
HTML="""<h1>Stagione Lirica di Padova 2026</h1>
<p>Il debutto estivo è stato Cavalleria rusticana in Piazza Eremitani.</p>
<h2>Programma</h2>
<p>Pagliacci, 20 novembre ore 20.45, 22 novembre ore 16.00, Teatro Verdi di Padova</p>
<p>Opera in due atti, musica e libretto di Ruggero Leoncavallo.</p>
<p>biglietti da 35,82 euro</p>
<p>La Traviata, 28 dicembre ore 20.45, 29 dicembre ore 20.45, 31 dicembre ore 21.00, Teatro Verdi di Padova</p>
<p>Opera in tre atti di Giuseppe Verdi su libretto di Francesco Maria Piave.</p>
<p>biglietti da 35,82 euro</p>
<p>Concerto di Capodanno, 1 gennaio 2027 ore 17.00, replica ore 21.00.</p>
<h2>Informazioni</h2><p>Via dei Livello 32 Padova</p>"""

class PadovaOperaTests(unittest.TestCase):
    def test_exact_first_party_source(self):
        self.assertTrue(eligible("padova-verdi-opera-2026",URL))
        self.assertFalse(eligible("padova-verdi-opera-2026",URL+"?other=1"))
        self.assertFalse(eligible("padova-verdi-opera-2026",
                         "https://other.example/it/attivita-culturali/stagione-lirica-di-padova-2026"))
        self.assertEqual(extract("padova-verdi-opera-2026",URL,HTML,1),[URL])

    def test_five_operatic_times_not_concert_or_outdoor_venue(self):
        self.assertEqual(parse_program(HTML,url=URL),[
            ("Pagliacci","Ruggero Leoncavallo","Teatro Verdi","2026-11-20","20:45"),
            ("Pagliacci","Ruggero Leoncavallo","Teatro Verdi","2026-11-22","16:00"),
            ("La traviata","Giuseppe Verdi","Teatro Verdi","2026-12-28","20:45"),
            ("La traviata","Giuseppe Verdi","Teatro Verdi","2026-12-29","20:45"),
            ("La traviata","Giuseppe Verdi","Teatro Verdi","2026-12-31","21:00"),
        ])
    def test_official_composer_followed_by_verb(self):
        # The official Comune di Padova text continues with "vedrà la regia"
        # without punctuation after the composer name.
        official=HTML.replace("Ruggero Leoncavallo.", "Ruggero Leoncavallo vedrà la regia di Gabriele Lavia.")
        self.assertEqual(len(parse_program(official,url=URL)),5)

    def test_missing_attribution_or_date_fails_closed(self):
        for bad in (HTML.replace("Ruggero Leoncavallo","Giacomo Puccini"),
                    HTML.replace("Giuseppe Verdi","Giuseppe Verdi jr"),
                    HTML.replace("29 dicembre ore 20.45","29 dicembre ore 21.00"),
                    HTML.replace("Teatro Verdi di Padova","Teatro Sociale di Rovigo"),
                    HTML.replace("Stagione Lirica di Padova 2026","Stagione Lirica di Padova 2025")):
            with self.assertRaises(ValueError):parse_program(bad,url=URL)
if __name__=="__main__":unittest.main()

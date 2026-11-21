"""New official detail adapters verify title, composer, venue and real showtimes."""
import unittest
from opera_atlas.italian_detail_parser import parse_detail

CARLO="https://www.carlofelice.it/spettacolo/pagliacci/"
DONIZETTI="https://www.donizettiopera.org/it/evento/l-esule-di-roma/"

class ItalianDetailTests(unittest.TestCase):
    def test_carlo_felice_dates_from_ticket_rows_not_season_range(self):
        html=('<p>VE 22/01/2027 Turno A | Ore 20:00 | Acquista</p>'
              '<p>DO 24/01/2027 Turno C | Ore 15:00 | Acquista</p>'
              '<p>Dove: Teatro Carlo Felice</p><h1>Pagliacci</h1>'
              '<p>Musica di Ruggero Leoncavallo</p>'
              '<p>Dal 22 al 31 gennaio 2027</p>')
        venue,dates=parse_detail(html,source_key="carlo-felice-season-2026-27",
                                 url=CARLO,title="Pagliacci",composer="Ruggero Leoncavallo")
        self.assertEqual(venue,"Teatro Carlo Felice")
        self.assertEqual(dates,[("2027-01-22","20:00"),("2027-01-24","15:00")])
        with self.assertRaises(ValueError):
            parse_detail(html.replace("Ruggero Leoncavallo","Giacomo Puccini"),
                         source_key="carlo-felice-season-2026-27",url=CARLO,
                         title="Pagliacci",composer="Ruggero Leoncavallo")

    def test_donizetti_preserves_actual_venue_and_exact_schedule(self):
        html=('<h1>L\'esule di Roma</h1><p>Musica di Gaetano Donizetti</p>'
              '<h2>Info</h2><p>data</p><a>13 novembre 2026 | 20:00</a>'
              '<a>21 novembre 2026 | 20:00</a><a>29 novembre 2026 | 15:30</a>'
              '<p>Luogo</p><p>Teatro Donizetti</p><p>18.00 altri eventi</p>')
        venue,dates=parse_detail(html,source_key="donizetti-opera-2026",
                                 url=DONIZETTI,title="L'esule di Roma",
                                 composer="Gaetano Donizetti")
        self.assertEqual(venue,"Teatro Donizetti")
        self.assertEqual(len(dates),3)
        self.assertEqual(dates[-1],("2026-11-29","15:30"))
        venue,_=parse_detail(html.replace("Teatro Donizetti","Teatro Sociale"),
                             source_key="donizetti-opera-2026",
                             url=DONIZETTI,title="L'esule di Roma",
                             composer="Gaetano Donizetti")
        self.assertEqual(venue,"Teatro Sociale")

    def test_official_genova_onegin_typographic_composer_apostrophe(self):
        html=('<p>VE 16/04/2027 (Prima)Turno A | Ore 20:00 | Acquista</p>'
              '<p>SA 17/04/2027 Turno F | Ore 15:00 | Acquista</p>'
              '<p>Dove: Teatro Carlo Felice</p><h1>Evgenij Onegin</h1>'
              '<p>Scene liriche in tre atti di Pëtr Il’ič Čajkovskij</p>')
        venue,dates=parse_detail(
            html,source_key="carlo-felice-season-2026-27",
            url="https://www.carlofelice.it/spettacolo/evgenij-onegin/",
            title="Evgenij Onegin",composer="Pëtr Il'ič Čajkovskij")
        self.assertEqual(venue,"Teatro Carlo Felice")
        self.assertEqual(dates,[("2027-04-16","20:00"),("2027-04-17","15:00")])
        with self.assertRaises(ValueError):
            parse_detail(html,source_key="carlo-felice-season-2026-27",
                         url="https://www.carlofelice.it/spettacolo/evgenij-onegin/",
                         title="Evgenij Onegin",composer="Giacomo Puccini")

    def test_ambiguous_or_unsafe_does_not_emit_schedule(self):
        valid=('<h1>Pagliacci</h1><p>Ruggero Leoncavallo</p>'
               '<p>VE 22/01/2027 Turno A | Ore 20:00</p>'
               '<p>Dove: Teatro Carlo Felice</p>')
        for html in (valid.replace("Ore 20:00","ore da confermare"),
                     valid.replace("Teatro Carlo Felice","Altro teatro"),
                     valid.replace("<h1>Pagliacci</h1>","<h1>La bohème</h1>"),
                     valid.replace("VE 22/01/2027 Turno A | Ore 20:00",
                                   "VE 22/01/2027 Turno A | Ore 20:00 Annullata")):
            with self.subTest(html=html):
                with self.assertRaises(ValueError):
                    parse_detail(html,source_key="carlo-felice-season-2026-27",
                                 url=CARLO,title="Pagliacci",composer="Ruggero Leoncavallo")
        with self.assertRaises(ValueError):
            parse_detail(valid,source_key="carlo-felice-season-2026-27",
                         url="https://evil.example/spettacolo/pagliacci/",
                         title="Pagliacci",composer="Ruggero Leoncavallo")

if __name__=="__main__":
    unittest.main()

"""Two Scala and one Arena pages: source-scoped strict date/hour extraction."""
import unittest
from opera_atlas.scala_arena_parser import parse_showtimes

SCALA_URL="https://www.teatroallascala.org/it/stagione/2026-2027/opera/don-giovanni.html"
ARENA_URL="https://www.arena.it/arena-opera-festival/nabucco/"

class SourceCalendarTests(unittest.TestCase):
    def test_scala_only_individual_dated_shows(self):
        html="""<h1>Don Giovanni</h1><p>Wolfgang Amadeus Mozart</p>
        <div>Date</div><p>mer 3 febbraio 2027</p><p>Ore 20:00</p><p>Turno Prime Opera</p>
        <p>sab 6 febbraio 2027</p><p>Ore 20:00</p><p>Fuori Abb.</p>
        <p>dom 28 febbraio 2027</p><p>Ore 14:30</p><p>ROLEX</p>
        <p>Opera Don Giovanni dal 3 al 28 febbraio 2027</p>"""
        result=parse_showtimes(html,url=SCALA_URL,title="Don Giovanni",
                               composer="Wolfgang Amadeus Mozart",adapter="scala")
        self.assertEqual(result,[("2027-02-03","20:00"),("2027-02-06","20:00"),
                                 ("2027-02-28","14:30")])

    def test_arena_replacement_date_is_not_mistaken_for_recita(self):
        html="""<h1>Nabucco</h1><p>Giuseppe Verdi</p>
        <p>Nabucco previsto 27 agosto 2027 sostituito con Carmen</p>
        <h2>Prossimi spettacoli</h2>
        <div>29 luglio 2027</div><p>ore 21:15</p>
        <p>Nabucco 29 luglio 2027 - Il Cast</p>
        <div>05 agosto 2027</div><p>ore 21:00</p>
        <h2>Cast</h2><p>Nabucco previsto 27 agosto 2027 sostituito</p>"""
        result=parse_showtimes(html,url=ARENA_URL,title="Nabucco",
                               composer="Giuseppe Verdi",adapter="arena")
        self.assertEqual(result,[("2027-07-29","21:15"),("2027-08-05","21:00")])
        self.assertTrue(all(d!="2027-08-27" for d,h in result))

    def test_invalid_host_and_missing_exact_hours_fail_closed(self):
        with self.assertRaises(ValueError):
            parse_showtimes("<h1>Nabucco</h1><p>Giuseppe Verdi</p>",
                 url="https://example.com/arena-opera-festival/nabucco/",
                 title="Nabucco",composer="Giuseppe Verdi",adapter="arena")
        html="<p>Don Giovanni Wolfgang Amadeus Mozart Date mer 3 febbraio 2027 ROLEX</p>"
        with self.assertRaises(ValueError):
            parse_showtimes(html,url=SCALA_URL,title="Don Giovanni",
                 composer="Wolfgang Amadeus Mozart",adapter="scala")

if __name__=="__main__":
    unittest.main()

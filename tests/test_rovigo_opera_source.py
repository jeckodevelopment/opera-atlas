"""Rovigo source: do not invent performances from a season announcement."""
import unittest

from opera_atlas.rovigo_opera_parser import identify_season,parse_program
from scripts.discover_season_indexes import eligible,extract

URL=("https://www.comune.rovigo.it/teatrosociale/dettaglio-teatro/"
     "teatrosociale-info/stagione-slider-2026-2027")
HEADER="<h1>Teatro Sociale di Rovigo — stagione 2026/2027</h1>"
ANNOUNCEMENT=HEADER+"<p>Pagliacci di Ruggero Leoncavallo e La traviata di Giuseppe Verdi.</p>"
DATES=(
    HEADER
    +"<h2>Pagliacci</h2><p>musica di Ruggero Leoncavallo</p>"
    +"<p>13 novembre 2026 ore 20.30</p><p>15 novembre 2026 ore 16.00</p>"
    +"<h2>La traviata</h2><p>musica di Giuseppe Verdi</p>"
    +"<p>21 gennaio 2027 ore 20.30</p>"
    +"<h2>Concerto di Capodanno</h2><p>1 gennaio 2027 ore 17.00</p>"
)
class RovigoOperaTests(unittest.TestCase):
    def test_approved_origin_only(self):
        self.assertTrue(eligible("rovigo-sociale-opera-2026-27",URL))
        self.assertFalse(eligible("rovigo-sociale-opera-2026-27",URL+"?utm=1"))
        self.assertFalse(eligible("rovigo-sociale-opera-2026-27",
                        URL.replace("www.comune.rovigo.it","fake.example")))
        self.assertEqual(extract("rovigo-sociale-opera-2026-27",URL,ANNOUNCEMENT,1),[URL])

    def test_municipal_season_heading_variants(self):
        for heading in (
            "<h1>Teatro Sociale - Rovigo: Stagione Teatrale 2026/27</h1>",
            "<h1>Teatro Sociale di Rovigo, Stagione Lirica 2026-2027</h1>",
            "<h1>Teatro Sociale Rovigo — Stagione Opera 2026/2027</h1>",
        ):
            with self.subTest(heading=heading):
                html=heading+"<p>Pagliacci di Ruggero Leoncavallo</p>"
                self.assertTrue(identify_season(html,url=URL))
        with self.assertRaises(ValueError):
            identify_season(
                "<h1>Teatro Sociale Rovigo</h1><p>Pagliacci 13 novembre 2026</p>",
                url=URL,
            )

    def test_announcement_is_not_showtime(self):
        self.assertEqual(parse_program(ANNOUNCEMENT,url=URL),[])
        self.assertEqual(parse_program(DATES,url=URL),[
            ("Pagliacci","Ruggero Leoncavallo","Teatro Sociale","2026-11-13","20:30"),
            ("Pagliacci","Ruggero Leoncavallo","Teatro Sociale","2026-11-15","16:00"),
            ("La traviata","Giuseppe Verdi","Teatro Sociale","2027-01-21","20:30"),
        ])

    def test_operetta_is_not_eligible_for_lyric_catalogue(self):
        # Even when a mixed season has an explicitly dated operetta panel,
        # only its verified lyrical opera remains eligible.
        html=(HEADER
              +"<h2>Il pipistrello</h2><p>musica di Johann Strauss II</p>"
              +"<p>18 dicembre 2026 ore 20.30</p>"
              +"<h2>Pagliacci</h2><p>musica di Ruggero Leoncavallo</p>"
              +"<p>13 novembre 2026 ore 20.30</p>")
        self.assertEqual(parse_program(html,url=URL),[
            ("Pagliacci","Ruggero Leoncavallo","Teatro Sociale",
             "2026-11-13","20:30"),
        ])

    def test_operetta_heading_never_leaks_showtime_into_preceding_opera(self):
        html=(HEADER
              +"<h2>Pagliacci</h2><p>musica di Ruggero Leoncavallo</p>"
              +"<h2>Il pipistrello</h2><p>musica di Johann Strauss II</p>"
              +"<p>18 dicembre 2026 ore 20.30</p>"
              +"<h2>La traviata</h2><p>musica di Giuseppe Verdi</p>"
              +"<p>22 gennaio 2027 ore 20.30</p>")
        self.assertEqual(parse_program(html,url=URL),[
            ("La traviata","Giuseppe Verdi","Teatro Sociale","2027-01-22","20:30"),
        ])
        # The original German operetta heading also ends the previous block.
        self.assertEqual(parse_program(html.replace("Il pipistrello","Die Fledermaus"),url=URL),
                         parse_program(html,url=URL))

    def test_menotti_bernstein_double_bill_is_not_two_tickets(self):
        combined=(HEADER
                  +"<h2>Pagliacci</h2><p>musica di Ruggero Leoncavallo</p>"
                  +"<p>13 novembre 2026 ore 20.30</p>"
                  +"<h2>Il telefono / Trouble in Tahiti</h2>"
                  +"<p>musica di Gian Carlo Menotti e Leonard Bernstein</p>"
                  +"<p>11 dicembre 2026 ore 20.30</p>")
        self.assertEqual(parse_program(combined,url=URL),[
            ("Pagliacci","Ruggero Leoncavallo","Teatro Sociale",
             "2026-11-13","20:30"),
        ])
        split=(HEADER
               +"<h2>Il telefono</h2><p>musica di Gian Carlo Menotti</p>"
               +"<p>11 dicembre 2026 ore 20.30</p>"
               +"<h2>Trouble in Tahiti</h2><p>musica di Leonard Bernstein</p>"
               +"<p>11 dicembre 2026 ore 20.30</p>"
               +"<h2>Pagliacci</h2><p>musica di Ruggero Leoncavallo</p>"
               +"<p>13 novembre 2026 ore 20.30</p>")
        self.assertEqual(parse_program(split,url=URL),[
            ("Pagliacci","Ruggero Leoncavallo","Teatro Sociale",
             "2026-11-13","20:30"),
        ])

    def test_ridotto_is_not_mislabelled_as_main_auditorium(self):
        # On the real season the Albinoni intermezzo is at the Ridotto,
        # not the theatre's main auditorium. A shared index must not
        # silently publish that as Teatro Sociale.
        html=(HEADER
              +"<h2>Pimpinone</h2><p>musica di Tomaso Albinoni</p>"
              +"<p>Ridotto del Teatro Sociale di Rovigo</p>"
              +"<p>26 novembre 2026 ore 20.30</p>"
              +"<p>28 novembre 2026 ore 18.00</p>"
              +"<h2>Pagliacci</h2><p>musica di Ruggero Leoncavallo</p>"
              +"<p>13 novembre 2026 ore 20.30</p>")
        self.assertEqual(parse_program(html,url=URL),[
            ("Pagliacci","Ruggero Leoncavallo","Teatro Sociale",
             "2026-11-13","20:30"),
        ])
        # When a hypothetical official panel explicitly establishes the
        # main venue instead, the original extraction remains functional.
        main=html.replace("Ridotto del Teatro Sociale di Rovigo",
                          "Teatro Sociale di Rovigo")
        self.assertEqual(len(parse_program(main,url=URL)),3)

    def test_fail_closed_on_missing_primary_evidence(self):
        for broken in (
            HEADER.replace("2026/2027","2025/2026")+"<p>Pagliacci</p>",
            HEADER.replace("Rovigo","Modena")+"<p>Pagliacci</p>",
            "<h1>Teatro Sociale di Rovigo 2026/27</h1><p>Prosa e musica</p>",
        ):
            with self.assertRaises(ValueError):
                identify_season(broken,url=URL)
        self.assertEqual(parse_program(DATES.replace("musica di Giuseppe Verdi",
                         "direzione di Giuseppe Verdi"),url=URL)[-1][0],"Pagliacci")
        with self.assertRaises(ValueError):
            parse_program(DATES,url=URL.replace("https://","http://"))
if __name__=="__main__":unittest.main()

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

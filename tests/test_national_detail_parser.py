"""Verified official page snippets: exact dates, no rehearsal or inferred year."""
import unittest
from opera_atlas.national_detail_parser import parse_national_showtimes

FENICE_URL="https://www.teatrolafenice.it/event/jenufa/"
PARMA_URL="https://teatroregioparma.it/spettacolo/rigoletto/"
MASSIMO_URL="https://www.teatromassimo.it/event/macbeth/"

class NationalDetailsTests(unittest.TestCase):
    def test_fenice_full_dates_and_clocks(self):
        html="""<h1>Jenůfa</h1><p>Leoš Janáček</p><h2>Teatro La Fenice</h2>
            <p>Seleziona una data:</p>
            <a>venerdì 12 Marzo 2027 19:00 ACQUISTA</a>
            <a>domenica 14 Marzo 2027 15:30 ACQUISTA</a>
            <a>martedì 16 Marzo 2027 19:00 ACQUISTA</a>
            <h2>I prossimi eventi</h2><a>domenica 21 Marzo 2027 18:00</a>"""
        found=parse_national_showtimes(html,source_key="fenice-opera-2026-27",
                url=FENICE_URL,title="Jenůfa",composer="Leoš Janáček")
        self.assertEqual(found,[("2027-03-12","19:00"),("2027-03-14","15:30"),
                                ("2027-03-16","19:00")])

    def test_parma_detailed_cards_exclude_rehearsals(self):
        html="""<h1>Rigoletto</h1><p>Giuseppe Verdi</p>
        <ul><li>14 feb 2027</li><li>17 feb 2027</li><li>19 feb 2027</li>
        <li>21 feb 2027</li><li>23 feb 2027</li><li>25 feb 2027</li></ul>
        <h2>Spettacolo</h2><p>Musica Giuseppe Verdi</p>
        <h2>Teatro Regio di Parma</h2>
        <article><p>dom 14 feb</p><p>20:00</p><p>Prova Under30</p></article>
        <article><p>mer 17 feb</p><p>15:30</p><p>Prova Aperta</p></article>
        <article><p>ven 19 feb</p><p>20:00</p><p>TURNO A</p></article>
        <article><p>dom 21 feb</p><p>15:30</p><p>TURNO D</p></article>
        <article><p>mar 23 feb</p><p>20:00</p><p>TURNO B</p></article>
        <article><p>gio 25 feb</p><p>20:00</p><p>TURNO C</p></article>
        <p>Tickets for the open rehearsal will be available</p>
        """
        actual=parse_national_showtimes(html,source_key="parma-opera-2027",
                  url=PARMA_URL,title="Rigoletto",composer="Giuseppe Verdi")
        self.assertEqual(actual,[("2027-02-19","20:00"),("2027-02-21","15:30"),
                                 ("2027-02-23","20:00"),("2027-02-25","20:00")])

    def test_live_parma_layout_has_cast_navigation_before_ticket_cards(self):
        # Mirrors the official Rigoletto detail page: "Cast" occurs in
        # a navigation bar well before any day/time cards.
        html="""<nav>Spettacoli | Stagione 27 | Opera</nav>
        <h1>Rigoletto</h1><p>Giuseppe Verdi</p>
        <ul><li>14 feb 2027</li><li>17 feb 2027</li><li>19 feb 2027</li>
        <li>21 feb 2027</li><li>23 feb 2027</li><li>25 feb 2027</li></ul>
        <nav><a>Spettacolo</a><a>Cast</a><a>Informazioni</a></nav>
        <h2>Spettacolo</h2><p>Musica&nbsp;Giuseppe Verdi</p>
        <p>Melodramma in tre atti</p><p>Teatro Regio di Parma</p>
        <section><p>dom 14 feb</p><p>20:00</p><p>Prova Under30</p>
        <p>mer 17 feb</p><p>15:30</p><p>Prova Aperta</p>
        <p>ven 19 feb</p><p>20:00</p><p>TURNO A</p>
        <p>dom 21 feb</p><p>15:30</p><p>TURNO D</p>
        <p>mar 23 feb</p><p>20:00</p><p>TURNO B</p>
        <p>gio 25 feb</p><p>20:00</p><p>TURNO C</p></section>
        <p>Tickets for the open rehearsal will be available later</p>
        <h2>Cast</h2><p>Rigoletto</p>"""
        actual=parse_national_showtimes(html,source_key="parma-opera-2027",
                  url=PARMA_URL,title="Rigoletto",composer="Giuseppe Verdi")
        self.assertEqual(actual,[("2027-02-19","20:00"),("2027-02-21","15:30"),
                                 ("2027-02-23","20:00"),("2027-02-25","20:00")])

    def test_palermo_date_summary_proves_year(self):
        html="""<section>Date <p>5 Febbraio</p><p>19:00</p><p>Turno Prime</p>
        <p>7 Febbraio</p><p>17:30</p><p>Turno D</p>
        <p>9 Febbraio</p><p>19:00</p><p>Turno B</p></section>
        <h2>Lo spettacolo</h2>
        <p>5, 7, 9 febbraio 2027 | Sala Grande</p>
        <h1>Macbeth</h1><p>Musiche di Giuseppe Verdi</p>
        <h2>Date</h2><p>5 Febbraio 19:00</p>"""
        actual=parse_national_showtimes(html,source_key="massimo-season-2026-27",
                url=MASSIMO_URL,title="Macbeth",composer="Giuseppe Verdi")
        self.assertEqual(actual,[("2027-02-05","19:00"),("2027-02-07","17:30"),
                                 ("2027-02-09","19:00")])

    def test_fail_closed_on_missing_year_or_composer(self):
        with self.assertRaises(ValueError):
            parse_national_showtimes("<h1>Jenůfa</h1><p>12 Marzo 2027 19:00</p>",
                    source_key="fenice-opera-2026-27",url=FENICE_URL,
                    title="Jenůfa",composer="Leoš Janáček")
        with self.assertRaises(ValueError):
            parse_national_showtimes("<h1>Macbeth</h1><p>5 Febbraio 19:00</p>",
                    source_key="massimo-season-2026-27",url=MASSIMO_URL,
                    title="Macbeth",composer="Giuseppe Verdi")
        with self.assertRaises(ValueError):
            parse_national_showtimes("Jenůfa Leoš Janáček Seleziona una data venerdì 12 Marzo 2027 19:00",
                    source_key="fenice-opera-2026-27",
                    url="https://other.example/event/jenufa/",
                    title="Jenůfa",composer="Leoš Janáček")
if __name__=="__main__":
    unittest.main()

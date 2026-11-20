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

    def test_palermo_carmen_hidden_early_navigation_does_not_truncate_dates(self):
        # The site can place a "Lo spettacolo" navigation link before the
        # actual ticket cards. Use the *verified summary* as the delimiter.
        html="""<nav><a>Date</a><a>Lo spettacolo</a><a>Cast</a></nav>
        <h2>Date</h2>
        <p>24 Novembre</p><p>19:00</p><p>Turno Prime</p>
        <p>25 Novembre</p><p>19:00</p><p>Fuori abbonamento</p>
        <p>26 Novembre</p><p>19:00</p><p>Turno B</p>
        <p>27 Novembre</p><p>20:00</p><p>Turno F</p>
        <p>28 Novembre</p><p>17:30</p><p>Turno D</p>
        <p>30 Novembre</p><p>19:00</p><p>Fuori abbonamento</p>
        <p>1 Dicembre</p><p>19:00</p><p>Turno C</p>
        <p>2 Dicembre</p><p>18:30</p><p>Turno Scuola</p>
        <h2>Lo spettacolo</h2>
        <p>24, 25, 26, 27, 28, 30 novembre, 1, 2 dicembre 2027 | Sala Grande</p>
        <h1>Carmen</h1><p>Musiche di Georges Bizet</p>"""
        actual=parse_national_showtimes(
            html,source_key="massimo-season-2026-27",
            url="https://www.teatromassimo.it/event/carmen-3/",
            title="Carmen",composer="Georges Bizet")
        self.assertEqual(actual,[
            ("2027-11-24","19:00"),("2027-11-25","19:00"),
            ("2027-11-26","19:00"),("2027-11-27","20:00"),
            ("2027-11-28","17:30"),("2027-11-30","19:00"),
            ("2027-12-01","19:00"),("2027-12-02","18:30")])

    def test_palermo_ernani_across_october_and_november(self):
        html="""<h2>Date</h2>
        <p>31 Ottobre</p><p>20:00</p><p>Turno Prime</p>
        <p>2 Novembre</p><p>18:30</p><p>Turno Opera</p>
        <p>3 Novembre</p><p>19:00</p><p>Turno B</p>
        <p>4 Novembre</p><p>18:30</p><p>Turno Scuola</p>
        <p>5 Novembre</p><p>19:00</p><p>Turno C</p>
        <p>6 Novembre</p><p>19:00</p><p>Turno E</p>
        <p>7 Novembre</p><p>17:30</p><p>Turno D</p>
        <h2>Lo spettacolo</h2>
        <p>31 ottobre, 2, 3, 4, 5, 6, 7 novembre 2027 | Sala Grande</p>
        <h1>Ernani</h1><p>Musiche di Giuseppe Verdi</p>"""
        actual=parse_national_showtimes(
            html,source_key="massimo-season-2026-27",
            url="https://www.teatromassimo.it/event/ernani-2/",
            title="Ernani",composer="Giuseppe Verdi")
        self.assertEqual(actual,[
            ("2027-10-31","20:00"),("2027-11-02","18:30"),
            ("2027-11-03","19:00"),("2027-11-04","18:30"),
            ("2027-11-05","19:00"),("2027-11-06","19:00"),
            ("2027-11-07","17:30")])

    def test_palermo_multimonth_incomplete_cards_fail_closed(self):
        html="""<h2>Date</h2><p>31 Ottobre</p><p>20:00</p>
        <h2>Lo spettacolo</h2>
        <p>31 ottobre, 2 novembre 2027 | Sala Grande</p>
        <h1>Ernani</h1><p>Musiche di Giuseppe Verdi</p>"""
        with self.assertRaises(ValueError):
            parse_national_showtimes(html,
                source_key="massimo-season-2026-27",
                url="https://www.teatromassimo.it/event/ernani-2/",
                title="Ernani",composer="Giuseppe Verdi")

    def test_fenice_explicit_cancellation_not_published_as_active(self):
        html="""<h1>Fedora</h1><p>Umberto Giordano</p>
        <p>La prima recita di Fedora prevista venerdì 13 novembre 2026
        al Teatro La Fenice non avrà luogo; le altre recite si svolgeranno regolarmente.</p>
        <h2>Seleziona una data:</h2>
        <a>venerdì 13 novembre 2026 19:00 ACQUISTA</a>
        <a>sabato 14 novembre 2026 19:00 ACQUISTA</a>
        <a>domenica 15 novembre 2026 15:30 ACQUISTA</a>
        <h2>I prossimi eventi</h2>"""
        actual=parse_national_showtimes(
            html,source_key="fenice-opera-2026-27",
            url="https://www.teatrolafenice.it/event/fedora/",
            title="Fedora",composer="Umberto Giordano")
        self.assertEqual(actual,[("2026-11-14","19:00"),
                                 ("2026-11-15","15:30")])

    def test_fenice_ambiguous_cancellation_blocks_page(self):
        html="""<h1>Fedora</h1><p>Umberto Giordano</p>
        <p>Una recita è stata annullata.</p>
        <h2>Seleziona una data:</h2>
        <a>sabato 14 novembre 2026 19:00 ACQUISTA</a>
        <h2>I prossimi eventi</h2>"""
        with self.assertRaises(ValueError):
            parse_national_showtimes(
                html,source_key="fenice-opera-2026-27",
                url="https://www.teatrolafenice.it/event/fedora/",
                title="Fedora",composer="Umberto Giordano")

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

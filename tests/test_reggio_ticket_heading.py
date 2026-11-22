"""Reggio Opera: nested official ticket headings and strict bounded performance dates."""
import unittest
from opera_atlas.reggio_opera_parser import parse_detail

URL="https://www.iteatri.re.it/spettacolo/simon-boccanegra-2/"
PREAMBLE="""<h1>Simon Boccanegra</h1>
<p>Musica di Giuseppe Verdi</p><nav>Cast Descrizione Extra Acquista</nav>
<p>Teatro Municipale Valli</p><span>Opera</span>
<p>Una delle partiture più dense di Verdi.</p>"""
ROWS="""<div>19/03/2027 | 20:00 | da € 35,00 | <a href='/biglietti'>Acquista</a></div>
<div>21/03/2027 | 15:30 | da € 35,00 | <a href='/biglietti'>Acquista</a></div>"""
TAIL="""<h3><span>Riduzioni</span></h3><h3>Opera -</h3>
<p>10/05/2027 | 20:00 | da € 45,00 | Acquista</p>"""


class ReggioTicketHeadingTests(unittest.TestCase):
    def test_nested_ticket_headings_preserve_exact_year_clock_and_work(self):
        html=PREAMBLE+"<h2><span>Biglietti</span></h2>"+ROWS+TAIL
        title,composer,venue,performances=parse_detail(html,url=URL)
        self.assertEqual((title,composer,venue),(
            "Simon Boccanegra","Giuseppe Verdi","Teatro Valli"))
        self.assertEqual(performances,[
            ("2027-03-19","20:00"),("2027-03-21","15:30")])

    def test_unrelated_footer_dates_cannot_create_performances(self):
        html=PREAMBLE+"<h2>Biglietti</h2>"+ROWS+TAIL
        self.assertEqual(len(parse_detail(html,url=URL)[3]),2)

    def test_missing_ticket_section_or_unverified_clocks_is_blocked(self):
        with self.assertRaisesRegex(ValueError,"bounded ticket calendar"):
            parse_detail(PREAMBLE+ROWS+TAIL,url=URL)
        with self.assertRaisesRegex(ValueError,"incomplete Valli ticket dates"):
            parse_detail(PREAMBLE+"<h2>Biglietti</h2>"+
                "<div>19/03/2027 | orario da definire | da € 35,00 |</div>"+TAIL,url=URL)


if __name__=="__main__":
    unittest.main()

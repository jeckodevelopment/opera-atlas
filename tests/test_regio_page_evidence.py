"""Small, independently authored fixture reflecting observed official 2026/27 layout.

Not a copy of page contents or a claim that any live fetch was performed.
"""
import unittest
from opera_atlas.regio_parser import parse_regio_detail

URL = "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata"

class RegioEvidenceTests(unittest.TestCase):
    def test_season_2027_multiple_recite_including_afternoon(self):
        html = """<h1>La traviata | Giuseppe Verdi</h1>
        <section><h2>Calendario rappresentazioni</h2>
        <article>Venerdì 26 Febbraio <time>2027-02-26 20:00:00 Europe/Rome</time></article>
        <article>Domenica 28 Febbraio <time>2027-02-28 15:00:00 Europe/Rome</time></article>
        <article>Mercoledì 10 Marzo <time>2027-03-10 15:00:00 Europe/Rome</time></article>
        </section>"""
        results = parse_regio_detail(html,source_url=URL,
                                     expected_title="La traviata",
                                     expected_composer="Giuseppe Verdi")
        self.assertEqual(len(results),3)
        self.assertEqual(results[1].starts_at.hour,15)

    def test_date_interval_not_a_recita(self):
        html="<h1>La traviata | Giuseppe Verdi</h1><p>27 Febbraio-13 Marzo 2027</p>"
        self.assertEqual(parse_regio_detail(html,source_url=URL,
                                             expected_title="La traviata",
                                             expected_composer="Giuseppe Verdi"),[])

if __name__ == "__main__":
    unittest.main()

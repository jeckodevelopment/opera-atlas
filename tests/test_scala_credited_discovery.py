"""Source-credited Scala discovery: four unknown repertory works must not vanish."""
import unittest

from opera_atlas.scala_credited_detail import (
    extract_scala_official_credit,parse_scala_credited_opera)
from scripts.collect_candidate_details import parse_source_credited_opera_detail

URL="https://www.teatroallascala.org/it/stagione/2026-2027/opera/les-pecheurs-de-perles.html"
HTML="""<html><body>
<h2>LES PÊCHEURS DE PERLES</h2>
<div>Date</div>
<div>ven 22 gennaio 2027</div><p>Ore 20:00</p>
<div>dom 24 gennaio 2027</div><p>Ore 14:30</p>
<div>mer 27 gennaio 2027</div><p>Ore 20:00</p>
<div>sab 30 gennaio 2027</div><p>Ore 20:00</p>
<div>dom 7 febbraio 2027</div><p>Ore 20:00</p>
<div>Opera</div><h1>Les Pêcheurs de perles</h1>
<p>Georges Bizet</p><p>Dal 22 gennaio al 7 febbraio 2027</p>
<h2>Cast</h2><p>Direttore Henrik Nánási</p>
</body></html>"""

class OfficialScalaCredits(unittest.TestCase):
    def test_first_party_title_composer_and_five_recite(self):
        title,composer,dates=parse_scala_credited_opera(HTML,url=URL)
        self.assertEqual((title,composer),("Les Pêcheurs de perles","Georges Bizet"))
        self.assertEqual(dates,[("2027-01-22","20:00"),("2027-01-24","14:30"),
                               ("2027-01-27","20:00"),("2027-01-30","20:00"),
                               ("2027-02-07","20:00")])
        rows=parse_source_credited_opera_detail("scala-season-2026-27",URL,HTML)
        self.assertEqual(len(rows),5)
        self.assertEqual({row["composer"] for row in rows},{"Georges Bizet"})
        self.assertEqual({row["venue"] for row in rows},{"Teatro alla Scala"})
        self.assertEqual(rows[0]["starts_at"],"2027-01-22T20:00:00+01:00")

    def test_not_guessing_composer_from_url_or_cast(self):
        with self.assertRaises(ValueError):
            extract_scala_official_credit(
                HTML.replace("<p>Georges Bizet</p>",""),url=URL)
        with self.assertRaises(ValueError):
            extract_scala_official_credit(
                HTML.replace("<h1>Les Pêcheurs de perles</h1>","<h1></h1>"),url=URL)
        # Composer in the cast or article body is insufficient: it must appear
        # adjacent to the official opera title before the dated summary.
        with self.assertRaises(ValueError):
            extract_scala_official_credit(
                HTML.replace("<p>Georges Bizet</p>","<p>Autore ignoto</p>")
                    .replace("</body>","<p>Georges Bizet</p></body>"),url=URL)

    def test_unsafe_url_and_incomplete_showtime(self):
        for url in (URL.replace("www.teatroallascala.org","example.com"),URL+"?bogus=1",
                    URL.replace("https://","http://")):
            with self.subTest(url=url),self.assertRaises(ValueError):
                parse_scala_credited_opera(HTML,url=url)
        with self.assertRaises(ValueError):
            parse_scala_credited_opera(HTML.replace("Ore 20:00","alle ore non definite")
                                      .replace("Ore 14:30","alle ore non definite"),url=URL)

    def test_dido_and_aeneas_unicode_credit(self):
        html=HTML.replace("Les Pêcheurs de perles","Dido and Æneas").replace(
            "Georges Bizet","Henry Purcell")
        title,composer=extract_scala_official_credit(html,url=URL)
        self.assertEqual((title,composer),("Dido and Æneas","Henry Purcell"))

if __name__=="__main__":
    unittest.main()

"""Five real Teatro di Pisa first-party opera calendars and source validation."""
import unittest
from opera_atlas.pisa_opera_parser import WORKS,parse_detail

ROOT="https://teatrodipisa.it/spettacolo/"
CASES={
 "dido-and-aeneas":[("2026-10-23","20:30"),("2026-10-25","15:30")],
 "loccasione-fa-il-ladro-ossia-il-cambio-della-valigia":[("2026-12-04","20:30"),("2026-12-06","15:30")],
 "otello":[("2027-02-05","20:30"),("2027-02-07","15:30")],
 "aida":[("2027-03-12","20:30"),("2027-03-14","15:30")],
 "la-clemenza-di-tito":[("2027-04-16","20:30"),("2027-04-18","15:30")]
}
MONTHS={10:"Ottobre",12:"Dicembre",2:"Febbraio",3:"Marzo",4:"Aprile"}
def fixture(slug,performances,*,footer=True,composer=None):
    title,musician,_=WORKS[slug]
    artist=composer if composer is not None else musician
    rows="".join(f"<h4>{int(day[-2:])} {MONTHS[int(day[5:7])]} {day[:4]} {clock}</h4>"
                 for day,clock in performances)
    institution="<footer>Fondazione Teatro di Pisa</footer>" if footer else ""
    # Official page shows title/composer at its top and two dated H4 tickets
    # in a source-scoped Date section, not the full theater name beside dates.
    return (f"<h1>{title}</h1><p>Musica di {artist}</p>"
            +"<p>Prima rappresentazione nel 1812</p>"
            +f"<h3>Date:</h3>{rows}<h3>Allegati:</h3>"
            +institution)

class PisaBatchCalendarTests(unittest.TestCase):
    def test_five_official_first_party_calendars_have_ten_exact_showtimes(self):
        for slug,dates in CASES.items():
            with self.subTest(slug=slug):
                title,composer,_=WORKS[slug]
                self.assertEqual(parse_detail(fixture(slug,dates),url=ROOT+slug+"/"),
                    (title,composer,"Teatro Verdi",dates))

    def test_official_attribution_and_composer_remain_mandatory(self):
        slug="otello"
        with self.assertRaisesRegex(ValueError,"opera house"):
            parse_detail(fixture(slug,CASES[slug],footer=False),url=ROOT+slug+"/")
        with self.assertRaisesRegex(ValueError,"composer"):
            parse_detail(fixture(slug,CASES[slug],composer="Gioachino Rossini"),
                         url=ROOT+slug+"/")
        with self.assertRaisesRegex(ValueError,"unapproved"):
            parse_detail(fixture(slug,CASES[slug]),
                         url="https://unrelated.example/spettacolo/otello/")

    def test_missing_clock_or_wrong_year_cannot_create_recita(self):
        slug="la-clemenza-di-tito"
        complete=fixture(slug,CASES[slug])
        with self.assertRaisesRegex(ValueError,"missing or duplicate"):
            parse_detail(complete.replace("18 Aprile 2027 15:30",
                                         "18 Aprile 2027 ora da definire"),
                         url=ROOT+slug+"/")
        with self.assertRaisesRegex(ValueError,"season year mismatch"):
            parse_detail(complete.replace("16 Aprile 2027","16 Aprile 2026"),
                         url=ROOT+slug+"/")

if __name__=="__main__":
    unittest.main()

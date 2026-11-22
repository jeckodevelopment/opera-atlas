"""Carlo Felice 2026/27: six official Figaro ticket dates, without invented hours."""
import unittest
from opera_atlas.italian_detail_parser import parse_detail

URL="https://www.carlofelice.it/spettacolo/le-nozze-di-figaro/"
ROWS=[
("16/10/2026","19:30"),("17/10/2026","15:00"),
("18/10/2026","15:00"),("23/10/2026","19:30"),
("24/10/2026","19:30"),("25/10/2026","15:00")]
def fixture(*,missing=False):
    tickets=" ".join(
       f"<div>{'VE' if i==0 else 'DO'} {day} (Prima)Turno A | Ore {clock} | Biglietti non più disponibili</div>"
       for i,(day,clock) in enumerate(ROWS)
       if not (missing and i==2))
    if missing:
        tickets+="<div>18/10/2026 Turno C | Orario da definire</div>"
    return ("<div>"+tickets+"</div>"
      "<div>Dove: Teatro Carlo Felice Durata: 220 minuti</div>"
      "<h1>Le nozze di figaro</h1>"
      "<p>Musica di Wolfgang Amadeus Mozart</p>"
      "<p>Direttore Jordi Bernàcer</p>"
      "<div>Spettacoli consigliati 22/11/2026 ore 15:00</div>")

class CarloFeliceTicketTests(unittest.TestCase):
    def test_six_verified_dates(self):
        venue,rows=parse_detail(fixture(),source_key="carlo-felice-season-2026-27",
             url=URL,title="Le nozze di figaro",composer="Wolfgang Amadeus Mozart")
        self.assertEqual(venue,"Teatro Carlo Felice")
        self.assertEqual(rows,[("2026-"+x[3:5]+"-"+x[:2],t) for x,t in ROWS])

    def test_missing_clock_never_assumes_a_time(self):
        with self.assertRaisesRegex(ValueError,"incomplete"):
            parse_detail(fixture(missing=True),
              source_key="carlo-felice-season-2026-27",
              url=URL,title="Le nozze di figaro",
              composer="Wolfgang Amadeus Mozart")

    def test_no_unrelated_recommended_date(self):
        _,rows=parse_detail(fixture(),
              source_key="carlo-felice-season-2026-27",
              url=URL,title="Le nozze di figaro",
              composer="Wolfgang Amadeus Mozart")
        self.assertNotIn(("2026-11-22","15:00"),rows)

if __name__=="__main__":
    unittest.main()

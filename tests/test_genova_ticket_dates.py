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

    def test_real_cms_inline_ticket_fields_preserve_six_recite(self):
        from opera_atlas.italian_detail_parser import extract_source_credited_carlo_felice
        tickets="".join(
            f"<div><span>{'VE' if i%3==0 else 'SA'} {day}</span>"
            f"<small>{'(Prima)' if i==0 else ''}</small>"
            f"<b>Turno {'A' if i==0 else 'FA'}</b>"
            f"<span>|</span><strong>Ore {clock}</strong>"
            "<span>| Biglietti non più disponibili</span></div>"
            for i,(day,clock) in enumerate(ROWS))
        html=(tickets+"<div>Dove:</div><div>Teatro Carlo Felice</div>"
              "<h1>Le nozze di figaro</h1>"
              "<p>Musica di</p><p>Wolfgang Amadeus Mozart</p>"
              "<p>Direttore</p><p>Jordi Bernàcer</p>")
        venue,rows=parse_detail(html,
            source_key="carlo-felice-season-2026-27",
            url=URL,title="Le nozze di figaro",
            composer="Wolfgang Amadeus Mozart")
        self.assertEqual(venue,"Teatro Carlo Felice")
        self.assertEqual(rows,[("2026-"+x[3:5]+"-"+x[:2],t)
                               for x,t in ROWS])
        self.assertEqual(len(extract_source_credited_carlo_felice(
            html,url=URL)[-1]),6)
        missing=html.replace("<strong>Ore 15:00</strong>",
                             "<strong>Orario da definire</strong>",1)
        with self.assertRaisesRegex(ValueError,"incomplete"):
            parse_detail(missing,
                source_key="carlo-felice-season-2026-27",
                url=URL,title="Le nozze di figaro",
                composer="Wolfgang Amadeus Mozart")
        # A date in the programme description is not a seventh showtime.
        html+=("<p>Altra produzione 22/11/2026 Ore 16:00</p>")
        self.assertEqual(len(parse_detail(html,
            source_key="carlo-felice-season-2026-27",
            url=URL,title="Le nozze di figaro",
            composer="Wolfgang Amadeus Mozart")[-1]),6)

    def test_ticket_cards_with_extra_accessibility_labels(self):
        # Each verified date owns its own clock, even when the source CMS
        # inserts labels between the subscription turn and the time.
        html=fixture().replace(" | Ore "," | Accessibilità e informazioni | Ore ")
        venue,rows=parse_detail(
            html,source_key="carlo-felice-season-2026-27",
            url=URL,title="Le nozze di figaro",
            composer="Wolfgang Amadeus Mozart")
        self.assertEqual(venue,"Teatro Carlo Felice")
        self.assertEqual(rows,[("2026-"+x[3:5]+"-"+x[:2],t) for x,t in ROWS])
        # A date without an adjacent clock must not silently borrow the
        # following row's time.
        broken=html.replace("Ore 15:00","Orario da definire",1)
        with self.assertRaisesRegex(ValueError,"incomplete"):
            parse_detail(
                broken,source_key="carlo-felice-season-2026-27",
                url=URL,title="Le nozze di figaro",
                composer="Wolfgang Amadeus Mozart")

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

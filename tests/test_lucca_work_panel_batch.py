"""Lucca Opera: official card dates must be work-scoped, not MENU-scoped."""
import unittest
from opera_atlas.lucca_opera_parser import parse_detail
ROOT="https://www.teatrodelgigliogiacomopuccini.it/it/cartellone/lirica/stagione-2026-2027/"
CASES=[
("otello","Otello","Giuseppe Verdi","Dramma lirico",[
 ("2027-02-12","20:30"),("2027-02-14","16:00")]),
("aida","Aida","Giuseppe Verdi","Opera in quattro atti",[
 ("2027-03-21","16:00")]),
("il-barbiere-di-siviglia","Il barbiere di Siviglia","Gioachino Rossini","Commedia in due atti",[
 ("2027-01-22","20:30"),("2027-01-24","16:00")])]
MONTHS={"01":"gennaio","02":"febbraio","03":"marzo"}

def fixture(title,composer,genre,shows,*,menu="MENU <span>Site navigation</span>"):
    months=MONTHS
    listings="".join(
       f"<div>Il {int(day[-2:])} {months[day[5:7]]} {day[:4]} Ore {clock}</div>"
       for day,clock in shows)
    return ("<div>Prossimi spettacoli Il 8 novembre 2026 Ore 21:00</div>"
            +menu+"<div>TEATRO DEL GIGLIO</div>"
            +f"<section>{title} Teatro del Giglio Lirica {listings}</section>"
            +f"<h1>{title}</h1><div>{genre}</div>"
            +f"<p>Musica di {composer}</p>"
            +"<div>Segui tutte le novità</div><div>Il 3 giugno 2027 Ore 18:00</div>")

class LuccaWorkPanelTests(unittest.TestCase):
    def test_all_three_lucca_classical_operas_have_exact_official_hours(self):
        for slug,title,composer,genre,dates in CASES:
            with self.subTest(slug=slug):
                row=parse_detail(fixture(title,composer,genre,dates),url=ROOT+slug+"/")
                self.assertEqual(row,(title,composer,"Teatro del Giglio Giacomo Puccini",dates))

    def test_never_pulls_upcoming_other_shows_from_site_header(self):
        slug,title,composer,genre,dates=CASES[0]
        html=fixture(title,composer,genre,dates)
        self.assertEqual(parse_detail(html,url=ROOT+slug+"/")[3],dates)

    def test_other_work_heading_or_missing_individual_clock_fails_closed(self):
        slug,title,composer,genre,dates=CASES[0]
        with self.assertRaisesRegex(ValueError,"work-specific"):
            parse_detail(fixture(title,composer,genre,dates).replace(
                "TEATRO DEL GIGLIO</div><section>Otello",
                "TEATRO DEL GIGLIO</div><section>Macbeth"),url=ROOT+slug+"/")
        html=fixture(title,composer,genre,dates).replace("Ore 20:30","orario da definire")
        with self.assertRaisesRegex(ValueError,"incomplete"):
            parse_detail(html,url=ROOT+slug+"/")


if __name__=="__main__":
    unittest.main()

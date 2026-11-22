"""Official Novara opera season 2027: bounded recite, identities and exclusions."""
import unittest

from opera_atlas.novara_coccia_parser import parse_detail
from scripts.discover_season_indexes import eligible, extract

HOST="https://www.fondazioneteatrococcia.it"
INDEX=HOST+"/spettacoli.html"
RIGOLETTO=HOST+"/stagione-27-rigoletto.html"
BARBIERE=HOST+"/stagione-27-il-barbiere-di-siviglia.html"
NOZZE=HOST+"/stagione-27-le-nozze-di-figaro.html"
DATES=(
    ("Venerdì 29 gennaio 2027", "20:00"),
    ("Sabato 30 gennaio 2027", "20:00"),
    ("Domenica 31 gennaio 2027", "16:00"),
    ("Martedì 2 febbraio 2027", "20:00"),
)

def page(title="Rigoletto",composer="Giuseppe Verdi",dates=DATES):
    dates_html="".join(
        f"<h4>{day}</h4><p>ore {clock} (Turno A)</p>" for day,clock in dates)
    return (
        f"<h1>{title}</h1><p>Melodramma in tre atti</p>"
        f"<p>Musica di {composer}</p>"
        "<p>Prima rappresentazione 11 marzo 1851</p>"
        "<p>Il duca 29, 31 gennaio, 2 febbraio</p>"
        "<h3>informazioni sull'evento</h3>"
        +dates_html+
        "<h3>TEATRO COCCIA</h3><a>Compra il biglietto</a>"
        "<footer>opera nel 2028 ore 20:00</footer>")

class NovaraOperaTests(unittest.TestCase):
    def test_allowlisted_opera_pages_only(self):
        self.assertTrue(eligible("coccia-novara-opera-2027",RIGOLETTO))
        for denied in (HOST+"/stagione-27-il-lago-dei-cigni.html",
                       HOST+"/stagione-27-rigoletto.html?ticket=1",
                       HOST+"/stagione-26-rigoletto.html",
                       HOST+"/stagione-27-opera-gala.html"):
            self.assertFalse(eligible("coccia-novara-opera-2027",denied))
        html="".join(f'<a href="{u}">{u}</a>' for u in (RIGOLETTO,BARBIERE,NOZZE))
        html+='<a href="/stagione-27-il-lago-dei-cigni.html">Balletto</a>'
        self.assertEqual(len(extract("coccia-novara-opera-2027",INDEX,html,3)),3)

    def test_specific_dates_without_cast_or_history(self):
        title,composer,venue,rows=parse_detail(page(),url=RIGOLETTO)
        self.assertEqual((title,composer,venue),("Rigoletto","Giuseppe Verdi","Teatro Coccia"))
        self.assertEqual(rows,[("2027-01-29","20:00"),("2027-01-30","20:00"),
                               ("2027-01-31","16:00"),("2027-02-02","20:00")])
        for bad in (page(dates=DATES[:3]),page(composer="Giovanni Paisiello"),
                    page(dates=(("Lunedì 29 gennaio 2027","20:00"),)+DATES[1:])):
            with self.assertRaises(ValueError):
                parse_detail(bad,url=RIGOLETTO)
        with self.assertRaises(ValueError):
            parse_detail(page(),url="https://example.org/stagione-27-rigoletto.html")

    def test_three_mozart_performances(self):
        dates=(("Venerdì 8 ottobre 2027","20:00"),("Sabato 9 ottobre 2027","20:00"),
               ("Domenica 10 ottobre 2027","16:00"))
        self.assertEqual(parse_detail(page("Le nozze di Figaro","Wolfgang Amadeus Mozart",dates),
                                      url=NOZZE)[-1],
                         [("2027-10-08","20:00"),("2027-10-09","20:00"),
                          ("2027-10-10","16:00")])

if __name__=="__main__":
    unittest.main()

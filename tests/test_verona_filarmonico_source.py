"""Official 2027 Filarmonico opera pages: date attribution and genre guard."""
import unittest
from opera_atlas.verona_filarmonico_parser import parse_detail
from scripts.discover_season_indexes import eligible,extract

ROOT="https://www.arena.it"
BASE=ROOT+"/teatro-filarmonico-verona/2027/"
INDEX=ROOT+"/teatro-filarmonico-verona/spettacoli-prossima-stagione/"
ROWS=("domenica 17 gennaio 2027 ore 15:30",
      "mercoledì 20 gennaio 2027 ore 19:00",
      "venerdì 22 gennaio 2027 ore 20:00",
      "domenica 24 gennaio 2027 ore 15:30")
def html(rows=ROWS, composer="Wolfgang Amadeus Mozart", kind="Opera", venue="Teatro Filarmonico"):
    return ("<h1>Il Ratto dal Serraglio</h1>"
        "<p>Location</p><p>"+venue+"</p><p>Tipo di spettacolo</p>"
        "<p>"+kind+"</p><p>Musica</p><p>"+composer+"</p>"
        "<p>Durata 2h</p><h2>Prossimi spettacoli</h2>"
        + "".join("<h4>"+r+"</h4><p>Mostra il cast</p>" for r in rows)
        +"<h2>Cast</h2><p>Regia Giorgio Strehler</p>"
        "<p>Opera nel footer: domenica 23 maggio 2027 ore 21:00</p>")

class VeronaFilarmonicoTests(unittest.TestCase):
    def test_only_five_verified_opera_links(self):
        slugs=("il-ratto-dal-serraglio","alzira","fidelio",
               "il-signor-bruschino","cristoforo-colombo")
        index="".join(f'<a href="/teatro-filarmonico-verona/2027/{slug}/">{slug}</a>'
                      for slug in slugs)
        index+='<a href="/teatro-filarmonico-verona/2027/il-lago-dei-cigni/">Balletto</a>'
        index+='<a href="/arena-opera-festival/carmen/">Arena</a>'
        self.assertEqual(len(extract("filarmonico-verona-opera-2027",INDEX,index,5)),5)
        self.assertFalse(eligible("filarmonico-verona-opera-2027",BASE+"il-lago-dei-cigni/"))
        self.assertFalse(eligible("filarmonico-verona-opera-2027",BASE+"alzira/?ref=outside"))
        self.assertFalse(eligible("filarmonico-verona-opera-2027",ROOT+"/arena-opera-festival/carmen/"))
    def test_four_tickets_not_cast_or_footer(self):
        work,composer,venue,rows=parse_detail(html(),url=BASE+"il-ratto-dal-serraglio/")
        self.assertEqual((work,composer,venue),("Il ratto dal serraglio","Wolfgang Amadeus Mozart","Teatro Filarmonico"))
        self.assertEqual(rows,[("2027-01-17","15:30"),("2027-01-20","19:00"),
                               ("2027-01-22","20:00"),("2027-01-24","15:30")])
        for source in (html(rows=ROWS[:3]),html(composer="Antonio Salieri"),
                       html(kind="Balletto"),html(venue="Arena di Verona"),
                       html(rows=("lunedì 17 gennaio 2027 ore 15:30",)+ROWS[1:])):
            with self.assertRaises(ValueError):
                parse_detail(source,url=BASE+"il-ratto-dal-serraglio/")
        with self.assertRaises(ValueError):
            parse_detail(html(),url="https://evil.example/teatro-filarmonico-verona/2027/il-ratto-dal-serraglio/")
if __name__=="__main__":
    unittest.main()

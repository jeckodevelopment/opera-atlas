"""Official performing-orchestra 2027 Ravenna recite evidence."""
import unittest
from opera_atlas.ravenna_cherubini_parser import parse_detail
from scripts.discover_season_indexes import eligible,extract

BASE="https://www.orchestracherubini.it"
INDEX=BASE+"/eventi/tpl/list/"
PAGLIACCI=BASE+"/eventi/pagliacci-2/"
CENERENTOLA=BASE+"/eventi/la-cenerentola-4/"

def page(title="Pagliacci",composer="Ruggero Leoncavallo",rows=(
        "venerdì 15 gennaio 2027 alle 20:00",
        "domenica 17 gennaio 2027 alle 15:30"),
        venue="Teatro Alighieri, Ravenna",kind="Opera"):
    return (f"<h1>{title}</h1><p>libretto e musica di {composer}</p>"
            "<p>prima rappresentazione 21 maggio 1892 ore 19:00</p>"
            "<p>Orchestra Giovanile Luigi Cherubini</p><h3>Date</h3>"
            + "".join(f"<p>{x}</p>" for x in rows)
            + f"<h3>Dettagli</h3><p>{kind}</p><h3>Luogo</h3>"
            + f"<p>{venue}</p><footer>Opera 2027 ore 21:00</footer>")

class RavennaCherubiniTests(unittest.TestCase):
    def test_exact_verified_production_links(self):
        html=(f'<a href="{PAGLIACCI}">Pagliacci</a>'
              f'<a href="{CENERENTOLA}">La Cenerentola</a>'
              '<a href="/eventi/macbeth/">Modena only</a>'
              '<a href="/eventi/concerto/">Concerto</a>')
        self.assertEqual(len(extract("ravenna-alighieri-cherubini-2027",INDEX,html,2)),2)
        self.assertTrue(eligible("ravenna-alighieri-cherubini-2027",PAGLIACCI))
        for bad in (BASE+"/eventi/macbeth/",BASE+"/eventi/pagliacci-2/?utm=1",
                    BASE+"/eventi/il-lago-dei-cigni/",BASE+"/eventi/pagliacci/"):
            self.assertFalse(eligible("ravenna-alighieri-cherubini-2027",bad))

    def test_pagliacci_has_exact_venue_composer_and_hours(self):
        self.assertEqual(parse_detail(page(),url=PAGLIACCI),
            ("Pagliacci","Ruggero Leoncavallo","Teatro Dante Alighieri",
             [("2027-01-15","20:00"),("2027-01-17","15:30")]))
        for invalid in (page(rows=("venerdì 15 gennaio 2027 alle 20:00",)),
                        page(composer="Pietro Mascagni"),
                        page(venue="Teatro Comunale di Ferrara"),
                        page(kind="Balletto"),
                        page(rows=("sabato 15 gennaio 2027 alle 20:00",
                                   "domenica 17 gennaio 2027 alle 15:30"))):
            with self.assertRaises(ValueError):parse_detail(invalid,url=PAGLIACCI)
        with self.assertRaises(ValueError):
            parse_detail(page(),url="https://example.com/eventi/pagliacci-2/")

    def test_cenerentola(self):
        src=page(title="La Cenerentola",composer="Gioachino Rossini",
                 rows=("venerdì 02 aprile 2027 alle 20:00",
                       "domenica 04 aprile 2027 alle 15:30"))
        self.assertEqual(parse_detail(src,url=CENERENTOLA)[-1],
                         [("2027-04-02","20:00"),("2027-04-04","15:30")])

if __name__=="__main__":unittest.main()

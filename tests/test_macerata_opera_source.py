"""Macerata 2027: exact allowlist and verified performance rows."""
import unittest
from opera_atlas.macerata_opera_parser import parse_detail
from scripts.discover_season_indexes import eligible, extract
BASE="https://www.sferisterio.it"
HTML="<h2>Tosca</h2><p>Giacomo Puccini</p><p>Opera lirica in tre atti di Giacomo Puccini su libretto</p><ul>"+"".join(
    "<li>"+x+"</li>" for x in ["Venerdì 16 Luglio H 21:00","Domenica 25 Luglio H 21:00",
                               "Sabato 31 Luglio H 21:00","Venerdì 06 Agosto H 21:00"]
)+"</ul><h4>Cast</h4><p>17, 23 luglio e 1, 7 agosto</p>"
class MacerataOperaTests(unittest.TestCase):
    def test_exact_links_only(self):
        self.assertTrue(eligible("macerata-festival-2027",BASE+"/macerata-opera-festival/tosca"))
        self.assertFalse(eligible("macerata-festival-2027",BASE+"/sferisterio-scuola-27"))
        self.assertFalse(eligible("macerata-festival-2027",BASE+"/macerata-opera-festival/tosca?x=1"))
        html='<a href="/macerata-opera-festival/tosca">Tosca</a><a href="/macerata-opera-festival/la-traviata">Traviata</a><a href="/macerata-opera-festival/elisir-damore">Elisir</a><a href="/sferisterio-scuola-27">Scuola</a>'
        self.assertEqual(len(extract("macerata-festival-2027",BASE+"/",html,3)),3)
    def test_verified_detail_and_weekdays(self):
        url=BASE+"/macerata-opera-festival/tosca"
        title,composer,venue,rows=parse_detail(HTML,url=url)
        self.assertEqual((title,composer,venue),("Tosca","Giacomo Puccini","Arena Sferisterio"))
        self.assertEqual([d for d,_ in rows],["2027-07-16","2027-07-25","2027-07-31","2027-08-06"])
        self.assertTrue(all(clock=="21:00" for _,clock in rows))
        with self.assertRaises(ValueError):
            parse_detail(HTML.replace("Venerdì 16","Sabato 16"),url=url)
        with self.assertRaises(ValueError):
            parse_detail(HTML,url="https://other.example/macerata-opera-festival/tosca")
        with self.assertRaises(ValueError):
            parse_detail(HTML.replace("Domenica 25 Luglio H 21:00",""),url=url)
if __name__=="__main__":
    unittest.main()

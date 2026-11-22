"""Future Petruzzelli annual indexes are independently season-scoped."""
import copy
import json
import unittest
from datetime import date

from scripts.discover_season_indexes import CONFIG, extract, validate_config
from scripts.rollover_season_indexes import next_index

SOURCE="petruzzelli-opera-2027"
HOST="https://www.fondazionepetruzzelli.it"
NEXT=HOST+"/opera-e-balletto-2028/"
DETAILS=[
    HOST+"/eventi/nuova-opera-2028/",
    HOST+"/eventi/altra-opera-2028/",
    HOST+"/eventi/terza-opera-2028/",
]

def page(year,links=DETAILS):
    return ("<nav><a href='/eventi/archivio/'>Archivio</a></nav>"
            "<div class='elementor-heading-title'><span>OPERA E BALLETTO</span>"
            f"<span>{year}</span></div>"
            +''.join(f"<article><a href='{link}'>Produzione</a></article>" for link in links)
            +"<footer><a href='/eventi/vecchio/'>Vecchio</a></footer>")

class PetruzzelliFutureYearTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text())
        cls.source=next(x for x in cls.config["sources"] if x["key"]==SOURCE)

    def test_rollover_2028_and_2029_without_changing_current_2026_index(self):
        self.assertIsNone(next_index(self.source,today=date(2026,11,22)))
        self.assertEqual(next_index(self.source,today=date(2026,11,22),
                                    allow_early=True),NEXT)
        self.assertIsNone(next_index(self.source,today=date(2027,8,31)))
        self.assertEqual(next_index(self.source,today=date(2027,9,1)),NEXT)
        future=dict(self.source,url=NEXT)
        self.assertEqual(next_index(future,today=date(2028,9,1)),
                         HOST+"/opera-e-balletto-2029/")
        self.assertEqual(extract(SOURCE,NEXT,page(2028),3),sorted(DETAILS))
        amended=copy.deepcopy(self.config)
        next(x for x in amended["sources"] if x["key"]==SOURCE)["url"]=NEXT
        validate_config(amended)
        self.assertEqual(next(x for x in amended["sources"]
                              if x["key"]=="petruzzelli-opera-2026")["url"],
                         HOST+"/opera-e-balletto-2026/")

    def test_wrong_heading_never_relabels_previous_season_as_future(self):
        for wrong in (2026,2027,2029):
            with self.subTest(year=wrong),self.assertRaises(ValueError):
                extract(SOURCE,NEXT,page(wrong),3)
        with self.assertRaises(ValueError):
            extract(SOURCE,NEXT,
                    "<nav><a href='"+DETAILS[0]+"'>OPERA E BALLETTO 2028</a></nav>"
                    +"".join(f"<a href='{x}'>Opera</a>" for x in DETAILS),3)

    def test_archives_external_links_and_invalid_index_urls_rejected(self):
        self.assertEqual(extract(SOURCE,NEXT,page(2028),3),sorted(DETAILS))
        for bad in (HOST+"/opera-e-balletto-2028/?ref=1",
                    HOST+"/opera-e-balletto-2028/extra/",
                    "https://example.org/opera-e-balletto-2028/"):
            amended=copy.deepcopy(self.config)
            next(x for x in amended["sources"] if x["key"]==SOURCE)["url"]=bad
            with self.subTest(url=bad),self.assertRaises(ValueError):
                validate_config(amended)

if __name__=="__main__":
    unittest.main()

"""Source-grounded Teatro Sangiorgi 2026/27 chamber opera dates."""
import json
import unittest
from opera_atlas.catania_press_calendar import EVENTS,parse_press_calendar,press_url
from scripts.auto_catalogue import verified_venue
from scripts.publish_catalog_v2 import REGISTRY

SOURCES={
    "https://www.teatromassimobellini.it/eventi/il-quinto-moschettiere-2/":(
        "Il quinto moschettiere","Il compositore Matteo Musumeci",
        "Dal 13 novembre 2026 al 22 gennaio 2027",
        "13 novembre ore 11\n14 novembre ore 20.30\n15 novembre ore 17.30\n"
        "16 e 17 dicembre ore 11\n18 dicembre ore 19\n20, 21 e 22 gennaio ore 11",
        [("2026-11-13","11:00"),("2026-11-14","20:30"),
         ("2026-11-15","17:30"),("2026-12-16","11:00"),
         ("2026-12-17","11:00"),("2026-12-18","19:00"),
         ("2027-01-20","11:00"),("2027-01-21","11:00"),
         ("2027-01-22","11:00")]),
    "https://www.teatromassimobellini.it/eventi/le-nozze-dellorso/":(
        "Le nozze dell’Orso","Musica di Joe Schittino",
        "Dal 20 novembre 2026 al 15 gennaio 2027",
        "20 novembre ore 11\n21 novembre ore 20.30\n22 novembre ore 17.30\n"
        "10, 12 e 13 dicembre ore 11\n13, 14 e 15 gennaio ore 11",
        [("2026-11-20","11:00"),("2026-11-21","20:30"),
         ("2026-11-22","17:30"),("2026-12-10","11:00"),
         ("2026-12-12","11:00"),("2026-12-13","11:00"),
         ("2027-01-13","11:00"),("2027-01-14","11:00"),
         ("2027-01-15","11:00")])
}

class CataniaPressCalendarTests(unittest.TestCase):
    def fixture(self,url):
        title,credit,period,dates,_=SOURCES[url]
        event="<h1>"+title+"</h1><p>Luogo Teatro Sangiorgi Categoria Opere e Balletto</p>"
        press="<h2>"+title+"</h2><p>"+credit+"</p><p>"+period+"</p>"
        press+="<h3>Calendario</h3><p>"+dates.replace("\n","</p><p>")+"</p>"
        press+="<h3>Naviga sul sito</h3>"
        return event,press

    def test_eighteen_first_party_times_and_second_venue(self):
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        for url,(_,_,_,_,expected) in SOURCES.items():
            with self.subTest(url=url):
                event,news=self.fixture(url)
                title,composer,venue,shows=parse_press_calendar(
                    event,news,event_url=url,news_url=press_url(url))
                self.assertEqual(shows,expected)
                self.assertEqual(venue,"Teatro Sangiorgi")
                rows=[{"venue":venue,"event_title":title,"composer":composer,
                       "date":day,"starts_at":day+"T"+clock+":00+01:00"}
                      for day,clock in shows]
                resolved=verified_venue("bellini-catania-opera-2026-27",rows,registry)
                self.assertIsNotNone(resolved)
                self.assertEqual(resolved[0],"Catania")

    def test_different_title_composer_or_official_page_fails_closed(self):
        url=next(iter(SOURCES))
        event,press=self.fixture(url)
        with self.assertRaisesRegex(ValueError,"source pair"):
            parse_press_calendar(event,press,event_url=url,
                                 news_url="https://example.com/other")
        with self.assertRaisesRegex(ValueError,"composer"):
            parse_press_calendar(event,press.replace("Matteo Musumeci","Wrong Composer"),
                                 event_url=url,news_url=press_url(url))
        with self.assertRaisesRegex(ValueError,"venue"):
            parse_press_calendar(event.replace("Teatro Sangiorgi","Teatro Metropolitan"),
                                 press,event_url=url,news_url=press_url(url))
        with self.assertRaisesRegex(ValueError,"calendar"):
            parse_press_calendar(event,press.replace("18 dicembre ore 19","18 dicembre"),
                                 event_url=url,news_url=press_url(url))

    def test_no_arbitrary_date_inference_from_overview(self):
        url=next(iter(SOURCES))
        event,press=self.fixture(url)
        with self.assertRaisesRegex(ValueError,"year range"):
            parse_press_calendar(event,press.replace("22 gennaio 2027","22 gennaio"),
                                 event_url=url,news_url=press_url(url))
        self.assertIsNone(press_url("https://www.teatromassimobellini.it/eventi/la-bella-addormentata-5/"))

if __name__=="__main__":
    unittest.main()

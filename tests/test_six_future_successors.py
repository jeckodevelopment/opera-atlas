"""All six legacy municipal opera sources have independent future-season contracts."""
import copy
import json
import unittest
from datetime import date
from opera_atlas.six_future_seasons import SOURCES,index_year,next_url,extract_index,known_recite
from scripts.discover_season_indexes import CONFIG,extract,validate_config
from scripts.rollover_season_indexes import next_index
from scripts.collect_candidate_details import parse_known_opera_detail

CASES={
 "chieti-marrucino-season-2027":("2027/2027","Chieti","Marrucino"),
 "modena-municipal-opera-2027-28":("2027/2028","Modena","Teatro Comunale"),
 "rovigo-sociale-season-2027-28":("2027/2028","Rovigo","Teatro Sociale"),
 "treviso-del-monaco-season-2027-28":("27/28","Treviso","Teatro"),
 "padova-verdi-season-2027":("2027","Padova","Teatro Verdi"),
 "lecce-provincia-season-2027":("2027/2027","Lecce","Politeama")
}
REGISTRY={"works":{"macbeth":{"title":"Macbeth","composer":"Giuseppe Verdi"}}}

def programme(year,city,venue):
    return (f"<h1>Stagione Lirica {year} - {city}</h1>"
            f"<p>{venue}, opera in programma</p>"
            "<p>Macbeth di Giuseppe Verdi, 20 novembre 2027 ore 20:00</p>")

def search_results(key):
    if key.startswith("chieti"):
        return ('<nav><a href="/novita/vecchia-stagione-lirica-2026-del-teatro-marrucino/">'
                'Vecchia</a></nav>'
                '<a href="/novita/presentata-la-stagione-lirica-2027-del-teatro-marrucino/">'
                'Stagione lirica 2027 del Teatro Marrucino</a>')
    return ('<a href="/52-stagione-lirica-della-provincia-di-lecce-2027/">'
            '52 Stagione Lirica della Provincia di Lecce 2027</a>')

class SixSuccessorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text())
        cls.sources={s["key"]:s for s in cls.config["sources"]}

    def test_all_six_validate_and_roll_across_future_seasons(self):
        validate_config(self.config)
        self.assertEqual(len(SOURCES),6)
        for key in SOURCES:
            with self.subTest(key=key):
                current=self.sources[key]
                start,end=index_year(key,current["url"])
                self.assertEqual(start,2027)
                self.assertIn(end,(2027,2028))
                future=next_index(current,today=date(2026,11,22),allow_early=True)
                self.assertIsNotNone(future)
                self.assertEqual(index_year(key,future)[0],2028)
                future2=next_index(dict(current,url=future),
                                   today=date(2028,10,1),allow_early=True)
                self.assertEqual(index_year(key,future2)[0],2029)
                changed=copy.deepcopy(self.config)
                next(x for x in changed["sources"] if x["key"]==key)["url"]=future
                validate_config(changed)

    def test_direct_official_year_and_real_opera_required(self):
        for key,(year,city,venue) in CASES.items():
            if key.startswith(("chieti","lecce")):continue
            url=self.sources[key]["url"]
            html=programme(year,city,venue)
            with self.subTest(key=key):
                self.assertEqual(extract(key,url,html,1),[url])
                for bad in (html.replace("Macbeth di Giuseppe Verdi","Un concerto jazz"),
                            html.replace(year,"2026"),
                            html.replace(city,"Altro Comune"),
                            html.replace("<h1>","<p>").replace("</h1>","</p>")):
                    with self.assertRaises(ValueError):
                        extract(key,url,bad,1)
                self.assertEqual(len(parse_known_opera_detail(key,url,html,REGISTRY)),1)

    def test_search_indexes_only_discover_official_future_notice_links(self):
        for key in ("chieti-marrucino-season-2027","lecce-provincia-season-2027"):
            url=self.sources[key]["url"]
            links=extract_index(key,url,search_results(key),1)
            self.assertEqual(len(links),1)
            self.assertIn("2027",links[0])
            with self.assertRaises(ValueError):
                extract_index(key,url,"<a href='/notizie/stagione-lirica-2026'>Archivio</a>",1)

    def test_municipal_announcements_require_edition_and_city(self):
        chieti="https://comune.chieti.it/novita/presentata-la-stagione-lirica-2027-del-teatro-marrucino/"
        body="<h1>Stagione lirica 2027 a Chieti - Teatro Marrucino</h1><p>Macbeth di Giuseppe Verdi, 20 novembre 2027 ore 20:00</p>"
        self.assertEqual(len(known_recite("chieti-marrucino-season-2027",chieti,body,REGISTRY)),1)
        lecce="https://www.provincia.le.it/52-stagione-lirica-della-provincia-di-lecce-2027/"
        body2="<h1>52 Stagione lirica della Provincia di Lecce 2027</h1><p>Teatro Politeama. Macbeth di Giuseppe Verdi, 20 novembre 2027 ore 20:00</p>"
        self.assertEqual(len(known_recite("lecce-provincia-season-2027",lecce,body2,REGISTRY)),1)
        with self.assertRaises(ValueError):
            known_recite("lecce-provincia-season-2027",lecce,body2.replace("52 Stagione","51 Stagione"),REGISTRY)

    def test_historical_sources_remain_present_and_unmodified(self):
        historic=[
          "chieti-marrucino-lirica-2026","modena-opera-2026-27",
          "rovigo-sociale-opera-2026-27","treviso-del-monaco-opera-2026-27",
          "padova-verdi-opera-2026","lecce-provincia-politeama-2026"]
        self.assertTrue(all(key in self.sources for key in historic))
        self.assertEqual(len(self.sources),64)

    def test_unknown_identity_and_missing_time_do_not_infer_recite(self):
        key="modena-municipal-opera-2027-28"
        url=self.sources[key]["url"]
        html=programme("2027/2028","Modena","Teatro Comunale")
        self.assertEqual(known_recite(key,url,html,{"works":{}}),[])
        self.assertEqual(known_recite(key,url,html.replace("ore 20:00","nel pomeriggio"),REGISTRY),[])

if __name__=="__main__":
    unittest.main()

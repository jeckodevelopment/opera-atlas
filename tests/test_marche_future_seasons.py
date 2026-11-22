"""Shared future-year monitoring for Jesi and Ancona, without reusing 2026 bills."""
import copy
import json
import unittest
from datetime import date

from opera_atlas.marche_future_parser import verify_index, parse_known_opera_program
from scripts.collect_candidate_details import parse_known_opera_detail
from scripts.discover_season_indexes import CONFIG,extract,validate_config
from scripts.rollover_season_indexes import next_index

CASES={
    "jesi-opera-season-2027":(
      "https://www.fondazionepergolesispontini.com/lirica/programma-stagione-lirica-2027/",
      "Jesi Teatro Pergolesi","Teatro Giovan Battista Pergolesi"),
    "ancona-opera-season-2027":(
      "https://www.fondazionemuse.org/stagione-lirica-2027/",
      "Ancona Teatro delle Muse","Teatro delle Muse"),
}
REGISTRY={"works":{"traviata|verdi":{"title":"La traviata","composer":"Giuseppe Verdi"}}}

def page(venue,year=2027,title="La traviata",composer="Giuseppe Verdi"):
    return (f"<h1>Stagione lirica {year}</h1><h2>{venue}</h2>"
            "<p>sabato 2 ottobre, ore 20:00</p>"
            "<p>domenica 3 ottobre, ore 16:00</p>"
            f"<h3>{title}</h3><p>musica di {composer}</p>")

class MarcheFutureSeasonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text())

    def test_two_sources_roll_independently_without_rewriting_2026(self):
        for key,(url,venue,_) in CASES.items():
            with self.subTest(key=key):
                item=next(x for x in self.config["sources"] if x["key"]==key)
                self.assertIsNone(next_index(item,today=date(2027,8,31)))
                self.assertEqual(next_index(item,today=date(2026,11,22),
                                            allow_early=True),url.replace("2027","2028"))
                self.assertEqual(next_index(item,today=date(2027,9,1)),
                                 url.replace("2027","2028"))
                self.assertEqual(next_index(dict(item,url=url.replace("2027","2028")),
                                            today=date(2028,9,1)),
                                 url.replace("2027","2029"))
                changed=copy.deepcopy(self.config)
                next(x for x in changed["sources"] if x["key"]==key)["url"]=url.replace("2027","2028")
                validate_config(changed)

    def test_verified_future_program_yields_known_work_recite(self):
        for key,(url,venue,expected_venue) in CASES.items():
            with self.subTest(key=key):
                html=page(venue)
                self.assertTrue(verify_index(html,url=url,source_key=key))
                self.assertEqual(extract(key,url,html,1),[url])
                rows=parse_known_opera_program(html,url=url,source_key=key,registry=REGISTRY)
                self.assertEqual(rows,[
                    ("La traviata","Giuseppe Verdi",expected_venue,"2027-10-02","20:00"),
                    ("La traviata","Giuseppe Verdi",expected_venue,"2027-10-03","16:00")])
                evidence=parse_known_opera_detail(key,url,html,REGISTRY)
                self.assertEqual(len(evidence),2)
                self.assertEqual([x["date"] for x in evidence],
                                 ["2027-10-02","2027-10-03"])

    def test_wrong_year_venue_and_weekday_are_never_accepted(self):
        for key,(url,venue,_) in CASES.items():
            html=page(venue)
            for wrong in (html.replace("2027","2026"),
                          html.replace(venue,"Un altro teatro"),
                          html.replace("sabato 2","venerdì 2"),
                          html.replace("musica di Giuseppe Verdi","Concerto jazz")):
                with self.subTest(key=key,wrong=wrong[-35:]),self.assertRaises(ValueError):
                    verify_index(wrong,url=url,source_key=key)
            with self.assertRaises(ValueError):
                verify_index(html,url=url+"?year=2026",source_key=key)

    def test_no_guessed_work_when_composer_not_source_credited(self):
        key,(url,venue,_)=next(iter(CASES.items()))
        html=page(venue)
        for wrong in (html.replace("Giuseppe Verdi","Giacomo Puccini"),
                      html.replace("La traviata","Una nuova opera sconosciuta")):
            self.assertEqual(parse_known_opera_program(
                wrong,url=url,source_key=key,registry=REGISTRY),[])

    def test_legacy_six_productions_stay_2026_bound(self):
        keys={x["key"] for x in self.config["sources"]}
        self.assertTrue({"jesi-trittico-opera-2026","jesi-don-pasquale-opera-2026",
             "jesi-esecuzione-opera-2026","jesi-nabucco-opera-2026",
             "ancona-elisir-opera-2026","ancona-cavalleria-program-2026"}.issubset(keys))

if __name__=="__main__":
    unittest.main()

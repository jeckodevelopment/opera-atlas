"""Future Ferrara regional season source is distinct from five verified 2026/27 works."""
import copy
import json
import unittest
from datetime import date

from opera_atlas.ferrara_future_parser import verify_index,parse_known_recite
from scripts.collect_candidate_details import parse_known_opera_detail
from scripts.discover_season_indexes import CONFIG,extract,validate_config
from scripts.rollover_season_indexes import next_index

KEY="ferrara-season-opera-2027-28"
HOST="https://spettacolo.emiliaromagnacultura.it"
URL=HOST+"/it/rassegna/teatro-comunale-ferrara-opera-danza-2027-2028/"
REGISTRY={"works":{"macbeth|verdi":{"title":"Macbeth","composer":"Giuseppe Verdi"}}}

def page(*,year="2027/2028",time=True,heading="MACBETH - Giuseppe Verdi"):
    first="27 Novembre 2027"+(", ore 20:00" if time else "")
    second="29 Novembre 2027"+(", ore 16:00" if time else "")
    return ("<nav><h1>Altre stagioni 2026/2027</h1></nav>"
            f"<h1>TEATRO COMUNALE FERRARA - OPERA &amp; DANZA {year}</h1>"
            "<h3>IL LAGO DEI CIGNI</h3><p>danza balletto 9 Novembre 2027, ore 21:00"
            " - Ferrara TEATRO COMUNALE DI FERRARA</p>"
            f"<h3>{heading}</h3><p>musica di Giuseppe Verdi "
            f"{first} - {second} Ferrara - TEATRO COMUNALE DI FERRARA</p>"
            "<h3>L'ANNO CHE VERRÀ</h3><p>musical crossover"
            " 30 Novembre 2027, ore 20:00 - Teatro Comunale di Ferrara</p>"
            "<footer><h1>Stagione 2026/2027</h1></footer>")

class FerraraRollingSeasonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text())
        cls.item=next(x for x in cls.config["sources"] if x["key"]==KEY)

    def test_future_index_can_roll_multiple_years(self):
        self.assertEqual(self.item["url"],URL)
        self.assertIsNone(next_index(self.item,today=date(2028,5,31)))
        self.assertEqual(next_index(self.item,today=date(2027,11,22),allow_early=True),
                         URL.replace("2027-2028","2028-2029"))
        self.assertEqual(next_index(self.item,today=date(2028,6,1)),
                         URL.replace("2027-2028","2028-2029"))
        amended=dict(self.item,url=URL.replace("2027-2028","2028-2029"))
        self.assertEqual(next_index(amended,today=date(2029,6,1)),
                         URL.replace("2027-2028","2029-2030"))
        document=copy.deepcopy(self.config)
        next(x for x in document["sources"] if x["key"]==KEY)["url"]=amended["url"]
        validate_config(document)

    def test_future_regional_opera_is_verified_without_inventing_hours(self):
        html=page(time=False)
        self.assertTrue(verify_index(html,url=URL))
        self.assertEqual(extract(KEY,URL,html,1),[URL])
        self.assertEqual(parse_known_recite(html,url=URL,registry=REGISTRY),[])
        self.assertEqual(parse_known_opera_detail(KEY,URL,html,REGISTRY),[])

    def test_only_exact_source_credited_opera_and_recite_can_be_published(self):
        html=page()
        self.assertEqual(parse_known_recite(html,url=URL,registry=REGISTRY),
                         [("Macbeth","Giuseppe Verdi","Teatro Comunale Claudio Abbado",
                           "2027-11-27","20:00"),
                          ("Macbeth","Giuseppe Verdi","Teatro Comunale Claudio Abbado",
                           "2027-11-29","16:00")])
        self.assertEqual([x["date"] for x in
                          parse_known_opera_detail(KEY,URL,html,REGISTRY)],
                         ["2027-11-27","2027-11-29"])

    def test_wrong_year_or_host_and_unscoped_html_fail_closed(self):
        for wrong_url in (URL+"?ref=2026",
                         URL.replace(HOST,"https://example.invalid"),
                         URL.replace("2027-2028","2027-2029")):
            with self.subTest(url=wrong_url),self.assertRaises(ValueError):
                verify_index(page(),url=wrong_url)
        with self.assertRaises(ValueError):
            verify_index(page(year="2026/2027"),url=URL)
        with self.assertRaises(ValueError):
            verify_index("<nav><h1>TEATRO COMUNALE FERRARA - OPERA & DANZA 2027/2028</h1></nav>"
                         "<h3>MACBETH</h3><p>musica di Giuseppe Verdi 27 Novembre 2027"
                         " - TEATRO COMUNALE DI FERRARA</p>",url=URL)

    def test_crossover_ballet_and_uncredited_new_work_never_get_times(self):
        self.assertEqual(parse_known_recite(page(),url=URL,registry={"works":{}}),[])
        self.assertEqual(parse_known_recite(page(heading="MACBETH - Giorgio Rossi"),
                                            url=URL,registry=REGISTRY),[])
        for existing in ("ferrara-macbeth-opera-2026-27",
                         "ferrara-barbiere-opera-2026-27",
                         "ferrara-dido-opera-2026-27",
                         "ferrara-clemenza-opera-2026-27",
                         "ferrara-boccanegra-opera-2026-27"):
            historical=next(x for x in self.config["sources"] if x["key"]==existing)
            self.assertIn("2026-2027",historical["url"])

if __name__=="__main__":
    unittest.main()

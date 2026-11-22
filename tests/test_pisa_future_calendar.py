"""Dynamic first-party Pisa Opera events, isolated from the 2026/27 five-title list."""
import copy
import json
import unittest

from opera_atlas.pisa_future_calendar import INDEX,eligible_detail,extract_calendar,parse_calendar_detail
from scripts.discover_season_indexes import CONFIG,eligible,extract,validate_config
from scripts.collect_candidate_details import parse_known_opera_detail

HOST="https://teatrodipisa.it"
EVENT=HOST+"/calendario/nuova-traviata/"
REGISTRY={"works":{"verdi-traviata":{"title":"La traviata","composer":"Giuseppe Verdi"}}}

def index_page():
    return ("""<nav><a href="/calendario/teatro-di-prosa/">Prosa</a></nav>
      <h1>opera</h1><h3><a href="/calendario/nuova-traviata/">La traviata</a></h3>
      <h3><a href="/calendario/la-traviata-scuole/">La traviata (riservata alle scuole)</a></h3>
      <h3><a href="https://elsewhere.example/calendario/fake/">Opera esterna</a></h3>
      <h3><a href="/calendario/otello/">Otello</a></h3>
      <footer><h3><a href="/calendario/vecchio/">Vecchio</a></h3></footer>""")

def detail(*,title="La traviata",composer="Giuseppe Verdi",year=2028,
           category="opera",time="20:30"):
    return (f"<h1>{title}</h1><p>Musica di {composer}</p>"
            "<p>Prima rappresentazione 6 Marzo 1853</p>"
            "<h2>Dettagli</h2>"
            f"<p>Data: 8 Marzo {year}</p><p>Ora: {time}</p>"
            f"<p>Categoria Evento: {category}</p>"
            "<footer>Fondazione Teatro di Pisa</footer>")

class PisaFutureCalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text())
    def test_dynamic_category_is_tied_to_firstparty_card_headings(self):
        self.assertEqual(extract_calendar(index_page(),url=INDEX,min_links=1),
                         [EVENT,HOST+"/calendario/otello/"])
        self.assertEqual(extract("pisa-future-calendar",INDEX,index_page(),1),
                         [EVENT,HOST+"/calendario/otello/"])
        self.assertTrue(eligible("pisa-future-calendar",EVENT))
        self.assertFalse(eligible("pisa-future-calendar",HOST+"/spettacolo/nuova-traviata/"))
        self.assertFalse(eligible_detail(EVENT+"?utm_source=wrong"))
        for bad in (INDEX+"?page=2",INDEX.replace(HOST,"https://other.example")):
            with self.assertRaises(ValueError):
                extract_calendar(index_page(),url=bad,min_links=1)
        for bad in (index_page().replace("<h1>opera</h1>","<h1>prosa</h1>"),
                    "<nav><h1>opera</h1></nav><a href='/calendario/nuova-traviata/'>Opera</a>"):
            with self.assertRaises(ValueError):
                extract_calendar(bad,url=INDEX,min_links=1)
    def test_future_one_recita_has_exact_canonical_credit_and_time(self):
        rows=parse_calendar_detail(detail(),url=EVENT,registry=REGISTRY)
        self.assertEqual(rows,[("La traviata","Giuseppe Verdi","Teatro Verdi",
                                "2028-03-08","20:30")])
        evidence=parse_known_opera_detail("pisa-future-calendar",EVENT,detail(),REGISTRY)
        self.assertEqual(len(evidence),1)
        self.assertEqual(evidence[0]["date"],"2028-03-08")
        self.assertTrue(evidence[0]["starts_at"].startswith("2028-03-08T20:30"))
    def test_unknown_or_mixed_show_never_published(self):
        for html in (detail(composer="Giacomo Puccini"),
                     detail(title="Il musical pop"),
                     detail(category="prosa"),
                     detail(year=2026),
                     detail(time="non annunciata"),
                     detail(title="La traviata (riservata alle scuole)"),
                     detail().replace("Fondazione Teatro di Pisa","Altra fondazione"),
                     detail().replace("Data: 8 Marzo 2028","Data da definire"),
                     detail().replace("Data: 8 Marzo 2028","Annullato Data: 8 Marzo 2028")):
            with self.subTest(html=html[:65]),self.assertRaises(ValueError):
                parse_calendar_detail(html,url=EVENT,registry=REGISTRY)
        with self.assertRaises(ValueError):
            parse_calendar_detail(detail(),url=EVENT,registry={"works":{}})
    def test_history_and_successor_remain_independent(self):
        config=copy.deepcopy(self.config)
        validate_config(config)
        keys={x["key"]:x for x in config["sources"]}
        self.assertIn("pisa-future-calendar",keys)
        self.assertEqual(keys["pisa-future-calendar"]["url"],INDEX)
        self.assertEqual(keys["pisa-verdi-opera-2026-27"]["url"],
                         HOST+"/tipologia-spettacolo/opera/")
        self.assertFalse(eligible("pisa-verdi-opera-2026-27",
                                  HOST+"/spettacolo/carmen/"))

if __name__=="__main__":
    unittest.main()

"""Future Macerata festival editions are distinct from the three historical 2027 works."""
import json
import unittest
from datetime import date
from opera_atlas.macerata_future_parser import (
    edition_year,next_edition,eligible_detail,extract_index,parse_detail)
from scripts.rollover_season_indexes import next_index
from scripts.discover_season_indexes import CONFIG,eligible,extract,validate_config
from scripts.collect_candidate_details import parse_known_opera_detail,parse_source_credited_opera_detail

ROOT="https://www.sferisterio.it"
INDEX=ROOT+"/macerata-opera-festival-2027"
INDEX_NEXT=ROOT+"/macerata-opera-festival-2028"
EVENT=ROOT+"/macerata-opera-festival/tosca"
NEW=ROOT+"/macerata-opera-festival/nuova-opera"
REGISTRY={"works":{"tosca":{"title":"Tosca","composer":"Giacomo Puccini"}}}
ROWS=("Venerdì 16 Luglio H 21:00","Domenica 25 Luglio H 21:00",
      "Sabato 31 Luglio H 21:00","Venerdì 06 Agosto H 21:00")

def index_page(year=2027,*,other=False):
    return (f"<header>Sferisterio - Macerata Opera Festival {year}</header>"
            f"<h2>Il Macerata Opera Festival {year}: Arena Sferisterio</h2>"
            "<h2>Gli appuntamenti in cartellone</h2>"
            "<p>16, 25, 31 luglio e 6 agosto</p>"
            '<a href="/macerata-opera-festival/tosca">SCOPRI DI PIÙ SU TOSCA</a>'
            '<a href="/macerata-opera-festival/la-traviata">SCOPRI DI PIÙ SU LA TRAVIATA</a>'
            '<a href="/macerata-opera-festival/nuova-opera">SCOPRI DI PIÙ SU NUOVA OPERA</a>'
            '<a href="/sferisterio-scuola-27">SCOPRI DI PIÙ SU SCUOLA</a>'
            "<h2>Hai già le idee chiare su cosa acquistare?</h2>"
            '<a href="/macerata-opera-festival/concerto-pop">SCOPRI DI PIÙ SU CONCERTO</a>'
            '<footer><a href="/macerata-opera-festival/vecchio">SCOPRI DI PIÙ SU VECCHIO</a></footer>')

def page(year=2027,rows=ROWS,composer="Giacomo Puccini",
         credit="Opera lirica in tre atti",title="Tosca"):
    return (f'<nav>Macerata Opera Festival {year}</nav><h2>{title}</h2>'
        '<p>Arena Sferisterio</p>'
        f'<p>{credit} di {composer} su libretto di Giuseppe Giacosa e Luigi Illica</p>'
        '<p>Prima rappresentazione 14 gennaio 1900</p>'
        '<ul>'+"".join(f"<li>{x}</li>" for x in rows)+'</ul>'
        '<h4>Cast</h4><p>Ruolo e interpreti</p>'
        '<h2>Gli appuntamenti in cartellone</h2>'
        '<p>Una replica del 2026 non è una data dell opera</p>')

class MacerataRollingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text())

    def test_current_and_future_index_are_firstparty_and_year_scoped(self):
        validate_config(self.config)
        self.assertEqual(edition_year(INDEX),2027)
        self.assertEqual(next_edition(INDEX),INDEX_NEXT)
        sources={x["key"]:x for x in self.config["sources"]}
        current=sources["macerata-festival-rolling"]
        self.assertEqual(current["url"],INDEX)
        self.assertIsNone(next_index(current,today=date(2027,8,31)))
        self.assertEqual(next_index(current,today=date(2027,9,1)),INDEX_NEXT)
        future=dict(current,url=INDEX_NEXT)
        self.assertEqual(next_index(future,today=date(2028,9,1)),
                         ROOT+"/macerata-opera-festival-2029")
        for wrong in (INDEX+"?ref=1",INDEX+"#top",INDEX.replace(ROOT,"https://fake.example")):
            with self.assertRaises(ValueError):edition_year(wrong)

    def test_year_specific_official_production_cards_only(self):
        self.assertEqual(extract_index(index_page(),url=INDEX,min_links=1),
                         [ROOT+"/macerata-opera-festival/la-traviata",
                          NEW,EVENT])
        self.assertEqual(extract("macerata-festival-rolling",INDEX,index_page(),1),
                         [ROOT+"/macerata-opera-festival/la-traviata",
                          NEW,EVENT])
        self.assertEqual(extract_index(index_page(2028),url=INDEX_NEXT,min_links=1),
                         [ROOT+"/macerata-opera-festival/la-traviata",NEW,EVENT])
        for wrong in (index_page(2028),'<nav>Macerata Opera Festival 2027</nav><a href="'+EVENT+'">Tosca</a>'):
            with self.assertRaises(ValueError):extract_index(wrong,url=INDEX,min_links=1)
        self.assertTrue(eligible("macerata-festival-rolling",NEW))
        self.assertFalse(eligible("macerata-festival-2027",NEW))

    def test_exact_2027_recite_and_known_canonical_identity(self):
        self.assertEqual(parse_detail(page(),url=EVENT),
                         ("Tosca","Giacomo Puccini","Arena Sferisterio",
                          [("2027-07-16","21:00"),("2027-07-25","21:00"),
                           ("2027-07-31","21:00"),("2027-08-06","21:00")]))
        known=parse_known_opera_detail("macerata-festival-rolling",EVENT,page(),REGISTRY)
        self.assertEqual(len(known),4)
        unknown=parse_source_credited_opera_detail("macerata-festival-rolling",EVENT,page())
        self.assertEqual(len(unknown),4)
        self.assertEqual(known[0]["event_title"],"Tosca")

    def test_unverified_year_genre_composer_and_incomplete_dates_are_rejected(self):
        cases=(page(year=2028),page(rows=ROWS[:2]+(ROWS[2].replace("H 21:00","H da definire"),)+ROWS[3:]),
               page(rows=(ROWS[0],ROWS[0])),page(composer="ignoto autore"),
               page(composer="Giuseppe Verdi e Giacomo Puccini"),
               page(credit="Balletto coreografia"),
               page().replace("Cast</h4>","Personaggi</h4>"),
               page().replace("Venerdì 16","Sabato 16"),
               page().replace("Venerdì 16 Luglio H 21:00","Annullato Venerdì 16 Luglio H 21:00"))
        for x in cases:
            with self.subTest(body=x[-140:]),self.assertRaises(ValueError):
                parse_detail(x,url=EVENT)
        with self.assertRaises(ValueError):
            parse_detail(page(),url=EVENT+"?utm=1")

    def test_original_allowlist_and_parser_remain_unmodified(self):
        sources={x["key"]:x for x in self.config["sources"]}
        self.assertEqual(sources["macerata-festival-2027"]["url"],ROOT+"/")
        self.assertTrue(eligible("macerata-festival-2027",EVENT))
        self.assertFalse(eligible("macerata-festival-2027",NEW))
        self.assertTrue(eligible_detail(NEW))
        self.assertFalse(eligible_detail(ROOT+"/sferisterio-scuola-27"))

if __name__=="__main__":
    unittest.main()

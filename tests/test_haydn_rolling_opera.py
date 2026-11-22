"""Haydn first-party opera evidence routes to distinct theatres without genre leakage."""
import json
import unittest
from datetime import date

from opera_atlas.haydn_rolling_opera import INDEX,extract_index,parse_detail,eligible_detail
from opera_atlas.controlled_fetch import FetchResult
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract
from scripts.collect_candidate_details import parse_source_credited_opera_detail,collect
from scripts.source_automation import INDEX_VENUES,build,DIRECTORY,DAILY,DAILY_HEALTH
from scripts.auto_catalogue import VENUE_BY_SOURCE,verified_venue
from scripts.publish_catalog_v2 import REGISTRY

KEY="haydn-rolling-opera"
BOLZANO="https://www.haydn.it/eventi/la-boheme-5"
TRENTO="https://www.haydn.it/eventi/la-clemenza-di-tito"
INDEX_HTML=f'<a href="/eventi/la-boheme-5">Boheme</a><a href="{TRENTO}">Clemenza</a>'

def page(title="La bohème",composer="Giacomo Puccini",location="Bolzano",
         when="16.04.2027",hour="20.00",genre="Opera"):
    if location=="Bolzano":
        where="Teatro Comunale - Sala Grande Piazza Verdi 40 - Bolzano"
    else:
        where="Teatro Sociale Via Paolo Oss-Mazzurana 19 - Trento"
    return (f'<main><h1>{title}</h1><p>{composer}</p><p>{genre}</p>'
            f'<p>Musica di {composer} Libretto di Autore</p>'
            f'<p>Venerdì {when} alle {hour}</p><p>{where}</p>'
            '<h2>Programma</h2><p>Stagione d’Opera 2026/27</p>'
            '<h2>Cast</h2><p>Artist biographies mention Teatro Sociale and '
            'a different opera by Wagner</p></main>')

class HaydnRollingOperaTests(unittest.TestCase):
    def test_evergreen_index_approved_for_both_venues(self):
        src=next(x for x in validate_config(json.loads(CONFIG.read_text()))
                 if x["key"]==KEY)
        self.assertEqual(src["url"],INDEX)
        self.assertEqual(set(INDEX_VENUES[KEY]),
                         {"Bolzano|Teatro Comunale di Bolzano","Trento|Teatro Sociale"})
        self.assertEqual(VENUE_BY_SOURCE[KEY],("Bolzano","Teatro Comunale di Bolzano"))
        self.assertEqual(extract(KEY,INDEX,INDEX_HTML,2),
                         sorted((BOLZANO,TRENTO)))
        self.assertTrue(eligible(KEY,BOLZANO))
        for bad in ("https://elsewhere.example/eventi/la-boheme-5",
                    "http://www.haydn.it/eventi/la-boheme-5",
                    BOLZANO+"?preview=1","https://www.haydn.it/educazione"):
            self.assertFalse(eligible_detail(bad))
        with self.assertRaises(ValueError):
            extract_index("<h1>Nessun evento</h1>",url=INDEX,min_links=1)

    def test_bolzano_and_trento_metadata_are_separate(self):
        bolzano=page()
        trento=page("La clemenza di Tito","Wolfgang A. Mozart","Trento",
                    "27.11.2026","20.00")
        self.assertEqual(parse_detail(bolzano,url=BOLZANO),
                         ("La bohème","Giacomo Puccini",
                          "Teatro Comunale di Bolzano",[("2027-04-16","20:00")]))
        self.assertEqual(parse_detail(trento,url=TRENTO),
                         ("La clemenza di Tito","Wolfgang A. Mozart",
                          "Teatro Sociale",[("2026-11-27","20:00")]))
        rows=parse_source_credited_opera_detail(KEY,BOLZANO,bolzano)
        self.assertEqual(rows,[{
            "event_title":"La bohème","composer":"Giacomo Puccini",
            "venue":"Teatro Comunale di Bolzano","date":"2027-04-16",
            "starts_at":"2027-04-16T20:00:00+02:00"}])
        registry=json.loads(REGISTRY.read_text())
        self.assertEqual(verified_venue(KEY,rows,registry)[0:2],
                         ("Bolzano","Teatro Comunale di Bolzano"))
        trento_rows=parse_source_credited_opera_detail(KEY,TRENTO,trento)
        self.assertEqual(verified_venue(KEY,trento_rows,registry)[0:2],
                         ("Trento","Teatro Sociale"))

    def test_mixed_concerts_and_wrong_places_never_become_operas(self):
        original=page()
        cases=[original.replace("<p>Opera</p>","<p>Concerto</p>"),
               original.replace("Musica di Giacomo Puccini","Musica di"),
               original.replace("16.04.2027 alle 20.00",""),
               original.replace("Piazza Verdi 40 - Bolzano","Piazza Altrove - Bolzano"),
               original.replace("16.04.2027 alle 20.00","31.02.2027 alle 20.00")]
        for html in cases:
            with self.subTest(html=html[:150]),self.assertRaises(ValueError):
                parse_detail(html,url=BOLZANO)

    def test_future_event_year_is_read_from_source(self):
        actual=parse_detail(page(when="16.04.2029"),url=BOLZANO)
        self.assertEqual(actual[3],[("2029-04-16","20:00")])

    def test_common_collection_dispatch_excludes_generic_fallback(self):
        candidate={"schema_version":1,"candidates":[{
            "id":"oa-haydn-bolzano-test","source_key":KEY,
            "official_url":BOLZANO,"status":"needs_review"}]}
        def fake(db,*,source_id,url,network_enabled):
            self.assertEqual(url,BOLZANO)
            html=page()
            return FetchResult(url,html,"d"*64,len(html))
        found,health=collect(candidate,{"schema_version":1,"evidence":[]},
                             network_enabled=True,fetcher=fake,
                             today=date(2026,11,22))
        self.assertEqual(health[0]["outcome"],"facts_found",health)
        self.assertEqual(found["evidence"][0]["event_facts"][0]["venue"],
                         "Teatro Comunale di Bolzano")

if __name__=="__main__":
    unittest.main()

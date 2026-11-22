"""Rossini Opera Festival: never misattribute Scavolini, recitals or academy."""
import json
import unittest
from datetime import date

from opera_atlas.pesaro_rof import INDEX,extract_index,parse_detail
from opera_atlas.controlled_fetch import FetchResult
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract
from scripts.collect_candidate_details import collect
from scripts.source_automation import INDEX_VENUES
from scripts.auto_catalogue import VENUE_BY_SOURCE,verified_venue
from scripts.publish_catalog_v2 import REGISTRY
from scripts.rollover_season_indexes import next_index,ROLLOVER_KEYS

KEY="pesaro-rof-2026"
OCCASIONE="https://www.rossinioperafestival.it/archivio/stagione-2026/loccasione-fa-il-ladro/"
SCALA="https://www.rossinioperafestival.it/archivio/stagione-2026/la-scala-di-seta/"
VIAGGIO="https://www.rossinioperafestival.it/archivio/stagione-2026/il-viaggio-a-reims/"
SIEGE="https://www.rossinioperafestival.it/archivio/stagione-2026/le-siege-de-corinthe/"
CONCERTO="https://www.rossinioperafestival.it/archivio/stagione-2026/concerto-di-belcanto/"
def page(title="La scala di seta",venue="Teatro Rossini",
         slots="13, 16, 19, 22 agosto, ore 20.00",kind="Farsa comica"):
    return (f'<main><h1>{title}</h1><p>{slots}</p>'
            f'<p>{venue} &gt;</p><h2>{title.upper()}</h2>'
            f'<p>{kind} in un atto di Giuseppe Foppa</p>'
            '<p>Edizione critica della Fondazione Rossini di Pesaro</p>'
            '<p>Direttore Iván López Reynos</p></main>')
class ROFTests(unittest.TestCase):
    def test_scoped_archive_and_future_season(self):
        config=json.loads(CONFIG.read_text())
        source=next(x for x in validate_config(config) if x["key"]==KEY)
        self.assertEqual(source["url"],INDEX)
        self.assertIn(KEY,ROLLOVER_KEYS)
        self.assertEqual(INDEX_VENUES[KEY],("Pesaro|Teatro Gioachino Rossini",))
        self.assertEqual(VENUE_BY_SOURCE[KEY],("Pesaro","Teatro Gioachino Rossini"))
        self.assertIsNone(next_index(source,today=date(2026,8,31)))
        self.assertEqual(next_index(source,today=date(2026,9,1)),INDEX.replace("2026","2027"))
        html="".join(f'<a href="{u}">Evento</a>' for u in
                     (OCCASIONE,SCALA,VIAGGIO,SIEGE,CONCERTO))
        self.assertEqual(extract(KEY,INDEX,html,3),sorted(
            (OCCASIONE,SCALA,VIAGGIO,SIEGE,CONCERTO)))
        self.assertTrue(eligible(KEY,SCALA))
        self.assertTrue(eligible(KEY,SCALA.replace("2026","2028")))
        self.assertFalse(eligible(KEY,SCALA.replace("https:","http:")))
        self.assertFalse(eligible(KEY,SCALA+"?utm=1"))
        with self.assertRaises(ValueError):
            extract_index("<h1>Archive missing</h1>",url=INDEX)

    def test_rossini_productions_and_first_party_recite(self):
        self.assertEqual(parse_detail(page(),url=SCALA),
                         ("La scala di seta","Gioachino Rossini",
                          "Teatro Gioachino Rossini",
                          [("2026-08-13","20:00"),("2026-08-16","20:00"),
                           ("2026-08-19","20:00"),("2026-08-22","20:00")]))
        self.assertEqual(parse_detail(page("L’occasione fa il ladro",
            slots="12, 15 agosto ore 20.00, 18 agosto ore 12.00, 20 agosto, ore 20.00",
            kind="Burletta per musica"),url=OCCASIONE)[3],
            [("2026-08-12","20:00"),("2026-08-15","20:00"),
             ("2026-08-18","12:00"),("2026-08-20","20:00")])
        self.assertEqual(parse_detail(page("Il viaggio a Reims",
            slots="16, 19 agosto, ore 11.00",
            kind="Dramma giocoso"),url=VIAGGIO)[3],
            [("2026-08-16","11:00"),("2026-08-19","11:00")])
        candidate={"schema_version":1,"candidates":[{
            "id":"test-rof-scala","source_key":KEY,
            "official_url":SCALA,"status":"needs_review"}]}
        def fake(db,*,source_id,url,network_enabled):
            return FetchResult(url,page(),"a"*64,100)
        result,health=collect(candidate,{"schema_version":1,"evidence":[]},
                              network_enabled=True,fetcher=fake,
                              today=date(2026,11,22))
        self.assertEqual(health[0]["outcome"],"facts_found",health)
        rows=result["evidence"][0]["event_facts"]
        self.assertEqual(len(rows),4)
        self.assertEqual(rows[0]["starts_at"],"2026-08-13T20:00:00+02:00")
        self.assertEqual(verified_venue(KEY,rows,
                          json.loads(REGISTRY.read_text()))[:2],
                         ("Pesaro","Teatro Gioachino Rossini"))

    def test_no_scavolini_concert_missing_authority_or_wrong_year(self):
        bad=[
            (page(venue="Auditorium Scavolini"),SIEGE),
            (page(title="Concerto di belcanto",kind="Concerto"),CONCERTO),
            (page(kind="Concerto").replace("Fondazione Rossini","Fondazione Orchestrale"),SCALA),
            (page(slots="32 agosto ore 20.00"),SCALA),
            (page().replace("13, 16, 19, 22 agosto","13, 16, 19, 22 settembre"),SCALA)
        ]
        for html,url in bad:
            with self.subTest(url=url),self.assertRaises(ValueError):
                parse_detail(html,url=url)
        html=page("La scala di seta").replace("Fondazione Rossini di Pesaro",
                                                "Musica di Gioachino Rossini")
        self.assertEqual(parse_detail(html,url=SCALA.replace("2026","2028"))[3][0],
                         ("2028-08-13","20:00"))

if __name__=="__main__":
    unittest.main()

"""Official Trapani opera connector: strict genre, outdoor venue and clocks."""
import json
import unittest
from datetime import date

from opera_atlas.trapani_luglio_opera import INDEX,extract_index,parse_detail
from opera_atlas.controlled_fetch import FetchResult
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract
from scripts.collect_candidate_details import collect
from scripts.source_automation import INDEX_VENUES
from scripts.auto_catalogue import VENUE_BY_SOURCE,verified_venue
from scripts.publish_catalog_v2 import REGISTRY

KEY="trapani-luglio-musicale-2026"
NABUCCO="https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/nabucco/"
CAPULETI="https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/i-capuleti-e-i-montecchi/"
ELISIR="https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/l-elisir-d-amore/"
CONCERTO="https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/omaggio-a-lelio-luttazzi/"
def page(title="Nabucco",composer="Giuseppe Verdi",genre="Opera",venue='Teatro "Giuseppe Di Stefano"',year="2026"):
    return (f'<h1>{title}</h1><p>Homepage Eventi Stagione {year}</p>'
            f'<div>{genre}</div><p>{title}</p><p>Musica di {composer}</p>'
            '<p>Libretto di Temistocle Solera</p>'
            f'<div>{venue}</div><div>12 luglio {year}, Ore 21:00</div>'
            f'<div>{venue}</div><div>14 luglio {year}, Ore 21:00</div>'
            '<h2>Personaggi e interpreti</h2><p>Opera biografica di un altro autore</p>')
class TrapaniOfficialOperaTests(unittest.TestCase):
    def test_index_is_source_scoped_and_future_detail_pattern(self):
        j=json.loads(CONFIG.read_text())
        source=next(x for x in validate_config(j) if x["key"]==KEY)
        self.assertEqual(source["url"],INDEX)
        self.assertEqual(INDEX_VENUES[KEY],("Trapani|Teatro Giuseppe Di Stefano",))
        self.assertEqual(VENUE_BY_SOURCE[KEY],("Trapani","Teatro Giuseppe Di Stefano"))
        html="".join(f'<a href="{u}">{i}</a>' for i,u in enumerate(
            [NABUCCO,CAPULETI,ELISIR,CONCERTO]))
        self.assertEqual(extract(KEY,INDEX,html,3),sorted(
            [NABUCCO,CAPULETI,ELISIR,CONCERTO]))
        self.assertTrue(eligible(KEY,NABUCCO))
        self.assertTrue(eligible(KEY,NABUCCO.replace("2026","2027")))
        for url in (NABUCCO+"?utm_source=spam",NABUCCO.replace("https:","http:"),
                    "https://evil.invalid/it/luglio-musicale-stagioni/stagione-2026/nabucco/"):
            self.assertFalse(eligible(KEY,url))
        with self.assertRaises(ValueError):extract_index('<h1>No season</h1>',url=INDEX)

    def test_official_nabucco_two_reprises_and_idempotent_details(self):
        self.assertEqual(parse_detail(page(),url=NABUCCO),(
            "Nabucco","Giuseppe Verdi","Teatro Giuseppe Di Stefano",
            [("2026-07-12","21:00"),("2026-07-14","21:00")]))
        candidate={"schema_version":1,"candidates":[{
            "id":"test-trapani-nabucco","source_key":KEY,
            "official_url":NABUCCO,"status":"needs_review"}]}
        def fake(db,*,source_id,url,network_enabled):
            self.assertEqual(url,NABUCCO)
            return FetchResult(url,page(),"f"*64,100)
        result,health=collect(candidate,{"schema_version":1,"evidence":[]},
                              network_enabled=True,fetcher=fake,today=date(2026,11,22))
        self.assertEqual(health[0]["outcome"],"facts_found",health)
        facts=result["evidence"][0]["event_facts"]
        self.assertEqual(len(facts),2)
        self.assertEqual(facts[0]["starts_at"],"2026-07-12T21:00:00+02:00")
        registry=json.loads(REGISTRY.read_text())
        self.assertEqual(verified_venue(KEY,facts,registry)[:2],
                         ("Trapani","Teatro Giuseppe Di Stefano"))

    def test_automatic_rollover_requires_verified_next_official_season(self):
        from scripts.rollover_season_indexes import next_index,ROLLOVER_KEYS
        from scripts.discover_season_indexes import validate_config
        from scripts.season_lifecycle_health import build
        import copy
        config=json.loads(CONFIG.read_text())
        policy=json.loads(open("data/season-lifecycle-policy.json",encoding="utf-8").read())
        source=next(x for x in config["sources"] if x["key"]==KEY)
        self.assertEqual(policy["sources"][KEY]["strategy"],"verified_rollover")
        self.assertIn(KEY,ROLLOVER_KEYS)
        self.assertIsNone(next_index(source,today=date(2026,9,30)))
        next_url=next_index(source,today=date(2026,11,22))
        self.assertEqual(next_url,INDEX.replace("2026","2027"))
        advanced=copy.deepcopy(config)
        next(x for x in advanced["sources"] if x["key"]==KEY)["url"]=next_url
        validate_config(advanced)
        self.assertEqual(next_index(
            next(x for x in advanced["sources"] if x["key"]==KEY),
            today=date(2027,10,1)),
            INDEX.replace("2026","2028"))
        health=build(config,policy,{"sources":[]},{"outcomes":[]})
        result=next(x for x in health["sources"] if x["source_key"]==KEY)
        self.assertTrue(result["rollover_implemented"])
        self.assertFalse(result["future_season_verified"])

    def test_same_theatre_concert_or_other_venue_is_excluded(self):
        for html in (
            page(title="Omaggio a Luttazzi",genre="Concerto"),
            page(venue="Chiostro di San Domenico"),
            page(venue="Teatro M° Tonino Pardo"),
            page(composer=""),
            page().replace("12 luglio 2026, Ore 21:00","12 luglio 2027, Ore 21:00"),
            page().replace("12 luglio 2026, Ore 21:00","32 luglio 2026, Ore 21:00"),
        ):
            with self.subTest(html=html[:100]),self.assertRaises(ValueError):
                parse_detail(html,url=NABUCCO)
        title,composer,venue,recite=parse_detail(page(year="2028"),
            url=NABUCCO.replace("2026","2028"))
        self.assertEqual(recite,[("2028-07-12","21:00"),("2028-07-14","21:00")])

if __name__=="__main__":
    unittest.main()

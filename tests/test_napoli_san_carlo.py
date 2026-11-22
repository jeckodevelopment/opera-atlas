"""San Carlo connector: mixed genres, bot challenge and future years."""
import json
import unittest
from datetime import date
from opera_atlas.napoli_san_carlo import INDEX,extract_index,parse_detail,eligible_detail,SanCarloSecurityChallenge
from opera_atlas.controlled_fetch import FetchResult
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract,scan
from scripts.collect_candidate_details import collect
from scripts.source_automation import INDEX_VENUES
from scripts.auto_catalogue import VENUE_BY_SOURCE,verified_venue
from scripts.publish_catalog_v2 import REGISTRY

KEY="napoli-san-carlo-rolling-opera"
WORK="https://www.teatrosancarlo.it/spettacoli/luisa-miller/"
DANCE="https://www.teatrosancarlo.it/spettacoli/il-lago-dei-cigni/"
CHALLENGE="""<h1>WE'RE SO SORRY...</h1>
Your browsing looks a bit unusual. Please complete this security check."""
def page(*,genre="Opera",composer="Giuseppe Verdi",
         title="Luisa Miller",venue="Teatro di San Carlo",
         when="02/12/2026 ore 20:00"):
    return (f'<main><h1>{title}</h1><p>{genre}</p>'
            f'<p>Musica di {composer}</p><p>Libretto di Salvadore Cammarano</p>'
            f'<p>{venue}</p><p>{when}</p></main>')

class NapoliSanCarloTests(unittest.TestCase):
    def test_evergreen_official_index_and_exact_venue(self):
        source=next(x for x in validate_config(json.loads(CONFIG.read_text()))
                    if x["key"]==KEY)
        self.assertEqual(source["url"],INDEX)
        self.assertEqual(INDEX_VENUES[KEY],("Napoli|Teatro di San Carlo",))
        self.assertEqual(VENUE_BY_SOURCE[KEY],("Napoli","Teatro di San Carlo"))
        html=f'<a href="{WORK}">Opera</a><a href="{DANCE}">Balletto</a>'
        self.assertEqual(extract(KEY,INDEX,html,1),[DANCE,WORK])
        self.assertTrue(eligible(KEY,WORK))
        for bad in (WORK+"?utm=1",WORK.replace("https:","http:"),
                    WORK.replace("www.teatrosancarlo.it","evil.example"),
                    "https://www.teatrosancarlo.it/spettacoli/"):
            self.assertFalse(eligible_detail(bad))

    def test_first_party_title_composer_genre_date_and_venue(self):
        self.assertEqual(parse_detail(page(),url=WORK),
            ("Luisa Miller","Giuseppe Verdi","Teatro di San Carlo",
             [("2026-12-02","20:00")]))
        rows=parse_detail(page(when="02/12/2028 ore 20:00"),url=WORK)[3]
        self.assertEqual(rows,[("2028-12-02","20:00")])

    def test_security_challenge_concert_ballet_ambiguous_dates_fail(self):
        with self.assertRaisesRegex(ValueError,"security challenge"):
            extract_index(CHALLENGE,url=INDEX)
        with self.assertRaisesRegex(ValueError,"security challenge"):
            parse_detail(CHALLENGE,url=WORK)
        bad=[page(genre="Balletto"),
             page(genre="Concerto"),
             page(composer=""),
             page(venue="Teatro Nazionale"),
             page(when="32/12/2026 ore 20:00"),
             page(when="02/12/2026 ore 20:00 e 02/12/2026 ore 21:00")]
        for html in bad:
            with self.subTest(html=html[:100]),self.assertRaises(ValueError):
                parse_detail(html,url=WORK)

    def test_security_challenge_is_reported_as_external_access_blocker(self):
        def challenge_fetch(db,*,source_id,url,network_enabled):
            self.assertEqual(url,INDEX)
            return FetchResult(url,CHALLENGE,"a"*64,len(CHALLENGE))
        config={"schema_version":1,"sources":[{
            "key":KEY,"official_url":"https://www.teatrosancarlo.it/",
            "url":INDEX,"access_status":"approved","min_links":1}]}
        with self.assertRaises(SanCarloSecurityChallenge):
            extract_index(CHALLENGE,url=INDEX)
        _,statuses=scan(config,{"schema_version":1,"candidates":[]},
                        network_enabled=True,fetcher=challenge_fetch,
                        source_keys={KEY},now="2026-11-22T21:15:00+00:00")
        self.assertEqual(len(statuses),1)
        self.assertEqual(statuses[0]["status"],"unavailable_or_invalid")
        self.assertEqual(statuses[0]["diagnostic"],"official_anti_bot_challenge")
        self.assertEqual(statuses[0]["links"],0)

    def test_candidates_use_canonical_gate_not_generic_event_fallback(self):
        doc={"schema_version":1,"candidates":[{
            "id":"test-san-carlo-opera","source_key":KEY,
            "official_url":WORK,"status":"needs_review"}]}
        def fetch(db,*,source_id,url,network_enabled):
            self.assertEqual(url,WORK)
            return FetchResult(url,page(),"a"*64,250)
        result,health=collect(doc,{"schema_version":1,"evidence":[]},
                             network_enabled=True,fetcher=fetch,
                             today=date(2026,11,22))
        self.assertEqual(health[0]["outcome"],"facts_found",health)
        facts=result["evidence"][0]["event_facts"]
        self.assertEqual(facts[0]["starts_at"],"2026-12-02T20:00:00+01:00")
        registry=json.loads(REGISTRY.read_text())
        self.assertEqual(verified_venue(KEY,facts,registry)[:2],
                         ("Napoli","Teatro di San Carlo"))

if __name__=="__main__":
    unittest.main()

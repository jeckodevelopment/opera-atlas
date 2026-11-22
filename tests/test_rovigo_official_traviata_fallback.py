"""End-to-end official Rovigo Traviata fallback without inferred performances."""
import copy
import json
import unittest

from opera_atlas.controlled_fetch import FetchResult
from opera_atlas.rovigo_traviata_official import URL,parse_official_traviata
from scripts.discover_season_indexes import CONFIG,scan,eligible,extract
from scripts.collect_candidate_details import (
    parse_known_opera_detail,parse_source_credited_opera_detail,
)
from scripts.publish_catalog_v2 import ROOT

KEY="rovigo-sociale-opera-2026-27"
HTML="""<h1>LA TRAVIATA</h1>
<p>giovedì 21.1.27 ore 16.00 TeatroRagazzi -
venerdì 22.1.27 ore 20.30 - domenica 24.1.27 ore 16.00</p>
<h2>LA TRAVIATA</h2><p>musiche di Giuseppe Verdi</p>
<p>libretto di Francesco Maria Piave</p>
<p>Nuova produzione del Teatro Sociale di Rovigo, Teatro Mario Del Monaco.</p>"""

class RovigoTraviataFallbackTests(unittest.TestCase):
    def test_exact_public_bookings_exclude_school_session(self):
        rows=parse_official_traviata(HTML,url=URL)
        self.assertEqual(rows,[
            ("La traviata","Giuseppe Verdi","Teatro Sociale","2027-01-22","20:30"),
            ("La traviata","Giuseppe Verdi","Teatro Sociale","2027-01-24","16:00")])
        self.assertTrue(eligible(KEY,URL))
        self.assertEqual(extract(KEY,URL,HTML,1),[URL])
        registry=json.loads((ROOT/"data/identity-registry.json").read_text())
        facts=parse_known_opera_detail(KEY,URL,HTML,registry)
        self.assertEqual(len(facts),2)
        self.assertEqual(facts[0]["starts_at"],"2027-01-22T20:30:00+01:00")
        self.assertEqual(len(parse_source_credited_opera_detail(KEY,URL,HTML)),2)

    def test_legacy_invalid_index_uses_first_party_event_fallback(self):
        config=json.loads(CONFIG.read_text())
        for row in config["sources"]:
            if row["key"]!=KEY:
                row["access_status"]="blocked"
        visited=[]
        def fetcher(db,*,source_id,url,network_enabled):
            visited.append(url)
            body=(HTML if url==URL else
                  "<h1>Non è più disponibile il cartellone</h1>")
            return FetchResult(url,body,"a"*64,len(body))
        candidates,status=scan(config,{"schema_version":1,"candidates":[]},
                               fetcher=fetcher,network_enabled=True)
        info=next(x for x in status if x["key"]==KEY)
        self.assertEqual(info["status"],"success")
        self.assertEqual(info["fallback_official_source"],"comune.rovigo.it")
        self.assertEqual(info["links"],1)
        self.assertIn(URL,visited)
        self.assertEqual(len(candidates["candidates"]),1)
        self.assertEqual(candidates["candidates"][0]["official_url"],URL)

    def test_fail_closed_on_wrong_artist_dates_and_origin(self):
        for broken in (
            HTML.replace("Giuseppe Verdi","Giacomo Puccini"),
            HTML.replace("Teatro Sociale di Rovigo","Teatro Sociale di Bergamo"),
            HTML.replace("venerdì 22.1.27","sabato 22.1.27"),
            HTML.replace("domenica 24.1.27 ore 16.00",""),
            HTML.replace("TeatroRagazzi",""),
        ):
            with self.subTest(broken=broken[-55:]),self.assertRaises(ValueError):
                parse_official_traviata(broken,url=URL)
        for suffix in ("?q=1","#bad"):
            with self.assertRaises(ValueError):
                parse_official_traviata(HTML,url=URL+suffix)

if __name__=="__main__":
    unittest.main()

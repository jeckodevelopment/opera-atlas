"""End-to-end official Rovigo Traviata fallback without inferred performances."""
import copy
import json
import unittest

from opera_atlas.controlled_fetch import FetchResult, FetchUnavailable
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

    def test_identical_duplicate_schedule_in_municipal_description_is_one_event(self):
        # The real Comune social-sharing page repeats the header's calendar
        # under Descrizione before the second LA TRAVIATA composer heading.
        schedule=("giovedì 21.1.27 ore 16.00 TeatroRagazzi - "
                  "venerdì 22.1.27 ore 20.30 - domenica 24.1.27 ore 16.00")
        html=HTML.replace("<h2>LA TRAVIATA</h2>",
                          "<h2>Descrizione</h2><p>"+schedule+"</p>"
                          "<h2>LA TRAVIATA</h2>")
        rows=parse_official_traviata(html,url=URL)
        self.assertEqual([(r[3],r[4]) for r in rows],
                         [("2027-01-22","20:30"),("2027-01-24","16:00")])
        bad=html.replace("<h2>Descrizione</h2><p>"+schedule,
                         "<h2>Descrizione</h2><p>"+
                         schedule.replace("22.1.27 ore 20.30",
                                          "22.1.27 ore 21.00"))
        with self.assertRaises(ValueError):
            parse_official_traviata(bad,url=URL)

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

    def test_bounded_priority_scan_keeps_other_candidates_and_avoids_national_fetch(self):
        config=json.loads(CONFIG.read_text())
        visited=[]
        def fetcher(db,*,source_id,url,network_enabled):
            visited.append(url)
            body=(HTML if url==URL else
                  "<h1>Lo slider della stagione non è disponibile</h1>")
            return FetchResult(url,body,"b"*64,len(body))
        previous={"schema_version":1,"candidates":[{
            "id":"oa-index-other","source_key":"modena-teatro-opera-2026-27",
            "official_url":"https://www.teatrocomunalemodena.it/spettacolo/gaia-aloisi-veleno/",
            "status":"already_catalogued",
            "first_seen":"2026-11-22T10:00:00+00:00",
            "last_seen":"2026-11-22T10:00:00+00:00",
        }]}
        candidates,status=scan(config,previous,fetcher=fetcher,
                               network_enabled=True,source_keys={KEY})
        self.assertEqual(len(status),1)
        self.assertEqual(status[0]["key"],KEY)
        self.assertEqual(status[0]["status"],"success")
        self.assertEqual(len(visited),2)
        self.assertEqual(visited[1],URL)
        self.assertEqual(len(candidates["candidates"]),2)
        self.assertTrue(any(c["id"]=="oa-index-other"
                            for c in candidates["candidates"]))
        for invalid in ({"not-approved"},set()):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                scan(config,previous,fetcher=fetcher,network_enabled=True,
                     source_keys=invalid)

    def test_unavailable_season_html_still_checks_exact_official_detail(self):
        config=json.loads(CONFIG.read_text())
        seen=[]
        def fetcher(db,*,source_id,url,network_enabled):
            seen.append(url)
            if url!=URL:
                raise FetchUnavailable("page unavailable")
            return FetchResult(url,HTML,"c"*64,len(HTML))
        docs,rows=scan(config,{"schema_version":1,"candidates":[]},
                       fetcher=fetcher,network_enabled=True,
                       source_keys={KEY})
        self.assertEqual(seen[-1],URL)
        self.assertEqual(len(seen),2)
        self.assertEqual(rows[0]["status"],"success")
        self.assertEqual(rows[0]["fallback_official_source"],"comune.rovigo.it")
        self.assertEqual(docs["candidates"][0]["official_url"],URL)

    def test_fallback_failure_is_distinguished_from_obsolete_slider(self):
        config=json.loads(CONFIG.read_text())
        from opera_atlas.rovigo_traviata_official import OFFICIAL_URLS
        for problem in ("fetch","content"):
            def fetcher(db,*,source_id,url,network_enabled):
                if url not in OFFICIAL_URLS:
                    return FetchResult(url,"<h1>Non valido</h1>","d"*64,21)
                if problem=="fetch":
                    raise FetchUnavailable("page unavailable")
                return FetchResult(url,"<h1>LA TRAVIATA</h1>","e"*64,19)
            _,rows=scan(config,{"schema_version":1,"candidates":[]},
                        fetcher=fetcher,network_enabled=True,
                        source_keys={KEY})
            self.assertEqual(rows[0]["diagnostic"],
                             "rovigo_fallback_fetch_unavailable" if problem=="fetch"
                             else "rovigo_fallback_content_unverified")
            self.assertEqual(rows[0]["links"],0)

    def test_exact_municipal_event_route_rescues_empty_social_api(self):
        from opera_atlas.rovigo_traviata_official import DETAIL_URL
        from scripts.collect_candidate_details import parse_known_opera_detail
        config=json.loads(CONFIG.read_text())
        for source in config["sources"]:
            if source["key"]!=KEY:
                source["access_status"]="blocked"
        visited=[]
        def fetcher(db,*,source_id,url,network_enabled):
            visited.append(url)
            # The obsolete index and social-sharing endpoint return HTML
            # without extractable content. Only the exact event URL is valid.
            body=HTML if url==DETAIL_URL else "<html><p>Attendere</p></html>"
            return FetchResult(url,body,"a"*64,len(body))
        candidates,status=scan(
            config,{"schema_version":1,"candidates":[]},
            fetcher=fetcher,network_enabled=True,source_keys={KEY})
        self.assertEqual(status[0]["status"],"success")
        self.assertEqual(status[0]["links"],1)
        self.assertEqual(candidates["candidates"][0]["official_url"],DETAIL_URL)
        self.assertEqual(visited[-1],DETAIL_URL)
        self.assertTrue(eligible(KEY,DETAIL_URL))
        self.assertEqual(len(parse_source_credited_opera_detail(
            KEY,DETAIL_URL,HTML)),2)
        registry=json.loads((ROOT/"data/identity-registry.json").read_text())
        self.assertEqual(len(parse_known_opera_detail(
            KEY,DETAIL_URL,HTML,registry)),2)
        for spoofed in (DETAIL_URL+"?q=1",
                        DETAIL_URL.replace("www.comune.rovigo.it","evil.example")):
            self.assertFalse(eligible(KEY,spoofed))
            with self.assertRaises(ValueError):
                parse_official_traviata(HTML,url=spoofed)

    def test_both_official_endpoints_without_content_fail_closed(self):
        config=json.loads(CONFIG.read_text())
        for source in config["sources"]:
            if source["key"]!=KEY:
                source["access_status"]="blocked"
        def fetcher(db,*,source_id,url,network_enabled):
            body="<html><h1>Pagina non disponibile</h1></html>"
            return FetchResult(url,body,"b"*64,len(body))
        candidate,health=scan(
            config,{"schema_version":1,"candidates":[]},
            fetcher=fetcher,network_enabled=True,source_keys={KEY})
        self.assertEqual(candidate["candidates"],[])
        self.assertEqual(health[0]["status"],"unavailable_or_invalid")
        self.assertEqual(health[0]["diagnostic"],"rovigo_fallback_content_unverified")

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

"""Tests for the read-only national 2025/26 archive lookup."""
import unittest
from unittest.mock import patch

from scripts.audit_2026_retrospective_batch import (
    candidate_links, index_seeds, queue_historical_indexes, queue_details,
    create_report
)


class RetroBatchTests(unittest.TestCase):
    def test_rejects_external_host_and_only_discovers_grounded_links(self):
        page = """<a href="/archivio/stagione-2025-2026/">Stagione 2025/26</a>
        <a href="https://wrong.example/2026/opera/">2026</a>
        <a href="/privacy/">Privacy 2026</a>"""
        found = candidate_links(page, "https://official.example/", "https://official.example/")
        self.assertEqual(["https://official.example/archivio/stagione-2025-2026/"],
                         [x["url"] for x in found])

    def test_archive_queue_prioritizes_historical_urls(self):
        seeds = [{"source_key":"source", "seed_url":"https://official.example/",
                  "official_url":"https://official.example/", "links":[
                      {"url":"https://official.example/stagione/opera", "category":"archive_or_season_lead"},
                      {"url":"https://official.example/2025-2026", "category":"historical_year"}]}]
        queue, overflow = queue_historical_indexes(seeds)
        self.assertEqual("https://official.example/2025-2026", queue[0][1])
        self.assertEqual(0, overflow)

    def test_archive_pagination_does_not_repeat_first_batch(self):
        seeds = [{"source_key":"s","seed_url":"https://official.example/",
                  "official_url":"https://official.example/","links":[
                    {"url":f"https://official.example/2026/{n}","category":"historical_year"}
                    for n in range(7)]}]
        first, _ = queue_historical_indexes(seeds,limit=3,offset=0)
        second, remaining = queue_historical_indexes(seeds,limit=3,offset=3)
        self.assertEqual(3,len(first))
        self.assertEqual(3,len(second))
        self.assertFalse({x[1] for x in first} & {x[1] for x in second})
        self.assertEqual(1,remaining)

    def test_host_pagination_skips_first_detail_slice(self):
        source={"key":"s","official_url":"https://official.example/","access_status":"approved"}
        archives=[{"source_key":"s","archive_url":"https://official.example/2026",
                   "status":"scanned","links":[
                       {"url":f"https://official.example/2026/{n}","category":"historical_year"}
                       for n in range(30)]}]
        with patch('scripts.audit_2026_retrospective_batch.approved_hosts',
                   return_value={"official.example":[source]}), patch(
                   'scripts.audit_2026_retrospective_batch.excluded_nonopera',
                   return_value=False):
            first,_=queue_details([],archives,{},host_offset=0)
            second,_=queue_details([],archives,{},host_offset=25)
        self.assertEqual(25,len(first))
        self.assertEqual(5,len(second))
        self.assertFalse({x[1] for x in first} & {x[1] for x in second})

    def test_modena_official_wall_clock_is_scoped_and_preserves_original(self):
        from scripts.audit_2026_retrospective_batch import reconcile_verified_modena_clocks
        source={"key":"modena-teatro-opera-2026-27"}
        sample=[{"date":"2026-09-25","event_title":"La costanza trionfante",
                 "starts_at":"2026-09-25T22:30:00+02:00","venue":"Teatro Comunale Pavarotti-Freni"},
                {"date":"2026-10-03","event_title":"Kammermusik n. 2",
                 "starts_at":"2026-10-03T19:00:00+02:00","venue":"Palazzo Ducale di Sassuolo"},
                {"date":"2026-11-12","event_title":"Caterina Barbieri e Fontanamix ensemble",
                 "starts_at":"2026-11-12T22:30:00+01:00"}]
        result=reconcile_verified_modena_clocks(sample,source,
                             "https://www.teatrocomunalemodena.it/spettacoli/")
        self.assertEqual(["20:30","17:00","20:30"],
                         [x["starts_at"][11:16] for x in result])
        self.assertEqual(["+02:00","+02:00","+01:00"],
                         [x["starts_at"][-6:] for x in result])
        self.assertEqual(["2026-09-25T22:30:00+02:00", "2026-10-03T19:00:00+02:00"],
                         [x["source_original_starts_at"] for x in result[:2]])
        self.assertTrue(all(x["official_clock_evidence_url"] for x in result))
        copy=[{"date":"2026-09-25","event_title":"La costanza trionfante",
               "starts_at":"2026-09-25T22:30:00+02:00"}]
        reconcile_verified_modena_clocks(copy,{"key":"another-source"},
                                         "https://www.teatrocomunalemodena.it/spettacoli/")
        self.assertEqual("2026-09-25T22:30:00+02:00",copy[0]["starts_at"])
        reconcile_verified_modena_clocks(copy,source,"https://other.example/spettacoli/")
        self.assertEqual("2026-09-25T22:30:00+02:00",copy[0]["starts_at"])
        unknown=[{"date":"2027-09-25","event_title":"La costanza trionfante",
                  "starts_at":"2027-09-25T22:30:00+02:00"}]
        reconcile_verified_modena_clocks(unknown,source,
                                         "https://www.teatrocomunalemodena.it/spettacoli/")
        self.assertNotIn("source_original_starts_at",unknown[0])

    def test_truncated_http_response_is_unverified_in_all_three_scan_phases(self):
        from http.client import IncompleteRead
        from scripts.audit_2026_retrospective_batch import first_pass, second_pass, details_batch
        source={"key":"example-opera","official_url":"https://official.example/",
                "url":"https://official.example/2026/",
                "access_status":"approved","min_links":1}
        def broken(_source,_url):
            raise IncompleteRead(b"partial",100)
        with patch("scripts.audit_2026_retrospective_batch.validate_config",
                   return_value=[source]):
            seeds=first_pass({"sources":[source]},fetch_page=broken,workers=1)
        self.assertEqual("unverified",seeds[0]["status"])
        self.assertEqual("IncompleteRead",seeds[0]["failure"])
        self.assertEqual([],seeds[0]["links"])
        archives=second_pass([(source,"https://official.example/2026/",0,source["key"])],
                             fetch_page=broken,workers=1)
        self.assertEqual("unverified",archives[0]["status"])
        self.assertEqual("IncompleteRead",archives[0]["failure"])
        self.assertEqual([],archives[0]["event_facts"])
        details=details_batch([(source,"https://official.example/2026/macbeth",
                                "https://official.example/2026/")],
                              fetch_page=broken,workers=1)
        self.assertEqual("unverified",details[0]["status"])
        self.assertEqual("IncompleteRead",details[0]["failure"])
        self.assertEqual([],details[0]["facts"])

    def test_truncated_detail_does_not_abort_following_good_page(self):
        from http.client import IncompleteRead
        from scripts.audit_2026_retrospective_batch import details_batch
        source={"key":"example-opera","official_url":"https://official.example/"}
        def mixed(_source,url):
            if url.endswith("/broken"):
                raise IncompleteRead(b"partial")
            return ('<script type="application/ld+json">'
                    '{"@type":"MusicEvent","name":"Macbeth",'
                    '"startDate":"2026-09-25T20:30:00+02:00"}'
                    '</script>')
        result=details_batch([
            (source,"https://official.example/broken","https://official.example/2026"),
            (source,"https://official.example/good","https://official.example/2026"),
        ],fetch_page=mixed,workers=2)
        self.assertEqual(["unverified","scanned"],[x["status"] for x in result])
        self.assertEqual(1,len(result[1]["facts"]))
        self.assertEqual("Macbeth",result[1]["facts"][0]["event_title"])

    def test_unverified_source_not_claimed_complete(self):
        source = {"key":"one", "official_url":"https://official.example/",
                  "url":"https://official.example/archivio/", "access_status":"approved",
                  "min_links":1}
        config={"schema_version":1,"sources":[source]}
        venues={"venues":[{"id":"v1","name":"Teatro Esempio",
                           "city":"Torino","website":"https://official.example/"}]}
        def unavailable(_source,_url):
            from opera_atlas.controlled_fetch import FetchUnavailable
            raise FetchUnavailable("unavailable")
        with patch('scripts.audit_2026_retrospective_batch.validate_config',
                   return_value=[source]):
            report=create_report(config,venues,fetch_page=unavailable,workers=1)
        self.assertEqual(0,report["complete_seasons_certified"])
        self.assertEqual(0,report["seed_pages_scanned"])
        self.assertEqual([],report["unverified_2026_facts"])
        self.assertTrue(report["venues"][0]["has_matching_approved_host"])
        self.assertFalse(report["venues"][0]["complete_2026_calendar_verified"])


if __name__ == "__main__":
    unittest.main()

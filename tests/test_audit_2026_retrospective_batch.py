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

"""Mass archive scanner must stay bounded, source-scoped and review-only."""
import unittest
from unittest.mock import patch
from scripts.audit_2026_mass_scan import valid_official_url, clean_facts, detail_queue, index_batch


class MassScanTests(unittest.TestCase):
    def test_only_exact_approved_hostname(self):
        official = "https://www.teatro.example/"
        self.assertTrue(valid_official_url("https://www.teatro.example/opera", official))
        for url in ("http://www.teatro.example/opera",
                    "https://evil.example/opera",
                    "https://www.teatro.example.evil.test/opera",
                    "https://www.teatro.example:8443/opera"):
            self.assertFalse(valid_official_url(url, official))

    def test_no_automatic_public_confirmation(self):
        facts = clean_facts([
            {"date": "2026-01-20", "event_title": "La Cenerentola",
             "venue": "Teatro Regio", "starts_at": "2026-01-20T20:00:00+01:00"},
            {"date": "2027-01-20", "event_title": "Outside 2026"},
            {"date": "2026-02-01", "event_title": ""},
        ])
        self.assertEqual(1, len(facts))
        self.assertEqual("not_verified", facts[0]["audience"])
        self.assertEqual("not_verified", facts[0]["genre"])
        self.assertEqual("needs_independent_validation", facts[0]["review_status"])

    def test_index_failure_is_not_empty_verified_calendar(self):
        config = {"schema_version": 1, "sources": [{
            "key": "scala-season-2026-27",
            "official_url": "https://www.teatroallascala.org/",
            "url": "https://www.teatroallascala.org/it/stagione/2026-2027/index.html",
            "access_status": "approved", "min_links": 3,
        }]}
        def blocked(_source, _url):
            from opera_atlas.controlled_fetch import AccessDenied
            raise AccessDenied("robots denied")
        with patch('scripts.audit_2026_mass_scan.validate_config', return_value=config['sources']):
            results = index_batch(config, fetch_page=blocked, workers=1)
        self.assertEqual("unverified", results[0]["status"])
        self.assertEqual([], results[0]["candidate_urls"])

    def test_bounded_queue_never_crosses_official_host(self):
        config = {"schema_version": 1, "sources": [{
            "key": "scala-season-2026-27",
            "official_url": "https://www.teatroallascala.org/",
            "url": "https://www.teatroallascala.org/it/stagione/2026-2027/index.html",
            "access_status": "approved", "min_links": 3,
        }]}
        rows = [{"source_key": "scala-season-2026-27",
                 "candidate_urls": ["https://evil.example/opera"]}]
        cached = {"candidates": [{
            "source_key": "scala-season-2026-27", "status": "already_catalogued",
            "official_url": "https://evil.example/test"}]}
        with patch('scripts.audit_2026_mass_scan.validate_config', return_value=config['sources']):
            queue, overflow = detail_queue(config, rows, cached, max_pages=10)
        self.assertEqual([], queue)
        self.assertEqual([], overflow)


if __name__ == "__main__":
    unittest.main()

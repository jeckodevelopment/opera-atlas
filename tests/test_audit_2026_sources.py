"""Conservative source-lead mapping for the 2026 retrospective audit."""
import unittest
from scripts.audit_2026_sources import source_leads


class SourceLeadsTest(unittest.TestCase):
    def test_matching_host_does_not_certify_source(self):
        directory = {"venues": [
            {"id": "one", "name": "Sala A", "city": "Roma", "website": "https://theatre.example/a"},
            {"id": "two", "name": "Sala B", "city": "Roma", "website": "https://another.example/"}
        ]}
        config = {"sources": [
            {"key": "s1", "official_url": "https://www.theatre.example",
             "url": "https://theatre.example/stagione-2026"},
            {"key": "s2", "official_url": "https://not-theatre.example",
             "url": "https://not-theatre.example/2026"}
        ]}
        health = {"sources": [{"key": "s1", "status": "success"}]}
        result = source_leads(directory, config, health)
        self.assertEqual(2, result["inventory_venues"])
        self.assertEqual(2, result["configured_source_indexes"])
        lead = result["venues"][0]["source_leads"][0]
        self.assertEqual("hostname_candidate_not_verified", lead["association"])
        self.assertFalse(lead["full_2026_calendar_verified"])
        self.assertTrue(lead["year_2026_mentioned"])
        self.assertEqual("no_exact_host_candidate", result["venues"][1]["source_review_status"])
        self.assertIsNone(result["venues"][0]["2026_complete"])

    def test_same_host_for_multiple_venues_is_not_venue_proof(self):
        directory = {"venues": [
            {"id": "a", "name": "Sala 1", "website": "https://opera.example"},
            {"id": "b", "name": "Sala 2", "website": "https://opera.example"}
        ]}
        config = {"sources": [{"key": "calendar", "official_url": "https://opera.example/",
                                "url": "https://opera.example/calendar"}]}
        rows = source_leads(directory, config, {"sources": []})["venues"]
        self.assertEqual(1, len(rows[0]["source_leads"]))
        self.assertEqual(1, len(rows[1]["source_leads"]))
        self.assertFalse(rows[0]["source_leads"][0]["full_2026_calendar_verified"])


if __name__ == "__main__":
    unittest.main()

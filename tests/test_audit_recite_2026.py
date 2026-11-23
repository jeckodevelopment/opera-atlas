"""Regression tests for the read-only 2026 audit baseline."""
import unittest

from scripts.audit_recite_2026 import build


class Recite2026AuditTest(unittest.TestCase):
    def setUp(self):
        self.directory = {"venues": [
            {"id": "v1", "name": "Teatro Esempio", "city": "Torino",
             "profile_key": "Torino|Teatro Esempio"},
            {"id": "v2", "name": "Teatro Altro", "city": "Roma"},
        ]}
        self.catalog = {"productions": [
            {"venue": "Teatro Esempio", "municipality": "Torino",
             "dates": [["2026-04-01", "20:00"], ["2027-01-01", "20:00"]]}
        ]}
        self.evidence = {"evidence": [
            {"status": "verified", "event_facts": [
                {"venue": "Teatro Esempio", "date": "2026-04-01",
                 "starts_at": "2026-04-01T20:00:00+02:00"},
                {"venue": "Teatro Esempio", "date": "2026-04-03",
                 "starts_at": "2026-04-03T20:00:00+02:00"}]}
        ]}

    def test_reports_known_gap_without_certifying_completeness(self):
        result = build(self.directory, self.catalog, self.evidence, {"programs": []})
        self.assertEqual(0, result["complete_seasons_certified"])
        self.assertEqual(2, len(result["venues"]))
        april = result["venues"][0]["months"][3]
        self.assertEqual(1, april["published_known"])
        self.assertEqual(2, april["independently_observed"])
        self.assertEqual(1, april["observed_not_published"])
        self.assertEqual("known_gap", april["status"])
        self.assertEqual("not_verified_complete", result["venues"][1]["year_status"])
        self.assertFalse(april["official_full_calendar_checked"])

    def test_verified_historical_recita_is_a_diagnostic_gap_only(self):
        historic = {"records": [{
            "venue_id": "v1", "venue": "Teatro Esempio", "city": "Torino",
            "title": "La Cenerentola", "composer": "Gioachino Rossini",
            "source_url": "https://example.org/official/show",
            "source_type": "official_event_detail", "audience": "general_public",
            "dates": [{"date": "2026-01-20", "time": "20:00"}]
        }]}
        original = str(self.catalog)
        report = build(self.directory, self.catalog, self.evidence,
                       {"programs": []}, historic)
        january = report["venues"][0]["months"][0]
        self.assertEqual(1, january["observed_not_published"])
        self.assertEqual("La Cenerentola",
                         january["historical_official_candidates"][0]["title"])
        self.assertEqual(0, report["complete_seasons_certified"])
        self.assertEqual(original, str(self.catalog))

    def test_wrong_venue_rejected(self):
        bad = {"records": [{
            "venue_id": "v1", "venue": "Teatro Esempio", "city": "Napoli",
            "title": "Opera", "composer": "Compositore",
            "source_url": "https://example.org/show",
            "source_type": "official_event_detail", "audience": "general_public",
            "dates": [{"date": "2026-01-20", "time": "20:00"}]
        }]}
        with self.assertRaises(ValueError):
            build(self.directory, self.catalog, self.evidence,
                  {"programs": []}, bad)

    def test_exclusion_does_not_become_missing(self):
        self.evidence["evidence"][0]["status"] = "excluded_nonopera"
        result = build(self.directory, self.catalog, self.evidence, {"programs": []})
        self.assertEqual(0, result["venues"][0]["months"][3]["observed_not_published"])

    def test_does_not_guess_ambiguous_venue(self):
        self.directory["venues"].append({"id": "v3", "name": "Teatro Esempio", "city": "Napoli"})
        result = build(self.directory, self.catalog, self.evidence, {"programs": []})
        self.assertTrue(any(e["kind"] == "official_observation"
                            for e in result["unassigned_evidence"]))


if __name__ == "__main__":
    unittest.main()

"""Tests for source-reviewed first-half historical recite gap reporting."""
import unittest
from scripts.audit_2026_first_half_verified_gaps import audit


def production(title, clock="20:00"):
    return {"title": title, "venue": "Teatro Regio",
            "municipality": "Torino",
            "source_url": "https://official.example/detail",
            "dates": [["2026-04-02", clock]]}


def item(clock="20:00", title="Dialoghi delle carmelitane"):
    return {"title": title, "venue": "Teatro Regio", "city": "Torino",
            "source_type": "official_event_detail",
            "audience": "general_public",
            "source_url": "https://official.example/carmelitane",
            "dates": [{"date": "2026-04-02", "time": clock}]}


class HistoricalGapsTests(unittest.TestCase):
    def test_missing_reviewed_official_recita_is_not_auto_published(self):
        data = audit({"year": 2026, "records": [item()]},
                     {"productions": []}, {"venues": [{"id": "a"}]})
        self.assertEqual(data["official_match_counts"],
                         {"verified_official_recita_absent_from_catalog": 1})
        self.assertEqual(data["complete_seasons_certified"], 0)
        self.assertFalse(data["catalog_updated"])

    def test_exact_match_and_conflicting_clock_are_separate(self):
        for clock, expected in (
            ("20:00", "catalog_exact_day_time"),
            ("21:00", "catalog_day_clock_conflict"),
        ):
            with self.subTest(clock=clock):
                data = audit({"year": 2026, "records": [item(clock)]},
                             {"productions": [production("Dialoghi delle carmelitane")]},
                             {"venues": []})
                self.assertEqual(data["official_match_counts"], {expected: 1})

    def test_unreviewed_school_or_invalid_year_fails_closed(self):
        record = item()
        record["audience"] = "school_only"
        with self.assertRaises(ValueError):
            audit({"year": 2026, "records": [record]}, {"productions": []}, {"venues": []})
        record["audience"] = "general_public"
        record["dates"] = [{"date": "2027-04-02", "time": "20:00"}]
        with self.assertRaises(ValueError):
            audit({"year": 2026, "records": [record]}, {"productions": []}, {"venues": []})

    def test_duplicate_official_rows_rejected(self):
        record = item()
        with self.assertRaises(ValueError):
            audit({"year": 2026, "records": [record, record]},
                  {"productions": []}, {"venues": []})


if __name__ == "__main__":
    unittest.main()

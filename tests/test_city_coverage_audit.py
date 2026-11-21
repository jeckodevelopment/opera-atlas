"""Regression tests for the independent city coverage audit."""
import unittest
from datetime import date
from scripts.city_coverage_audit import audit


class CityAuditTests(unittest.TestCase):
    def test_never_invents_denominator_or_percentage(self):
        p = [{"id": "one", "local_date": "2026-11-22", "staging_id": "s",
              "status": "announced"}]
        stagings = [{"id": "s", "venue_id": "v"}]
        venues = [{"id": "v", "city": "Roma"}]
        season = {"sources": [{"key": "opera-roma-season-2026-27",
                               "status": "success", "links": 20}]}
        result = audit(p + p, stagings, venues, season, {}, date(2026, 11, 22))
        roma = next(x for x in result["cities"] if x["city"] == "Roma")
        self.assertEqual(roma["published_recite_in_window"], 1)
        self.assertIsNone(roma["official_total_recite"])
        self.assertIsNone(roma["coverage_percent"])
        self.assertEqual(roma["official_production_links_seen"], 20)

    def test_zero_with_successful_index_is_high_attention(self):
        result = audit([], [], [],
                       {"sources": [{"key": "opera-roma-season-2026-27",
                                     "status": "success", "links": 20}]},
                       {}, date(2026, 11, 22))
        roma = next(x for x in result["cities"] if x["city"] == "Roma")
        self.assertEqual(roma["attention"], "high")
        self.assertEqual(roma["published_recite_in_window"], 0)

    def test_window_is_inclusive_and_cancelled_excluded(self):
        dates = ["2026-11-21", "2026-11-22", "2026-12-21", "2026-12-22"]
        p = [{"id": str(i), "local_date": day, "staging_id": "s",
              "status": "announced"} for i, day in enumerate(dates)]
        p.append({"id": "cancelled", "local_date": "2026-11-25",
                  "staging_id": "s", "status": "cancelled"})
        result = audit(p, [{"id": "s", "venue_id": "v"}],
                       [{"id": "v", "city": "Torino"}], {}, {},
                       date(2026, 11, 22), 30)
        self.assertEqual(result["window_end"], "2026-12-21")
        self.assertEqual(result["cities"][0]["published_recite_in_window"], 2)


if __name__ == "__main__":
    unittest.main()

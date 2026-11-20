"""Discovery queue preserves candidates without publishing unreviewed recite."""
import copy
import unittest

from scripts.discovery_queue import reconcile


class DiscoveryQueueTests(unittest.TestCase):
    def setUp(self):
        self.config = {"schema_version": 1, "sources": [{
            "key": "opera-lombardia-calendar-2026-27",
            "adapter": "operalombardia_calendar",
            "url": "https://www.operalombardia.it/calendario/",
            "official_url": "https://www.operalombardia.it/",
            "title": "OperaLombardia calendar 2026/27",
            "composer": "Multiple canonical composers",
            "access_status": "approved",
            "approval_evidence": "Operator authorization with fresh runtime robots gate",
        }]}
        self.health = {"checked_at": "2026-11-20T20:00:00+00:00", "sources": [{
            "key": "opera-lombardia-calendar-2026-27",
            "outcome": "review_required",
            "candidates": [{
                "title": "Nuova opera", "composer": None,
                "venue": "Teatro Esempio", "city": "Como",
                "date": "2027-03-10", "time": None,
            }],
        }]}
        self.empty = {"schema_version": 1, "candidates": []}

    def test_candidate_persists_and_repeated_scan_is_idempotent(self):
        one = reconcile(self.empty, self.health, self.config)
        self.assertEqual(len(one["candidates"]), 1)
        self.assertEqual(one["candidates"][0]["status"], "needs_review")
        self.assertEqual(one["candidates"][0]["dates"], [{"date": "2027-03-10", "time": None}])
        self.assertEqual(reconcile(one, self.health, self.config), one)

    def test_additional_date_accumulates_without_new_identity(self):
        one = reconcile(self.empty, self.health, self.config)
        more = copy.deepcopy(self.health)
        more["sources"][0]["candidates"][0]["date"] = "2027-03-11"
        two = reconcile(one, more, self.config)
        self.assertEqual(len(two["candidates"]), 1)
        self.assertEqual(len(two["candidates"][0]["dates"]), 2)

    def test_blocked_source_not_accepted(self):
        config = copy.deepcopy(self.config)
        config["sources"][0]["access_status"] = "blocked"
        self.assertEqual(reconcile(self.empty, self.health, config), self.empty)

    def test_non_review_outcome_not_accepted(self):
        health = copy.deepcopy(self.health)
        health["sources"][0]["outcome"] = "unavailable_or_invalid"
        self.assertEqual(reconcile(self.empty, health, self.config), self.empty)

    def test_malformed_calendar_date_is_ignored(self):
        health = copy.deepcopy(self.health)
        health["sources"][0]["candidates"][0]["date"] = "not-a-date"
        self.assertEqual(reconcile(self.empty, health, self.config), self.empty)

    def test_resolved_entry_is_not_reopened(self):
        one = reconcile(self.empty, self.health, self.config)
        one["candidates"][0]["status"] = "resolved"
        self.assertEqual(reconcile(one, self.health, self.config), one)


if __name__ == "__main__":
    unittest.main()

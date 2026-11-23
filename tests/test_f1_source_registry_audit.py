"""F1 registry audit tests are isolated and never request network or change data."""
import unittest

from scripts.audit_source_registry import audit
from scripts.source_automation import INDEX_VENUES, DAILY_VENUES, ROOT
import json


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class SourceRegistryAuditTests(unittest.TestCase):
    def setUp(self):
        self.directory = load("data/venue-directory.json")
        self.index = load("data/season-index-config.json")
        self.daily = load("data/daily-source-config.json")
        self.health = load("data/season-index-health.json")

    def test_real_registry_invariants_and_complete_reporting(self):
        result = audit(self.directory, self.index, self.daily, self.health)
        self.assertEqual(result["venues"], len(self.directory["venues"]))
        self.assertEqual(result["index_sources"], len(self.index["sources"]))
        self.assertEqual(result["detail_sources"], len(self.daily["sources"]))
        for key in (
            "duplicate_venue_ids", "duplicate_venue_profiles",
            "duplicate_index_keys", "duplicate_detail_keys",
            "index_unknown_venue_targets", "daily_unmapped_adapters",
            "daily_unknown_venue_targets", "index_invalid_urls",
        ):
            self.assertFalse(result[key], (key, result[key]))
        # Deliberately report unmapped new season indexes; never auto-link them
        # by a shared city or festival name.
        self.assertEqual(
            result["index_missing_explicit_mapping"],
            sorted(set(s["key"] for s in self.index["sources"]) - set(INDEX_VENUES)),
        )
        self.assertEqual(
            result["index_missing_health"],
            sorted(set(s["key"] for s in self.index["sources"]) -
                   set(s["key"] for s in self.health["sources"])),
        )

    def test_unmapped_index_is_reported_not_silently_assigned(self):
        sample = {
            "sources": [{"key": "new-season-future",
                         "url": "https://example.org/calendar",
                         "official_url": "https://example.org/"}]
        }
        report = audit(
            self.directory, sample, {"sources": []}, {"sources": []},
            index_venues={}, daily_venues={},
        )
        self.assertEqual(report["index_missing_explicit_mapping"],
                         ["new-season-future"])
        self.assertEqual(report["index_missing_health"], ["new-season-future"])
        self.assertEqual(report["index_unknown_venue_targets"], [])

    def test_unknown_explicit_target_is_detected(self):
        report = audit(
            self.directory,
            {"sources": [{"key": "fake", "url": "https://example.org/",
                          "official_url": "https://example.org/"}]},
            {"sources": []},
            {"sources": [{"key": "fake"}]},
            index_venues={"fake": ("Unknown City|Unknown Theatre",)},
            daily_venues={},
        )
        self.assertEqual(report["index_unknown_venue_targets"],
                         [("fake", "Unknown City|Unknown Theatre")])

    def test_duplicate_source_identity_is_detected(self):
        config = {"sources": [{"key": "duplicated",
                               "url": "https://example.org/",
                               "official_url": "https://example.org/"}] * 2}
        result = audit(
            self.directory, config, {"sources": []}, {"sources": []},
            index_venues={}, daily_venues={},
        )
        self.assertEqual(result["duplicate_index_keys"], ["duplicated"])


if __name__ == "__main__":
    unittest.main()

"""Evidence mapping and candidate-status diagnostics must not invent venue ownership."""
import unittest
from scripts.catalogation_diagnostics import build


def venue(id, name, sources):
    return {
        "venue_id": id, "venue": name, "city": "Test city", "region": "Test",
        "sources": [{"source_key": key, "configured": True} for key in sources],
    }


class CatalogationVenueDiagnosticsTests(unittest.TestCase):
    def test_unique_source_is_attributed_and_shared_source_is_not(self):
        auto = {"venues": [
            venue("a", "Teatro A", ["a-only", "circuit"]),
            venue("b", "Teatro B", ["circuit"]),
        ]}
        candidates = {"schema_version": 1, "candidates": [
            {"id": "1", "source_key": "a-only", "status": "already_catalogued"},
            {"id": "2", "source_key": "a-only", "status": "needs_review",
             "official_url": "https://example.org/production"},
            {"id": "3", "source_key": "circuit", "status": "already_catalogued"},
            {"id": "4", "source_key": "missing-source", "status": "excluded_nonopera"},
        ]}
        details = {"checked_at": "2026-11-22T14:00:00+00:00", "outcomes": [
            {"candidate_id": "2", "outcome": "unavailable_or_unstructured",
             "reason": "no_verified_showtimes"},
        ]}
        identity = {"groups": [{"candidate_ids": ["2"]}]}
        r = build(auto, candidates, details, identity)
        a, b = r["venues"]
        self.assertEqual(a["total_attributed"], 2)
        self.assertEqual(a["states"]["already_catalogued"], 1)
        self.assertEqual(a["states"]["needs_review"], 1)
        self.assertEqual(a["pending"][0]["detail_reason"], "no_verified_showtimes")
        self.assertTrue(a["pending"][0]["identity_review"])
        self.assertEqual(b["total_attributed"], 0)
        self.assertEqual(r["excluded_from_attribution"],
                         {"already_catalogued": 1, "excluded_nonopera": 1})
        self.assertEqual(a["catalogue_identity_verification"], "not_measured")

    def test_invalid_registry_schema_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported candidate"):
            build({"venues": []}, {"schema_version": 9}, {}, {})


if __name__ == "__main__":
    unittest.main()

"""Narrow identity resolution for the San Carlo Rossini credit variant."""
import unittest

from scripts.auto_catalogue import canonicalize_san_carlo_rossini_credit


class SanCarloRossiniCreditTests(unittest.TestCase):
    def setUp(self):
        self.registry = {"works": {
            "il barbiere di siviglia|gioachino rossini": {
                "id": "oa-w-000038", "title": "Il barbiere di Siviglia",
                "composer": "Gioachino Rossini"}}}
        self.rows = [{
            "event_title": "Il barbiere di Siviglia",
            "composer": "Gioacchino Rossini", "venue": "Teatro di San Carlo",
            "date": "2027-06-16", "starts_at": "2027-06-16T20:00:00+02:00"}]

    def test_unique_canonical_credit_preserves_clock_and_venue(self):
        updated = canonicalize_san_carlo_rossini_credit(self.rows, self.registry)
        self.assertEqual(updated[0]["composer"], "Gioachino Rossini")
        self.assertEqual(updated[0]["starts_at"], self.rows[0]["starts_at"])
        self.assertEqual(updated[0]["venue"], self.rows[0]["venue"])
        self.assertEqual(self.rows[0]["composer"], "Gioacchino Rossini")

    def test_other_titles_and_venues_are_not_rewritten(self):
        for change in ({"event_title": "Il barbiere di Siviglia e la rosa"},
                       {"venue": "Teatro Comunale"},
                       {"composer": "Un altro Rossini"}):
            rows = [{**self.rows[0], **change}]
            self.assertEqual(canonicalize_san_carlo_rossini_credit(
                rows, self.registry), rows)

    def test_missing_or_ambiguous_canonical_identity_does_not_guess(self):
        self.assertEqual(canonicalize_san_carlo_rossini_credit(
            self.rows, {"works": {}}), self.rows)
        duplicate = {"works": {
            "a": dict(self.registry["works"]["il barbiere di siviglia|gioachino rossini"]),
            "b": dict(self.registry["works"]["il barbiere di siviglia|gioachino rossini"])}}
        self.assertEqual(canonicalize_san_carlo_rossini_credit(
            self.rows, duplicate), self.rows)

    def test_mixed_evidence_does_not_partially_rewrite(self):
        mixed = self.rows + [{**self.rows[0], "composer": "Gioachino Rossini"}]
        self.assertEqual(canonicalize_san_carlo_rossini_credit(
            mixed, self.registry), mixed)


if __name__ == "__main__":
    unittest.main()

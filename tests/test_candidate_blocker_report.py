"""One uncertain opera must not conceal other candidates' review outcomes."""
import unittest

from scripts.candidate_blocker_report import build


class CandidateBlockerReportTests(unittest.TestCase):
    def test_corrupted_and_verified_pending_candidates_have_separate_reasons(self):
        candidates = {"schema_version": 1, "candidates": [
            {"id": "bad", "source_key": "alpha", "official_url": "https://example.org/a",
             "status": "needs_review"},
            {"id": "ready", "source_key": "beta", "official_url": "https://example.org/b",
             "status": "needs_review"},
            {"id": "published", "source_key": "gamma", "status": "already_catalogued"}]}
        details = {"outcomes": [{"candidate_id": "bad",
                                 "outcome": "unavailable_or_unstructured",
                                 "reason": "no_verified_showtimes"}]}
        evidence = {"evidence": [{"candidate_id": "ready",
                                 "status": "needs_editorial_review"}]}
        identity = {"groups": [{"candidate_ids": ["bad"]}]}
        promotion = {"auto_skipped": [
            {"candidate_id": "bad", "reason": "unknown_or_conflicting_venue"}]}
        report = build(candidates, details, evidence, identity, promotion)
        self.assertEqual(report["candidate_count"], 2)
        self.assertEqual([p["candidate_id"] for p in report["pending"]],
                         ["bad", "ready"])
        self.assertEqual(report["pending"][0]["reasons"], [
            "identity_requires_review", "no_verified_showtimes",
            "unknown_or_conflicting_venue"])
        self.assertEqual(report["pending"][1]["reasons"],
                         ["awaiting_canonical_promotion"])
        self.assertNotIn("published", str(report))

    def test_pending_without_evidence_is_not_misreported_as_validated(self):
        result = build({"schema_version": 1, "candidates": [
            {"id": "x", "status": "needs_review", "source_key": "source"}]},
            {}, {}, {}, {})
        self.assertEqual(result["pending"][0]["reasons"],
                         ["awaiting_verified_detail"])

    def test_rejects_wrong_schema(self):
        with self.assertRaisesRegex(ValueError, "invalid candidate registry"):
            build({"schema_version": 2}, {}, {}, {}, {})


if __name__ == "__main__":
    unittest.main()

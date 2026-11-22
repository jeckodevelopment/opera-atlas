"""Only public catalog and frontend changes invalidate an in-flight browser probe."""
import unittest
from scripts.push_live_publication_audit import conflicting


class LiveAuditPushTests(unittest.TestCase):
    def test_unrelated_candidate_evidence_does_not_discard_verified_snapshot(self):
        self.assertFalse(conflicting(["data/candidate-detail-evidence.json"]))
        self.assertFalse(conflicting(["data/season-index-health.json"]))
        self.assertFalse(conflicting(["public/catalog/source-automation.json"]))

    def test_dependent_public_route_inputs_force_recheck(self):
        for name in (
            "site/detail.js",
            "site/.htaccess",
            "public/catalog/v2/manifest.json",
            "public/catalog/programs.json",
            "public/catalog/live-publication-health.json",
        ):
            self.assertTrue(conflicting([name]), name)


if __name__ == "__main__":
    unittest.main()

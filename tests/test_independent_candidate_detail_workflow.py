"""Independent early first-party source collection must never publish works."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FAST=ROOT/".github/workflows/collect-candidate-details-fast.yml"
FULL=ROOT/".github/workflows/refresh-catalog.yml"

class IndependentEvidenceWorkflowTests(unittest.TestCase):
    def test_crawl_is_bounded_robots_gated_and_not_stuck_behind_full_refresh(self):
        fast=FAST.read_text(encoding="utf-8")
        full=FULL.read_text(encoding="utf-8")
        self.assertIn("cron: '37 */3 * * *'",fast)
        self.assertIn("workflow_dispatch:",fast)
        self.assertIn("branches: [main]",fast)
        self.assertIn("timeout-minutes: 25",fast)
        self.assertIn("group: opera-atlas-official-detail-evidence",fast)
        self.assertIn("group: opera-atlas-public-feed",full)
        self.assertNotIn("cancel-in-progress: true",fast)
        self.assertIn("python -m scripts.collect_candidate_details --allow-network",fast)
        self.assertIn("python -m unittest tests.test_candidate_detail_evidence",fast)
        self.assertIn("python -m scripts.build_verified_catalog --check",fast)

    def test_only_review_evidence_can_be_pushed(self):
        fast=FAST.read_text(encoding="utf-8")
        self.assertIn("python -m scripts.safe_push_catalog",fast)
        self.assertIn("if git diff --cached --quiet",fast)
        self.assertIn("deferred == 'true'",fast)
        self.assertIn("git add data/candidate-detail-evidence.json data/candidate-detail-health.json public/catalog/candidate-detail-evidence.json",fast)
        for prohibited in (
          "git push --force","git push origin",
          "python -m scripts.auto_catalogue",
          "python -m scripts.publish_catalog_v2",
          "python -m scripts.reconcile_published_candidates",
          "git add data/identity-registry.json",
          "git add data/verified-launch-catalog.json",
          "git add site/performances.json"
        ):
            self.assertNotIn(prohibited,fast)

    def test_source_changed_triggers_are_not_created_by_writing_evidence(self):
        fast=FAST.read_text(encoding="utf-8")
        self.assertIn("      - 'data/season-index-candidates.json'",fast)
        self.assertIn("      - 'scripts/collect_candidate_details.py'",fast)
        self.assertNotIn("      - 'data/candidate-detail-evidence.json'",fast)
        self.assertNotIn("      - 'data/candidate-detail-health.json'",fast)

if __name__=="__main__":
    unittest.main()

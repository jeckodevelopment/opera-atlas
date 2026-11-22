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

    def test_workflow_has_one_retry_one_dispatch_and_no_stray_shell_fragments(self):
        fast=FAST.read_text(encoding="utf-8")
        self.assertEqual(fast.count("- name: Reacquire on latest main after concurrent changes"),1)
        self.assertEqual(fast.count("- name: Publish newly persisted official evidence through cached catalog"),1)
        self.assertEqual(fast.count("- name: Report remaining source checkpoint contention"),1)
        self.assertNotIn("\n \"$GITHUB_OUTPUT\"; then",fast)
        self.assertNotIn("\n \"$push_report\"; then",fast)

    def test_source_changed_triggers_are_not_created_by_writing_evidence(self):
        fast=FAST.read_text(encoding="utf-8")
        self.assertIn("      - 'data/season-index-candidates.json'",fast)
        self.assertIn("      - 'scripts/collect_candidate_details.py'",fast)
        self.assertNotIn("      - 'data/candidate-detail-evidence.json'",fast)
        self.assertNotIn("      - 'data/candidate-detail-health.json'",fast)

    def test_concurrent_source_updates_reacquire_from_latest_main(self):
        fast=FAST.read_text(encoding="utf-8")
        start=fast.index("- name: Reacquire on latest main after concurrent changes")
        end=fast.index("- name: Publish newly persisted official evidence through cached catalog")
        stage=fast[start:end]
        self.assertIn("if: steps.checkpoint.outputs.deferred == 'true'",stage)
        self.assertIn("for attempt in 1 2; do",stage)
        self.assertIn("git fetch origin main",stage)
        self.assertIn("git reset --hard origin/main",stage)
        self.assertLess(stage.index("git reset --hard origin/main"),
                        stage.index("python -m scripts.collect_candidate_details --allow-network"))
        self.assertIn("python -m scripts.build_verified_catalog --check",stage)
        self.assertIn("python -m scripts.safe_push_catalog",stage)
        self.assertIn('grep -q "deferred=false"',stage)
        self.assertNotIn("git push --force",stage)
        self.assertNotIn("git rebase",stage)

    def test_only_published_evidence_dispatches_existing_canonical_publisher(self):
        fast=FAST.read_text(encoding="utf-8")
        self.assertIn(
            "if: steps.checkpoint.outputs.published == 'true' || steps.retry.outputs.published == 'true'",
            fast)
        self.assertIn("event_type=cached-catalog-retry",fast)
        self.assertNotIn("event_type=catalog-refresh-retry",fast)
        self.assertIn("published=false",fast)
        self.assertIn("published=true",fast)
        source=(ROOT/".github/workflows/publish-cached-catalog.yml").read_text(encoding="utf-8")
        self.assertIn("types: [cached-catalog-retry]",source)
        self.assertIn("python -m scripts.auto_catalogue",source)
        self.assertIn("python -m scripts.reconcile_published_candidates",source)

if __name__=="__main__":
    unittest.main()

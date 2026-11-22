"""An independent source-health job must not depend on the national detail crawl."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FAST=ROOT/".github/workflows/refresh-source-health.yml"
FULL=ROOT/".github/workflows/refresh-catalog.yml"

class IndependentSourceHealthWorkflowTests(unittest.TestCase):
    def test_independent_dispatch_schedule_and_lock(self):
        health=FAST.read_text(encoding="utf-8")
        catalog=FULL.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:",health)
        self.assertIn("schedule:",health)
        self.assertIn("'data/season-index-config.json'",health)
        self.assertIn("group: opera-atlas-source-health",health)
        self.assertNotIn("group: opera-atlas-source-health",catalog)
        self.assertIn("group: opera-atlas-public-feed",catalog)
        self.assertIn("permissions:\n  contents: write",health)

    def test_scans_and_safely_publishes_diagnostics_not_recite(self):
        health=FAST.read_text(encoding="utf-8")
        self.assertIn("python -m scripts.discover_season_indexes --allow-network",health)
        self.assertIn("python -m scripts.source_automation",health)
        self.assertIn("python -m scripts.source_automation --check",health)
        self.assertIn("git add data/season-index-health.json",health)
        self.assertIn("git add public/catalog/source-automation.json",health)
        self.assertIn("python -m scripts.safe_push_catalog",health)
        self.assertIn("steps.checkpoint.outputs.deferred == 'true'",health)
        self.assertNotIn("python -m scripts.auto_catalogue",health)
        self.assertNotIn("python -m scripts.publish_catalog_v2",health)
        self.assertNotIn("git push --force",health)

if __name__=="__main__":
    unittest.main()

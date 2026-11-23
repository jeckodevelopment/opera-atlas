"""Deferred publication uses one bounded checkpoint-only recovery job."""
from pathlib import Path
import unittest

WORKFLOW=Path(__file__).resolve().parents[1]/".github/workflows/refresh-catalog.yml"

class BoundedRefreshRetryTests(unittest.TestCase):
    def test_deferred_push_does_not_dispatch_a_second_network_crawl(self):
        workflow=WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("event_type=catalog-refresh-retry",workflow)
        self.assertEqual(workflow.count("  recover_from_checkpoint:"),1)
        acquisition,recovery=workflow.split("  recover_from_checkpoint:",1)
        for checkpoint in (
            "early_national_checkpoint","cached_publication","roma_checkpoint",
            "early_season_checkpoint","source_checkpoint","publish_catalog"):
            self.assertIn("steps."+checkpoint+".outputs.deferred == 'true'",acquisition)
        self.assertIn("needs.update.result == 'failure'",recovery)
        self.assertNotIn("--allow-network",recovery)
        self.assertIn("python -m scripts.safe_push_catalog",recovery)
        self.assertIn("cancel-in-progress: false",workflow)

if __name__=="__main__":
    unittest.main()

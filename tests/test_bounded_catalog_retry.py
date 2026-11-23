"""One bounded retry per source refresh, even after many deferred pushes."""
from pathlib import Path
import unittest

WORKFLOW=Path(__file__).resolve().parents[1]/".github/workflows/refresh-catalog.yml"

class BoundedRefreshRetryTests(unittest.TestCase):
    def test_only_one_catalog_retry_dispatch_and_no_recursive_dispatch(self):
        workflow=WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(workflow.count("event_type=catalog-refresh-retry"),1)
        final=workflow.split("      - name: Retry deferred catalog once",1)[1]
        self.assertIn("github.event_name != 'repository_dispatch'",final)
        self.assertIn("GH_TOKEN:",final)
        for checkpoint in (
            "early_national_checkpoint","cached_publication","roma_checkpoint",
            "early_season_checkpoint","source_checkpoint","publish_catalog"):
            self.assertIn("steps."+checkpoint+".outputs.deferred == 'true'",final)
        # Source/canonical conflict safety stays unchanged: no stale rebase.
        self.assertIn("python -m scripts.safe_push_catalog",workflow)
        self.assertIn("cancel-in-progress: false",workflow)

if __name__=="__main__":
    unittest.main()

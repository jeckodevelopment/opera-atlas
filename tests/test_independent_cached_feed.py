"""Fast cached feed is independent of cancelable national acquisition."""
import unittest
from scripts.publish_catalog_v2 import ROOT

class CachedFeedWorkflowTests(unittest.TestCase):
    def test_independent_retry_and_no_external_network_crawl(self):
        fast=(ROOT/".github/workflows/publish-cached-catalog.yml").read_text(
            encoding="utf-8")
        slow=(ROOT/".github/workflows/refresh-catalog.yml").read_text(
            encoding="utf-8")
        self.assertIn("group: opera-atlas-cached-feed",fast)
        self.assertIn("cancel-in-progress: false",fast)
        self.assertIn("group: opera-atlas-public-feed",slow)
        self.assertIn("cancel-in-progress: false",slow)
        self.assertIn("repository_dispatch:",fast)
        self.assertIn("cached-catalog-retry",fast)
        self.assertIn("steps.commit_catalog.outputs.deferred == 'true'",fast)
        self.assertIn("python -m scripts.publish_cached_known",fast)
        for workflow in (fast,slow):
            self.assertIn("git add data/verified-launch-catalog.json",workflow)
            self.assertIn("site/work-synopses.json site/work-history.json",workflow)
        self.assertIn("python -m scripts.publish_catalog_v2 --check",fast)
        self.assertIn("python -m unittest discover -s tests -v",fast)
        self.assertIn("[skip ci]",fast)
        self.assertNotIn("--allow-network",fast)
        self.assertNotIn("sftp",fast.casefold())
        self.assertNotIn("opera-atlas-cached-feed",slow)

if __name__=="__main__":
    unittest.main()

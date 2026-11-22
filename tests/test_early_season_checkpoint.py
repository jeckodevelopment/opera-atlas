"""The national index health checkpoint must precede the slow detail backlog."""
import unittest
from pathlib import Path

WORKFLOW=Path(__file__).resolve().parents[1]/".github/workflows/refresh-catalog.yml"

class EarlySeasonIndexCheckpointTests(unittest.TestCase):
    def test_health_is_scanned_and_checkpointed_before_candidate_details(self):
        source=WORKFLOW.read_text(encoding="utf-8")
        scan=source.index("      - name: Discover approved season indexes ahead of slow details")
        checkpoint=source.index("      - name: Checkpoint current season-index status and candidate URLs")
        slow=source.index("      - name: Acquire pending official detail pages before slow discovery")
        self.assertLess(scan,checkpoint)
        self.assertLess(checkpoint,slow)
        step=source[scan:checkpoint]
        self.assertIn("python -m scripts.discover_season_indexes --allow-network",step)
        self.assertIn("python -m scripts.source_automation --check",step)
        stage=source[checkpoint:slow]
        self.assertIn("git add data/season-index-health.json",stage)
        self.assertIn("public/catalog/source-automation.json",stage)
        self.assertIn("python -m scripts.safe_push_catalog",stage)
        self.assertIn("steps.early_season_checkpoint.outputs.deferred == 'true'",stage)
        self.assertIn("catalog-refresh-retry",stage)

    def test_later_discovery_stays_for_newly_adopted_season_rollovers(self):
        source=WORKFLOW.read_text(encoding="utf-8")
        roll=source.index("python -m scripts.rollover_season_indexes --allow-network")
        later=source.index("      - name: Discover production links from approved national season indexes")
        self.assertLess(roll,later)

if __name__=="__main__":
    unittest.main()

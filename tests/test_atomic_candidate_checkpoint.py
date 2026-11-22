"""National candidate checkpoints must never publish stale review counters."""
import unittest
from pathlib import Path

WORKFLOW=Path(".github/workflows/refresh-catalog.yml")

class AtomicCandidateDiagnosticCheckpointTests(unittest.TestCase):
    def test_discovery_reconciles_before_its_checkpoint(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        first=text.index("- name: Discover approved season indexes ahead of slow details")
        checkpoint=text.index("- name: Checkpoint current season-index status and candidate URLs",first)
        block=text[first:checkpoint]
        self.assertLess(
            block.index("python -m scripts.discover_season_indexes --allow-network"),
            block.index("python -m scripts.reconcile_published_candidates"))
        self.assertLess(
            block.index("python -m scripts.reconcile_published_candidates"),
            block.index("python -m scripts.source_automation"))
        checkpoint_block=text[checkpoint:text.index("- name: Retry stale early season-index checkpoint",checkpoint)]
        self.assertIn("data/candidate-reconciliation-health.json",checkpoint_block)
        self.assertIn("data/season-index-candidates.json",checkpoint_block)

    def test_final_discovery_reconciles_before_publication(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        start=text.index("- name: Discover production links from approved national season indexes")
        end=text.index("- name: Refresh lifecycle diagnostics after index rollover",start)
        block=text[start:end]
        self.assertLess(
            block.index("python -m scripts.discover_season_indexes --allow-network"),
            block.index("python -m scripts.reconcile_published_candidates"))
        checkpoint=text.index("- name: Persist source discovery and verified detail evidence early")
        end=text.index("- name: Requeue source discovery checkpoint if main advanced",checkpoint)
        block=text[checkpoint:end]
        self.assertIn("data/candidate-reconciliation-health.json",block)
        self.assertIn("data/season-index-candidates.json",block)

if __name__=="__main__":
    unittest.main()

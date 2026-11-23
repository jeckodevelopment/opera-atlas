"""Discovery evidence must be checkpointed before expensive enrichment stages."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class SourceCheckpointWorkflowTests(unittest.TestCase):
    def test_source_diagnostics_are_persisted_before_research_and_poster(self):
        workflow=(ROOT/".github/workflows/refresh-catalog.yml").read_text(encoding="utf-8")
        collection=workflow.index("python -m scripts.collect_candidate_details --allow-network")
        checkpoint=workflow.index("id: source_checkpoint")
        research=workflow.index("python -m scripts.auto_work_research --allow-network")
        poster=workflow.index("python -m scripts.publish_work_posters --allow-network")
        self.assertLess(collection,checkpoint)
        self.assertLess(checkpoint,research)
        self.assertLess(research,poster)
        checkpoint_block=workflow[checkpoint:research]
        for file in ("data/season-index-candidates.json",
                     "data/season-index-health.json",
                     "data/candidate-detail-evidence.json",
                     "data/candidate-detail-health.json"):
            self.assertIn(file,checkpoint_block)
        self.assertIn("python -m scripts.safe_push_catalog",checkpoint_block)
        self.assertNotIn("catalog-refresh-retry",checkpoint_block)
        retry=workflow.split("      - name: Retry deferred catalog once",1)[1]
        self.assertIn("steps.source_checkpoint.outputs.deferred == 'true'",retry)
        self.assertIn("catalog-refresh-retry",retry)
        self.assertNotIn("data/verified-launch-catalog.json",checkpoint_block)
        self.assertNotIn("data/identity-registry.json",checkpoint_block)
        self.assertIn("[skip ci]",checkpoint_block)

if __name__=="__main__":
    unittest.main()

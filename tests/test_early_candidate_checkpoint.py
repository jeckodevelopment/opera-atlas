"""The full national detail backlog is checkpointed before slow source scans."""
import unittest
from pathlib import Path

WORKFLOW=Path(__file__).resolve().parents[1]/".github/workflows/refresh-catalog.yml"

class EarlyCandidateCheckpointTests(unittest.TestCase):
    def test_national_acquisition_precedes_slow_crawl(self):
        workflow=WORKFLOW.read_text(encoding="utf-8")
        roma=workflow.index("- name: Reconcile pending Roma official detail pages")
        national=workflow.index("- name: Acquire pending official detail pages before slow discovery")
        checkpoint=workflow.index("- name: Checkpoint national pending-candidate evidence and diagnostics")
        source=workflow.index("- name: Incrementally scan only explicitly approved official pages")
        self.assertLess(national,roma)
        self.assertLess(national,checkpoint)
        self.assertLess(checkpoint,source)
        self.assertIn("python -m scripts.collect_candidate_details --allow-network\n",workflow[national:checkpoint])
        self.assertIn("git add data/candidate-detail-evidence.json data/candidate-detail-health.json public/catalog/candidate-detail-evidence.json",workflow[checkpoint:source])
        self.assertIn("python -m scripts.safe_push_catalog",workflow[checkpoint:source])

    def test_early_scan_cannot_create_public_recite_without_validation(self):
        workflow=WORKFLOW.read_text(encoding="utf-8")
        start=workflow.index("- name: Acquire pending official detail pages before slow discovery")
        end=workflow.index("- name: Early publish previously verified known-opera recite")
        early=workflow[start:end]
        self.assertNotIn("auto_catalogue",early)
        self.assertNotIn("publish_catalog_v2",early)
        self.assertNotIn("site/performances.json",early)
        self.assertLess(workflow.index("- name: Validate current public catalog before acquisition"),start)
        self.assertLess(end,workflow.index("- name: Incrementally scan only explicitly approved official pages"))
        self.assertIn("if: steps.early_national_checkpoint.outputs.deferred == 'true'",early)

if __name__=="__main__":
    unittest.main()

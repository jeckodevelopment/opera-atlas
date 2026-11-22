"""Workflow must publish cached first-party works before external crawl."""
import unittest
from pathlib import Path

WORKFLOW=Path(__file__).resolve().parents[1]/".github/workflows/refresh-catalog.yml"

class EarlyVerifiedPublicationTests(unittest.TestCase):
    def test_source_verified_work_publishes_before_slow_acquisition(self):
        yml=WORKFLOW.read_text(encoding="utf-8")
        fast=yml.index("- name: Promote already verified cached works before external acquisition")
        checkpoint=yml.index("- name: Safely checkpoint fully validated early canonical work publication")
        crawl=yml.index("- name: Acquire pending official detail pages before slow discovery")
        discovery=yml.index("- name: Discover production links from approved national season indexes")
        remote_research=yml.index("- name: Resolve unseen opera identities and prepare verified short introductions")
        self.assertLess(fast,checkpoint)
        self.assertLess(checkpoint,crawl)
        self.assertLess(crawl,discovery)
        self.assertLess(discovery,remote_research)
        stage=yml[fast:checkpoint]
        required=[
          "python -m scripts.auto_catalogue",
          "python -m scripts.publish_work_posters",
          "python -m scripts.publish_programs",
          "python -m scripts.reconcile_published_candidates",
          "python -m scripts.build_verified_catalog --check",
          "python -m scripts.publish_catalog_v2 --check",
          "python -m scripts.publish_work_editorial --check",
          "python -m scripts.publish_work_posters --check",
          "python -m scripts.publish_programs --check"]
        for command in required:
            with self.subTest(command=command):
                self.assertIn(command,stage)
        self.assertLess(stage.index("python -m scripts.auto_catalogue"),
                        stage.index("python -m scripts.reconcile_published_candidates"))

    def test_checkpoint_is_derived_atomic_and_safe(self):
        yml=WORKFLOW.read_text(encoding="utf-8")
        start=yml.index("- name: Safely checkpoint fully validated early canonical work publication")
        stop=yml.index("- name: Acquire pending official detail pages before slow discovery")
        stage=yml[start:stop]
        self.assertIn("python -m scripts.safe_push_catalog",stage)
        self.assertNotIn("git push --force",stage)
        for f in ("data/identity-registry.json","data/verified-launch-catalog.json",
                  "data/candidate-reconciliation-health.json",
                  "public/catalog/v2/","public/catalog/work-posters.json"):
            with self.subTest(file=f):
                self.assertIn(f,stage)
        # Full source scan and late reconciling still run afterwards, so new
        # external discoveries cannot be falsely retired by the cached pass.
        self.assertIn("- name: Collect structured facts from bounded discovered detail pages",yml[stop:])
        self.assertIn("- name: Finalize all candidate outcomes before atomic public catalog publication",yml[stop:])

if __name__=="__main__":
    unittest.main()

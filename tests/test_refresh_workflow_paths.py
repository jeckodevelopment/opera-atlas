"""Changes to any source adapter must trigger the actual feed build."""
from pathlib import Path
import unittest

WORKFLOW=Path(__file__).resolve().parents[1]/".github"/"workflows"/"refresh-catalog.yml"

class RefreshWorkflowPathTests(unittest.TestCase):
    def test_every_adapter_and_parser_change_triggers_daily_workflow(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        for expected in ("- 'opera_atlas/**'","- 'scripts/**'","- 'tests/test_auto_catalogue.py'",
                         "- 'data/season-index-config.json'"):
            with self.subTest(pattern=expected):
                self.assertIn(expected,text)
        self.assertIn("workflow_dispatch:",text)
        self.assertIn("schedule:",text)
        self.assertIn("python -m scripts.auto_catalogue",text)
        self.assertIn("python -m scripts.publish_catalog_v2",text)
    def test_full_network_acquisition_is_labeled_and_enabled(self):
        workflow=WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("run-name: Catalog acquisition",workflow)
        self.assertIn("github.event_name",workflow)
        self.assertIn("workflow_dispatch:",workflow)
        self.assertIn("python -m scripts.discover_season_indexes --allow-network",workflow)
        self.assertIn("python -m scripts.collect_candidate_details --allow-network",workflow)
        self.assertIn("python -m scripts.auto_work_research --allow-network",workflow)
        self.assertIn("python -m scripts.reconcile_published_candidates",workflow)
        self.assertIn("python -m scripts.safe_push_catalog",workflow)

    def test_verified_editorial_seed_changes_trigger_full_publication(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        for path in ("data/verified-work-authority-seeds.json",
                     "data/verified-work-editorial-attribution.json"):
            with self.subTest(path=path):
                self.assertIn("- '"+path+"'",text)
        self.assertIn("python -m scripts.auto_catalogue",text)
        self.assertIn("python -m scripts.publish_work_editorial",text)
        self.assertIn("python -m scripts.publish_work_posters",text)
    def test_cached_publication_immediately_closes_verified_candidate_status(self):
        workflow=WORKFLOW.read_text(encoding="utf-8")
        early=workflow.split("- name: Early publish previously verified known-opera recite",1)[1]
        early=early.split("- name: Publish cached recite before slow source scans",1)[0]
        self.assertLess(early.index("python -m scripts.auto_catalogue"),
                        early.index("python -m scripts.reconcile_published_candidates"))
        self.assertLess(early.index("python -m scripts.publish_programs"),
                        early.index("python -m scripts.reconcile_published_candidates"))
        self.assertIn("git add data/season-index-candidates.json public/catalog/season-index-candidates.json data/candidate-reconciliation-health.json",workflow)
        self.assertIn("python -m scripts.reconcile_published_candidates",workflow)

    def test_catalog_git_staging_has_no_embedded_duplicate_command(self):
        workflow=WORKFLOW.read_text(encoding="utf-8")
        stage=[line.strip() for line in workflow.splitlines()
               if line.strip().startswith("git add ")]
        self.assertTrue(stage)
        for line in stage:
            with self.subTest(command=line[:60]):
                self.assertNotIn(" git add ",line)
        self.assertTrue(any("data/candidate-reconciliation-health.json" in line
                            for line in stage))
        self.assertIn("git diff --cached --quiet",workflow)
        self.assertIn("python -m scripts.safe_push_catalog",workflow)

if __name__=="__main__":
    unittest.main()

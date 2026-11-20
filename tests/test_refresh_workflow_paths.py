"""Changes to any source adapter must trigger the actual feed build."""
from pathlib import Path
import unittest

WORKFLOW=Path(__file__).resolve().parents[1]/".github"/"workflows"/"refresh-catalog.yml"

class RefreshWorkflowPathTests(unittest.TestCase):
    def test_every_adapter_and_parser_change_triggers_daily_workflow(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        for expected in ("- 'opera_atlas/**'","- 'scripts/**'","- 'tests/**'",
                         "- 'data/season-index-config.json'"):
            with self.subTest(pattern=expected):
                self.assertIn(expected,text)
        self.assertIn("workflow_dispatch:",text)
        self.assertIn("schedule:",text)
        self.assertIn("python -m scripts.auto_catalogue",text)
        self.assertIn("python -m scripts.publish_catalog_v2",text)
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
        self.assertIn("git push origin HEAD:main",workflow)

if __name__=="__main__":
    unittest.main()

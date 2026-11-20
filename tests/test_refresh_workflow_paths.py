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
if __name__=="__main__":
    unittest.main()

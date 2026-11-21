"""Cached validated new operas may publish without national network rescans."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/publish-cached-catalog.yml"

class FastCompleteOperaPublication(unittest.TestCase):
    def test_complete_editorial_and_historical_images_trigger_fast_publication(self):
        source=WORKFLOW.read_text(encoding="utf-8")
        push=source.split("  push:",1)[1].split("permissions:",1)[0]
        for expected in ("data/verified-work-authority-seeds.json",
                         "data/archival-work-images.json",
                         "data/candidate-detail-evidence.json"):
            self.assertIn(expected,push)
        self.assertIn("workflow_dispatch:",source)

    def test_same_universal_strict_work_and_image_pipeline_precedes_publication(self):
        source=WORKFLOW.read_text(encoding="utf-8")
        lines=source.splitlines()
        for token in (
            "python -m scripts.publish_cached_known",
            "python -m scripts.auto_catalogue",
            "python -m scripts.publish_work_posters",
            "python -m scripts.publish_programs",
            "python -m scripts.build_verified_catalog",
            "python -m scripts.publish_catalog_v2",
            "python -m scripts.publish_work_editorial",
            "python -m scripts.publish_work_posters --check",
            "python -m scripts.publish_programs --check",
            "python -m scripts.safe_push_catalog",
        ):
            self.assertIn(token,source)
        self.assertLess(source.index("python -m scripts.auto_catalogue"),
                        source.index("python -m scripts.build_verified_catalog"))
        self.assertLess(source.index("python -m scripts.publish_work_posters"),
                        source.index("python -m scripts.build_verified_catalog"))
        self.assertNotIn("--allow-network",source)
        for output in ("data/work-poster-evidence.json",
                       "data/work-poster-health.json",
                       "data/autonomous-catalogue-health.json",
                       "public/catalog/work-posters.json",
                       "public/catalog/programs.json"):
            self.assertIn(output,source)
        self.assertIn("cancel-in-progress: false",source)

if __name__=="__main__":
    unittest.main()

"""Official program evidence can advance ahead of a cached public program feed.

Preflight regenerates the deterministic companion from first-party facts
before validating the *entire* snapshot. Final publication still runs all
canonical checks and saves the actual public programs feed atomically.
"""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILES=(
 ".github/workflows/python-tests.yml",
 ".github/workflows/publish-cached-catalog.yml",
 ".github/workflows/refresh-catalog.yml",
)

class CompositeProgramCheckpointOrderTests(unittest.TestCase):
    def test_every_full_suite_preflight_regenerates_programs_first(self):
        for name in FILES:
            with self.subTest(workflow=name):
                yml=(ROOT/name).read_text(encoding="utf-8")
                generator=yml.index("python -m scripts.publish_programs")
                suite=yml.index("python -m unittest discover -s tests -v")
                self.assertLess(generator,suite)
                self.assertNotIn("git push --force",yml)

    def test_catalog_publishers_regenerate_v2_and_editorial_before_preflight(self):
        for name in FILES:
            with self.subTest(workflow=name):
                yml=(ROOT/name).read_text(encoding="utf-8")
                preflight=yml.split("python -m unittest discover -s tests -v",1)[0]
                self.assertIn("python -m scripts.publish_catalog_v2",preflight)
                self.assertIn("python -m scripts.publish_work_editorial",preflight)
                self.assertLess(preflight.index("python -m scripts.publish_catalog_v2"),
                                preflight.index("python -m scripts.publish_work_editorial"))
        self.assertIn("workflow_dispatch:",
                      (ROOT/FILES[2]).read_text(encoding="utf-8"))

    def test_frontend_sftp_deploy_regenerates_programs_but_does_not_upload_catalog(self):
        workflow=(ROOT/".github/workflows/deploy-atlas.yml").read_text(encoding="utf-8")
        created=workflow.index("python -m scripts.publish_programs")
        suite=workflow.index("python -m unittest discover -s tests -v")
        verified=workflow.index("python -m scripts.publish_programs --check")
        upload=workflow.index("python -u -m scripts.deploy_atlas_sftp")
        self.assertLess(created,suite)
        self.assertLess(suite,verified)
        self.assertLess(verified,upload)
        self.assertNotIn("git add public/catalog/programs.json",workflow)
        self.assertNotIn("git push --force",workflow)

    def test_cached_publisher_persists_final_program_feed_and_validates_after_promotion(self):
        yml=(ROOT/FILES[1]).read_text(encoding="utf-8")
        first=yml.index("python -m scripts.publish_programs")
        promotion=yml.index("python -m scripts.auto_catalogue")
        second=yml.index("python -m scripts.publish_programs",first+1)
        check=yml.index("python -m scripts.publish_programs --check")
        saved=yml.index("git add data/work-poster-evidence.json")
        self.assertLess(first,promotion)
        self.assertLess(promotion,second)
        self.assertLess(second,check)
        self.assertLess(check,saved)
        self.assertIn("public/catalog/programs.json",yml[saved:])

if __name__=="__main__":
    unittest.main()

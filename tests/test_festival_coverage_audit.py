"""Regression tests for the read-only festival coverage audit."""
import json
import unittest
from pathlib import Path
from scripts.festival_coverage_audit import audit

ROOT = Path(__file__).resolve().parents[1]


class FestivalCoverageAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((ROOT / "data/identity-registry.json").read_text(encoding="utf-8"))
        cls.published = json.loads((ROOT / "public/catalog/v2/festival-index.json").read_text(encoding="utf-8"))
        cls.targets = json.loads((ROOT / "data/festival-coverage-targets.json").read_text(encoding="utf-8"))

    def test_missing_targets_are_not_published_as_empty_festivals(self):
        report = audit(self.registry, self.published, self.targets)
        self.assertGreaterEqual(report["published_festivals"], 7)
        self.assertEqual({x["id"] for x in report["missing_festival_targets"]},
                         {x["id"] for x in self.targets["targets"]})
        self.assertTrue(all(x["status"] == "edition_requires_verified_staging_linkage"
                            for x in report["missing_festival_targets"]))

    def test_invalid_staging_links_are_rejected(self):
        copy = json.loads(json.dumps(self.published))
        copy["festivals"][0]["staging_ids"].append("oa-s-missing")
        with self.assertRaisesRegex(ValueError, "unknown staging ids"):
            audit(self.registry, copy, self.targets)

    def test_empty_editions_are_rejected(self):
        copy = json.loads(json.dumps(self.published))
        copy["festivals"][0]["staging_ids"] = []
        with self.assertRaisesRegex(ValueError, "empty festival edition"):
            audit(self.registry, copy, self.targets)


if __name__ == "__main__":
    unittest.main()

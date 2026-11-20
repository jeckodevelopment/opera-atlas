"""The first published catalog must match reviewed official observations."""
import json
import unittest
from pathlib import Path
from scripts.build_verified_catalog import ROOT, build, MANIFEST, OUTPUT

class VerifiedCatalogTests(unittest.TestCase):
    def test_published_catalog_is_reproducible(self):
        manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        generated=build(manifest)
        actual=json.loads(OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(generated,actual)
        self.assertGreaterEqual(len(actual["performances"]),19)
        self.assertGreaterEqual(sum(bool(e["time_known"]) for e in actual["performances"]),17)
        self.assertEqual(sum(not e["time_known"] for e in actual["performances"]),2)
        self.assertEqual(len(set(e["id"] for e in actual["performances"])),len(actual["performances"]))

    def test_no_artificial_midnight_or_source_without_evidence(self):
        events=json.loads(OUTPUT.read_text(encoding="utf-8"))["performances"]
        for event in events:
            self.assertTrue(event["sources"][0].startswith("https://"))
            self.assertTrue(event["title"] and event["venue"] and event["municipality"])
            if event["time_known"]:
                self.assertEqual(event["starts_at"][11:16], event["time_label"])
            else:
                self.assertIsNone(event["starts_at"])
                self.assertEqual(event["time_label"],"Orario da confermare")

    def test_unauthorized_page_fails_build(self):
        manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        manifest["productions"][0]["source_url"]="https://other.example/shows"
        with self.assertRaises(ValueError):
            build(manifest)

    def test_duplicate_reviewed_observation_fails_build(self):
        manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        manifest["productions"][0]["dates"].append(manifest["productions"][0]["dates"][0])
        with self.assertRaises(ValueError):
            build(manifest)

if __name__=="__main__":
    unittest.main()

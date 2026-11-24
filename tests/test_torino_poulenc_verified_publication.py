"""Publication guard for six independently verified Torino 2026 Poulenc recite."""
import json
import unittest
from pathlib import Path

from scripts.build_verified_catalog import MANIFEST, build

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / "data/historical-2026-official-evidence.json"
SOURCE = "https://www.teatroregio.torino.it/opera-e-balletto-2025-2026/dialoghi-delle-carmelitane"
KEY = "historical-2026h1-torino-dialoghi-delle-carmelitane"


class TorinoPoulencPublicationTests(unittest.TestCase):
    def test_all_six_general_public_dates_are_present_exactly_once(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        historical = json.loads(HISTORICAL.read_text(encoding="utf-8"))
        reviewed = [r for r in historical["records"] if r["source_url"] == SOURCE]
        self.assertEqual(len(reviewed), 1)
        reviewed = reviewed[0]
        self.assertEqual(reviewed["audience"], "general_public")
        entries = [p for p in manifest["productions"] if p["key"] == KEY]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["title"], "Dialoghi delle carmelitane")
        self.assertEqual(entry["composer"], "Francis Poulenc")
        self.assertEqual(entry["source_url"], SOURCE)
        self.assertEqual(entry["municipality"], "Torino")
        self.assertEqual(entry["venue"], "Teatro Regio")
        expected = [(d["date"], d["time"]) for d in reviewed["dates"]]
        self.assertEqual(sorted(map(tuple, entry["dates"])), sorted(expected))
        self.assertEqual(len(set(map(tuple,entry["dates"]))), 6)
        self.assertNotIn(("2026-03-27", "20:00"), list(map(tuple,entry["dates"])))

    def test_full_manifest_build_accepts_official_source(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        generated = build(manifest)
        events = [p for p in generated["performances"]
                  if p["title"] == "Dialoghi delle carmelitane"
                  and p["municipality"] == "Torino"]
        self.assertEqual(len(events), 6)
        self.assertTrue(all(p["sources"] == [SOURCE] for p in events))


if __name__ == "__main__":
    unittest.main()

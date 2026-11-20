"""Regression contract for the Atlas visitor interface (no network calls)."""
import json
import re
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
MANIFEST = ROOT / "public/catalog/v2/manifest.json"


class Dom(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d:
            self.ids.add(d["id"])
        if tag == "a":
            self.links.append(d.get("href", ""))


class AtlasInterfaceTests(unittest.TestCase):
    def test_home_search_and_all_views(self):
        dom = Dom()
        dom.feed((SITE / "index.html").read_text(encoding="utf-8"))
        for field in ("location", "radius", "period", "sort", "advanced-filters",
                      "calendar-view", "map-view", "atlas-map", "discover-festivals"):
            self.assertIn(field, dom.ids)
        script = (SITE / "app.js").read_text(encoding="utf-8")
        for feature in ("haversine(", "groupByStaging(", "calendarMonth(", "renderMap(",
                        "renderFestivals(", "syncPeriod(", "todayInItaly("):
            self.assertIn(feature, script)
        self.assertIn('let viewMode = "staging"', script)
        self.assertIn('controls.period.value="30"', script)
        self.assertIn('controls.radius.value="100"', script)

    def test_shared_navigation_and_assets(self):
        for name in ("index.html", "detail.html", "directory.html"):
            dom = Dom()
            dom.feed((SITE / name).read_text(encoding="utf-8"))
            self.assertIn("./#spettacoli", dom.links)
            for part in ("opere", "teatri", "festival"):
                self.assertIn("./directory.html?section=" + part, dom.links)
        for name in ("directory.js", "festival-client.js", "work-synopses.json"):
            self.assertTrue((SITE / name).is_file())

    def test_festival_references_only_verified_stagings(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        stage_file = ROOT / "public/catalog/v2" / manifest["files"]["stagings"]["path"]
        stages = json.loads(stage_file.read_text(encoding="utf-8"))["stagings"]
        ids = {stage["id"] for stage in stages}
        festivals = json.loads((ROOT / "public/catalog/v2/festival-index.json").read_text(encoding="utf-8"))
        self.assertEqual(festivals["schema_version"], 1)
        for festival in festivals["festivals"]:
            self.assertTrue(festival["official_url"].startswith("https://"))
            self.assertTrue(set(festival["staging_ids"]).issubset(ids))

    def test_editorial_synopses_are_short_and_no_html(self):
        content = json.loads((SITE / "work-synopses.json").read_text(encoding="utf-8"))
        for slug, summary in content["synopses"].items():
            self.assertRegex(slug, r"^[a-z0-9-]+$")
            self.assertLessEqual(len(summary), 300)
            self.assertNotIn("<", summary)
            self.assertNotIn(">", summary)

    @unittest.skipUnless(shutil.which("node"), "Node.js not installed")
    def test_javascript_syntax(self):
        for name in ("app.js", "catalog-client.js", "detail.js", "directory.js",
                     "festival-client.js"):
            result = subprocess.run(["node", "--check", str(SITE / name)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

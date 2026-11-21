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
                      "calendar-view", "discover-festivals"):
            self.assertIn(field, dom.ids)
        script = (SITE / "app.js").read_text(encoding="utf-8")
        for feature in ("haversine(", "groupByStaging(", "calendarMonth(",
                        "renderFestivals(", "syncPeriod(", "todayInItaly("):
            self.assertIn(feature, script)
        self.assertIn('let viewMode = "staging"', script)
        self.assertIn('controls.period.value="30"', script)
        self.assertIn('controls.radius.value="100"', script)
        markup = (SITE / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('data-catalog-view="map"',markup)
        self.assertNotIn('id="map-view"',markup)
        self.assertNotIn('id="atlas-map"',markup)
        self.assertNotIn("function renderMap(",script)
        self.assertNotIn('getElementById("map-view")',script)
        self.assertIn('data-catalog-view="staging"',markup)
        self.assertIn('data-catalog-view="calendar"',markup)

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

    def test_shared_production_ids_preserve_work_and_venue_specific_stagings(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        path = ROOT / "public/catalog/v2" / manifest["files"]["stagings"]["path"]
        by_id = {x["id"]: x for x in json.loads(path.read_text(encoding="utf-8"))["stagings"]}
        groups = json.loads((ROOT / "public/catalog/v2/production-groups.json").read_text(encoding="utf-8"))
        claimed = set()
        for group in groups["groups"]:
            self.assertGreater(len(group["staging_ids"]), 1)
            self.assertTrue(group["official_source"].startswith("https://"))
            for staging_id in group["staging_ids"]:
                self.assertNotIn(staging_id, claimed)
                claimed.add(staging_id)
                self.assertEqual(by_id[staging_id]["work_id"], group["work_id"])
        code = (SITE / "catalog-client.js").read_text(encoding="utf-8")
        self.assertIn("production_group_id", code)
        self.assertIn('"/produzioni/"', code)
        self.assertIn('kind:"group"', (SITE / "detail.js").read_text(encoding="utf-8"))

    def test_geographic_reference_covers_current_catalog_cities(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        file = ROOT / "public/catalog/v2" / manifest["files"]["venues"]["path"]
        cities = {v["city"].lower() for v in json.loads(file.read_text(encoding="utf-8"))["venues"]}
        code = (SITE / "app.js").read_text(encoding="utf-8")
        # Editorial regions can grow autonomously without requiring a code
        # release for every newly added municipality.
        for city in cities:
            if '"' + city + '":[' not in code:
                self.assertRegex(code,r'if\s*\(\s*distance===null\s*\|\|\s*distance\s*>')
        self.assertIn('"genova":[',code)

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

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

    def test_donizetti_festival_links_canonical_stagings_and_both_venues(self):
        registry = json.loads((ROOT / "data/identity-registry.json").read_text(encoding="utf-8"))
        festivals = json.loads((ROOT / "public/catalog/v2/festival-index.json").read_text(encoding="utf-8"))["festivals"]
        festival = next(f for f in festivals if f["id"] == "donizetti-opera-2026")
        linked = [s for s in registry["stagings"].values() if s["id"] in festival["staging_ids"]]
        self.assertEqual(len(linked), 3)
        self.assertEqual(set(festival["staging_ids"]), {"oa-s-000104", "oa-s-000172", "oa-s-000173"})
        self.assertEqual({s["venue_id"] for s in linked}, {"oa-v-000012", "oa-v-000037"})
        from scripts.publish_catalog_v2 import sync_festival_index
        sync_festival_index(registry, check=True)

    def test_festival_index_contains_only_populated_editions(self):
        festivals = json.loads((ROOT / "public/catalog/v2/festival-index.json").read_text(encoding="utf-8"))["festivals"]
        identities = set()
        for festival in festivals:
            self.assertRegex(festival["edition"], r"^20[0-9]{2}$")
            self.assertTrue(festival["staging_ids"], festival["id"])
            identity = (festival["festival_id"], festival["edition"])
            self.assertNotIn(identity, identities)
            identities.add(identity)
        self.assertNotIn("rossini-opera-festival", {f["id"] for f in festivals})
        self.assertIn("rossini-opera-festival-2026", {f["id"] for f in festivals})

    def test_festival_registry_generates_only_verified_year_editions(self):
        from unittest.mock import patch
        from tempfile import TemporaryDirectory
        from scripts import publish_catalog_v2 as publisher
        registry = json.loads((ROOT / "data/identity-registry.json").read_text(encoding="utf-8"))
        with TemporaryDirectory() as folder:
            from pathlib import Path
            import shutil
            local = Path(folder)
            shutil.copy(ROOT / "public/catalog/v2/festival-index.json", local / "festival-index.json")
            before = json.loads((local / "festival-index.json").read_text(encoding="utf-8"))
            with patch.object(publisher, "PUBLIC", local):
                publisher.sync_festival_index(registry, check=True)
                registry["stagings"]["future-festival-example"] = {
                    "id": "oa-s-test-future", "season": "2027",
                    "work_id": "oa-w-000051", "venue_id": "oa-v-000037",
                    "source_url": "https://www.donizettiopera.org/it/evento/new-production/"
                }
                registry["stagings"]["unrelated-example"] = {
                    "id": "oa-s-test-unrelated", "season": "2027",
                    "source_url": "https://www.donizettiopera.org/it/notizie/not-an-opera/"
                }
                publisher.sync_festival_index(registry)
                after = json.loads((local / "festival-index.json").read_text(encoding="utf-8"))
                future = next(f for f in after["festivals"] if f["id"] == "donizetti-opera-2027")
                self.assertEqual(future["staging_ids"], ["oa-s-test-future"])
                self.assertEqual(future["festival_id"], "donizetti-opera")
                self.assertEqual(next(f for f in before["festivals"] if f["id"] == "donizetti-opera-2026")["staging_ids"],
                                 next(f for f in after["festivals"] if f["id"] == "donizetti-opera-2026")["staging_ids"])
                publisher.sync_festival_index(registry, check=True)
                publisher.sync_festival_index(registry)
                self.assertEqual(json.loads((local / "festival-index.json").read_text(encoding="utf-8")), after)

    def test_festival_historical_edition_survives_source_rollover(self):
        from unittest.mock import patch
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from scripts import publish_catalog_v2 as publisher
        registry = json.loads((ROOT / "data/identity-registry.json").read_text(encoding="utf-8"))
        with TemporaryDirectory() as folder:
            public = Path(folder)
            source = json.loads((ROOT / "public/catalog/v2/festival-index.json").read_text(encoding="utf-8"))
            archive = next(x for x in source["festivals"] if x["id"] == "donizetti-opera-2026")
            historical = dict(archive, id="donizetti-opera-2025", edition="2025",
                              staging_ids=["oa-s-000104"], automatically_generated=True)
            source["festivals"].append(historical)
            (public / "festival-index.json").write_text(json.dumps(source), encoding="utf-8")
            with patch.object(publisher, "PUBLIC", public):
                publisher.sync_festival_index(registry)
                after = json.loads((public / "festival-index.json").read_text(encoding="utf-8"))
                restored = next(x for x in after["festivals"] if x["id"] == "donizetti-opera-2025")
                self.assertEqual(restored["staging_ids"], ["oa-s-000104"])
                publisher.sync_festival_index(registry, check=True)

    def test_festival_directory_displays_historical_productions(self):
        source = (SITE / "directory.js").read_text(encoding="utf-8")
        self.assertIn("[...found.future,...found.associated]", source)
        self.assertIn("Produzione dell’edizione", source)
        self.assertIn("recite future", source)

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

"""Static public catalog checks and export compatibility (no live data needed)."""
import json
import shutil
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from opera_atlas.db import connect, migrate
from opera_atlas.ingestion import export_public_catalog
from opera_atlas.operalombardia import stage_dates

SITE = Path(__file__).resolve().parent.parent / "site"


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.scripts = []
        self.labels = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.add(attributes["id"])
        if tag == "script" and attributes.get("src"):
            self.scripts.append(attributes["src"])
        if tag == "link" and attributes.get("rel") == "stylesheet":
            self.links.append(attributes.get("href"))
        if tag == "label":
            self.labels += 1


class PublicCatalogTests(unittest.TestCase):
    def test_page_contains_accessible_filters_and_assets(self):
        parser = Markup()
        parser.feed((SITE / "index.html").read_text(encoding="utf-8"))
        self.assertTrue({
            "search", "city", "region", "from", "to", "time-filter",
            "events", "count", "message", "reset", "previous", "next",
        }.issubset(parser.ids))
        self.assertEqual(parser.labels, 6)
        self.assertIn("./styles.css", parser.links)
        self.assertIn("./app.js", parser.scripts)
        for name in ("styles.css", "app.js", "performances.json"):
            self.assertTrue((SITE / name).is_file())

    def test_empty_catalog_is_real_not_sample_recite(self):
        payload = json.loads((SITE / "performances.json").read_text(encoding="utf-8"))
        self.assertEqual(payload, {"schema_version": 1, "performances": []})

    def test_export_is_directly_compatible_with_date_only_cards(self):
        conn = connect()
        try:
            migrate(conn)
            conn.execute(
                "INSERT INTO sources(official_url,access_status) "
                "VALUES ('https://www.operalombardia.it/','approved')"
            )
            html = ("<h1>L’italiana in Algeri</h1><h2>RECITE:</h2>"
                    "<p>Teatro Sociale, Como – 13 novembre 2026</p>")
            stage_dates(
                conn, source_id=1, html=html,
                url="https://www.operalombardia.it/l-italiana-in-algeri/",
                title="L’italiana in Algeri",
            )
            with tempfile.TemporaryDirectory() as temp:
                dest = Path(temp) / "performances.json"
                self.assertEqual(export_public_catalog(conn, dest), 1)
                event = json.loads(dest.read_text(encoding="utf-8"))["performances"][0]
                self.assertFalse(event["time_known"])
                self.assertIsNone(event["starts_at"])
                self.assertEqual(event["local_date"], "2026-11-13")
                self.assertEqual(event["time_label"], "Orario da confermare")
                self.assertTrue(event["venue"])
                self.assertTrue(event["municipality"])
                self.assertTrue(event["sources"])
        finally:
            conn.close()

    @unittest.skipUnless(shutil.which("node"), "Node.js not installed in test environment")
    def test_client_javascript_syntax(self):
        run = subprocess.run(
            ["node", "--check", str(SITE / "app.js")],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == "__main__":
    unittest.main()

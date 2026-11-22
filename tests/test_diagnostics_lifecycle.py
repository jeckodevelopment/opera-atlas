"""Checks for the compact, process-first Atlas diagnostics lifecycle view."""
import unittest
from pathlib import Path
from html.parser import HTMLParser

PAGE = Path(__file__).resolve().parents[1] / "diagnostics/index.html"


class Ids(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])


class DiagnosticsLifecycleTests(unittest.TestCase):
    def test_dashboard_groups_process_and_advanced_details(self):
        text = PAGE.read_text(encoding="utf-8")
        parser = Ids()
        parser.feed(text)
        self.assertTrue({
            "phases", "issues", "venues", "scan-stats", "catalog-stats",
            "publish-stats", "indexes", "lifecycle", "freshness",
        }.issubset(parser.ids))
        self.assertIn("public/catalog/season-lifecycle.json", text)
        self.assertIn('<details class="accordion">', text)
        self.assertIn("Scansione delle fonti", text)
        self.assertIn("Acquisizione e catalogazione", text)
        self.assertIn("Pubblicazione", text)

    def test_future_season_readiness_is_not_mislabeled_complete(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('if(key==="lifecycle")return null', text)
        self.assertIn('lifecycle.future_seasons_verified', text)
        self.assertIn('lifecycle.legacy_year_bound', text)
        self.assertIn("non equivale alla copertura dell'intera stagione", text)
        self.assertIn("non certifica l'intera stagione", text)
        self.assertIn("non disponibili", text)


if __name__ == "__main__":
    unittest.main()

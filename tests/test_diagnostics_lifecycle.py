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

    def test_legacy_successor_table_is_explicit_not_a_second_endless_list(self):
        text=PAGE.read_text(encoding="utf-8")
        self.assertIn("legacy_covered_by_successor",text)
        self.assertIn("legacy_still_uncovered",text)
        self.assertIn("successor_source_key",text)
        self.assertIn("Storico · successore implementato",text)
        self.assertIn("Ancora senza successore",text)
        self.assertIn("indici ancora senza successore",text)
        self.assertIn("<th>Copertura stagioni future</th>",text)
        self.assertIn('<details class="accordion">',text)

    def test_evergreen_scope_is_not_confused_with_future_verified(self):
        text=PAGE.read_text(encoding="utf-8")
        self.assertIn("evergreen_dynamic_category",text)
        self.assertIn("evergreen_fixed_production_set",text)
        self.assertIn("evergreen_historical_notice",text)
        self.assertIn("Titoli fissati · non pluriennale",text)
        self.assertIn("Documento storico · non pluriennale",text)
        self.assertIn("futuro da verificare",text)

    def test_live_audit_freshness_exists_in_render_scope(self):
        text = PAGE.read_text(encoding="utf-8")
        script = text.split("<script>", 1)[1].split("</script>", 1)[0]
        render = script.split("function render(){", 1)[1].split("function refresh()", 1)[0]
        self.assertIn("const auditCurrent=", render)
        self.assertLess(render.index("const auditCurrent="),
                        render.index("const liveTotals="))
        self.assertIn("const auditCurrent=", script.split("function build(){", 1)[1].split("function render(){", 1)[0])

    def test_future_season_readiness_is_not_mislabeled_complete(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('if(["lifecycle","catalogation","evidence","live"].includes(key))return null', text)
        self.assertIn('lifecycle.future_seasons_verified', text)
        self.assertIn('lifecycle.legacy_year_bound', text)
        self.assertIn("non equivale alla copertura dell'intera stagione", text)
        self.assertIn("non una verifica completa di ogni stagione", text)
        self.assertIn("non disponibili", text)


if __name__ == "__main__":
    unittest.main()

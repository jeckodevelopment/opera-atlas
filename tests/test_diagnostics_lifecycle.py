"""Contract tests for the editorial-first Atlas governance dashboard."""
import unittest
from pathlib import Path
from html.parser import HTMLParser

PAGE = Path(__file__).resolve().parents[1] / "diagnostics/index.html"

class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.tabs = []
        self.buttons = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if "id" in props:
            self.ids.add(props["id"])
        if props.get("data-tab"):
            self.tabs.append(props["data-tab"])
        if props.get("data-goto"):
            self.buttons.append(props["data-goto"])

class DiagnosticsLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PAGE.read_text(encoding="utf-8")
        cls.dom = Markup()
        cls.dom.feed(cls.source)

    def test_five_focus_areas_are_navigable(self):
        expected = {"overview", "venues", "catalog", "activity", "tech"}
        self.assertEqual(set(self.dom.tabs), expected)
        self.assertTrue({"view-" + x for x in expected}.issubset(self.dom.ids))
        self.assertTrue(set(self.dom.buttons).issubset(expected))
        self.assertIn('aria-selected="true"', self.source)
        self.assertIn("function tab(name)", self.source)

    def test_sources_are_canonical_and_separately_validated(self):
        for feed in (
            "source-automation.json", "recite-coverage.json",
            "catalogation-diagnostics.json", "candidate-publication-evidence.json",
            "live-publication-health.json", "pipeline-operations-health.json",
        ):
            self.assertIn(feed, self.source)
        self.assertIn("Promise.allSettled", self.source)
        self.assertIn("Caricamento incompleto", self.source)
        self.assertIn("catalog_release_sha256", self.source)

    def test_editorial_and_technical_states_are_not_conflated(self):
        for label in (
            "Candidate in revisione", "Recite individuate non ancora pubblicate",
            "Workflow che richiedono attenzione", "Copertura assoluta della stagione",
            "non certifica la completezza", "Escluse non pertinenti",
        ):
            self.assertIn(label, self.source)
        self.assertIn('type:"editorial"', self.source)
        self.assertIn('type:"technical"', self.source)
        self.assertIn('type:"publication"', self.source)

    def test_venue_details_and_filters_exist(self):
        for item in ("venue-search", "venue-filter", "venue-rows", "catalog-venues", "activity-list", "workflow-rows"):
            self.assertIn(item, self.dom.ids)
        self.assertIn('aria-expanded', self.source)
        self.assertIn("last_attempt_at", self.source)
        self.assertIn("failure_reason", self.source)

    def test_null_city_and_venue_labels_are_safe_for_sorting(self):
        # Directory and recite records may legitimately omit these labels.
        self.assertIn('String(a.city??"").localeCompare(String(b.city??""),"it")', self.source)
        self.assertIn('String(a.venue??"").localeCompare(String(b.venue??""),"it")', self.source)
        self.assertNotIn('a.city.localeCompare(b.city', self.source)

    def test_venue_inventory_distinguishes_missing_registry_from_absent_connector(self):
        self.assertIn('"torino|teatro regio":"torino|teatro regio di torino"', self.source)
        self.assertIn('"savona|teatro chiabrera":"savona|teatro gabriello chiabrera"', self.source)
        self.assertIn("canonicalVenueKey", self.source)
        self.assertIn('status:"not_in_inventory"', self.source)
        self.assertIn('v.status==="not_in_inventory"?"Da censire":"Senza connettore"', self.source)
        self.assertIn("Sedi pubblicate assenti dall’inventario tecnico", self.source)

    def test_no_false_global_completion_percentage(self):
        self.assertIn("non garantisce", self.source)
        self.assertIn("Non misurato", self.source)
        self.assertIn("Non equivale", self.source)
        self.assertNotIn("100% copertura nazionale", self.source)

if __name__ == "__main__":
    unittest.main()

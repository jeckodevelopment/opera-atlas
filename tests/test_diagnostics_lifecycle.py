"""Diagnostics must expose lifecycle status without confusing readiness with coverage."""
import unittest
from pathlib import Path
from html.parser import HTMLParser

PAGE=Path(__file__).resolve().parents[1]/"diagnostics/index.html"

class Ids(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set()
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if "id" in attrs:self.ids.add(attrs["id"])

class DiagnosticsLifecycleTests(unittest.TestCase):
    def test_dashboard_loads_readiness_feed_and_gracefully_handles_absence(self):
        text=PAGE.read_text(encoding="utf-8")
        parser=Ids()
        parser.feed(text)
        self.assertTrue({"lifecycle-rows","season-lifecycle-metrics",
                         "lifecycle-filter","lifecycle-strategy",
                         "lifecycle-updated"}.issubset(parser.ids))
        self.assertIn("public/catalog/season-lifecycle.json",text)
        self.assertIn("latest.lifecycle=await fetchJson(urls.lifecycle).catch(()=>null)",text)
        self.assertIn("Feed delle stagioni non ancora disponibile",text)

    def test_rollover_capability_never_masquerades_as_verified_future(self):
        text=PAGE.read_text(encoding="utf-8")
        self.assertIn('x.next_season_status==="verified"',text)
        self.assertIn('x.strategy==="verified_rollover"',text)
        self.assertIn("Link futuri",text)
        self.assertIn("non equivalgono a recite pubblicate",text)
        self.assertIn('lifecycle.legacy_year_bound',text)

if __name__=="__main__":
    unittest.main()

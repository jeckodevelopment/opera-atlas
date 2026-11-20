"""Opera Atlas historical work facts and shared calendar-card CTA regression."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"

class OperaHistoryTests(unittest.TestCase):
    def test_historical_coverage_matches_canonical_works(self):
        manifest=json.loads((ROOT/"public/catalog/v2/manifest.json").read_text(encoding="utf-8"))
        works=json.loads((ROOT/"public/catalog/v2"/manifest["files"]["works"]["path"]).read_text(encoding="utf-8"))["works"]
        history=json.loads((SITE/"work-history.json").read_text(encoding="utf-8"))
        self.assertEqual(history["schema_version"],1)
        self.assertTrue(set(item["slug"] for item in works).issubset(set(history["works"])))
        for slug,entry in history["works"].items():
            self.assertTrue(entry["librettist"],slug)
            self.assertTrue(1600<=entry["premiere_year"]<=2026,slug)
            self.assertTrue(entry["premiere_venue"] and entry["premiere_city"],slug)
            self.assertTrue(entry["sources"],slug)
            self.assertTrue(all(url.startswith("https://") for url in entry["sources"]),slug)
            self.assertTrue("composition_year" not in entry or entry["composition_year"]<=entry["premiere_year"],slug)

    def test_production_summaries_and_historical_render(self):
        js=(SITE/"detail.js").read_text(encoding="utf-8")
        self.assertIn("async function appendHistory(event)",js)
        self.assertIn('["Libretto",history.librettist]',js)
        self.assertIn('["Composizione",Number.isInteger(history.composition_year)',js)
        self.assertIn('["Prima rappresentazione",Number.isInteger(history.premiere_year)',js)
        self.assertIn('["Teatro della prima",history.premiere_venue]',js)
        self.assertIn('["Città della prima",history.premiere_city]',js)
        self.assertEqual(js.count("await appendSynopsis(first);"),3) # opera, shared production, individual production
        self.assertIn('await appendHistory(first);',js)
        self.assertIn('results.after(references)',js)

    def test_calendar_card_link_anchoring(self):
        css=(SITE/"styles.css").read_text(encoding="utf-8")
        detail=(SITE/"detail.js").read_text(encoding="utf-8")
        self.assertIn('link("Scopri la produzione",window.OperaAtlasCatalog.urls(first).production,"detail-link staging-action")',detail)
        self.assertIn(".detail-related .staging-group>.staging-action{display:flex;",css)
        self.assertIn("margin-top:auto;border-top:1px solid #dfd9cd;",css)
        self.assertIn(".event-main>.detail-link{display:block;",css)
        self.assertNotIn("align-self:stretch;min-height:100%;height:100%",css)

    @unittest.skipUnless(shutil.which("node"),"Node not available")
    def test_dynamic_opera_metadata(self):
        r=subprocess.run(["node",str(ROOT/"tests/work_history_smoke.cjs")],
                         cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+"\n"+r.stderr)

if __name__=="__main__":
    unittest.main()

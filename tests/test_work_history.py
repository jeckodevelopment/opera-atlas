"""Opera Atlas historical work facts and shared calendar-card CTA regression."""
import json
import re
import shutil
import subprocess
import unittest
from urllib.parse import urlsplit
from scripts.discover_season_indexes import CONFIG,validate_config,eligible
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"

class OperaHistoryTests(unittest.TestCase):
    def test_historical_coverage_matches_canonical_works(self):
        manifest=json.loads((ROOT/"public/catalog/v2/manifest.json").read_text(encoding="utf-8"))
        works=json.loads((ROOT/"public/catalog/v2"/manifest["files"]["works"]["path"]).read_text(encoding="utf-8"))["works"]
        history=json.loads((SITE/"work-history.json").read_text(encoding="utf-8"))
        self.assertEqual(history["schema_version"],1)
        registry=json.loads((ROOT/"data/identity-registry.json").read_text(encoding="utf-8"))
        canonical_by_id={w["id"]:w for w in list(registry["works"].values())+list(registry["reserved_works"].values())}
        approved=[x for x in validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
                  if x["access_status"]=="approved"]
        import re
        for item in works:
            historical=history.get("works_by_id",{}).get(item["id"],
                         history["works"].get(item["slug"]))
            if historical is not None:continue
            if item["id"] in {w["id"] for w in registry["reserved_works"].values()}:
                # Verified program-only works have their authoritative
                # source-backed history in the published editorial feed.
                doc=json.loads((ROOT/"public/catalog/work-editorial.json").read_text(encoding="utf-8"))
                profile=next((w for w in doc["works"] if w["work_id"]==item["id"]),None)
                from scripts.publish_work_editorial import validate_history
                self.assertIsNotNone(profile)
                self.assertTrue(validate_history(profile["history"]))
                continue
            # A verified identity without known premiere information is
            # permitted. Never invent a history for a newly sourced opera.
            canonical=canonical_by_id[item["id"]]
            wikidata=canonical.get("wikidata_id","")
            official=canonical.get("authority_url","")
            staged=[v for v in registry["stagings"].values()
                    if v["work_id"]==item["id"]]
            official_verified=bool(official and any(
                v.get("source_url")==official for v in staged) and any(
                urlsplit(source["official_url"]).hostname==urlsplit(official).hostname
                and eligible(source["key"],official) for source in approved))
            self.assertTrue(bool(re.fullmatch(r"Q[1-9][0-9]*",wikidata))
                            or official_verified,item["title"])
        for slug,entry in history["works"].items():
            self.assertTrue(entry["librettist"],slug)
            # A verified opera announced for the coming seasons can be
            # a genuine world premiere; its first performance is not
            # constrained to the year this test was originally written.
            self.assertTrue(1600<=entry["premiere_year"]<=__import__("datetime").date.today().year+3,slug)
            self.assertTrue(entry["premiere_venue"] and entry["premiere_city"],slug)
            self.assertTrue(entry["sources"],slug)
            self.assertTrue(all(url.startswith("https://") for url in entry["sources"]),slug)
            self.assertTrue("composition_year" not in entry or entry["composition_year"]<=entry["premiere_year"],slug)

    def test_production_summaries_and_historical_render(self):
        js=(SITE/"detail.js").read_text(encoding="utf-8")
        self.assertIn("async function appendHistory(event)",js)
        self.assertIn('const librettists=String(history.librettist||"").trim()',js)
        self.assertIn('Number.isInteger(history.composition_year)',js)
        self.assertIn('Number.isInteger(history.premiere_year)',js)
        self.assertIn('String(history.premiere_venue||"").trim()',js)
        self.assertIn('String(history.premiere_city||"").trim()',js)
        self.assertIn('const beginning=futurePremiere?"La prima assoluta è prevista ":"La prima rappresentazione ebbe luogo ";',js)
        self.assertIn('history.premiere_date>todayISO',js)
        self.assertIn('beginning+when+" al "+place',js)
        self.assertIn('history.premiere_date',js)
        self.assertIn('node("p","work-history-story",historyParts.join(" "))',js)
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

"""Approved Atlas homepage counts, small dates, and festival visual hierarchy."""
import unittest
from pathlib import Path
import subprocess
import shutil

SITE=Path(__file__).resolve().parents[1]/"site"
class AtlasHomeRefinementTests(unittest.TestCase):
    def test_small_calendars_and_dynamic_count(self):
        js=(SITE/"app.js").read_text()
        css=(SITE/"styles.css").read_text()
        self.assertIn("function compactDate(event)",js)
        self.assertIn('node("div","home-calendar-list")',js)
        self.assertIn('const productionCount=groupByStaging(filtered).length;',js)
        self.assertIn('" in scena vicino a te"',js)
        self.assertIn(".home-calendar{width:53px",css)
        self.assertIn(".home-calendar-more",css)
    def test_festival_band_and_theatre_titles(self):
        css=(SITE/"styles.css").read_text()
        self.assertIn("#festival::before",css)
        self.assertIn("background:linear-gradient(115deg,#18242a",css)
        self.assertIn(".detail-related .theatre-production h3 a{font:inherit!important",css)
        self.assertIn(".detail-related .theatre-production .mini-calendar{min-height:68px",css)
        self.assertIn(".mini-calendar{appearance:none",css) # original production sizing intact
    def test_summary_fallback_and_home_discovery(self):
        home=(SITE/"app.js").read_text()
        directory=(SITE/"directory.js").read_text()
        self.assertIn("loadWorkDescriptions()",home)
        self.assertIn('workDescriptions[event.work_slug]||""',home)
        self.assertIn('node("span","discovery-description",description)',home)
        self.assertIn('https://raw.githubusercontent.com/jeckodevelopment/opera-atlas/main/site/',directory)
    def test_curated_repertoire_is_in_requested_order(self):
        import re
        home=(SITE/"app.js").read_text(encoding="utf-8")
        block=home.split("const HOME_REPERTOIRE_IDS=Object.freeze([",1)[1].split("]);",1)[0]
        ids=re.findall(r'"(oa-w-\d{6})"',block)
        self.assertEqual(ids,[
            "oa-w-000026", # Rigoletto
            "oa-w-000015", # Aida
            "oa-w-000023", # Don Giovanni
            "oa-w-000031", # Norma
            "oa-w-000022", # Tosca
            "oa-w-000021"  # Lucia di Lammermoor
        ])
        self.assertIn("for(const id of HOME_REPERTOIRE_IDS)",home)
        self.assertNotIn("[...works].sort",home)

    @unittest.skipUnless(shutil.which("node"),"Node.js unavailable")
    def test_distinct_archival_works_not_fictional_primary_poster(self):
        result=subprocess.run(["node",str(SITE.parent/"tests/image_client_smoke.cjs")],
          capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+"\n"+result.stderr)
if __name__=="__main__":
    unittest.main()

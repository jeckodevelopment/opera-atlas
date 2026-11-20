"""Privacy contact and the approved work/theatre detail layout."""
import unittest
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

SITE=Path(__file__).resolve().parents[1]/"site"

class DetailPolishTests(unittest.TestCase):
    def test_privacy_contact_without_street_address(self):
        privacy=(SITE/"privacy.html").read_text(encoding="utf-8")
        self.assertIn("Associazione Opera+",privacy)
        self.assertIn("97925160018",privacy)
        self.assertIn("operaplus@pec.it",privacy)
        self.assertIn("mailto:info@opera.plus",privacy)
        self.assertNotIn("via Federico Patetta",privacy)
        self.assertNotIn("10155",privacy)

    def test_work_overview_uses_vertical_poster_and_side_by_side_intro(self):
        js=(SITE/"detail.js").read_text(encoding="utf-8")
        css=(SITE/"styles.css").read_text(encoding="utf-8")
        self.assertIn('function arrangeWorkOverview(event)',js)
        self.assertIn('layout.append(copy,figure)',js)
        self.assertIn('if(selected.kind==="work")arrangeWorkOverview(first)',js)
        self.assertIn('poster.className="work-cover-image"',js)
        self.assertIn('.work-overview{display:grid;grid-template-columns:',css)
        self.assertIn('.work-cover-image{display:block;',css)
        self.assertIn('object-fit:contain',css)
        self.assertIn('.work-overview{grid-template-columns:minmax(0,1fr)',css)

    def test_production_and_touring_posters_are_portrait_uncropped(self):
        js=(SITE/"detail.js").read_text(encoding="utf-8")
        css=(SITE/"styles.css").read_text(encoding="utf-8")
        self.assertIn('selected.kind==="staging" || selected.kind==="group"',js)
        self.assertIn('poster.className="production-cover-image"',js)
        self.assertIn('content.classList.add("production-detail")',js)
        self.assertIn('.production-cover-image{display:block;',css)
        self.assertIn('aspect-ratio:3/4;object-fit:contain;',css)
        self.assertIn('.production-cover-figure{float:none;',css)
        self.assertIn('if(selected.kind==="work")arrangeWorkOverview(first)',js)
        self.assertIn('results.append(dateSelector(future))',js)

    def test_theatre_calendar_action_bottom_with_separator(self):
        js=(SITE/"detail.js").read_text(encoding="utf-8")
        css=(SITE/"styles.css").read_text(encoding="utf-8")
        self.assertIn('section.append(dateSelector(events))',js)
        self.assertIn('link("Scopri la produzione"',js)
        self.assertIn('.detail-related .theatre-production{display:flex;flex-direction:column;',css)
        self.assertIn('.detail-related .theatre-production .date-picker-section{display:flex;flex-direction:column;flex:1 0 auto}',css)
        self.assertIn('.detail-related .theatre-production > .detail-link{display:inline-flex;',css)
        self.assertIn('border-top:1px solid #dfd9cd;margin-top:auto;',css)
        self.assertIn('.detail-related .theatre-production .mini-calendar{min-height:68px',css)

    @unittest.skipUnless(shutil.which("node"),"Node.js not installed")
    def test_detail_js_syntax(self):
        r=subprocess.run(["node","--check",str(SITE/"detail.js")],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)

if __name__=="__main__":
    unittest.main()

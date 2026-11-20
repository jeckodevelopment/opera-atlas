"""Production mini-date calendar interaction and differentiated imagery."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"

class MiniCalendarTests(unittest.TestCase):
    def test_calendar_component_wired_in_production_and_theatre_views(self):
        js=(SITE/"detail.js").read_text()
        css=(SITE/"styles.css").read_text()
        self.assertIn('function miniDateParts(day)',js)
        self.assertIn('function dateSelector(events)',js)
        self.assertIn('results.append(dateSelector(future))',js)
        self.assertIn('section.append(dateSelector(events))',js)
        self.assertIn('button.setAttribute("aria-pressed","false")',js)
        self.assertIn('.mini-calendar-list{display:grid',css)
        self.assertIn('.theatre-production h3{font-size:27px',css)
        self.assertNotIn('function replicaLine(e)',js)
    @unittest.skipUnless(shutil.which("node"),"Node.js not available")
    def test_calendar_selects_dates_and_displays_time(self):
        r=subprocess.run(["node",str(ROOT/"tests/mini_calendars_smoke.cjs")],
                         cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+"\n"+r.stderr)
    @unittest.skipUnless(shutil.which("node"),"Node.js not available")
    def test_image_mapping_and_local_fallback(self):
        r=subprocess.run(["node",str(ROOT/"tests/image_client_smoke.cjs")],
                         cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+"\n"+r.stderr)

if __name__=="__main__":
    unittest.main()

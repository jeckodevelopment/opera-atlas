"""Homepage map should remain useful with narrow filters and no data."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"

class HomeMapTests(unittest.TestCase):
    def test_adaptive_map_viewport_and_no_results(self):
        script=(SITE/"app.js").read_text(encoding="utf-8")
        self.assertIn('Math.max(300,maxX-minX+160)',script)
        self.assertIn('svg.setAttribute("viewBox"',script)
        self.assertIn('Nessun teatro corrisponde ai filtri attuali.',script)
        self.assertIn('location',script)
        self.assertIn('aria-label',script)
        self.assertIn('venueLinks.append(link)',script)
        self.assertIn('holder.append(svg)',script)
        self.assertIn('holder.append(caption)',script)
        self.assertNotIn('svg.setAttribute("viewBox","0 0 720 690")',script)
        css=(SITE/"styles.css").read_text(encoding="utf-8")
        self.assertIn('.map-empty{',css)
        self.assertIn('.map-caption{',css)

    @unittest.skipUnless(shutil.which("node"),"Node.js not available")
    def test_rendering_and_interaction_smoke(self):
        process=subprocess.run(["node",str(ROOT/"tests/home_map_smoke.cjs")],
            cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(process.returncode,0,process.stdout+"\n"+process.stderr)

if __name__=="__main__":
    unittest.main()

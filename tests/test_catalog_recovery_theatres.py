"""Catalog fallback, theatre coverage and visitor-link regressions."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"

class RecoveryTheatreTests(unittest.TestCase):
    def test_all_canonical_theatres_have_editorial_profiles(self):
        manifest=json.loads((ROOT/"public/catalog/v2/manifest.json").read_text())
        venues=json.loads((ROOT/"public/catalog/v2"/manifest["files"]["venues"]["path"]).read_text())["venues"]
        profiles=json.loads((SITE/"theatre-profiles.json").read_text())["venues"]
        self.assertGreaterEqual(len(venues),14)
        for venue in venues:
            key=venue["city"]+"|"+venue["name"]
            self.assertIn(key,profiles)
            p=profiles[key]
            self.assertTrue(p["address"])
            self.assertLessEqual(len(p["description"]),260)
            self.assertTrue(p["website"].startswith("https://"))
    def test_image_failure_does_not_hide_catalog(self):
        for filename in ("app.js","directory.js","detail.js"):
            code=(SITE/filename).read_text()
            self.assertIn("image-placeholder",code)
            self.assertIn("console.",code)
        detail=(SITE/"detail.js").read_text()
        self.assertIn('sourceLinks(selected.events,selected.kind,theatreProfile)',detail)
        self.assertIn('if(kind==="work")return;',detail)
        self.assertNotIn('"Fonte ufficiale"',detail)
        self.assertIn("appendTheatreProfile(first)",detail)
    @unittest.skipUnless(shutil.which("node"),"Node.js not available")
    def test_catalog_fetch_endpoints_and_fallback(self):
        result=subprocess.run(["node",str(ROOT/"tests/catalog_resilience_smoke.cjs")],
                              cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+"\n"+result.stderr)
    @unittest.skipUnless(shutil.which("node"),"Node.js not available")
    def test_javascript_syntax(self):
        for name in ("app.js","directory.js","detail.js","catalog-client.js"):
            result=subprocess.run(["node","--check",str(SITE/name)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,name+": "+result.stderr)

if __name__=="__main__":
    unittest.main()

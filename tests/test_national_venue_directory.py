"""Independent national theatre census and no-event venue route guarantees."""
import copy
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from scripts.publish_venue_directory import SOURCE,OUTPUT,CANONICAL,build,publish

ROOT=Path(__file__).resolve().parents[1]

class NationalVenueDirectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=json.loads(SOURCE.read_text(encoding="utf-8"))
        cls.registry=json.loads(CANONICAL.read_text(encoding="utf-8"))
        cls.result=build(cls.source,cls.registry)

    def test_complete_independent_directory_is_publishable(self):
        self.assertGreaterEqual(len(self.result["venues"]),50)
        self.assertGreaterEqual(len(self.result["related_organizations"]),12)
        self.assertEqual(len({v["id"] for v in self.result["venues"]}),len(self.result["venues"]))
        self.assertEqual(len({v["city_slug"]+"/"+v["slug"] for v in self.result["venues"]}),len(self.result["venues"]))
        self.assertEqual(len({v["region"] for v in self.result["venues"]}),16)
        self.assertEqual(publish(check=True)["venues"],self.result["venues"])

    def test_original_performance_venues_are_preserved(self):
        venues={v["id"]:v for v in self.result["venues"]}
        for canonical in self.registry["venues"].values():
            venue=venues[canonical["id"]]
            self.assertEqual(venue["slug"],canonical["slug"])
            self.assertEqual(venue["city_slug"],canonical["city_slug"])
        self.assertEqual(venues["oa-v-000001"]["name"],"Teatro Regio di Torino")

    def test_missing_festival_organizer_is_not_misrepresented_as_a_theatre(self):
        titles={v["name"] for v in self.result["venues"]}
        for name in ("OperaLombardia","Fondazione Haydn di Bolzano e Trento",
                     "Festival Verdi","Rossini Opera Festival","Festival della Valle d'Itria"):
            self.assertNotIn(name,titles)
        self.assertIn("Arena Sferisterio",titles)
        self.assertIn("Teatro Carlo Felice",titles)
        self.assertIn("Teatro Lirico di Cagliari",titles)
        self.assertIn("Teatro Petruzzelli",titles)

    def test_invalid_or_colliding_venues_fail_closed(self):
        duplicate=copy.deepcopy(self.source)
        duplicate["venues"].append(copy.deepcopy(duplicate["venues"][-1]))
        with self.assertRaisesRegex(ValueError,"duplicate"):
            build(duplicate,self.registry)
        bad=copy.deepcopy(self.source)
        bad["venues"][-1]["source_url"]="http://unsupported.example"
        with self.assertRaisesRegex(ValueError,"HTTPS"):
            build(bad,self.registry)

    def test_static_frontend_resolves_venues_even_without_performances(self):
        directory=(ROOT/"site/directory.js").read_text(encoding="utf-8")
        detail=(ROOT/"site/detail.js").read_text(encoding="utf-8")
        client=(ROOT/"site/catalog-client.js").read_text(encoding="utf-8")
        self.assertIn("const national=await window.OperaAtlasCatalog.venues()",directory)
        self.assertIn("for(const venue of national)",directory)
        self.assertIn("const venues=await window.OperaAtlasCatalog.venues()",detail)
        self.assertIn('selected.kind==="venue" && selected.venue',detail)
        self.assertIn('venueRecord.source_url',detail)
        self.assertIn('public/catalog/venue-directory.json',client)
        htaccess=(ROOT/"site/.htaccess").read_text(encoding="utf-8")
        self.assertIn("[a-z0-9-]+/[a-z0-9-]+",htaccess)

    @unittest.skipUnless(shutil.which("node"),"Node.js unavailable")
    def test_browser_client_syntax(self):
        for f in ("site/catalog-client.js","site/directory.js","site/detail.js","site/image-client.js"):
            result=subprocess.run(["node","--check",str(ROOT/f)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,f+" "+result.stderr)

if __name__=="__main__":
    unittest.main()

"""Editorial coverage and public-facing festival language."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"

class AtlasDescriptionsTests(unittest.TestCase):
    def test_all_canonical_works_have_synopsis(self):
        manifest=json.loads((ROOT/"public/catalog/v2/manifest.json").read_text())
        works=json.loads((ROOT/"public/catalog/v2"/manifest["files"]["works"]["path"]).read_text())["works"]
        editorial=json.loads((ROOT/"public/catalog/work-editorial.json").read_text())
        by_id={w["work_id"]:w["synopsis"] for w in editorial["works"]}
        self.assertTrue(works)
        for work in works:
            self.assertIn(work["id"],by_id,work["title"])
            self.assertTrue(35<=len(by_id[work["id"]])<=300)
    def test_festivals_have_editorial_description_not_internal_audit(self):
        festivals=json.loads((ROOT/"public/catalog/v2/festival-index.json").read_text())["festivals"]
        self.assertTrue(festivals)
        for festival in festivals:
            self.assertGreater(len(festival["description"]),60)
            self.assertNotIn("Fonte ufficiale",festival["description"])
            self.assertNotIn("note",festival)
        source=(SITE/"directory.js").read_text()
        self.assertNotIn("x.note",source)
        self.assertIn('node("p","directory-description",item.description)',source)
    def test_all_theatres_have_brief_profiles(self):
        venues=json.loads((SITE/"theatre-profiles.json").read_text())["venues"]
        self.assertGreaterEqual(len(venues),52)
        for item in venues.values():
            self.assertGreater(len(item["description"]),40)
            self.assertLessEqual(len(item["description"]),260)

if __name__=="__main__":
    unittest.main()

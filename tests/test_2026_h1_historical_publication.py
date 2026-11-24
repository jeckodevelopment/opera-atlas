"""Historical 2026 H1 recite: immutable, source-scoped canonical publication."""
import copy
import json
import unittest
from scripts.build_verified_catalog import MANIFEST, approved_historical_h1, build
from scripts.publish_catalog_v2 import REGISTRY, assemble


class HistoricalH1PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.approved=approved_historical_h1()

    def test_exact_57_dated_showtimes_and_stable_ids(self):
        self.assertEqual(8,len(self.approved))
        records=[p for p in self.manifest["productions"] if p["source_url"] in self.approved]
        self.assertEqual(8,len(records))
        self.assertEqual(57,sum(len(p["dates"]) for p in records))
        self.assertEqual(57,sum(len(a["dates"]) for a in self.approved.values()))
        canonical=assemble(self.manifest,self.registry)
        published=[p for p in canonical["performances"]
                   if p["source_url"] in self.approved]
        self.assertEqual(57,len(published))
        self.assertEqual(57,len({p["id"] for p in published}))
        self.assertTrue(all(p["time_known"] and p["starts_at"]
                            for p in published))

    def test_reject_changed_venue_title_or_time(self):
        for field,replacement in (("title","La traviata"),("venue","Teatro Inventato")):
            manifest=copy.deepcopy(self.manifest)
            p=next(p for p in manifest["productions"] if p["source_url"] in self.approved)
            p[field]=replacement
            with self.assertRaises(ValueError):
                build(manifest)
        manifest=copy.deepcopy(self.manifest)
        p=next(p for p in manifest["productions"] if p["source_url"] in self.approved)
        p["dates"][0][1]="22:30"
        with self.assertRaises(ValueError):
            build(manifest)

    def test_nabucodonosor_is_explicit_alias_only(self):
        rows=[x for x in self.approved.values()
              if x["official_source_title"]!=x["canonical_title"]]
        self.assertEqual(1,len(rows))
        self.assertEqual(("Nabucco","Nabucodonosor","Giuseppe Verdi"),
                         (rows[0]["canonical_title"],rows[0]["official_source_title"],
                          rows[0]["composer"]))
        self.assertEqual(9,len(rows[0]["dates"]))

    def test_existing_2027_routes_remain_unchanged(self):
        fenice=[s for s in self.registry["stagings"].values()
                if s["source_url"] in self.approved
                and s["source_url"].startswith("https://www.teatrolafenice.it/")
                and s["slug"]=="carmen"]
        self.assertEqual(1,len(fenice))
        self.assertEqual("carmen-2025-2026",fenice[0]["route_slug"])
        self.assertIn("fenice-carmen-2027",self.registry["stagings"])


if __name__=="__main__":
    unittest.main()

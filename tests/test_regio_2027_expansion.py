"""Official 2026/27 Regio expansion: Edgar and Salome are new unique staged productions."""
import json
import unittest
from scripts.build_verified_catalog import MANIFEST, build
from scripts.publish_catalog_v2 import REGISTRY, assemble, release_parts

EDGAR = [
    ("2027-01-22","20:00"),("2027-01-26","20:00"),("2027-01-28","20:00"),
    ("2027-01-30","15:00"),("2027-02-02","15:00"),("2027-02-04","20:00"),
    ("2027-02-06","15:00"),
]
SALOME = [
    ("2027-04-02","20:00"),("2027-04-06","20:00"),("2027-04-09","20:00"),
    ("2027-04-11","15:00"),("2027-04-14","20:00"),("2027-04-17","15:00"),
]


class RegioExpandedCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_each_verified_page_has_only_explicit_replicas(self):
        by_key={p["key"]:p for p in self.facts["productions"]}
        self.assertEqual(by_key["regio-edgar-2027"]["dates"],[list(x) for x in EDGAR])
        self.assertEqual(by_key["regio-salome-2027"]["dates"],[list(x) for x in SALOME])
        self.assertTrue(by_key["regio-edgar-2027"]["source_url"].endswith("/edgar"))
        self.assertTrue(by_key["regio-salome-2027"]["source_url"].endswith("/salome"))
        self.assertEqual(len(self.facts["productions"]),18)

    def test_new_stagings_and_replica_ids_are_stable(self):
        graph=assemble(self.facts,self.registry)
        self.assertEqual(len(graph["works"]),13)
        self.assertEqual(len(graph["venues"]),5)
        self.assertEqual(len(graph["stagings"]),18)
        self.assertEqual(len(graph["performances"]),91)
        self.assertEqual(graph["performances"][-1]["starts_at"],"2027-06-29T20:00:00+02:00")
        self.assertEqual(self.registry["stagings"]["regio-edgar-2027"]["id"],"oa-s-000006")
        self.assertEqual(self.registry["stagings"]["regio-salome-2027"]["id"],"oa-s-000007")
        self.assertEqual(self.registry["performances"]["regio-salome-2027|2027-04-17"]["id"],"oa-r-000032")
        for key in ("regio-edgar-2027","regio-salome-2027"):
            self.assertEqual(self.registry["stagings"][key]["venue_id"],"oa-v-000001")
        paths={s["url"] for s in graph["stagings"]}
        self.assertIn("/torino/teatro-regio/edgar/", paths)
        self.assertIn("/torino/teatro-regio/salome/", paths)

    def test_old_ids_and_missing_time_states_unchanged(self):
        graph=assemble(self.facts,self.registry)
        originals=[r for r in graph["performances"] if int(r["id"].split("-")[-1])<=19]
        self.assertEqual(len(originals),19)
        self.assertEqual(sum(not e["time_known"] for e in graph["performances"]),2)
        self.assertEqual(sum(e["time_known"] for e in graph["performances"]),89)
        self.assertEqual(len({e["id"] for e in graph["performances"]}),91)
        _,manifest=release_parts(self.facts,self.registry)
        self.assertEqual(manifest["files"]["performances"]["count"],91)


if __name__=="__main__":
    unittest.main()

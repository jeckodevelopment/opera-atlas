"""The complete verified main-stage Regio opera set for season 2026/27.

The official season includes ballets and an oratorio; they are not added as
operas. Paired Cavalleria/Pagliacci use different canonical work IDs while
retaining the same official performance dates.
"""
import json
import unittest
from scripts.build_verified_catalog import MANIFEST, build
from scripts.publish_catalog_v2 import REGISTRY, assemble

EXPECT = {
    "regio-cavalleria-rusticana-2026":9,
    "regio-pagliacci-2026":9,
    "regio-boheme-leoncavallo-2026":6,
    "regio-iris-2026":7,
    "regio-edgar-2027":7,
    "regio-traviata-2027":11,
    "regio-salome-2027":6,
    "regio-carmen-2027":11,
    "regio-evgenij-onegin-2027":7,
}


class RegioSeasonCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.ids=json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_mainstage_opera_productions_have_explicit_dates(self):
        found={p["key"]:p for p in self.facts["productions"]
               if p["key"].startswith("regio-")}
        self.assertEqual({k:len(p["dates"]) for k,p in found.items()},EXPECT)
        self.assertTrue(all(p["composer"] and p["dates"] and
                         all(hour is not None for _,hour in p["dates"])
                         for p in found.values()))
        self.assertFalse(any("schiaccianoci" in k or "ballet" in k or
                             "juditha" in k for k in found))

    def test_double_bill_replica_dates_belong_to_distinct_works(self):
        main={p["key"]:p for p in self.facts["productions"]}
        left=main["regio-cavalleria-rusticana-2026"]
        right=main["regio-pagliacci-2026"]
        self.assertEqual(left["dates"],right["dates"])
        self.assertNotEqual(
            self.ids["stagings"][left["key"]]["work_id"],
            self.ids["stagings"][right["key"]]["work_id"]
        )

    def test_real_local_offsets_across_dst_october_2026(self):
        events={e["id"]:e for e in build(self.facts)["performances"]}
        self.assertEqual(events["curated:regio-boheme-leoncavallo-2026:2026-10-23"]["starts_at"],
                         "2026-10-23T20:00:00+02:00")
        self.assertEqual(events["curated:regio-boheme-leoncavallo-2026:2026-10-31"]["starts_at"],
                         "2026-10-31T15:00:00+01:00")

    def test_catalog_ids_and_all_nine_routes(self):
        graph=assemble(self.facts,self.ids)
        self.assertEqual(len(graph["performances"]),131)
        self.assertEqual(len(graph["works"]),19)
        self.assertEqual(len(graph["venues"]),10)
        self.assertEqual(len(graph["stagings"]),24)
        routes={x["url"] for x in graph["stagings"]}
        for p in self.facts["productions"]:
            if p["key"] in EXPECT:
                self.assertIn("/torino/teatro-regio/"+
                              self.ids["works"][
                                p["title"].casefold()+"|"+p["composer"].casefold()
                              ]["slug"]+"/",routes)

if __name__=="__main__":
    unittest.main()

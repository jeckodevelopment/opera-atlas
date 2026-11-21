"""The official OperaLombardia public calendar supplies date/venue, not hour.

The 2026/27 index contains 38 recite in 19 newly recognized stagings.
No midnight or guessed 20:00 should ever enter the public feed.
"""
import json
import unittest
from scripts.build_verified_catalog import MANIFEST, build
from scripts.publish_catalog_v2 import REGISTRY, assemble

SOURCE="https://www.operalombardia.it/calendario/"
EXPECTED={
 "turandot": {"como","cremona","brescia","novara","bergamo"},
 "death-venice": {"brescia","como","reggio-emilia","cremona","ravenna"},
 "cavalleria": {"como","brescia","cremona"},
 "pagliacci": {"como","brescia","cremona"},
 "ballo": {"cremona","como","bergamo"},
}

class OperaLombardiaFullCalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    def test_official_calendar_new_stagings_are_date_only(self):
        products={p["key"]:p for p in self.facts["productions"]}
        count=0
        for title,cities in EXPECTED.items():
            for city in cities:
                p=products["lombardia-"+title+"-"+city]
                self.assertEqual(p["source_url"],SOURCE)
                self.assertEqual(len(p["dates"]),2)
                self.assertTrue(all(clock is None for _,clock in p["dates"]))
                self.assertEqual(len({day for day,_ in p["dates"]}),2)
                count+=2
        self.assertEqual(count,38)
    def test_new_partners_venues_and_staging_links(self):
        graph=assemble(self.facts,self.registry)
        self.assertEqual(len(graph["performances"]),sum(len(p["dates"]) for p in self.facts["productions"]))
        self.assertGreaterEqual(len(graph["works"]),22)
        self.assertGreaterEqual(len(graph["venues"]),14)
        self.assertGreaterEqual(len(graph["stagings"]),48)
        # Previously unknown OperaLombardia hours may become verified from a
        # second official theatre page without altering the circuit source.
        self.assertLessEqual(sum(not r["time_known"] for r in graph["performances"]),40)
        self.assertEqual(len({r["id"] for r in graph["performances"]}),len(graph["performances"]))
        places={v["city"] for v in graph["venues"]}
        self.assertTrue({"Bergamo","Novara","Reggio Emilia","Ravenna"}.issubset(places))
        self.assertIn("/novara/teatro-coccia/turandot/",{s["url"] for s in graph["stagings"]})
        self.assertIn("/ravenna/teatro-dante-alighieri/death-in-venice/",
                      {s["url"] for s in graph["stagings"]})
    def test_original_stable_ids_and_unknown_hours_are_preserved(self):
        events={e["id"]:e for e in build(self.facts)["performances"]}
        self.assertEqual(events["curated:lombardia-turandot-como:2026-09-24"]["starts_at"],None)
        self.assertEqual(events["curated:lombardia-death-venice-ravenna:2027-02-14"]["time_label"],
                         "Orario da confermare")
        self.assertEqual(self.registry["performances"]["regio-traviata-2027|2027-02-26"]["id"],
                         "oa-r-000001")
        self.assertEqual(self.registry["performances"]["lombardia-italiana-pavia|2026-11-20"]["id"],
                         "oa-r-000014")
    def test_no_fake_clock_for_circuit_recita(self):
        graph=assemble(self.facts,self.registry)
        for r in graph["performances"]:
            if r["sources"][0]==SOURCE:
                if len(r["sources"])==1:
                    self.assertIsNone(r["starts_at"])
                    self.assertFalse(r["time_known"])
                else:
                    self.assertTrue(r["time_known"])
                    self.assertIsNotNone(r["starts_at"])
                    self.assertTrue(all(x.startswith("https://") for x in r["sources"]))

if __name__=="__main__":
    unittest.main()

"""Editorial verification contract for five new sources at Venezia and Palermo."""
import json
import unittest
from scripts.build_verified_catalog import MANIFEST, build
from scripts.publish_catalog_v2 import REGISTRY, assemble, release_parts

OFFICIAL = {
 "fenice-jenufa-2027": ("https://www.teatrolafenice.it/event/jenufa/", 5),
 "fenice-madama-butterfly-2027": ("https://www.teatrolafenice.it/event/madamabutterflycallegari/", 9),
 "fenice-carmen-2027": ("https://www.teatrolafenice.it/event/carmenaxelrod/", 8),
 "massimo-lucia-lammermoor-2027": ("https://www.teatromassimo.it/event/lucia-di-lammermoor-2/", 8),
 "massimo-tosca-2027": ("https://www.teatromassimo.it/event/tosca-2/", 9),
}

class FiveOfficialStagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.ids=json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_full_verified_counts_and_provenance(self):
        stages={p["key"]:p for p in self.facts["productions"]}
        self.assertEqual(sum(len(stages[k]["dates"]) for k in OFFICIAL),39)
        for key,(url,count) in OFFICIAL.items():
            p=stages[key]
            self.assertEqual(p["source_url"],url)
            self.assertEqual(len(p["dates"]),count)
            self.assertTrue(all(hour is not None for _,hour in p["dates"]))
            self.assertEqual(len({d for d,_ in p["dates"]}),count)
        graph=assemble(self.facts,self.ids)
        self.assertTrue(all(len(graph[k])>=v for k,v in {"works":22,"venues":10,"stagings":29,"performances":170}.items()))
        self.assertGreaterEqual(sum(not p["time_known"] for p in graph["performances"]),2)
        self.assertEqual(len({p["id"] for p in graph["performances"]}),len(graph["performances"]))
        self.assertTrue(all(p["sources"] for p in graph["performances"]))
        _,manifest=release_parts(self.facts,self.ids)
        self.assertEqual(manifest["files"]["performances"]["count"],len(graph["performances"]))

    def test_expected_replica_examples_and_italian_dst(self):
        data={e["id"]:e for e in build(self.facts)["performances"]}
        for key,day,clock in [
            ("fenice-jenufa-2027","2027-03-14","15:30"),
            ("fenice-carmen-2027","2027-05-02","15:30"),
            ("massimo-lucia-lammermoor-2027","2027-03-09","18:30"),
            ("massimo-tosca-2027","2027-04-24","18:30"),
        ]:
            e=data["curated:"+key+":"+day]
            self.assertTrue(e["time_known"])
            self.assertEqual(e["time_label"],clock)
            self.assertEqual(e["starts_at"][-6:],"+02:00" if day >= "2027-03-28" else "+01:00")

    def test_earlier_identifiers_are_unchanged(self):
        self.assertEqual(self.ids["performances"]["regio-traviata-2027|2027-02-26"]["id"],"oa-r-000001")
        self.assertEqual(self.ids["stagings"]["fenice-fedora-2026"]["venue_id"],"oa-v-000008")
        self.assertEqual(self.ids["stagings"]["fenice-jenufa-2027"]["venue_id"],"oa-v-000008")
        self.assertEqual(self.ids["stagings"]["massimo-lucia-lammermoor-2027"]["venue_id"],"oa-v-000009")
        self.assertEqual(self.ids["works"]["carmen|georges bizet"]["id"],"oa-w-000009")
        self.assertEqual(self.ids["works"]["madama butterfly|giacomo puccini"]["id"],"oa-w-000019")

if __name__=="__main__":
    unittest.main()

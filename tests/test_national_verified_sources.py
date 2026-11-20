"""Source-based national expansion and explicit cancelled-show exclusion."""
import json
import unittest
from scripts.build_verified_catalog import MANIFEST, build
from scripts.publish_catalog_v2 import REGISTRY, assemble

class NationalSourceExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.by_key={x["key"]:x for x in cls.facts["productions"]}

    def test_verified_six_productions_with_exact_counts(self):
        expected={
            "scala-otello-2026":9,
            "arena-aida-de-bosio-2027":9,
            "fenice-fedora-2026":7,
            "massimo-samson-dalila-2026":6,
            "massimo-macbeth-2027":5,
            "parma-madama-butterfly-2027":4,
        }
        for key,count in expected.items():
            self.assertEqual(len(self.by_key[key]["dates"]),count)
            self.assertTrue(all(hour is not None for _,hour in self.by_key[key]["dates"]))
            self.assertTrue(self.by_key[key]["source_url"].startswith("https://"))
        self.assertEqual(sum(expected.values()),40)

    def test_cancelled_fedora_premiere_not_published(self):
        dates=dict(self.by_key["fenice-fedora-2026"]["dates"])
        self.assertNotIn("2026-11-13",dates)
        self.assertEqual(dates["2026-11-14"],"15:30")
        self.assertEqual(dates["2026-11-22"],"15:30")

    def test_no_rehearsals_silently_catalogued_as_parma_performance(self):
        dates=dict(self.by_key["parma-madama-butterfly-2027"]["dates"])
        self.assertEqual(set(dates),{
            "2027-04-16","2027-04-18","2027-04-22","2027-04-24"})
        self.assertNotIn("2027-04-12",dates)
        self.assertNotIn("2027-04-14",dates)

    def test_distinct_staging_urls_and_continuous_ids(self):
        graph=assemble(self.facts,self.registry)
        self.assertEqual(len(graph["performances"]),sum(len(p["dates"]) for p in self.facts["productions"]))
        self.assertGreaterEqual(len(graph["works"]),19)
        self.assertGreaterEqual(len(graph["venues"]),10)
        self.assertGreaterEqual(len(graph["stagings"]),24)
        self.assertGreaterEqual(sum(not e["time_known"] for e in graph["performances"]),2)
        paths={p["url"] for p in graph["stagings"]}
        for url in ("/milano/teatro-alla-scala/otello/",
                    "/verona/arena-di-verona/aida/",
                    "/venezia/teatro-la-fenice/fedora/",
                    "/palermo/teatro-massimo/macbeth/",
                    "/parma/teatro-regio-di-parma/madama-butterfly/"):
            self.assertIn(url,paths)
        self.assertEqual(
            self.registry["performances"]["regio-traviata-2027|2027-02-26"]["id"],
            "oa-r-000001")

    def test_italian_dst_and_official_start_hours(self):
        events={e["id"]:e for e in build(self.facts)["performances"]}
        self.assertEqual(events["curated:arena-aida-de-bosio-2027:2027-06-12"]["starts_at"],
                         "2027-06-12T21:30:00+02:00")
        self.assertEqual(events["curated:scala-otello-2026:2026-12-07"]["starts_at"],
                         "2026-12-07T18:00:00+01:00")
        self.assertEqual(events["curated:massimo-macbeth-2027:2027-02-07"]["time_label"],
                         "17:30")
        self.assertEqual(len(events),sum(len(p["dates"]) for p in self.facts["productions"]))

if __name__=="__main__":
    unittest.main()

"""The Donizetti Opera 2026 programme covers both real Bergamo venues."""
import json
import unittest

from scripts.build_verified_catalog import MANIFEST
from scripts.source_automation import build, INDEX_VENUES, DIRECTORY, DAILY, DAILY_HEALTH, INDEX, INDEX_HEALTH

class BergamoSocialeSourceCoverageTests(unittest.TestCase):
    def test_approved_programme_links_two_real_venues(self):
        self.assertEqual(set(INDEX_VENUES["donizetti-opera-2026"]),
                         {"Bergamo|Teatro Donizetti","Bergamo|Teatro Sociale"})
        catalog=json.loads(MANIFEST.read_text(encoding="utf-8"))
        productions=[p for p in catalog["productions"]
                     if p["municipality"]=="Bergamo" and
                     p["title"]=="Alahor in Granata" and
                     p["venue"]=="Teatro Sociale"]
        self.assertEqual(len(productions),1)
        production=productions[0]
        self.assertEqual(production["dates"],
                         [["2026-11-14","20:00"],["2026-11-22","15:30"],
                          ["2026-11-27","20:00"]])
        self.assertTrue(production["source_url"].startswith(
            "https://www.donizettiopera.org/it/evento/alahor-in-granata/"))

    def test_scanned_donizetti_index_counts_for_both_venues(self):
        def read(path):
            return json.loads(path.read_text(encoding="utf-8"))
        index=read(INDEX)
        health=read(INDEX_HEALTH)
        row=next(x for x in health["sources"] if x["key"]=="donizetti-opera-2026")
        self.assertEqual(row["status"],"success")
        self.assertTrue(row["current_scan_verified"])
        result=build(read(DIRECTORY),read(DAILY),read(DAILY_HEALTH),
                     index,health)
        bergamo={x["venue"]:x for x in result["venues"] if x["city"]=="Bergamo"}
        for venue in ("Teatro Donizetti","Teatro Sociale"):
            self.assertEqual(bergamo[venue]["status"],"operational")
            self.assertTrue(any(x["source_key"]=="donizetti-opera-2026"
                                and x["recent_success"] for x in bergamo[venue]["sources"]))

if __name__=="__main__":
    unittest.main()

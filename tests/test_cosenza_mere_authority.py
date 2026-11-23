"""Milhaud's historic identity remains source-bound to the Rendano ticket."""
import json
import unittest
from scripts.auto_catalogue import ROOT
from scripts.publish_work_editorial import validate_history
from scripts.discover_season_indexes import eligible

class MereCoupableAuthorityTests(unittest.TestCase):
    def test_exact_official_ticket_and_history(self):
        data=json.loads((ROOT/"data/verified-work-authority-seeds.json").read_text(encoding="utf-8"))
        rows=[r for r in data["works"] if r["source_key"]=="cosenza-inprimafila-rolling-opera"
              and r["title"]=="La mère coupable"]
        self.assertEqual(len(rows),1)
        row=rows[0]
        self.assertEqual(row["composer"],"Darius Milhaud")
        self.assertTrue(eligible(row["source_key"],row["source_url"]))
        self.assertTrue(45<=len(row["synopsis"])<=300)
        self.assertTrue(validate_history(row["history"]))
        self.assertEqual(row["history"]["premiere_year"],1966)
        self.assertEqual(row["history"]["premiere_city"],"Ginevra")
        self.assertEqual(row["history"]["librettist"],
            "Madeleine Milhaud, da Pierre-Augustin Caron de Beaumarchais")

if __name__=="__main__":
    unittest.main()

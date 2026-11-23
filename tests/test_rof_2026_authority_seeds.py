"""Official 2026 Rossini Opera Festival authority records remain publishable."""
import json
import unittest
from scripts.auto_catalogue import ROOT
from scripts.publish_work_editorial import validate_history
from scripts.discover_season_indexes import eligible

class ROF2026AuthorityTests(unittest.TestCase):
    def test_three_rof_works_have_complete_source_bound_profiles(self):
        doc=json.loads((ROOT/"data/verified-work-authority-seeds.json").read_text(encoding="utf-8"))
        rows=[w for w in doc["works"] if w["source_key"]=="pesaro-rof-2026"]
        self.assertEqual({w["title"] for w in rows},
                         {"Le Siège de Corinthe","Il viaggio a Reims","La scala di seta"})
        for w in rows:
            with self.subTest(work=w["title"]):
                self.assertEqual(w["composer"],"Gioachino Rossini")
                self.assertTrue(eligible(w["source_key"],w["source_url"]))
                self.assertTrue(validate_history(w["history"]))
                self.assertTrue(45<=len(w["synopsis"])<=300)
                self.assertGreaterEqual(len(w["history"]["sources"]),2)

if __name__=="__main__":
    unittest.main()

"""Rome: one public operetta double bill, not two independent tickets."""
import json
import unittest
from scripts.publish_catalog_v2 import ROOT
from scripts.publish_programs import assemble_programs
from scripts.discover_season_indexes import CONFIG

class RomeOffenbachTests(unittest.TestCase):
    def test_reviewed_offenbach_schedule_and_venue(self):
        read=lambda name:json.loads((ROOT/name).read_text(encoding="utf-8"))
        result=assemble_programs(read("data/season-index-candidates.json"),
            read("data/candidate-detail-evidence.json"),read("data/identity-registry.json"),
            read("data/verified-launch-catalog.json"),json.loads(CONFIG.read_text(encoding="utf-8")),
            read("data/reviewed-program-work-editorials.json"))
        bills=[p for p in result["programs"] if p["source_url"]=="https://www.operaroma.it/spettacoli/fabbrica-offenbach/"]
        self.assertEqual(len(bills),1)
        bill=bills[0]
        self.assertEqual(bill["venue"],"Teatro Nazionale")
        self.assertEqual(len(bill["components"]),2)
        self.assertEqual([p["local_date"] for p in bill["performances"]],
                         ["2026-01-22","2026-01-23"])
        self.assertTrue(all(p.get("editorial") for p in bill["components"]))

if __name__=="__main__":
    unittest.main()

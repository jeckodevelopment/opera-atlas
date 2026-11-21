"""Homepage curated opera identities and Bologna future-season automation."""
import json
import unittest
from scripts.publish_catalog_v2 import REGISTRY,ROOT
from scripts.discover_season_indexes import CONFIG,validate_config,eligible

class HomeBolognaEditorialTests(unittest.TestCase):
    def test_featured_barbiere_is_rossini_not_aida_or_paisiello(self):
        source=(ROOT/"site"/"app.js").read_text(encoding="utf-8")
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))["works"]
        selection=source.split("const HOME_REPERTOIRE_IDS=Object.freeze([",1)[1].split("]);",1)[0]
        self.assertIn('"oa-w-000038"',selection)
        self.assertNotIn('"oa-w-000015"',selection)
        matching=[w for w in registry.values() if w["id"]=="oa-w-000038"]
        self.assertEqual(len(matching),1)
        self.assertEqual((matching[0]["title"],matching[0]["composer"]),
                         ("Il barbiere di Siviglia","Gioachino Rossini"))

    def test_bologna_present_and_future_urls_are_monitored(self):
        config=json.loads(CONFIG.read_text(encoding="utf-8"))
        entries={x["key"]:x for x in validate_config(config)}
        self.assertEqual(entries["bologna-comunale-opera-2026"]["access_status"],"approved")
        self.assertEqual(entries["bologna-comunale-opera-2027"]["access_status"],"approved")
        self.assertTrue(eligible("bologna-comunale-opera-2027",
                         "https://www.tcbo.it/evento/opera/a-new-opera-2028/"))

if __name__=="__main__":unittest.main()

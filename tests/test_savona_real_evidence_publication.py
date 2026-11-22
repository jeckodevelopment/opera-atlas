"""Use real checked-in official Savona evidence, not a handcrafted calendar.

This catches a source->detail->canonical publication break when the upstream
homepage changes or when one of several works on the same URL is dropped.
"""
import json
import unittest
from datetime import date

from scripts.auto_catalogue import promote,split_verified_season
from scripts.build_verified_catalog import MANIFEST
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.publish_catalog_v2 import REGISTRY

SOURCE="savona-giocosa-rolling-opera"
URL="https://operagiocosa.it/"

class SavonaRealEvidenceToCatalogTests(unittest.TestCase):
    def test_real_official_evidence_promotes_all_three_canonical_works(self):
        evidence=json.loads(DETAILS.read_text(encoding="utf-8"))
        candidates=json.loads(CANDIDATES.read_text(encoding="utf-8"))
        real=[r for r in evidence["evidence"]
              if r["source_key"]==SOURCE and r["source_url"]==URL]
        self.assertEqual(len(real),1,"Savona official evidence not acquired")
        item=real[0]
        self.assertEqual(item["status"],"needs_editorial_review")
        self.assertEqual(len(item["event_facts"]),5)
        self.assertEqual(len(split_verified_season(item)),3)
        official={"schema_version":1,"evidence":real}
        candidate={"schema_version":1,"candidates":[{**x,"status":"needs_review"}
                   for x in candidates["candidates"]
                   if x["source_key"]==SOURCE and x["official_url"]==URL]}
        self.assertEqual(len(candidate["candidates"]),1)
        original=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        result,ids,authorized,stats=promote(
            original,registry,official,candidate,[],today=date(2026,11,22))
        produced=[p for p in result["productions"]
                  if p.get("source_url")==URL and p.get("municipality")=="Savona"]
        self.assertEqual({p["title"] for p in produced},
            {"L'arca di Noè","La traviata","I salvatori della mezzanotte"},stats)
        self.assertEqual(sum(len(p["dates"]) for p in produced),5)
        self.assertEqual(len({p["key"] for p in produced}),3)
        self.assertEqual({p["venue"] for p in produced},{"Teatro Chiabrera"})
        for p in produced:
            self.assertIn(p["key"],ids["stagings"])
        self.assertIn(URL,authorized)
        again,again_ids,_,repeat=promote(
            result,ids,official,candidate,authorized,today=date(2026,11,22))
        self.assertEqual(repeat["new_recite"],0)
        self.assertEqual(again,result)
        self.assertEqual(again_ids,ids)

if __name__=="__main__":
    unittest.main()

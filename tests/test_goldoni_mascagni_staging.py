"""Two separately ticketed Goldoni performances must share a production."""
import copy
import json
import unittest
from datetime import date
from scripts.auto_catalogue import promote
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY

class GoldoniMascagniStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_existing_canonical_provenance_remains_valid_after_reprocessing(self):
        # All first-party candidate evidence must be replay-safe, even if
        # new unrelated publications have landed on main since the fixture.
        from scripts.auto_catalogue import SOURCE_ALLOWLIST
        from scripts.collect_candidate_details import OUTPUT as EVIDENCE
        from scripts.discover_season_indexes import OUTPUT as CANDIDATES
        all_candidates=json.loads(CANDIDATES.read_text(encoding="utf-8"))
        all_evidence=json.loads(EVIDENCE.read_text(encoding="utf-8"))
        authorized=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))["urls"]
        doc={"schema_version":1,"candidates":[
            {**x,"status":"needs_review"} for x in all_candidates["candidates"]
            if x["source_key"]=="carlo-felice-season-2026-27"]}
        details={"schema_version":1,"evidence":[
            x for x in all_evidence["evidence"]
            if x["source_key"]=="carlo-felice-season-2026-27"]}
        after,ids,urls,report=promote(
            self.facts,self.registry,details,doc,authorized,
            today=date(2026,11,22))
        mismatches=[]
        for p in after["productions"]:
            for day,hour in p["dates"]:
                perf=ids["performances"].get(p["key"]+"|"+day)
                if perf is None or perf["source_url"]!=p["source_url"]:
                    mismatches.append((p["title"],p["source_url"],day,
                                      perf and perf["source_url"]))
        self.assertEqual(mismatches,[],report)

    def test_mascagni_festival_two_tickets_share_one_outdoor_staging(self):
        from scripts.publish_catalog_v2 import ROOT
        from scripts.reconcile_published_candidates import verified_livorno_recital_urls
        candidates_doc=json.loads((ROOT/"data/season-index-candidates.json").read_text())
        details_doc=json.loads((ROOT/"data/candidate-detail-evidence.json").read_text())
        source="goldoni-livorno-rolling-lirica"
        urls={
            "https://www.goldoniteatro.it/spettacoli/cavalleria-rusticana/",
            "https://www.goldoniteatro.it/spettacoli/cavalleria-rusticana-2/",
        }
        candidates=[{**x,"status":"needs_review"}
                    for x in candidates_doc["candidates"]
                    if x.get("source_key")==source and x.get("official_url") in urls]
        evidences=[x for x in details_doc["evidence"]
                   if x.get("source_key")==source and x.get("source_url") in urls]
        self.assertEqual(len(candidates),2)
        self.assertEqual(len(evidences),2)
        self.assertTrue(all(x["status"]=="needs_editorial_review" for x in evidences))
        from scripts.repair_livorno_mascagni_staging import consolidate
        canonical,identities,migrated=consolidate(self.facts,self.registry)
        self.assertIsInstance(migrated,bool)
        facts,registry,approved,health=promote(
            canonical,identities,{"schema_version":1,"evidence":evidences},
            {"schema_version":1,"candidates":candidates},
            list(urls),today=date(2026,11,22))
        productions=[p for p in facts["productions"]
                     if p["municipality"]=="Livorno" and p["venue"]=="Piazza Goldoni"
                     and p["title"]=="Cavalleria rusticana"]
        self.assertEqual(len(productions),1,health)
        repaired,canonical_ids,again_migrated=consolidate(facts,registry)
        self.assertFalse(again_migrated)
        self.assertEqual(repaired,facts)
        self.assertEqual(canonical_ids,registry)
        self.assertEqual(productions[0]["dates"],
                         [["2026-08-19","21:30"],["2026-08-20","21:30"]])
        self.assertEqual(verified_livorno_recital_urls(
            facts,{"evidence":evidences}),urls)
        again,identity,_,repeat=promote(
            facts,registry,{"schema_version":1,"evidence":evidences},
            {"schema_version":1,"candidates":candidates},
            approved,today=date(2026,11,22))
        self.assertEqual(repeat["new_recite"],0)
        self.assertEqual(again,facts)
        self.assertEqual(identity,registry)
        corrupted=copy.deepcopy(evidences)
        corrupted[0]["event_facts"][0]["composer"]="Different composer"
        self.assertNotEqual(
            verified_livorno_recital_urls(facts,{"evidence":corrupted}),urls)


if __name__=="__main__":
    unittest.main()

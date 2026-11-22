"""Existing dual-production Mascagni data is migrated without losing recita IDs."""
import copy
import json
import unittest
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.consolidate_goldoni_mascagni import URLS,consolidate

class GoldoniLegacyConsolidationTests(unittest.TestCase):
    def test_existing_festival_stagings_merge_once_and_keep_recita_identity(self):
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        prior=[p for p in facts["productions"]
               if p["municipality"]=="Livorno"
               and p["venue"]=="Piazza Goldoni"
               and p["title"]=="Cavalleria rusticana"]
        if len(prior)==1:
            result,ids,count=consolidate(facts,registry)
            self.assertEqual(count,0)
            self.assertEqual(result,facts)
            return
        self.assertEqual(len(prior),2)
        old_recite={day:registry["performances"][p["key"]+"|"+day]["id"]
                    for p in prior for day,_ in p["dates"]}
        result,ids,count=consolidate(facts,registry)
        self.assertEqual(count,1)
        final=[p for p in result["productions"]
               if p["municipality"]=="Livorno"
               and p["venue"]=="Piazza Goldoni"
               and p["title"]=="Cavalleria rusticana"]
        self.assertEqual(len(final),1)
        self.assertEqual(final[0]["dates"],
                         [["2026-08-19","21:30"],["2026-08-20","21:30"]])
        for day,old_id in old_recite.items():
            item=ids["performances"][final[0]["key"]+"|"+day]
            self.assertEqual(item["id"],old_id)
            self.assertEqual(item["source_url"],final[0]["source_url"])
            self.assertEqual(item["staging_id"],ids["stagings"][final[0]["key"]]["id"])
        self.assertEqual(len(ids["stagings"]),len(registry["stagings"])-1)
        self.assertEqual(assemble(result,ids)["performances"] is not None,True)
        again,second,changes=consolidate(result,ids)
        self.assertEqual(changes,0)
        self.assertEqual(again,result)
        self.assertEqual(second,ids)

    def test_never_merge_conflicting_festival_work_or_times(self):
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cases=[
            lambda p:p.__setitem__("composer","Different composer"),
            lambda p:p.__setitem__("venue","Teatro Goldoni"),
            lambda p:p["dates"][0].__setitem__(1,"20:00"),
        ]
        original=[p for p in facts["productions"]
                  if p["source_url"] in URLS.values()
                  and p["municipality"]=="Livorno"
                  and p["title"]=="Cavalleria rusticana"]
        if len(original)!=2:return
        for mutate in cases:
            doc=copy.deepcopy(facts)
            row=next(p for p in doc["productions"]
                     if p["key"]==original[0]["key"])
            mutate(row)
            after,ids,changed=consolidate(doc,registry)
            self.assertEqual(changed,0)
            self.assertEqual(after,doc)
            self.assertEqual(ids,registry)

if __name__=="__main__":
    unittest.main()

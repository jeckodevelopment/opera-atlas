"""Known incorrect Petruzzelli title attributions must be retired safely."""
import copy
import json
import unittest

from scripts.repair_petruzzelli_mixed_program import repair,WRONG,BASE
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.auto_catalogue import SOURCE_ALLOWLIST

class IncorrectPetruzzelliRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.approved=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))["urls"]

    def test_only_six_wrong_stagings_are_quarantined_idempotently(self):
        keys={x[0] for x in WRONG}
        bad_urls={BASE+x[1]+"/" for x in WRONG}
        preserved=[p for p in self.facts["productions"] if p["key"] not in keys]
        facts,ids,urls,removed=repair(self.facts,self.registry,self.approved)
        self.assertEqual(facts["productions"],preserved)
        expected=sum(len(p["dates"]) for p in self.facts["productions"]
                     if p["key"] in keys)
        self.assertEqual(removed,expected)
        for key in keys:
            self.assertNotIn(key,ids["stagings"])
            self.assertFalse(any(row.startswith(key+"|") for row in ids["performances"]))
        self.assertTrue(bad_urls.isdisjoint(urls))
        for key,stage in self.registry["stagings"].items():
            if key not in keys:self.assertEqual(ids["stagings"][key],stage)
        for key,performance in self.registry["performances"].items():
            if not any(key.startswith(stage_key+"|") for stage_key in keys):
                self.assertEqual(ids["performances"][key],performance)
        # The true Nabucco and Traviata remain, with their exact original IDs.
        self.assertIn("auto-ef3fc228eb643db3",ids["stagings"])
        self.assertTrue(any(p["municipality"]=="Bari"
                            and p["title"]=="La traviata"
                            and "la-traviata-verdi" in p["source_url"]
                            for p in facts["productions"]))
        self.assertTrue(assemble(facts,ids,approved_extra=set(urls))["performances"])
        again,again_ids,again_urls,second=repair(facts,ids,urls)
        self.assertEqual(second,0)
        self.assertEqual(again,facts)
        self.assertEqual(again_ids,ids)
        self.assertEqual(again_urls,urls)

    def test_fail_closed_on_identity_or_immutable_performance_mismatch(self):
        key=WRONG[0][0]
        present=any(p["key"]==key for p in self.facts["productions"])
        if not present:return
        for change in ("title","venue","performance"):
            facts=copy.deepcopy(self.facts)
            ids=copy.deepcopy(self.registry)
            if change=="title":
                next(p for p in facts["productions"] if p["key"]==key)["title"]="L'Arlésienne"
            elif change=="venue":
                next(p for p in facts["productions"] if p["key"]==key)["venue"]="Another theatre"
            else:
                ids["performances"][key+"|2027-10-13"]["source_url"]="https://example.invalid"
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    repair(facts,ids,self.approved)

    def test_both_workflows_repair_before_public_catalog_promotion(self):
        from scripts.publish_catalog_v2 import ROOT
        for path in (".github/workflows/publish-cached-catalog.yml",
                     ".github/workflows/refresh-catalog.yml"):
            content=(ROOT/path).read_text(encoding="utf-8")
            self.assertLess(content.index("python -m scripts.repair_petruzzelli_mixed_program"),
                            content.index("python -m scripts.publish_cached_known"))
            self.assertIn("python -m scripts.publish_catalog_v2",content)

if __name__=="__main__":
    unittest.main()

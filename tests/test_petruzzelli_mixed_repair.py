"""A composite Petruzzelli bill must never masquerade as solo Pagliacci."""
import copy
import json
import unittest

from scripts.repair_petruzzelli_mixed_program import repair,MIXED_KEY,MIXED_URL
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.auto_catalogue import SOURCE_ALLOWLIST

class CompositeRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.approved=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))["urls"]

    def test_only_wrong_seven_recite_removed_once(self):
        before=[p for p in self.facts["productions"] if p["key"]!=MIXED_KEY]
        facts,ids,urls,removed=repair(self.facts,self.registry,self.approved)
        self.assertEqual(facts["productions"],before)
        self.assertEqual(removed,7 if len(self.facts["productions"])!=len(before) else 0)
        self.assertNotIn(MIXED_KEY,ids["stagings"])
        self.assertFalse(any(key.startswith(MIXED_KEY+"|") for key in ids["performances"]))
        self.assertNotIn(MIXED_URL,urls)
        # Existing IDs, including Nabucco's seven verified recite, stay stable.
        for key,stage in self.registry["stagings"].items():
            if key!=MIXED_KEY:self.assertEqual(ids["stagings"][key],stage)
        for key,recite in self.registry["performances"].items():
            if not key.startswith(MIXED_KEY+"|"):
                self.assertEqual(ids["performances"][key],recite)
        self.assertIn("auto-ef3fc228eb643db3",ids["stagings"])
        graph=assemble(facts,ids,approved_extra=set(urls))
        self.assertTrue(graph["performances"])
        again,replay_ids,replay_urls,deleted=repair(facts,ids,urls)
        self.assertEqual(deleted,0)
        self.assertEqual(again,facts)
        self.assertEqual(replay_ids,ids)
        self.assertEqual(replay_urls,urls)

    def test_fail_closed_on_unexpected_single_work_or_mislinked_id(self):
        matching=[p for p in self.facts["productions"] if p["key"]==MIXED_KEY]
        if not matching:return # Once repaired, no erroneous stage remains.
        for corrupt in ("title","venue","performance"):
            facts=copy.deepcopy(self.facts)
            registry=copy.deepcopy(self.registry)
            if corrupt=="title":
                next(x for x in facts["productions"] if x["key"]==MIXED_KEY)["title"]="L'Arlésienne"
            elif corrupt=="venue":
                next(x for x in facts["productions"] if x["key"]==MIXED_KEY)["venue"]="Altro teatro"
            else:
                registry["performances"][MIXED_KEY+"|2027-10-13"]["source_url"]="https://example.com"
            with self.subTest(corrupt=corrupt):
                with self.assertRaises(ValueError):
                    repair(facts,registry,self.approved)

    def test_workflow_quarantines_before_promoting_and_rebuilding(self):
        from scripts.publish_catalog_v2 import ROOT
        for p in (".github/workflows/publish-cached-catalog.yml",
                  ".github/workflows/refresh-catalog.yml"):
            source=(ROOT/p).read_text(encoding="utf-8")
            self.assertLess(source.index("python -m scripts.repair_petruzzelli_mixed_program"),
                            source.index("python -m scripts.publish_cached_known"))
            self.assertIn("python -m scripts.publish_catalog_v2",source)

if __name__=="__main__":
    unittest.main()

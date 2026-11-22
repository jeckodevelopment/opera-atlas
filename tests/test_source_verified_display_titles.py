"""Source-authenticated opera title typography never alters canonical identity."""
import copy
import json
import unittest

from scripts.auto_catalogue import normalize_published_work_titles
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY, assemble

TITLES={
    "il gobbo del califfo|franco casavola":"Il gobbo del Califfo",
    "la cecchina|niccolò piccinni":"La Cecchina",
    "bona sforza|zygmunt krauze":"Bona Sforza",
}

class VerifiedOperaDisplayTitlesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.seeds=json.loads((MANIFEST.parents[1]/
            "data/verified-work-authority-seeds.json").read_text(encoding="utf-8"))

    def test_published_source_title_case_is_consistent_and_idempotent(self):
        facts,registry,changed=normalize_published_work_titles(
            self.facts,self.registry,self.seeds)
        from scripts.publish_catalog_v2 import normalized
        self.assertGreaterEqual(changed,0)
        for key,title in TITLES.items():
            with self.subTest(work=key):
                old=self.registry["works"][key]
                new=registry["works"][key]
                self.assertEqual(new["title"],title)
                self.assertEqual(new["id"],old["id"])
                self.assertEqual(new["slug"],old["slug"])
                for production in facts["productions"]:
                    if (normalized(production["title"])+"|"+
                            normalized(production["composer"]))==key:
                        self.assertEqual(production["title"],title)
        second_facts,second_registry,second_changed=normalize_published_work_titles(
            facts,registry,self.seeds)
        self.assertEqual(second_changed,0)
        self.assertEqual(second_facts,facts)
        self.assertEqual(second_registry,registry)
        # Same immutable IDs, routes and recite throughout the generated graph.
        assemble(facts,registry,approved_extra=set(
            x["source_url"] for x in facts["productions"]))

    def test_simon_boccanegra_composer_is_reviewed_and_preserves_ids(self):
        key="simon boccanegra|giuseppe verdi"
        facts,registry,_=normalize_published_work_titles(
            self.facts,self.registry,self.seeds)
        work=registry["works"][key]
        self.assertEqual(work["composer"],"Giuseppe Verdi")
        self.assertEqual(work["id"],self.registry["works"][key]["id"])
        relevant=[p for p in facts["productions"]
                  if p["title"]=="Simon Boccanegra"]
        self.assertGreaterEqual(len(relevant),3)
        self.assertTrue(all(p["composer"]=="Giuseppe Verdi" for p in relevant))
        old=[p["key"] for p in self.facts["productions"]
             if p["title"]=="Simon Boccanegra"]
        self.assertEqual([p["key"] for p in relevant],old)

    def test_uppercase_credits_cannot_change_unsupported_homonyms(self):
        facts=copy.deepcopy(self.facts)
        registry=copy.deepcopy(self.registry)
        before=copy.deepcopy(registry)
        seeds={"schema_version":1,"works":[{
            "source_url":"https://example.invalid/simon-boccanegra",
            "title":"Simon Boccanegra","composer":"Giuseppe Verdi"}]}
        newer,works,changed=normalize_published_work_titles(facts,registry,seeds)
        self.assertEqual((newer,works,changed),(facts,before,0))

    def test_mismatched_source_or_composer_does_not_change_title(self):
        facts=copy.deepcopy(self.facts)
        registry=copy.deepcopy(self.registry)
        seed={"schema_version":1,"works":[{
            "source_url":"https://example.invalid/other",
            "title":"Il gobbo del Califfo",
            "composer":"Franco Casavola"}]}
        _,works,changed=normalize_published_work_titles(facts,registry,seed)
        self.assertEqual(changed,0)
        self.assertEqual(works,registry)

    def test_different_casing_cannot_change_work_identity(self):
        from scripts.publish_catalog_v2 import normalized
        facts,registry,_=normalize_published_work_titles(
            self.facts,self.registry,self.seeds)
        self.assertEqual(set(registry["works"]),set(self.registry["works"]))
        for old_key in registry["works"]:
            self.assertEqual(normalized(registry["works"][old_key]["title"]),
                             normalized(self.registry["works"][old_key]["title"]))

if __name__=="__main__":
    unittest.main()

"""Every canonical opera must have a publishable brief original summary."""
import copy
import json
import unittest
from scripts.publish_work_editorial import EDITORIAL, MANIFEST, REGISTRY, build_editorial

class WorkEditorialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.editorial=json.loads(EDITORIAL.read_text(encoding="utf-8"))

    def test_all_existing_works_are_publishable(self):
        report=build_editorial(self.facts,self.registry,self.editorial)
        self.assertEqual(len(report["works"]),len(self.registry["works"]))
        self.assertEqual(len({x["work_id"] for x in report["works"]}),len(report["works"]))
        self.assertTrue(all(x["synopsis"] and x["composer"] for x in report["works"]))

    def test_new_work_without_synopsis_must_block_publication(self):
        editorial=copy.deepcopy(self.editorial)
        editorial["synopses"].pop(next(iter(editorial["synopses"])))
        with self.assertRaisesRegex(ValueError,"missing verified work synopsis"):
            build_editorial(self.facts,self.registry,editorial)

    def test_prepared_extra_synopsis_is_allowed_but_not_published(self):
        editorial=copy.deepcopy(self.editorial)
        editorial["synopses"]["not-in-catalog"]="Description that should not be published without a canonical work and a staging."
        result=build_editorial(self.facts,self.registry,editorial)
        self.assertNotIn("not-in-catalog",{x["slug"] for x in result["works"]})

    def test_empty_or_long_synopsis_is_rejected(self):
        editorial=copy.deepcopy(self.editorial)
        key=next(iter(editorial["synopses"]))
        editorial["synopses"][key]="short"
        with self.assertRaisesRegex(ValueError,"invalid short synopsis"):
            build_editorial(self.facts,self.registry,editorial)
        editorial["synopses"][key]="A"*301
        with self.assertRaises(ValueError):
            build_editorial(self.facts,self.registry,editorial)

if __name__=="__main__":
    unittest.main()

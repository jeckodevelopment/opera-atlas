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

    def test_new_operas_have_specific_plot_and_verified_historical_facts(self):
        from scripts.publish_work_editorial import validate_history
        report=build_editorial(self.facts,self.registry,self.editorial)
        by_id={item["work_id"]:item for item in report["works"]}
        for wid in ("oa-w-000045","oa-w-000046","oa-w-000047","oa-w-000048"):
            with self.subTest(work=wid):
                item=by_id[wid]
                self.assertTrue(validate_history(item["history"]))
                self.assertNotIn("Consulta le rappresentazioni verificate",item["synopsis"])
                self.assertGreater(len(item["synopsis"]),75)
                self.assertTrue(item["history"]["sources"])

    def test_identity_only_synopsis_or_missing_history_is_rejected(self):
        from scripts.publish_work_editorial import HISTORY
        synopsis=copy.deepcopy(self.editorial)
        by_id=synopsis.setdefault("synopses_by_id",{})
        by_id["oa-w-000045"]=(
            "«Le nozze di Figaro» è un'opera di Mozart. "
            "Consulta le rappresentazioni verificate in programma nei teatri italiani.")
        with self.assertRaisesRegex(ValueError,"identity-only"):
            build_editorial(self.facts,self.registry,synopsis)
        history=json.loads(HISTORY.read_text(encoding="utf-8"))
        history["works_by_id"].pop("oa-w-000048",None)
        history["works"].pop("fidelio",None)
        with self.assertRaisesRegex(ValueError,"missing complete sourced work history"):
            build_editorial(self.facts,self.registry,self.editorial,history=history)

    def test_distinct_bohème_history_and_synopses_by_permanent_identity(self):
        report=build_editorial(self.facts,self.registry,self.editorial)
        works={x["work_id"]:x for x in report["works"]}
        leo=works["oa-w-000007"]
        puc=works["oa-w-000024"]
        self.assertEqual(leo["composer"],"Ruggero Leoncavallo")
        self.assertEqual(puc["composer"],"Giacomo Puccini")
        self.assertNotEqual(leo["synopsis"],puc["synopsis"])
        self.assertEqual(leo["history"]["librettist"],"Ruggero Leoncavallo")
        self.assertEqual(leo["history"]["premiere_year"],1897)
        self.assertEqual(leo["history"]["premiere_venue"],"Teatro La Fenice")
        self.assertEqual(leo["history"]["premiere_city"],"Venezia")
        self.assertEqual(puc["history"]["premiere_year"],1896)
        self.assertEqual(puc["history"]["premiere_venue"],"Teatro Regio")
        self.assertEqual(puc["history"]["premiere_city"],"Torino")
        self.assertEqual(leo["route_slug"],"la-boheme-leoncavallo")
        self.assertEqual(puc["route_slug"],"la-boheme-puccini")

    def test_missing_identity_specific_editorial_fails_closed(self):
        editorial=copy.deepcopy(self.editorial)
        del editorial["synopses_by_id"]["oa-w-000007"]
        with self.assertRaisesRegex(ValueError,"ambiguous synopsis"):
            build_editorial(self.facts,self.registry,editorial)

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

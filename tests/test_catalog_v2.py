"""Canonical catalog identity is stable across sorting and repeated generation."""
import copy
import json
import unittest
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY, assemble, release_parts, slugify


class CanonicalCatalogV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_four_entity_types_with_permanent_unique_identifiers(self):
        result = assemble(self.facts, self.registry)
        self.assertTrue(all(len(result[k]) >= minimum for k,minimum in
                            {"works":2, "venues":5, "stagings":5,
                             "performances":19}.items()))
        ids = [entity["id"] for records in result.values() for entity in records]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(item["id"].startswith("oa-") for items in result.values() for item in items))

    def test_slugs_and_relationships(self):
        result=assemble(self.facts, self.registry)
        self.assertEqual(slugify("L’italiana in Algeri"), "italiana-in-algeri")
        self.assertEqual(slugify("Così fan tutte"), "cosi-fan-tutte")
        self.assertEqual(slugify("Teatro Regio"), "teatro-regio")
        self.assertEqual(result["stagings"][0]["url"],
                         "/torino/teatro-regio/la-traviata/")
        works={w["id"] for w in result["works"]}
        venues={v["id"] for v in result["venues"]}
        stagings={s["id"] for s in result["stagings"]}
        self.assertTrue(all(s["work_id"] in works and s["venue_id"] in venues
                            for s in result["stagings"]))
        self.assertTrue(all(r["staging_id"] in stagings for r in result["performances"]))

    def test_adding_production_requires_persisted_ids(self):
        changed=copy.deepcopy(self.facts)
        changed["productions"][0]["key"]="untracked-new-production"
        with self.assertRaises(ValueError):
            assemble(changed,self.registry)

    def test_changed_date_fails_closed_instead_of_reidentifying(self):
        changed=copy.deepcopy(self.facts)
        changed["productions"][0]["dates"][0][0]="2027-04-04"
        with self.assertRaises(ValueError):
            assemble(changed,self.registry)

    def test_duplicate_routes_are_rejected(self):
        changed=copy.deepcopy(self.facts)
        reg=copy.deepcopy(self.registry)
        # A second run of same work at same venue would need an explicit
        # season-qualified public slug, rather than overwrite the first URL.
        product=copy.deepcopy(changed["productions"][0])
        product["key"]="another-run"
        product["dates"]=[["2027-04-10","20:00"]]
        changed["productions"].append(product)
        reg["stagings"]["another-run"]={
            "id":"oa-s-999999", "work_id":"oa-w-000001",
            "venue_id":"oa-v-000001","slug":"la-traviata",
            "season":"2027-2028","source_url":product["source_url"]
        }
        reg["performances"]["another-run|2027-04-10"]={
            "id":"oa-r-999999","staging_id":"oa-s-999999",
            "original_date":"2027-04-10","source_url":product["source_url"]
        }
        with self.assertRaisesRegex(ValueError,"ambiguous public staging URL"):
            assemble(changed,reg)

    def test_deterministic_content_addressed_manifest(self):
        files1,manifest1=release_parts(self.facts,self.registry)
        files2,manifest2=release_parts(self.facts,self.registry)
        self.assertEqual(files1,files2)
        self.assertEqual(manifest1,manifest2)
        self.assertTrue(all(path.startswith("data/") for path in files1))
        self.assertEqual(manifest1["schema_version"],2)
        self.assertEqual(manifest1["files"]["performances"]["count"],141)


if __name__=="__main__":
    unittest.main()

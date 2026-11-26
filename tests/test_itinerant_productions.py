import copy
import json
import unittest
from datetime import date
from scripts.publish_catalog_v2 import ROOT, assemble
from scripts.auto_catalogue import next_id
from opera_atlas.itinerant import promote,reviewed,validate_production

class ItinerantProductionTests(unittest.TestCase):
    def test_owner_identity_and_actual_locations(self):
        facts=json.loads((ROOT/"data/verified-launch-catalog.json").read_text())
        registry=json.loads((ROOT/"data/identity-registry.json").read_text())
        f,r,added,count=promote(facts,registry,today=date(2026,11,26),allocate=next_id)
        key="roma-operacamion-barbiere-2026"
        self.assertIn((added,count),((1,15),(0,0)))
        self.assertEqual(registry["venues"],r["venues"])
        staging=r["stagings"][key]
        graph=assemble(f,r)
        stage=next(s for s in graph["stagings"] if s["id"]==staging["id"])
        self.assertEqual(stage["project_name"],"OperaCamion")
        shows=[s for s in graph["performances"] if s["staging_id"]==staging["id"]]
        self.assertEqual(len(shows),15)
        self.assertEqual({s["actual_location"]["municipality"] for s in shows},{"Roma","Bracciano","Valmontone"})
        self.assertNotIn("2026-05-31",{s["local_date"] for s in shows})
        self.assertEqual(len({s["id"] for s in shows}),15)
        self.assertTrue(all(s["actual_location"]["source_url"] in s["sources"] for s in shows))
        self.assertEqual(promote(f,r,today=date(2026,11,26),allocate=next_id),(f,r,0,0))
        changed=copy.deepcopy(next(p for p in f["productions"] if p["key"]==key))
        changed["performance_locations"]["2026-06-09"]["municipality"]="Roma"
        with self.assertRaises(ValueError):validate_production(changed,reviewed())

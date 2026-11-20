"""Como OperaLombardia subscription calendar: 5 titles, separate staging IDs."""
import json
import unittest
from scripts.build_verified_catalog import MANIFEST, build
from scripts.publish_catalog_v2 import REGISTRY, assemble

OFFICIAL="https://teatrosocialecomo.it/spettacoli/abbonamento-opera-2026-27/"
EXPECTED={
    "lombardia-turandot-como":[["2026-09-24","20:00"],["2026-09-26","20:00"]],
    "lombardia-death-venice-como":[["2026-10-09","20:00"],["2026-10-11","15:30"]],
    "lombardia-cavalleria-como":[["2026-12-04","20:00"],["2026-12-06","15:30"]],
    "lombardia-pagliacci-como":[["2026-12-04","20:00"],["2026-12-06","15:30"]],
    "lombardia-ballo-como":[["2027-01-15","20:00"],["2027-01-17","15:30"]],
}

class OperaLombardiaComoTests(unittest.TestCase):
    def test_official_2026_27_como_calendar_is_exact(self):
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        productions={x["key"]:x for x in facts["productions"]}
        for key,dates in EXPECT.items():
            self.assertEqual(productions[key]["dates"],dates)
            self.assertEqual(productions[key]["source_url"],OFFICIAL)
            self.assertEqual(productions[key]["venue"],"Teatro Sociale")
            self.assertEqual(productions[key]["municipality"],"Como")
        self.assertEqual(len(set(d for dates in EXPECT.values() for d,_ in dates)),8)
        self.assertNotIn("2026-09-22",dict(EXPECT["lombardia-turandot-como"]))

    def test_same_double_bill_dates_do_not_merge_canonical_works(self):
        reg=json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertNotEqual(reg["stagings"]["lombardia-cavalleria-como"]["work_id"],
                            reg["stagings"]["lombardia-pagliacci-como"]["work_id"])
        self.assertEqual(reg["stagings"]["lombardia-cavalleria-como"]["venue_id"],
                         "oa-v-000002")
        self.assertEqual(reg["stagings"]["lombardia-pagliacci-como"]["venue_id"],
                         "oa-v-000002")

    def test_existing_italiana_and_pavia_replicas_unchanged(self):
        reg=json.loads(REGISTRY.read_text(encoding="utf-8"))
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        graph=assemble(facts,reg)
        self.assertEqual(len(graph["performances"]),141)
        self.assertEqual(len(graph["stagings"]),29)
        self.assertEqual(sum(not r["time_known"] for r in graph["performances"]),2)
        self.assertEqual(reg["performances"]["lombardia-italiana-como|2026-11-13"]["id"],
                         "oa-r-000012")
        self.assertEqual(len({x["id"] for x in graph["performances"]}),141)
        events=build(facts)["performances"]
        self.assertEqual(len(events),141)
        self.assertEqual(sum(e["time_known"] for e in events),139)

if __name__=="__main__":
    unittest.main()

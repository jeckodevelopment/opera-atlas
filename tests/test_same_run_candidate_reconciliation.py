"""Published productions must leave the discovery queue in the same run."""
import copy
import unittest
from scripts.reconcile_published_candidates import reconcile

class SameRunCandidateReconciliationTests(unittest.TestCase):
    def test_newly_published_production_moves_to_catalogued_immediately(self):
        rows={"schema_version":1,"candidates":[
            {"id":"new-carmen","source_key":"arena-festival-2027",
             "official_url":"https://www.arena.it/arena-opera-festival/carmen/",
             "status":"needs_review","first_seen":"first","last_seen":"last"},
            {"id":"future","source_key":"scala-season-2026-27",
             "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/future.html",
             "status":"needs_review","first_seen":"first","last_seen":"last"},
            {"id":"manual","source_key":"arena-festival-2027",
             "official_url":"https://www.arena.it/arena-opera-festival/carmen/",
             "status":"editorially_rejected","first_seen":"first","last_seen":"last"}
        ]}
        before=copy.deepcopy(rows)
        results,report=reconcile(rows,{"https://www.arena.it/arena-opera-festival/carmen/"})
        self.assertEqual(rows,before)
        by={x["id"]:x for x in results["candidates"]}
        self.assertEqual(by["new-carmen"]["status"],"already_catalogued")
        self.assertEqual(by["future"]["status"],"needs_review")
        self.assertEqual(by["manual"]["status"],"editorially_rejected")
        self.assertEqual(by["new-carmen"]["first_seen"],"first")
        self.assertEqual(by["new-carmen"]["last_seen"],"last")
        self.assertEqual(report["states"]["already_catalogued"],1)
        self.assertEqual(len(report["changes"]),1)
        twice,second=reconcile(results,{"https://www.arena.it/arena-opera-festival/carmen/"})
        self.assertEqual(twice,results)
        self.assertEqual(second["changes"],[])

    def test_known_nonopera_is_excluded_but_kept_as_audit_record(self):
        old={"schema_version":1,"candidates":[{
            "id":"irrelevant","source_key":"arena-festival-2027",
            "official_url":"https://www.arena.it/arena-opera-festival/regolamento/",
            "status":"needs_review","first_seen":"old","last_seen":"old"}]}
        result,report=reconcile(old,set())
        self.assertEqual(result["candidates"][0]["status"],"excluded_nonopera")
        self.assertEqual(result["candidates"][0]["first_seen"],"old")
        self.assertEqual(report["total"],1)

    def test_invalid_registry_rejected_instead_of_erasing_queue(self):
        with self.assertRaises(ValueError):
            reconcile({"schema_version":1,"candidates":None},set())
if __name__=="__main__":
    unittest.main()

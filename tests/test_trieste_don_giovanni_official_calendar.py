"""Trieste Don Giovanni must publish six first-party public recite, no guesswork."""
import json
import unittest
from datetime import date
from scripts.auto_catalogue import promote
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY
from opera_atlas.trieste_don_giovanni_program import (
    KEY,URL,ROWS,verified_calendar)

class TriesteDonGiovanniOfficialCalendarTests(unittest.TestCase):
    def test_six_exact_official_recite(self):
        facts=verified_calendar(source_key=KEY,source_url=URL)
        self.assertEqual(len(facts),6)
        self.assertEqual([(x["date"],x["starts_at"][11:16]) for x in facts],
                         list(ROWS))
        self.assertEqual({x["event_title"] for x in facts},{"Don Giovanni"})
        self.assertEqual({x["composer"] for x in facts},{"Wolfgang Amadeus Mozart"})
        with self.assertRaises(ValueError):
            verified_calendar(source_key=KEY,source_url=URL+"?preview=1")

    def test_promotion_keeps_original_canonical_mozart_work(self):
        manifest=json.loads(MANIFEST.read_text())
        registry=json.loads(REGISTRY.read_text())
        cid="oa-index-19141fd504da67924d01"
        candidate={"schema_version":1,"candidates":[{"id":cid,
            "source_key":KEY,"official_url":URL,"status":"needs_review"}]}
        evidence={"schema_version":1,"evidence":[{
            "candidate_id":cid,"source_key":KEY,"source_url":URL,
            "status":"needs_editorial_review",
            "event_facts":verified_calendar(source_key=KEY,source_url=URL)}]}
        result,identity,approved,report=promote(
            manifest,registry,evidence,candidate,[],today=date(2026,11,22))
        matches=[x for x in result["productions"] if x["source_url"]==URL]
        self.assertEqual(len(matches),1,report)
        self.assertEqual([tuple(row) for row in matches[0]["dates"]],list(ROWS))
        self.assertEqual(identity["stagings"][matches[0]["key"]]["work_id"],
                         "oa-w-000023")
        result2,identity2,_,report2=promote(
            result,identity,evidence,candidate,approved,today=date(2026,11,22))
        self.assertEqual(result2,result)
        self.assertEqual(identity2,identity)
        self.assertEqual(report2["new_recite"],0)

if __name__=="__main__":
    unittest.main()

"""Reviewed cross-source decisions are safe, repeatable central inputs."""
import copy
import hashlib
import json
import unittest
from datetime import date

from scripts.apply_reviewed_performance_evidence import apply,CONFIG
from scripts.corroborate_performances import CONFIG as SOURCES
from scripts.auto_catalogue import promote
from scripts.publish_catalog_v2 import ROOT

DOC=json.loads(CONFIG.read_text(encoding="utf-8"))
SOURCE_DOC=json.loads(SOURCES.read_text(encoding="utf-8"))
EMPTY_C={"schema_version":1,"candidates":[]}
EMPTY_E={"schema_version":1,"evidence":[]}

class ReviewedCrossSourceEvidenceTests(unittest.TestCase):
    def test_reviewed_provenance_and_public_recite_use_canonical_publisher(self):
        candidates,evidence,status=apply(DOC,SOURCE_DOC,EMPTY_C,EMPTY_E,
                                          now="2026-11-22T16:20:00+00:00")
        self.assertEqual(status,[{
            "case_id":"rovigo-traviata-2027",
            "status":"reviewed_candidate_added"}])
        rec=evidence["evidence"][0]
        self.assertFalse(rec["corroboration"]["official_event_page_retrieved"])
        self.assertEqual(rec["content_hash_scope"],
                         "editorial_decision_not_primary_html")
        self.assertEqual(len(rec["corroboration"]["publisher_urls"]),2)
        self.assertEqual([(x["date"],x["starts_at"]) for x in rec["event_facts"]],[
            ("2027-01-22","2027-01-22T20:30:00+01:00"),
            ("2027-01-24","2027-01-24T16:00:00+01:00")])
        facts=json.loads((ROOT/"data/verified-launch-catalog.json").read_text())
        registry=json.loads((ROOT/"data/identity-registry.json").read_text())
        urls=json.loads((ROOT/"data/auto-source-urls.json").read_text())["urls"]
        published,ids,approved,report=promote(
            facts,registry,evidence,candidates,urls,today=date(2026,11,22))
        rovigo=[r for r in published["productions"]
                if r["municipality"]=="Rovigo" and r["title"]=="La traviata"]
        self.assertEqual(len(rovigo),1)
        self.assertEqual(rovigo[0]["dates"],[
            ["2027-01-22","20:30"],["2027-01-24","16:00"]])
        second,_,_,again=promote(
            published,ids,evidence,candidates,approved,today=date(2026,11,22))
        self.assertEqual(again["new_recite"],0)
        self.assertEqual(len([r for r in second["productions"]
                              if r["municipality"]=="Rovigo"
                              and r["title"]=="La traviata"]),1)

    def test_reviewed_decision_is_idempotent_and_never_replaces_primary_evidence(self):
        c,e,_=apply(DOC,SOURCE_DOC,EMPTY_C,EMPTY_E,
                    now="2026-11-22T16:20:00+00:00")
        c2,e2,result=apply(DOC,SOURCE_DOC,c,e,now="2026-11-23T10:00:00+00:00")
        self.assertEqual(c,c2)
        self.assertEqual(e,e2)
        self.assertEqual(result[0]["status"],"existing_evidence_preserved")
        primary=copy.deepcopy(e)
        primary["evidence"][0].pop("corroboration")
        primary["evidence"][0]["content_hash_scope"]="official_html"
        _,retained,status=apply(DOC,SOURCE_DOC,c,primary,
                                now="2026-11-23T10:00:00+00:00")
        self.assertEqual(retained,primary)
        self.assertEqual(status[0]["status"],"existing_evidence_preserved")

    def test_reviewed_decision_fail_closed_for_clock_and_policy_changes(self):
        for field,value in (
            ("reviewed_on","2026-11-20"),
            ("official_event_page_retrieved",True),
            ("independence_note",""),
            ("excluded_school_date","2027-01-22"),
        ):
            changed=copy.deepcopy(DOC)
            changed["decisions"][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                apply(changed,SOURCE_DOC,EMPTY_C,EMPTY_E,now="2026-11-22T16:20:00+00:00")
        changed=copy.deepcopy(DOC)
        changed["decisions"][0]["public_recite"][1]["time"]="18:00"
        with self.assertRaises(ValueError):
            apply(changed,SOURCE_DOC,EMPTY_C,EMPTY_E,now="2026-11-22T16:20:00+00:00")

if __name__=="__main__":
    unittest.main()

"""Source-labelled editorial proof must enter central canonical transaction only."""
import json
import unittest
from datetime import date

from scripts.auto_catalogue import promote
from scripts.publish_catalog_v2 import ROOT

ID="oa-index-7ff44b89bf8d688bbee0"
SOURCE="rovigo-sociale-opera-2026-27"
URL="https://www.comune.rovigo.it/teatrosociale/dettaglio-teatro/eventi/la-traviata-2027"

class RovigoEditorialEvidenceTests(unittest.TestCase):
    def test_record_has_explicit_secondary_provenance_and_two_public_clocks(self):
        candidates=json.loads((ROOT/"data/season-index-candidates.json").read_text())
        evidence=json.loads((ROOT/"data/candidate-detail-evidence.json").read_text())
        candidate=next(x for x in candidates["candidates"] if x["id"]==ID)
        record=next(x for x in evidence["evidence"] if x["candidate_id"]==ID)
        self.assertEqual(candidate["source_key"],SOURCE)
        self.assertEqual(candidate["official_url"],URL)
        self.assertEqual(record["source_url"],URL)
        self.assertEqual(record["content_hash_scope"],
                         "editorial_cross_source_provenance_v1")
        self.assertFalse(record["corroboration"]["official_event_page_retrieved"])
        self.assertEqual(len(record["corroboration"]["publisher_urls"]),2)
        self.assertEqual(len(record["event_facts"]),2)
        self.assertEqual([(x["date"],x["starts_at"]) for x in record["event_facts"]],[
            ("2027-01-22","2027-01-22T20:30:00+01:00"),
            ("2027-01-24","2027-01-24T16:00:00+01:00")])
        self.assertNotIn("2027-01-21",[x["date"] for x in record["event_facts"]])

    def test_review_record_uses_central_idempotent_publisher(self):
        candidates=json.loads((ROOT/"data/season-index-candidates.json").read_text())
        evidence=json.loads((ROOT/"data/candidate-detail-evidence.json").read_text())
        facts=json.loads((ROOT/"data/verified-launch-catalog.json").read_text())
        registry=json.loads((ROOT/"data/identity-registry.json").read_text())
        urls=json.loads((ROOT/"data/auto-source-urls.json").read_text())
        selected={"schema_version":1,"candidates":[
            x for x in candidates["candidates"] if x["id"]==ID]}
        detail={"schema_version":1,"evidence":[
            x for x in evidence["evidence"] if x["candidate_id"]==ID]}
        next_facts,ids,approved,report=promote(
            facts,registry,detail,selected,urls["urls"],today=date(2026,11,22))
        recite=[p for p in next_facts["productions"]
                if p["municipality"]=="Rovigo" and p["title"]=="La traviata"]
        # The test remains valid after the real refresh has already
        # published and closed this candidate.
        self.assertEqual(len(recite),1)
        self.assertEqual(recite[0]["dates"],[
            ["2027-01-22","20:30"],["2027-01-24","16:00"]])
        self.assertEqual(next_facts["productions"].count(recite[0]),1)
        self.assertEqual(report["new_recite"],2 if not any(
            p["municipality"]=="Rovigo" and p["title"]=="La traviata"
            for p in facts["productions"]) else 0)
        again,_,_,repeated=promote(next_facts,ids,detail,selected,approved,
                                   today=date(2026,11,22))
        self.assertEqual(repeated["new_recite"],0)
        self.assertEqual(len([p for p in again["productions"]
                              if p["municipality"]=="Rovigo" and
                              p["title"]=="La traviata"]),1)

if __name__=="__main__":
    unittest.main()

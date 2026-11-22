"""Regression: two different Savona works sharing one official URL get stable IDs."""
import json
import unittest
from datetime import date

from scripts.auto_catalogue import promote, split_verified_season
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY

KEY="savona-giocosa-rolling-opera"
URL="https://operagiocosa.it/"
CID="oa-index-savona-multiwork-fixture"
def facts():
    return [
        {"event_title":"La traviata","composer":"Giuseppe Verdi",
         "venue":"Teatro Chiabrera","date":"2028-10-23",
         "starts_at":"2028-10-23T20:00:00+02:00"},
        {"event_title":"La traviata","composer":"Giuseppe Verdi",
         "venue":"Teatro Chiabrera","date":"2028-10-25",
         "starts_at":"2028-10-25T15:30:00+01:00"},
        {"event_title":"I salvatori della mezzanotte","composer":"Daniele Furlati",
         "venue":"Teatro Chiabrera","date":"2028-11-07",
         "starts_at":"2028-11-07T18:00:00+01:00"},
    ]

class SavonaMultiworkIdentityTests(unittest.TestCase):
    def test_two_official_works_have_distinct_id_and_replay_safe(self):
        originals=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        evidence={"schema_version":1,"evidence":[{
            "candidate_id":CID,"source_key":KEY,"source_url":URL,
            "status":"needs_editorial_review","event_facts":facts()}]}
        candidates={"schema_version":1,"candidates":[{
            "id":CID,"source_key":KEY,"official_url":URL,"status":"needs_review"}]}
        self.assertEqual(len(split_verified_season(evidence["evidence"][0])),2)
        staged,ids,urls,report=promote(
            originals,registry,evidence,candidates,[],today=date(2026,11,22))
        produced=[p for p in staged["productions"] if
                  p["source_url"]==URL and p["municipality"]=="Savona"
                  and any(day.startswith("2028-") for day,_ in p["dates"])]
        self.assertEqual({p["title"] for p in produced},
                         {"La traviata","I salvatori della mezzanotte"},report)
        self.assertEqual(len({p["key"] for p in produced}),2)
        self.assertEqual(sum(len(p["dates"]) for p in produced),3)
        self.assertEqual({ids["stagings"][p["key"]]["work_id"] for p in produced},
                         {"oa-w-000001","oa-w-000097"})
        again,ids_again,_,retry=promote(
            staged,ids,evidence,candidates,urls,today=date(2026,11,22))
        self.assertEqual(retry["new_recite"],0)
        self.assertEqual(again,staged)
        self.assertEqual(ids_again,ids)

if __name__=="__main__":
    unittest.main()

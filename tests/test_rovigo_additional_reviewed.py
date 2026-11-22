"""Reviewed municipal Aida and Cenerentola recite flow through canonical IDs."""
import copy
import json
import unittest
from datetime import date

from scripts.apply_rovigo_additional_reviewed import CONFIG,apply,validate
from scripts.auto_catalogue import promote
from scripts.publish_catalog_v2 import ROOT

DOC=json.loads(CONFIG.read_text(encoding="utf-8"))
EMPTY_C={"schema_version":1,"candidates":[]}
EMPTY_E={"schema_version":1,"evidence":[]}
TIMES={"Aida":[("2027-02-26","20:30"),("2027-02-28","16:00")],
       "La Cenerentola":[("2027-04-23","20:30"),("2027-04-25","16:00")]}

class RovigoAdditionalReviewTests(unittest.TestCase):
    def test_only_exact_reviewed_works_urls_clocks_are_accepted(self):
        validate(DOC)
        for title in TIMES:
            case=next(x for x in DOC["cases"] if x["title"]==title)
            self.assertEqual([(x["date"],x["time"]) for x in case["performances"]],
                             TIMES[title])
        for title,changed_field in (
            ("Aida","time"),("La Cenerentola","secondary_event_url"),
        ):
            altered=copy.deepcopy(DOC)
            case=next(x for x in altered["cases"] if x["title"]==title)
            case["performances"][1][changed_field]="unverified"
            with self.subTest(title=title),self.assertRaises(ValueError):
                validate(altered)

    def test_two_productions_four_recite_and_idempotent_canonical_publisher(self):
        c,e,status=apply(DOC,EMPTY_C,EMPTY_E,
                         now="2026-11-22T16:28:11+00:00")
        self.assertEqual([x["status"] for x in status],
                         ["reviewed_candidate_added"]*2)
        self.assertEqual(len(c["candidates"]),2)
        self.assertEqual(len(e["evidence"]),2)
        self.assertTrue(all(
            record["corroboration"]["official_event_page_retrieved"] is False
            and record["content_hash_scope"]=="reviewed_secondary_evidence_not_official_html"
            for record in e["evidence"]))
        facts=json.loads((ROOT/"data/verified-launch-catalog.json").read_text())
        registry=json.loads((ROOT/"data/identity-registry.json").read_text())
        urls=json.loads((ROOT/"data/auto-source-urls.json").read_text())["urls"]
        new,ids,approved,report=promote(
            facts,registry,e,c,urls,today=date(2026,11,22))
        for title,wanted in TIMES.items():
            rows=[x for x in new["productions"] if x["municipality"]=="Rovigo"
                  and x["title"]==title]
            self.assertEqual(len(rows),1)
            self.assertEqual([tuple(x) for x in rows[0]["dates"]],wanted)
        self.assertEqual(report["new_recite"],4 if not any(
            r["municipality"]=="Rovigo" and r["title"] in TIMES
            for r in facts["productions"]) else 0)
        twice,_,_,again=promote(
            new,ids,e,c,approved,today=date(2026,11,22))
        self.assertEqual(again["new_recite"],0)
        self.assertEqual(len(twice["productions"]),len(new["productions"]))

    def test_existing_primary_evidence_is_not_overwritten(self):
        c,e,_=apply(DOC,EMPTY_C,EMPTY_E,
                    now="2026-11-22T16:28:11+00:00")
        c2,e2,outcome=apply(DOC,c,e,now="2026-11-23T10:00:00+00:00")
        self.assertEqual(c,c2)
        self.assertEqual(e,e2)
        self.assertEqual([x["status"] for x in outcome],
                         ["existing_evidence_preserved"]*2)

if __name__=="__main__":
    unittest.main()

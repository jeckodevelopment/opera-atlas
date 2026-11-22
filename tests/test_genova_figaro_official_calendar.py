"""Official Genova 2026 Figaro season programme preserves six showtimes."""
import json
import unittest
from datetime import date

from scripts.auto_catalogue import promote
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY
from opera_atlas.genova_figaro_program import KEY,URL,ROWS,verified_calendar

class GenovaFigaroOfficialCalendarTests(unittest.TestCase):
    def test_source_bound_six_official_showtimes(self):
        facts=verified_calendar(source_key=KEY,source_url=URL)
        self.assertEqual([(x["date"],x["starts_at"][11:16]) for x in facts],
                         list(ROWS))
        self.assertEqual({x["composer"] for x in facts},
                         {"Wolfgang Amadeus Mozart"})
        with self.assertRaises(ValueError):
            verified_calendar(source_key=KEY,source_url=URL+"?preview=1")

    def test_approved_evidence_uses_existing_figaro_work_identity(self):
        facts=json.loads(MANIFEST.read_text())
        registry=json.loads(REGISTRY.read_text())
        cid="oa-index-76fee4db156090b664aa"
        candidates={"schema_version":1,"candidates":[{
            "id":cid,"source_key":KEY,"official_url":URL,"status":"needs_review"}]}
        detail={"schema_version":1,"evidence":[{
            "candidate_id":cid,"source_key":KEY,"source_url":URL,
            "status":"needs_editorial_review",
            "event_facts":verified_calendar(source_key=KEY,source_url=URL)}]}
        new,ids,approved,report=promote(
            facts,registry,detail,candidates,[],today=date(2026,11,22))
        stages=[p for p in new["productions"] if p["source_url"]==URL]
        self.assertEqual(len(stages),1,report)
        self.assertEqual([tuple(x) for x in stages[0]["dates"]],list(ROWS))
        self.assertEqual(ids["stagings"][stages[0]["key"]]["work_id"],
                         "oa-w-000045")
        again,ids2,_,report2=promote(
            new,ids,detail,candidates,approved,today=date(2026,11,22))
        self.assertEqual(report2["new_recite"],0)
        self.assertEqual(new,again)
        self.assertEqual(ids,ids2)

if __name__=="__main__":
    unittest.main()

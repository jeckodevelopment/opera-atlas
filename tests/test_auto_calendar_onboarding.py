"""Unattended OperaLombardia date-only production onboarding."""
import json
import unittest
from datetime import date
from scripts.auto_catalogue import promote_calendar
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble

class CalendarAutoPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    @staticmethod
    def health(title="Tosca",venue="Teatro Sociale",city="Como",day="2027-05-09"):
        return {"schema_version":1,"sources":[{
            "key":"opera-lombardia-calendar-2026-27",
            "outcome":"review_required",
            "candidates":[{"title":title,"composer":None,
                           "venue":venue,"city":city,"date":day,"time":None}]
        }]}
    def test_known_work_and_existing_venue_are_catalogued_without_manual_action(self):
        h=self.health()
        facts,ids,report=promote_calendar(self.facts,self.registry,h,today=date(2026,11,20))
        self.assertEqual(report["new_recite"],1)
        self.assertEqual(report["new_stagings"],1)
        self.assertEqual(len(ids["works"]),len(self.registry["works"]))
        staged=next(x for x in facts["productions"] if x["key"].startswith("auto-lombardia-"))
        self.assertEqual(staged["dates"],[["2027-05-09",None]])
        self.assertEqual(staged["composer"],"Giacomo Puccini")
        assembled=assemble(facts,ids)
        self.assertEqual(len(assembled["performances"]),len(self.registry["performances"])+1)
        once,once_ids,again=promote_calendar(facts,ids,h,today=date(2026,11,20))
        self.assertEqual(again["new_recite"],0)
        self.assertEqual(once,facts)
        self.assertEqual(once_ids,ids)

    def test_unknown_or_ambiguous_work_is_never_falsely_identified(self):
        for title in ("Unknown Opera","La bohème"):
            facts,ids,report=promote_calendar(self.facts,self.registry,
                               self.health(title=title),today=date(2026,11,20))
            self.assertEqual(report["new_recite"],0)
            self.assertEqual(facts,self.facts)
            self.assertEqual(ids,self.registry)

    def test_unknown_venue_and_incomplete_date_do_not_publish(self):
        for city,day in (("Unknown City","2027-05-09"),("Como","not-a-date")):
            facts,ids,report=promote_calendar(self.facts,self.registry,
                                 self.health(city=city,day=day),today=date(2026,11,20))
            self.assertEqual(report["new_recite"],0)
            self.assertEqual(facts,self.facts)
            self.assertEqual(ids,self.registry)

    def test_unapproved_calendar_state_is_not_promoted(self):
        bad=self.health()
        bad["sources"][0]["outcome"]="unavailable_or_invalid"
        facts,ids,report=promote_calendar(self.facts,self.registry,bad,
                                            today=date(2026,11,20))
        self.assertEqual(report["new_recite"],0)
        self.assertEqual(facts,self.facts)
        self.assertEqual(ids,self.registry)
if __name__=="__main__":
    unittest.main()

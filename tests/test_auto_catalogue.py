"""Autonomous canonical promotion must preserve identities and fail safely."""
import copy
import json
import unittest
from datetime import date

from scripts.auto_catalogue import promote
from scripts.build_verified_catalog import MANIFEST, validate_auto_sources
from scripts.publish_catalog_v2 import REGISTRY, assemble

URL="https://www.teatroallascala.org/it/stagione/2026-2027/opera/fixture-new-staging.html"
CID="oa-index-test-macbeth"

class AutoCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        staged={(p["title"].casefold(),p["composer"].casefold())
                for p in cls.facts["productions"]
                if p["municipality"]=="Milano" and p["venue"]=="Teatro alla Scala"}
        cls.unstaged=next((w for w in cls.registry["works"].values()
                          if (w["title"].casefold(),w["composer"].casefold())
                          not in staged),None)
        if cls.unstaged is None:
            raise AssertionError("No unstaged canonical opera for isolated test")

    def fixture(self,*,composer=None, hour="2027-02-05T20:00:00+01:00",
                title=None,status="needs_review",url=URL):
        title=title or self.unstaged["title"]
        composer=composer or self.unstaged["composer"]
        candidates={"schema_version":1,"candidates":[
            {"id":CID,"source_key":"scala-season-2026-27","official_url":url,
             "status":status}]}
        evidence={"schema_version":1,"evidence":[{
            "candidate_id":CID,"source_key":"scala-season-2026-27",
            "source_url":url,"status":"needs_editorial_review",
            "event_facts":[{
                "event_title":title,"composer":composer,"date":"2027-02-05",
                "starts_at":hour,"venue":"Teatro alla Scala"}]
        }]}
        return evidence,candidates

    def test_new_production_and_recita_publish_with_stable_ids(self):
        evidence,candidates=self.fixture()
        facts,ids,urls,report=promote(self.facts,self.registry,evidence,candidates,[],
                                        today=date(2026,11,20))
        self.assertEqual(report["new_stagings"],1)
        self.assertEqual(report["new_recite"],1)
        self.assertIn(URL,urls)
        self.assertEqual(len(facts["productions"]),len(self.facts["productions"])+1)
        self.assertEqual(len(ids["performances"]),len(self.registry["performances"])+1)
        self.assertEqual(len(ids["works"]),len(self.registry["works"]))
        output=assemble(facts,ids,approved_extra=set(urls))
        self.assertEqual(len(output["performances"]),len(self.registry["performances"])+1)
        again,again_ids,again_urls,report2=promote(facts,ids,evidence,candidates,urls,
                                                     today=date(2026,11,20))
        self.assertEqual(report2["new_recite"],0)
        self.assertEqual(again,facts)
        self.assertEqual(again_ids,ids)
        self.assertEqual(again_urls,urls)

    def test_unknown_or_wrong_composer_requires_no_human_reconciliation(self):
        for composer in ("Unknown Composer","Another Composer with No Matching Opera"):
            evidence,candidates=self.fixture(composer=composer)
            facts,ids,urls,report=promote(self.facts,self.registry,evidence,
                                            candidates,[],today=date(2026,11,20))
            self.assertEqual(report["new_recite"],0)
            self.assertEqual(facts,self.facts)
            self.assertEqual(ids,self.registry)
            self.assertEqual(urls,[])
            self.assertEqual(report["auto_skipped"][0]["reason"],
                             "unknown_work_needs_authority_data")

    def test_no_timestamp_or_wrong_domain_never_publishes(self):
        for hour,url in ((None,URL),("2027-02-05T20:00:00+01:00",
                                    "https://evil.example/opera/macbeth.html")):
            evidence,candidates=self.fixture(hour=hour,url=url)
            facts,ids,urls,report=promote(self.facts,self.registry,evidence,
                                             candidates,[],today=date(2026,11,20))
            self.assertEqual(report["new_recite"],0)
            self.assertEqual(facts,self.facts)
            self.assertEqual(ids,self.registry)

    def test_unknown_official_url_not_silently_allowlisted(self):
        with self.assertRaises(ValueError):
            validate_auto_sources(["https://evil.example/opera/fake.html"])
        with self.assertRaises(ValueError):
            validate_auto_sources(["https://www.arena.it/arena-opera-festival/regolamento/"])

    def test_change_existing_date_does_not_override_canonical_data(self):
        evidence,candidates=self.fixture()
        facts,ids,urls,report=promote(self.facts,self.registry,evidence,candidates,[],
                                         today=date(2026,11,20))
        changed=copy.deepcopy(evidence)
        changed["evidence"][0]["event_facts"][0]["starts_at"]="2027-02-05T21:00:00+01:00"
        again,after,_,status=promote(facts,ids,changed,candidates,urls,
                                      today=date(2026,11,20))
        self.assertEqual(status["new_recite"],0)
        self.assertEqual(status["auto_skipped"][0]["reason"],"conflicting_existing_time")
        self.assertEqual(after,ids)
        self.assertEqual(again,facts)

if __name__=="__main__":
    unittest.main()

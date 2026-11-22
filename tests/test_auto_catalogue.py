"""Autonomous canonical promotion must preserve identities and fail safely."""
import copy
import json
import unittest
from datetime import date

from scripts.auto_catalogue import promote, split_verified_season
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

    def test_complete_official_multiwork_seasons_publish_distinct_stagings(self):
        from scripts.collect_candidate_details import parse_known_opera_detail
        from tests.test_lecce_provincia_source import HTML as LECCE_HTML
        from tests.test_padova_opera_source import HTML as PADOVA_HTML
        from opera_atlas.lecce_provincia_parser import URL as LECCE_URL
        from tests.test_padova_opera_source import URL as PADOVA_URL
        cases=(
            ("lecce-provincia-politeama-2026",LECCE_URL,LECCE_HTML,3,6),
            ("padova-verdi-opera-2026",PADOVA_URL,PADOVA_HTML,2,5),
        )
        for key,url,html,productions,recite in cases:
            with self.subTest(source=key):
                rows=parse_known_opera_detail(key,url,html,self.registry)
                self.assertEqual(len(rows),recite)
                candidate_id="test-"+key
                candidate={"schema_version":1,"candidates":[{
                    "id":candidate_id,"source_key":key,"official_url":url,
                    "status":"needs_review"}]}
                evidence={"schema_version":1,"evidence":[{
                    "candidate_id":candidate_id,"source_key":key,"source_url":url,
                    "status":"needs_editorial_review","event_facts":rows}]}
                self.assertEqual(len(split_verified_season(evidence["evidence"][0])),productions)
                existing=[p for p in self.facts["productions"]
                          if p["source_url"]==url]
                # After a successful previous refresh the same source is
                # replay-safe, rather than creating the same events again.
                self.assertIn(len(existing),(0,productions))
                prior_recite=sum(len(p["dates"]) for p in existing)
                self.assertIn(prior_recite,(0,recite))
                facts,ids,urls,report=promote(self.facts,self.registry,evidence,
                    candidate,[],today=date(2026,11,22))
                self.assertEqual(report["new_stagings"],productions-len(existing))
                self.assertEqual(report["new_recite"],recite-prior_recite)
                staged=[p for p in facts["productions"] if p["source_url"]==url]
                self.assertEqual(len(staged),productions)
                self.assertEqual(sum(len(p["dates"]) for p in staged),recite)
                if not existing:self.assertIn(url,urls)
                again,again_ids,_,second=promote(
                    facts,ids,evidence,candidate,urls,today=date(2026,11,22))
                self.assertEqual(second["new_recite"],0)
                self.assertEqual(again,facts)
                self.assertEqual(again_ids,ids)

    def test_incomplete_multiwork_season_does_not_publish_partial_data(self):
        from tests.test_lecce_provincia_source import HTML as LECCE_HTML
        from opera_atlas.lecce_provincia_parser import URL,parse_program
        from scripts.build_verified_catalog import official_local_time
        rows=[{"event_title":title,"composer":composer,"venue":venue,
               "date":day,"starts_at":official_local_time(day,clock)}
              for title,composer,venue,day,clock in parse_program(LECCE_HTML,url=URL)]
        evidence={"schema_version":1,"evidence":[{
            "candidate_id":"lecce-incomplete","source_key":"lecce-provincia-politeama-2026",
            "source_url":URL,"status":"needs_editorial_review","event_facts":rows[:-1]}]}
        self.assertEqual(len(split_verified_season(evidence["evidence"][0])),1)
        candidates={"schema_version":1,"candidates":[{
            "id":"lecce-incomplete","source_key":"lecce-provincia-politeama-2026",
            "official_url":URL,"status":"needs_review"}]}
        facts,ids,urls,report=promote(self.facts,self.registry,evidence,
                                      candidates,[],today=date(2026,11,22))
        self.assertEqual(report["new_recite"],0)
        self.assertEqual(facts,self.facts)
        self.assertEqual(ids,self.registry)

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

    def test_alternate_official_title_uses_exact_canonical_qid(self):
        evidence,candidates=self.fixture(title="Verified Alternative Title")
        registry=copy.deepcopy(self.registry)
        key=next(k for k,v in registry["works"].items()
                 if v["id"]==self.unstaged["id"])
        registry["works"][key]["wikidata_id"]="Q987654321"
        intel={"works":[{
            "candidate_id":CID,"source_key":"scala-season-2026-27",
            "source_url":URL,"composer":self.unstaged["composer"],
            "wikidata_id":"Q987654321"}]}
        facts,ids,urls,report=promote(self.facts,registry,evidence,candidates,[],
                                    today=date(2026,11,20),intelligence=intel)
        self.assertEqual(report["new_stagings"],1)
        self.assertEqual(report["new_recite"],1)
        created=[p for p in facts["productions"] if p["source_url"]==URL]
        self.assertEqual(created[0]["title"],self.unstaged["title"])
        self.assertEqual(len(ids["works"]),len(registry["works"]))

        for altered in (
            {**intel["works"][0],"wikidata_id":"Q999999"},
            {**intel["works"][0],"composer":"Another Composer"},
            {**intel["works"][0],"source_url":"https://example.org/fake"},
        ):
            _,_,urls,report=promote(self.facts,registry,evidence,candidates,[],
                                    today=date(2026,11,20),
                                    intelligence={"works":[altered]})
            self.assertEqual(urls,[])
            self.assertEqual(report["new_recite"],0)

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

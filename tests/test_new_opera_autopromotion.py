"""End-to-end graph creation for entirely new verified opera and synopsis."""
import copy
import json
import unittest
from datetime import date
from scripts.auto_catalogue import promote_new_works
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.publish_work_editorial import EDITORIAL,build_editorial

URL="https://www.teatroallascala.org/it/stagione/2026-2027/opera/anna-bolena.html"
CID="oa-index-test-new-anna"

class NewOperaPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.editorial=json.loads(EDITORIAL.read_text(encoding="utf-8"))

    def fixture(self):
        candidates={"schema_version":1,"candidates":[{
            "id":CID,"source_key":"scala-season-2026-27",
            "official_url":URL,"status":"needs_review"}]}
        evidence={"schema_version":1,"evidence":[{
            "candidate_id":CID,"source_key":"scala-season-2026-27",
            "source_url":URL,"status":"needs_editorial_review",
            "event_facts":[{
                "event_title":"Anna Bolena","composer":"Gaetano Donizetti",
                "date":"2027-06-02",
                "starts_at":"2027-06-02T20:00:00+02:00",
                "venue":"Teatro alla Scala"}
            ]}]}
        enrichment={"schema_version":1,"works":[{
            "candidate_id":CID,"source_key":"scala-season-2026-27",
            "source_url":URL,"wikidata_id":"Q111",
            "title":"Anna Bolena","composer":"Gaetano Donizetti",
            "synopsis":"Anna Bolena affronta le tensioni della corte e un destino "
                       "segnato da passioni e lotte per il potere."
        }]}
        return evidence,candidates,enrichment

    def test_new_opera_and_synopsis_are_published_as_one_graph(self):
        evidence,candidates,enrichment=self.fixture()
        facts,ids,urls,editorial,report=promote_new_works(
            self.facts,self.registry,evidence,candidates,enrichment,
            self.editorial,[],today=date(2026,11,20))
        self.assertEqual((report["new_works"],report["new_stagings"],report["new_recite"]),
                         (1,1,1))
        self.assertEqual(len(ids["works"]),len(self.registry["works"])+1)
        self.assertIn("anna-bolena",editorial["synopses"])
        self.assertEqual(urls,[URL])
        graph=assemble(facts,ids,approved_extra=set(urls))
        self.assertEqual(len(graph["performances"]),len(self.registry["performances"])+1)
        from scripts.publish_work_editorial import HISTORY
        history=json.loads(HISTORY.read_text(encoding="utf-8"))
        history["works"]["anna-bolena"]={
            "librettist":"Giovanni Example","premiere_year":1830,
            "premiere_venue":"Teatro Nuovo","premiere_city":"Milano",
            "sources":["https://www.wikidata.org/wiki/Q111"]}
        card=build_editorial(facts,ids,editorial,approved_extra=set(urls),
                             history=history)
        self.assertEqual(len(card["works"]),len(ids["works"]))
        self.assertTrue(any(x["slug"]=="anna-bolena" for x in card["works"]))
        second=promote_new_works(facts,ids,evidence,candidates,enrichment,editorial,urls,
                                 today=date(2026,11,20))
        self.assertEqual(second[-1]["new_works"],0)
        self.assertEqual(second[0],facts)
        self.assertEqual(second[1],ids)

    def test_unattended_promotion_requires_full_historical_profile(self):
        evidence,candidates,enrichment=self.fixture()
        from scripts.publish_work_editorial import HISTORY
        existing=json.loads(HISTORY.read_text(encoding="utf-8"))
        pending=copy.deepcopy(enrichment)
        nohistory=promote_new_works(self.facts,self.registry,evidence,candidates,pending,
                                   self.editorial,[],today=date(2026,11,20),history=existing)
        self.assertEqual(nohistory[-1]["new_works"],0)
        self.assertEqual(nohistory[4],existing)
        pending["works"][0]["history"]={
            "librettist":"Giovanni Example","premiere_year":1830,
            "premiere_venue":"Teatro Nuovo","premiere_city":"Milano",
            "sources":["https://www.wikidata.org/wiki/Q111"]}
        accepted=promote_new_works(self.facts,self.registry,evidence,candidates,pending,
                                  self.editorial,[],today=date(2026,11,20),history=existing)
        self.assertEqual(accepted[-1]["new_works"],1)
        self.assertEqual(accepted[4]["works"]["anna-bolena"]["premiere_year"],1830)
        output=build_editorial(accepted[0],accepted[1],accepted[3],
                              approved_extra=set(accepted[2]),history=accepted[4])
        self.assertEqual(next(x for x in output["works"] if x["slug"]=="anna-bolena")
                         ["history"]["librettist"],"Giovanni Example")

    def test_wrong_composer_or_unproven_date_cannot_create_new_work(self):
        evidence,candidates,enrichment=self.fixture()
        variants=[]
        bad=copy.deepcopy(evidence)
        bad["evidence"][0]["event_facts"][0]["composer"]="Another composer"
        variants.append(bad)
        bad=copy.deepcopy(evidence)
        bad["evidence"][0]["event_facts"][0]["starts_at"]="2027-06-02T20:00:00"
        variants.append(bad)
        bad=copy.deepcopy(evidence)
        bad["evidence"][0]["event_facts"][0]["venue"]="Unknown theatre"
        variants.append(bad)
        for modified in variants:
            facts,ids,urls,editorial,report=promote_new_works(
                self.facts,self.registry,modified,candidates,enrichment,
                self.editorial,[],today=date(2026,11,20))
            self.assertEqual(report["new_works"],0)
            self.assertEqual(facts,self.facts)
            self.assertEqual(ids,self.registry)
            self.assertEqual(editorial,self.editorial)
            self.assertEqual(urls,[])

    def test_unverified_synopsis_or_source_is_not_published(self):
        evidence,candidates,enrichment=self.fixture()
        intel=copy.deepcopy(enrichment)
        intel["works"][0]["synopsis"]="Too short"
        one=promote_new_works(self.facts,self.registry,evidence,candidates,intel,
                              self.editorial,[],today=date(2026,11,20))
        self.assertEqual(one[-1]["new_works"],0)
        bad=copy.deepcopy(candidates)
        bad["candidates"][0]["official_url"]="https://evil.example/opera/anna-bolena.html"
        two=promote_new_works(self.facts,self.registry,evidence,bad,enrichment,
                              self.editorial,[],today=date(2026,11,20))
        self.assertEqual(two[-1]["new_works"],0)
if __name__=="__main__":
    unittest.main()

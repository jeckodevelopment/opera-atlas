"""End-to-end graph creation for entirely new verified opera and synopsis."""
import copy
import json
import unittest
from datetime import date
from unittest.mock import patch
from scripts.auto_catalogue import promote_new_works,merge_official_poster_cache
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.publish_work_editorial import EDITORIAL,build_editorial

URL="https://www.teatroallascala.org/it/stagione/2026-2027/opera/fixture-opera.html"
CID="oa-index-test-new-fixture"

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
                "event_title":"Fixture Opera","composer":"Gaetano Donizetti",
                "date":"2027-06-02",
                "starts_at":"2027-06-02T20:00:00+02:00",
                "venue":"Teatro alla Scala"}
            ]}]}
        enrichment={"schema_version":1,"works":[{
            "candidate_id":CID,"source_key":"scala-season-2026-27",
            "source_url":URL,"wikidata_id":"Q111",
            "title":"Fixture Opera","composer":"Gaetano Donizetti",
            "synopsis":"Fixture Opera affronta le tensioni della corte e un destino "
                       "segnato da passioni e lotte per il potere.",
            "history":{"librettist":"Giovanni Example",
                       "premiere_year":1830,"premiere_venue":"Teatro Nuovo",
                       "premiere_city":"Milano",
                       "sources":["https://www.wikidata.org/wiki/Q111"]}
        }]}
        return evidence,candidates,enrichment

    def test_new_work_is_deferred_until_authentic_poster_is_verified(self):
        evidence,candidates,enrichment=self.fixture()
        skipped=promote_new_works(
            self.facts,self.registry,evidence,candidates,enrichment,
            self.editorial,[],today=date(2026,11,20),require_image=True)
        self.assertEqual(skipped[-1]["new_works"],0)
        self.assertTrue(any(x["reason"]=="verified_work_image_missing"
                            for x in skipped[-1]["auto_skipped"]))
        self.assertEqual(skipped[1],self.registry)

        poster={"image_url":"https://www.teatroallascala.org/static/upload/fixture/fixture-opera-poster.jpg",
                "source_url":URL,"kind":"official_production_image",
                "alt":"Fixture Opera, immagine ufficiale", "credit":"Teatro alla Scala"}
        evidence["evidence"][0]["poster_evidence"]=poster
        result=promote_new_works(
            self.facts,self.registry,evidence,candidates,enrichment,
            self.editorial,[],today=date(2026,11,20),require_image=True)
        self.assertEqual(result[-1]["new_works"],1)
        for invalid in (
            {**poster,"image_url":"https://example.org/fixture-opera.jpg"},
            {**poster,"image_url":"https://www.teatroallascala.org/static/upload/other/nabucco.jpg"},
            {**poster,"source_url":"https://www.teatroallascala.org/it/fake.html"},
        ):
            evidence["evidence"][0]["poster_evidence"]=invalid
            denied=promote_new_works(
                self.facts,self.registry,evidence,candidates,enrichment,
                self.editorial,[],today=date(2026,11,20),require_image=True)
            self.assertEqual(denied[-1]["new_works"],0)

    def test_archival_art_promotes_new_work_without_official_poster_cache(self):
        # A trustworthy archival image is already in the archival work bank.
        # Its lack of an official-production image must not crash main().
        evidence,candidates,enrichment=self.fixture()
        with patch("scripts.publish_work_posters.load_archival_art",
                   return_value={"fixture-opera":{"image_url":
                       "https://commons.wikimedia.org/wiki/Special:Redirect/file/Fixture.png"}}):
            result=promote_new_works(
                self.facts,self.registry,evidence,candidates,enrichment,
                self.editorial,[],today=date(2026,11,20),require_image=True)
        self.assertEqual(result[-1]["new_works"],1)
        self.assertEqual(merge_official_poster_cache(None,{}),None)
        self.assertEqual(merge_official_poster_cache({"schema_version":2,
                                                      "posters":{}},{}),None)
        before={"schema_version":2,"posters":{},"checks":{}}
        image={"work_id":"oa-w-123456","kind":"official_production_image",
               "image_url":"https://www.teatroallascala.org/example.jpg"}
        after=merge_official_poster_cache(before,{"oa-w-123456":image})
        self.assertEqual(after["posters"]["oa-w-123456"],image)
        self.assertEqual(before["posters"],{})
        with self.assertRaises(ValueError):
            merge_official_poster_cache(before,{"oa-w-999999":image})

    def test_new_opera_and_synopsis_are_published_as_one_graph(self):
        evidence,candidates,enrichment=self.fixture()
        facts,ids,urls,editorial,report=promote_new_works(
            self.facts,self.registry,evidence,candidates,enrichment,
            self.editorial,[],today=date(2026,11,20))
        self.assertEqual((report["new_works"],report["new_stagings"],report["new_recite"]),
                         (1,1,1))
        self.assertEqual(len(ids["works"]),len(self.registry["works"])+1)
        self.assertIn("fixture-opera",editorial["synopses"])
        self.assertEqual(urls,[URL])
        graph=assemble(facts,ids,approved_extra=set(urls))
        self.assertEqual(len(graph["performances"]),len(self.registry["performances"])+1)
        from scripts.publish_work_editorial import HISTORY
        history=json.loads(HISTORY.read_text(encoding="utf-8"))
        history["works"]["fixture-opera"]={
            "librettist":"Giovanni Example","premiere_year":1830,
            "premiere_venue":"Teatro Nuovo","premiere_city":"Milano",
            "sources":["https://www.wikidata.org/wiki/Q111"]}
        card=build_editorial(facts,ids,editorial,approved_extra=set(urls),
                             history=history)
        self.assertEqual(len(card["works"]),len(ids["works"]))
        self.assertTrue(any(x["slug"]=="fixture-opera" for x in card["works"]))
        second=promote_new_works(facts,ids,evidence,candidates,enrichment,editorial,urls,
                                 today=date(2026,11,20))
        self.assertEqual(second[-1]["new_works"],0)
        self.assertEqual(second[0],facts)
        self.assertEqual(second[1],ids)

    def test_verified_identity_without_history_remains_unpublished(self):
        evidence,candidates,enrichment=self.fixture()
        enrichment["works"][0]["history"]=None
        from scripts.publish_work_editorial import HISTORY
        history=json.loads(HISTORY.read_text(encoding="utf-8"))
        result=promote_new_works(self.facts,self.registry,evidence,candidates,
                                 enrichment,self.editorial,[],
                                 today=date(2026,11,20),history=history,
                                 require_image=True)
        self.assertEqual(result[-1]["new_works"],0)
        self.assertIn({"candidate_id":CID,"reason":"incomplete_work_editorial"},
                      result[-1]["auto_skipped"])
        self.assertEqual(result[1],self.registry)

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
        bad["candidates"][0]["official_url"]="https://evil.example/opera/fixture-opera.html"
        two=promote_new_works(self.facts,self.registry,evidence,bad,enrichment,
                              self.editorial,[],today=date(2026,11,20))
        self.assertEqual(two[-1]["new_works"],0)
if __name__=="__main__":
    unittest.main()

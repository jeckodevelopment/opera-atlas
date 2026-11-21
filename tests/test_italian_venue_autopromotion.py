"""Approved source facts must resolve to the correct canonical theatre."""
import json
import unittest
from datetime import date
from scripts.auto_catalogue import promote
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble

CASES=[
 ("carlo-felice-season-2026-27","https://www.carlofelice.it/spettacolo/pagliacci/",
  "Pagliacci","Ruggero Leoncavallo","Teatro Carlo Felice","Genova"),
 ("donizetti-opera-2026","https://www.donizettiopera.org/it/evento/italiana-in-algeri/",
  "L’italiana in Algeri","Gioachino Rossini","Teatro Sociale","Bergamo"),
 ("donizetti-opera-2026","https://www.donizettiopera.org/it/evento/italiana-in-algeri/",
  "L’italiana in Algeri","Gioachino Rossini","Teatro Donizetti","Bergamo"),
]

class VerifiedVenuePromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.ids=json.loads(REGISTRY.read_text(encoding="utf-8"))

    def fixture(self,key,url,title,composer,venue):
        candidate={"id":"fixture-venue","source_key":key,"official_url":url,
                   "status":"needs_review"}
        entry={"candidate_id":candidate["id"],"source_key":key,
               "source_url":url,"status":"needs_editorial_review",
               "event_facts":[{"event_title":title,"composer":composer,
                               "date":"2027-03-12",
                               "starts_at":"2027-03-12T20:00:00+01:00",
                               "venue":venue}]}
        return {"evidence":[entry]},{"candidates":[candidate]}

    def test_known_operas_publish_to_verified_venues_only(self):
        for key,url,title,composer,venue,city in CASES:
            with self.subTest(venue=venue):
                evidence,candidates=self.fixture(key,url,title,composer,venue)
                facts,ids,urls,result=promote(
                    self.facts,self.ids,evidence,candidates,[],today=date(2026,11,21))
                self.assertEqual(result["new_recite"],1,result)
                self.assertEqual(result["new_stagings"],1)
                self.assertIn(url,urls)
                staging=next(p for p in facts["productions"] if p["source_url"]==url
                             and p["key"].startswith("auto-"))
                self.assertEqual((staging["municipality"],staging["venue"]),(city,venue))
                published=assemble(facts,ids,approved_extra=set(urls))
                self.assertTrue(any(x["local_date"]=="2027-03-12"
                                    for x in published["performances"]))
                again,after,after_urls,res2=promote(
                    facts,ids,evidence,candidates,urls,today=date(2026,11,21))
                self.assertEqual(res2["new_recite"],0)
                self.assertEqual(again,facts)
                self.assertEqual(after,ids)
                self.assertEqual(after_urls,urls)

    def test_unknown_missing_or_conflicting_venue_never_publishes(self):
        key,url,title,composer,venue,_=CASES[1]
        for wrong in (None,"Teatro Grande","Teatro Carlo Felice","Teatro Nuovo"):
            with self.subTest(venue=wrong):
                evidence,candidates=self.fixture(key,url,title,composer,wrong)
                facts,ids,urls,result=promote(
                    self.facts,self.ids,evidence,candidates,[],today=date(2026,11,21))
                self.assertEqual(result["new_recite"],0)
                self.assertEqual(result["auto_skipped"][0]["reason"],
                                 "unknown_or_conflicting_venue")
                self.assertEqual(facts,self.facts)
                self.assertEqual(ids,self.ids)
                self.assertEqual(urls,[])
        evidence,candidates=self.fixture(key,url,title,composer,venue)
        evidence["evidence"][0]["event_facts"].append(
            {**evidence["evidence"][0]["event_facts"][0],"venue":"Teatro Donizetti",
             "date":"2027-03-13","starts_at":"2027-03-13T20:00:00+01:00"})
        facts,ids,urls,result=promote(
            self.facts,self.ids,evidence,candidates,[],today=date(2026,11,21))
        self.assertEqual(result["new_recite"],0)
        self.assertEqual(facts,self.facts)

    def test_homonymous_title_never_overrides_composer(self):
        key,url,title,composer,venue,_=CASES[0]
        evidence,candidates=self.fixture(key,url,"La bohème",
                                          "Giacomo Puccini",venue)
        facts,ids,urls,result=promote(
            self.facts,self.ids,evidence,candidates,[],today=date(2026,11,21))
        if result["new_recite"]:
            key_result=next(p for p in facts["productions"]
                            if p["source_url"]==url and p["key"].startswith("auto-"))
            self.assertEqual(key_result["composer"],"Giacomo Puccini")
        self.assertEqual([w for w in ids["works"].values()
                          if w["title"]=="La bohème"],[w for w in self.ids["works"].values()
                          if w["title"]=="La bohème"])

if __name__=="__main__":
    unittest.main()

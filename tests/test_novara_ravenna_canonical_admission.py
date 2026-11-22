"""Verified repertory from Novara Coccia and Ravenna Alighieri is publishable."""
import json
import unittest
from datetime import date

from scripts.auto_catalogue import promote,VENUE_BY_SOURCE
from scripts.build_verified_catalog import MANIFEST,official_local_time
from scripts.publish_catalog_v2 import REGISTRY,assemble

CASES=[
 ("coccia-novara-opera-2027",
 "https://www.fondazioneteatrococcia.it/stagione-27-rigoletto.html",
 "Rigoletto","Giuseppe Verdi","Novara","Teatro Coccia",
 [("2027-01-29","20:00"),("2027-01-30","20:00"),
  ("2027-01-31","16:00"),("2027-02-02","20:00")]),
 ("ravenna-alighieri-cherubini-2027",
 "https://www.orchestracherubini.it/eventi/pagliacci-2/",
 "Pagliacci","Ruggero Leoncavallo","Ravenna","Teatro Dante Alighieri",
 [("2027-01-15","20:00"),("2027-01-17","15:30")])
]
class RegionalSourceEligibilityTests(unittest.TestCase):
    def test_official_performances_have_independent_canonical_venues(self):
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        for key,url,title,composer,city,venue,dates in CASES:
            self.assertEqual(VENUE_BY_SOURCE[key],(city,venue))
            self.assertIn(city+"|"+venue,registry["venues"])
            self.assertTrue(any(w["title"]==title and w["composer"]==composer
                                for w in registry["works"].values()))

    def test_six_dated_recite_two_stagings_no_invented_work(self):
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        # Existing real candidate promotions must not invalidate a
        # first-publication regression. Work on an in-memory baseline
        # without only the tested exact-source staging and its recite.
        source_urls={item[1] for item in CASES}
        deleted={p["key"] for p in facts["productions"]
                 if p["source_url"] in source_urls}
        ids={registry["stagings"][key]["id"] for key in deleted}
        facts["productions"]=[p for p in facts["productions"]
                              if p["key"] not in deleted]
        registry["stagings"]={k:v for k,v in registry["stagings"].items()
                              if k not in deleted}
        registry["performances"]={k:v for k,v in registry["performances"].items()
                                  if v["staging_id"] not in ids}
        evidence={"schema_version":1,"evidence":[]}
        candidates={"schema_version":1,"candidates":[]}
        for i,(key,url,title,composer,city,venue,dates) in enumerate(CASES):
            cid="source-verified-"+str(i)
            candidates["candidates"].append({
                "id":cid,"source_key":key,"official_url":url,"status":"needs_review"})
            evidence["evidence"].append({
                "candidate_id":cid,"source_key":key,"source_url":url,
                "status":"needs_editorial_review",
                "event_facts":[{"event_title":title,"composer":composer,
                                "venue":venue,"date":day,
                                "starts_at":official_local_time(day,clock)}
                               for day,clock in dates]})
        next_facts,next_ids,urls,health=promote(
            facts,registry,evidence,candidates,[],today=date(2026,11,22))
        self.assertEqual(health["new_stagings"],2,health)
        self.assertEqual(health["new_recite"],6,health)
        self.assertEqual(health["auto_skipped"],[],health)
        self.assertEqual(next_ids["works"],registry["works"])
        assembled=assemble(next_facts,next_ids,approved_extra=set(urls))
        self.assertEqual(len(assembled["performances"]),
                         len(registry["performances"])+6)
        for key,url,title,composer,city,venue,dates in CASES:
            matches=[x for x in next_facts["productions"] if
                     x["source_url"]==url and x["municipality"]==city]
            self.assertEqual(len(matches),1)
            self.assertEqual(matches[0]["dates"],[[day,hour] for day,hour in dates])
        again,stable,urls_again,health_again=promote(
            next_facts,next_ids,evidence,candidates,urls,today=date(2026,11,22))
        self.assertEqual(health_again["new_recite"],0)
        self.assertEqual(again,next_facts)
        self.assertEqual(stable,next_ids)
        self.assertEqual(urls_again,urls)

if __name__=="__main__":
    unittest.main()

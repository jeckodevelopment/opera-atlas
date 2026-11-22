"""Four source-verified 2026/27 regional theaters must become canonical.

Covers physical venue identity, composer distinction, timezone, immutable
work IDs, official candidate source matching, and idempotent second refresh.
"""
import json
import unittest
from datetime import date

from scripts.auto_catalogue import promote,VENUE_BY_SOURCE,verified_venue
from scripts.build_verified_catalog import MANIFEST,official_local_time
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.publish_venue_directory import SOURCE as DIRECTORY,build as build_directory

CASES=[
("pisa-verdi-opera-2026-27","https://teatrodipisa.it/spettacolo/otello/",
 "Otello","Giuseppe Verdi","Pisa","Teatro Verdi","Toscana","2027-02-05","20:30"),
("filarmonico-verona-opera-2027","https://www.arena.it/teatro-filarmonico-verona/2027/fidelio/",
 "Fidelio","Ludwig van Beethoven","Verona","Teatro Filarmonico","Veneto","2027-04-11","15:30"),
("salerno-verdi-opera-2026","https://cultura.comune.salerno.it/eventi/trovatore-2026/",
 "Il trovatore","Giuseppe Verdi","Salerno","Teatro Municipale Giuseppe Verdi","Campania","2026-04-16","21:00"),
("macerata-festival-2027","https://www.sferisterio.it/macerata-opera-festival/tosca",
 "Tosca","Giacomo Puccini","Macerata","Arena Sferisterio","Marche","2027-07-16","21:00")]

class RegionalCanonicalPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.directory=json.loads(DIRECTORY.read_text(encoding="utf-8"))
        # Exercise a clean first publication even after these real official
        # source URLs have entered the live catalog. Strip only the precise
        # source-bound stagings/recite from IN-MEMORY fixtures; never rewrite
        # persistent canonical JSON or regress already published identities.
        known_urls={case[1] for case in CASES}
        removed_keys={p["key"] for p in cls.facts["productions"]
                      if p["source_url"] in known_urls}
        removed_ids={cls.registry["stagings"][key]["id"]
                     for key in removed_keys}
        cls.facts["productions"]=[
            p for p in cls.facts["productions"] if p["key"] not in removed_keys]
        cls.registry["stagings"]={
            k:v for k,v in cls.registry["stagings"].items()
            if k not in removed_keys}
        cls.registry["performances"]={
            k:v for k,v in cls.registry["performances"].items()
            if v["staging_id"] not in removed_ids}

    def test_official_sources_are_explicit_and_do_not_conflate_home_theaters(self):
        directory={(x["city"],x["name"]):x for x in self.directory["venues"]}
        for key,url,title,composer,city,venue,region,day,clock in CASES:
            with self.subTest(source=key):
                self.assertEqual(VENUE_BY_SOURCE[key],(city,venue))
                self.assertIn((city,venue),directory)
                self.assertEqual(directory[city,venue]["region"],region)
                self.assertNotEqual(venue,"Arena di Verona" if city=="Verona" else "Unknown venue")
                official=[{"event_title":title,"composer":composer,
                           "venue":venue,"date":day,
                           "starts_at":official_local_time(day,clock)}]
                self.assertEqual(verified_venue(key,official,self.registry)[:2],(city,venue))
                self.assertIsNone(verified_venue(key,[{**official[0],"venue":"Fake venue"}],
                                                 self.registry))

    def test_known_works_publish_separately_and_repeat_safely(self):
        candidates={"schema_version":1,"candidates":[]}
        evidence={"schema_version":1,"evidence":[]}
        for i,(key,url,title,composer,city,venue,region,day,clock) in enumerate(CASES):
            cid=f"oa-index-fixture-region-{i}"
            candidates["candidates"].append({
              "id":cid,"source_key":key,"official_url":url,"status":"needs_review"})
            evidence["evidence"].append({
              "candidate_id":cid,"source_key":key,"source_url":url,
              "status":"needs_editorial_review",
              "event_facts":[{"event_title":title,"composer":composer,
                              "venue":venue,"date":day,
                              "starts_at":official_local_time(day,clock)}]})
        facts,ids,urls,report=promote(self.facts,self.registry,evidence,candidates,[],
                                     today=date(2026,11,22))
        self.assertEqual((report["new_stagings"],report["new_recite"]),(4,4),report)
        self.assertFalse(report["auto_skipped"],report)
        self.assertEqual(len(ids["works"]),len(self.registry["works"]))
        for key,url,title,composer,city,venue,region,day,clock in CASES:
            with self.subTest(city=city):
                self.assertIn(url,urls)
                self.assertIn(city+"|"+venue,ids["venues"])
                self.assertEqual(ids["venues"][city+"|"+venue]["region"],region)
                matches=[p for p in facts["productions"]
                         if p["source_url"]==url and p["municipality"]==city]
                self.assertEqual(len(matches),1)
                self.assertEqual(matches[0]["dates"],[[day,clock]])
        catalogue=assemble(facts,ids,approved_extra=set(urls))
        self.assertEqual(len(catalogue["performances"]),
                         len(self.registry["performances"])+4)
        directory=build_directory(self.directory,ids)
        self.assertEqual(len(directory["venues"]),len(self.directory["venues"]))
        for key,url,title,composer,city,venue,region,day,clock in CASES:
            row=next(v for v in directory["venues"]
                     if v["city"]==city and v["name"]==venue)
            self.assertEqual(row["canonical_venue_id"],ids["venues"][city+"|"+venue]["id"])
            self.assertEqual(row["calendar_status"],"acquired")
        again,again_ids,again_urls,repeat=promote(facts,ids,evidence,candidates,urls,
                                                      today=date(2026,11,22))
        self.assertEqual(repeat["new_recite"],0,repeat)
        self.assertEqual(again,facts)
        self.assertEqual(again_ids,ids)
        self.assertEqual(again_urls,urls)

if __name__=="__main__":
    unittest.main()

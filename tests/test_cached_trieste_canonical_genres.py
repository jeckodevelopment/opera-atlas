"""No refetch required when cached Trieste dates refer to known canonical works."""
import copy
import json
import unittest
from datetime import date

from scripts.auto_catalogue import canonicalize_cached_trieste_credit,promote,SOURCE_ALLOWLIST
from scripts.build_verified_catalog import MANIFEST
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.publish_catalog_v2 import REGISTRY

SOURCES={
    "https://www.teatroverdi-trieste.com/it/spettacoli/aida/":
       ("Aida","Giuseppe Verdi",4),
    "https://www.teatroverdi-trieste.com/it/spettacoli/norma/":
       ("Norma","Vincenzo Bellini",5)
}

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

class ArchivedTriesteGenres(unittest.TestCase):
    def test_normalization_requires_existing_exact_unique_composition(self):
        reg=read(REGISTRY)
        for title,composer,genre in (
                ("Aida","Giuseppe Verdi"," Opera"),
                ("Norma","Vincenzo Bellini"," Tragedia")):
            rows=[{"event_title":title,"composer":composer+genre,
                   "date":"2027-06-10","starts_at":"2027-06-10T20:00:00+02:00",
                   "venue":"Teatro Lirico Giuseppe Verdi"}]
            normalized=canonicalize_cached_trieste_credit(rows,reg)
            self.assertEqual(normalized[0]["composer"],composer)
            self.assertEqual(normalized[0]["date"],rows[0]["date"])
            self.assertEqual(rows[0]["composer"],composer+genre)
        for name,author in (("Aida","Giuseppe Verdi Danza"),
                            ("Aida","Other Verdi Opera"),
                            ("Unknown","Giuseppe Verdi Opera")):
            row=[{"event_title":name,"composer":author}]
            self.assertEqual(canonicalize_cached_trieste_credit(row,reg),row)
        row=[{"event_title":"Aida","composer":"Giuseppe Verdi Opera"},
             {"event_title":"Norma","composer":"Vincenzo Bellini Tragedia"}]
        self.assertEqual(canonicalize_cached_trieste_credit(row,reg),row)

    def test_two_cached_official_stagings_can_promote_without_network(self):
        reg=read(REGISTRY)
        fact=read(MANIFEST)
        cand=read(CANDIDATES)
        ev=read(DETAILS)
        urls=read(SOURCE_ALLOWLIST)["urls"]
        chosen={"schema_version":1,"candidates":[x for x in cand["candidates"]
             if x["official_url"] in SOURCES and x["status"]=="needs_review"]}
        details={"schema_version":1,"evidence":[x for x in ev["evidence"]
                 if x["source_url"] in SOURCES]}
        prev={x["source_url"] for x in fact["productions"]}
        new=promote(fact,reg,details,chosen,urls,today=date(2026,11,21))
        next_facts,next_reg,allowed,report=new
        for url,(title,composer,n) in SOURCES.items():
            if url not in prev:
                matched=[x for x in next_facts["productions"]
                         if x["source_url"]==url]
                self.assertEqual(len(matched),1,report)
                self.assertEqual((matched[0]["title"],matched[0]["composer"]),
                                 (title,composer))
                self.assertEqual(len(matched[0]["dates"]),n)
        again=promote(next_facts,next_reg,details,chosen,allowed,
                      today=date(2026,11,21))
        self.assertEqual(again[-1]["new_recite"],0)

if __name__=="__main__":
    unittest.main()

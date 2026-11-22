"""Goldoni individual ticket sources do not duplicate season-level recite."""
import copy
import unittest
from scripts.reconcile_published_candidates import (
    verified_livorno_recital_urls,reconcile)
from scripts.build_verified_catalog import official_local_time

SEASON="https://www.goldoniteatro.it/notizie/la-stagione-lirica/"
BASE="https://www.goldoniteatro.it/spettacoli/"

def item(slug,title,composer,day,clock,*,venue="Teatro Goldoni"):
    return {"source_key":"goldoni-livorno-rolling-lirica",
            "source_url":BASE+slug+"/",
            "status":"needs_editorial_review",
            "content_sha256":"a"*64,
            "event_facts":[{
                "event_title":title,"composer":composer,"venue":venue,
                "date":day,"starts_at":official_local_time(day,clock)}]}

def manifest():
    return {"productions":[
        {"municipality":"Livorno","venue":"Teatro Goldoni",
         "source_url":SEASON,"title":"Otello","composer":"Giuseppe Verdi",
         "dates":[["2027-01-29","20:00"],["2027-01-31","16:00"]]},
        {"municipality":"Livorno","venue":"Teatro Goldoni",
         "source_url":SEASON,"title":"L’elisir d’amore",
         "composer":"Gaetano Donizetti",
         "dates":[["2027-04-16","20:00"],["2027-04-18","16:00"]]},
        {"municipality":"Livorno","venue":"Teatro Goldoni",
         "source_url":SEASON,"title":"Dido and Æneas","composer":"Henry Purcell",
         "dates":[["2026-11-06","20:00"],["2026-11-08","16:00"]]},
    ]}

class LivornoRecitalReconciliationTests(unittest.TestCase):
    def test_four_individual_tickets_match_only_reviewed_season_recite(self):
        rows=[
            item("otello-4","Otello","Giuseppe Verdi","2027-01-29","20:00"),
            item("otello-3","Otello","Giuseppe Verdi","2027-01-31","16:00"),
            item("lelisir-damore-3","L'elisir d'amore","Gaetano Donizetti",
                 "2027-04-16","20:00"),
            item("lelisir-damore-2","L’elisir d’amore","Gaetano Donizetti",
                 "2027-04-18","16:00")
        ]
        urls={x["source_url"] for x in rows}
        found=verified_livorno_recital_urls(manifest(),{"evidence":rows})
        self.assertEqual(found,urls)
        candidates={"schema_version":1,"candidates":[
            {"id":str(n),"source_key":row["source_key"],
             "official_url":row["source_url"],"status":"needs_review"}
            for n,row in enumerate(rows)]}
        updated,report=reconcile(candidates,found)
        self.assertEqual(report["states"],{"already_catalogued":4})
        again,health=reconcile(updated,found)
        self.assertEqual(again,updated)
        self.assertFalse(health["changes"])

    def test_never_retire_wrong_composer_clock_venue_or_unverified_source(self):
        good=item("otello-4","Otello","Giuseppe Verdi","2027-01-29","20:00")
        changes=[
            lambda r:r["event_facts"][0].update(composer="Other composer"),
            lambda r:r["event_facts"][0].update(starts_at=
                  official_local_time("2027-01-29","19:00")),
            lambda r:r["event_facts"][0].update(venue="Piazza Goldoni"),
            lambda r:r.update(source_key="other-source"),
            lambda r:r.update(status="unavailable_or_unstructured"),
            lambda r:r.update(content_sha256="bad"),
            lambda r:r["event_facts"].append(dict(r["event_facts"][0])),
            lambda r:r.update(source_url=BASE+"otello-4/?advertisement=1"),
            lambda r:r["event_facts"][0].update(date="2027-01-30"),
        ]
        for change in changes:
            row=copy.deepcopy(good)
            change(row)
            with self.subTest(change=change.__code__.co_firstlineno):
                self.assertEqual(
                    verified_livorno_recital_urls(manifest(),{"evidence":[row]}),
                    set())

    def test_ambiguous_competing_stagings_cannot_retire_ticket(self):
        row=item("otello-4","Otello","Giuseppe Verdi","2027-01-29","20:00")
        dup=manifest()
        dup["productions"].append(copy.deepcopy(dup["productions"][0]))
        self.assertEqual(verified_livorno_recital_urls(dup,{"evidence":[row]}),set())
        # The 2026 Dido source has a conflicting header clock compared with
        # the official season notice: it must not be reconciled by title alone.
        contradictory=item("dido-ed-enea-2","Dido and Æneas",
                           "Henry Purcell","2026-11-08","20:00")
        self.assertEqual(verified_livorno_recital_urls(
            manifest(),{"evidence":[contradictory]}),set())

if __name__=="__main__":
    unittest.main()

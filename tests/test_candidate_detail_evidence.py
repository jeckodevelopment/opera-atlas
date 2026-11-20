"""Bounded detail scanning keeps proposed facts out of the canonical catalog."""
import json
import unittest
from datetime import date

from opera_atlas.controlled_fetch import FetchResult,FetchUnavailable
from scripts.collect_candidate_details import parse_event_facts,selected_candidates,collect,parse_known_opera_detail
from scripts.publish_catalog_v2 import REGISTRY

class CandidateDetailTests(unittest.TestCase):
    def setUp(self):
        self.empty={"schema_version":1,"evidence":[]}
        self.candidates={"schema_version":1,"candidates":[{
            "id":"candidate-a","source_key":"scala-season-2026-27",
            "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/anna-bolena.html",
            "status":"needs_review"},
            {"id":"candidate-b","source_key":"arena-festival-2027",
             "official_url":"https://www.arena.it/arena-opera-festival/regolamento/",
             "status":"excluded_nonopera"},
            {"id":"candidate-c","source_key":"fenice-opera-2026-27",
             "official_url":"https://other.example/event/fake/","status":"needs_review"}
        ]}
    def test_verified_scala_work_parser_produces_review_only_date(self):
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        url="https://www.teatroallascala.org/it/stagione/2026-2027/opera/macbeth.html"
        html="<h1>Macbeth Giuseppe Verdi</h1><p>5 febbraio 2027 ore 20:00</p>"
        rows=parse_known_opera_detail("scala-season-2026-27",url,html,registry)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["composer"],"Giuseppe Verdi")
        self.assertEqual(rows[0]["venue"],"Teatro alla Scala")
        self.assertEqual(rows[0]["date"],"2027-02-05")
        self.assertIn("+01:00",rows[0]["starts_at"])

    def test_verified_arena_known_work_and_unknown_rejected(self):
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        url="https://www.arena.it/arena-opera-festival/carmen/"
        html="<h1>Carmen Georges Bizet</h1><h2>Prossimi spettacoli</h2><p>12 giugno 2027 ore 21:00</p>"
        rows=parse_known_opera_detail("arena-festival-2027",url,html,registry)
        self.assertEqual(len(rows),1)
        self.assertIn("+02:00",rows[0]["starts_at"])
        unknown="https://www.teatroallascala.org/it/stagione/2026-2027/opera/unknown-opera.html"
        self.assertEqual(parse_known_opera_detail("scala-season-2026-27",unknown,html,registry),[])

    def test_incorrect_composer_does_not_produce_evidence(self):
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        url="https://www.teatroallascala.org/it/stagione/2026-2027/opera/macbeth.html"
        with self.assertRaises(ValueError):
            parse_known_opera_detail("scala-season-2026-27",url,
                                    "<h1>Macbeth by another composer</h1>"
                                    "<p>5 febbraio 2027 ore 20:00</p>",registry)

    def test_publishable_known_works_are_scanned_before_unknown_titles(self):
        candidates={"schema_version":1,"candidates":[]}
        for i in range(25):
            candidates["candidates"].append({
                "id":f"candidate-{i:03d}","source_key":"scala-season-2026-27",
                "official_url":f"https://www.teatroallascala.org/it/stagione/2026-2027/opera/unknown-{i}.html",
                "status":"needs_review"})
        candidates["candidates"].append({
            "id":"candidate-z-macbeth","source_key":"scala-season-2026-27",
            "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/macbeth.html",
            "status":"needs_review"})
        chosen=selected_candidates(candidates,today=date(2026,11,20))
        self.assertEqual(len(chosen),10)
        self.assertEqual(chosen[0]["id"],"candidate-z-macbeth")

    def test_structured_dates_and_explicit_timezone_only(self):
        html='<script type="application/ld+json">'+json.dumps({"@graph":[
            {"@type":"MusicEvent","name":"Anna Bolena",
             "startDate":"2027-05-02T20:00:00+02:00",
             "location":{"@type":"Place","name":"Teatro alla Scala"}},
            {"@type":"Event","name":"Preview","startDate":"2027-05-03"},
            {"@type":"Event","name":"Untrusted","startDate":"2027-05-04T20:00:00"}
        ]})+'</script>'
        events=parse_event_facts(html)
        self.assertEqual(len(events),2)
        self.assertEqual(events[0]["date"],"2027-05-02")
        self.assertIn("+02:00",events[0]["starts_at"])
        self.assertIsNone(events[1]["starts_at"])
    def test_scripts_not_events_are_ignored(self):
        self.assertEqual(parse_event_facts('<script type="application/ld+json">'+
            '{"@type":"Article","name":"Opere","datePublished":"2027-01-01"}'+
            '</script>'),[])
    def test_selection_only_review_and_exact_official_domains(self):
        chosen=selected_candidates(self.candidates,today=date(2026,11,20))
        self.assertEqual([x["id"] for x in chosen],["candidate-a"])
    def test_success_preserves_evidence_and_does_not_create_recite(self):
        html='<script type="application/ld+json">'+json.dumps({
            "@type":"MusicEvent","name":"Anna Bolena",
            "startDate":"2027-05-02T20:00:00+02:00"})+'</script>'
        def fake(db,*,source_id,url,network_enabled):
            return FetchResult(url,html,"a"*64,len(html))
        report,health=collect(self.candidates,self.empty,
                              network_enabled=True,fetcher=fake,today=date(2026,11,20))
        self.assertEqual(health[0]["outcome"],"facts_found")
        self.assertEqual(len(report["evidence"]),1)
        self.assertEqual(report["evidence"][0]["status"],"needs_editorial_review")
        self.assertEqual(len(report["evidence"][0]["event_facts"]),1)
    def test_robots_failure_preserves_last_evidence(self):
        past={"schema_version":1,"evidence":[{
            "candidate_id":"candidate-a","event_facts":[{"date":"2027-05-02"}]}]}
        def denied(*args,**kwargs):raise FetchUnavailable("robots denied")
        result,health=collect(self.candidates,past,
                              network_enabled=True,fetcher=denied,today=date(2026,11,20))
        self.assertEqual(result,past)
        self.assertEqual(health[0]["outcome"],"unavailable_or_unstructured")
    def test_without_network_does_not_fetch(self):
        def forbidden(*a,**k):raise AssertionError("unexpected network")
        result,health=collect(self.candidates,self.empty,network_enabled=False,
                              fetcher=forbidden,today=date(2026,11,20))
        self.assertEqual(result,self.empty)
        self.assertEqual(health[0]["reason"],"AccessDenied")

if __name__=="__main__":
    unittest.main()

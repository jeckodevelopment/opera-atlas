"""Bounded detail scanning keeps proposed facts out of the canonical catalog."""
import json
import unittest
from datetime import date

from opera_atlas.controlled_fetch import FetchResult,FetchUnavailable
from scripts.collect_candidate_details import parse_event_facts,selected_candidates,collect

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

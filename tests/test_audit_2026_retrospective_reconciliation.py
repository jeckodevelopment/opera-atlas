"""Retrospective 2026 reconciliation must never claim unreviewed missing opera."""
import unittest
from scripts.audit_2026_retrospective_reconciliation import reconcile

def fact(url, title, day="2026-03-04", start="2026-03-04T20:00:00+01:00"):
    return {"source_key":"scala-season-2026-27","source_url":url,
            "event_title":title,"date":day,"starts_at":start,
            "venue":"Teatro X","discovered_from":"https://official.example/archive/"}

def make(items, productions=(), historical=()):
    report={"year":2026,"read_only":True,"checked_at":"2026-11-24T06:00:00+00:00",
            "unverified_2026_facts":items,"seed_results":[],"archive_results":[],
            "detail_results":[]}
    return reconcile(report,{"productions":list(productions)},
                     {"programs":[]},{"records":list(historical)})

class RetroReconciliationTests(unittest.TestCase):
    def test_exact_source_date_title_and_time_catalogued(self):
        url="https://official.example/opera/x"
        p={"source_url":url,"title":"Macbeth","venue":"Teatro X",
           "municipality":"Torino","dates":[["2026-03-04","20:00"]]}
        x=make([fact(url,"Macbeth")], [p])
        self.assertEqual({"already_published_exact_source_day_work":1},x["observation_counts"])
        self.assertFalse(x["catalog_updated"])

    def test_different_title_same_source_date_does_not_merge(self):
        url="https://official.example/stagione"
        p={"source_url":url,"title":"Macbeth","venue":"Teatro X",
           "municipality":"Torino","dates":[["2026-03-04","20:00"]]}
        x=make([fact(url,"Carmen")],[p])
        self.assertEqual({"same_source_day_identity_or_time_conflict":1},x["observation_counts"])

    def test_different_time_is_conflict(self):
        url="https://official.example/opera"
        p={"source_url":url,"title":"Macbeth","venue":"Teatro X",
           "municipality":"Torino","dates":[["2026-03-04","15:00"]]}
        x=make([fact(url,"Macbeth")],[p])
        self.assertEqual({"same_source_day_identity_or_time_conflict":1},x["observation_counts"])

    def test_same_work_date_different_source_is_review_only(self):
        p={"source_url":"https://official.example/source-a","title":"Macbeth",
           "venue":"Teatro X","municipality":"Torino",
           "dates":[["2026-03-04","20:00"]]}
        x=make([fact("https://official.example/source-b","Macbeth")],[p])
        self.assertEqual({"possible_match_needs_venue_source_review":1},x["observation_counts"])

    def test_archive_evidence_is_not_published(self):
        url="https://official.example/opera"
        h={"source_url":url,"title":"Macbeth","venue":"Teatro X",
           "city":"Torino","dates":[{"date":"2026-03-04","time":"20:00"}]}
        x=make([fact(url,"Macbeth")],historical=[h])
        self.assertEqual({"official_archive_already_documented":1},x["observation_counts"])

    def test_duplicate_across_archive_and_details_collapsed(self):
        url="https://official.example/opera"
        x=make([fact(url,"Macbeth"),fact(url,"Macbeth")])
        self.assertEqual(2,x["raw_observation_count"])
        self.assertEqual(1,x["unique_observation_count"])
        self.assertEqual(1,x["duplicate_observations_collapsed"])
        self.assertEqual({"unmatched_requires_official_review":1},x["observation_counts"])

    def test_official_english_italian_festival_alias(self):
        p={"source_url":"https://www.festivaldellavalleditria.it/spettacolo/carmen/2026-07-25",
           "title":"Carmen","venue":"Palazzo Ducale","municipality":"Martina Franca",
           "dates":[["2026-07-25","21:00"]]}
        f=fact("https://www.festivaldellavalleditria.it/en/spettacolo/carmen/2026-07-25",
               "Carmen","2026-07-25","2026-07-25T21:00:00+02:00")
        x=make([f],[p])
        self.assertEqual({"already_published_exact_source_day_work":1},x["observation_counts"])

    def test_official_source_confirmed_candidate_not_auto_published(self):
        url="https://www.teatrocomunalemodena.it/modena-belcanto-festival/"
        f=fact(url,"La costanza trionfante","2026-09-25","2026-09-25T20:30:00+02:00")
        priority={"records":[{"source_url":url,"date":"2026-09-25",
                  "event_title":"La costanza trionfante","time":"20:30",
                  "classification":"official_opera_candidate_needs_publication_review",
                  "official_detail_url":"https://www.comune.modena.it/eventi/costanza",
                  "composer":"Antonio Vivaldi","venue":"Teatro Comunale",
                  "evidence":"Opera semiscenica"}]}
        x=reconcile({"year":2026,"read_only":True,"unverified_2026_facts":[f]},
                    {"productions":[]},{"programs":[]},{"records":[]},priority)
        self.assertEqual(1,x["observation_counts"]["official_opera_candidate_needs_publication_review"])
        self.assertFalse(x["catalog_updated"])

    def test_official_candidate_with_conflicting_aggregator_time_stays_visible(self):
        url="https://www.teatrocomunalemodena.it/modena-belcanto-festival/"
        f=fact(url,"La costanza trionfante","2026-09-25",
               "2026-09-25T17:00:00+02:00")
        review={"records":[{"source_url":url,"date":"2026-09-25",
                "event_title":"La costanza trionfante","time":"20:30",
                "classification":"official_opera_candidate_needs_publication_review",
                "official_detail_url":"https://www.comune.modena.it/official-opera",
                "composer":"Antonio Vivaldi","venue":"Teatro Comunale",
                "evidence":"Official event detail 20:30"}]}
        x=reconcile({"year":2026,"read_only":True,"unverified_2026_facts":[f]},
                    {"productions":[]},{"programs":[]},{"records":[]},review)
        self.assertEqual(1,x["observation_counts"][
            "official_opera_candidate_needs_publication_review_time_conflict"])

    def test_multiwork_evening_only_partly_catalogued(self):
        url="https://www.festivaldellavalleditria.it/spettacolo/pulcinella-la-favola-di-orfeo/2026-07-14"
        p={"source_url":url,"title":"La favola di Orfeo","venue":"Palazzo Ducale",
           "municipality":"Martina Franca","dates":[["2026-07-14","21:00"]]}
        f=fact(url,"Pulcinella / La favola di Orfeo (dittico)",
               "2026-07-14","2026-07-14T21:00:00+02:00")
        x=make([f],[p])
        self.assertEqual({"partial_multiwork_catalogued_needs_review":1},x["observation_counts"])

    def test_exact_source_specific_nonopera_decision_never_generalizes(self):
        url="https://www.tcbo.it/evento/concerto/angius-grazia-2026/"
        f=fact(url,"Angius, Grazia","2026-12-11","2026-12-11T20:30:00+01:00")
        f["venue"]="Teatro Auditorium Manzoni"
        decision={"decisions":[{"source_url":url,"event_title":"Angius, Grazia",
            "date":"2026-12-11","time":"20:30","venue":"Teatro Auditorium Manzoni",
            "decision":"exclude_nonopera","reason":"symphonic_concert",
            "provenance":url}]}
        report={"year":2026,"read_only":True,"unverified_2026_facts":[f]}
        x=reconcile(report,{"productions":[]},{"programs":[]},{"records":[]},
                    decisions=decision)
        self.assertEqual({"screened_nonopera_exact_source":1},x["observation_counts"])
        changed={**f,"date":"2026-12-12","starts_at":"2026-12-12T20:30:00+01:00"}
        y=reconcile({"year":2026,"read_only":True,"unverified_2026_facts":[changed]},
                    {"productions":[]},{"programs":[]},{"records":[]},decisions=decision)
        self.assertEqual({"unmatched_requires_official_review":1},y["observation_counts"])

    def test_duplicate_source_decision_fails_closed(self):
        d={"source_url":"https://official.example/event/1","event_title":"Concert",
           "date":"2026-12-11","time":"20:30","venue":"A",
           "decision":"exclude_nonopera","reason":"concert","provenance":"official"}
        with self.assertRaises(ValueError):
            reconcile({"year":2026,"read_only":True,"unverified_2026_facts":[]},
                    {"productions":[]},{"programs":[]},{"records":[]},
                    decisions={"decisions":[d,d]})

    def test_short_edition_is_excluded_without_blocking_full_opera(self):
        from scripts.discover_season_indexes import excluded_nonopera
        short="https://www.tcbo.it/evento/accademia/il-flauto-magico-short-edition-2026/"
        full="https://www.tcbo.it/evento/opera/il-flauto-magico-2026/"
        self.assertTrue(excluded_nonopera("bologna-comunale-opera-2026",short))
        self.assertFalse(excluded_nonopera("bologna-comunale-opera-2026",full))
        review={"records":[{"source_url":short,
            "event_title":"Il flauto magico – Short Edition",
            "date":"2026-12-05","time":"16:00",
            "venue":"Teatro Auditorium Manzoni",
            "composer":"Wolfgang Amadeus Mozart",
            "classification":"excluded_editorial_abbreviated_opera",
            "official_detail_url":short,
            "evidence":"Editorially excluded abbreviated adaptation"}]}
        f=fact(short,"Il flauto magico – Short Edition",
               "2026-12-05","2026-12-05T16:00:00+01:00")
        x=reconcile({"year":2026,"read_only":True,
                     "unverified_2026_facts":[f]},
                    {"productions":[]},{"programs":[]},{"records":[]},review)
        self.assertEqual({"excluded_by_approved_policy":1},x["observation_counts"])

    def test_non_2026_and_invalid_dates_rejected(self):
        x=make([fact("https://official.example/1","Macbeth","2027-03-04", "2027-03-04T20:00:00+01:00"),
                fact("https://official.example/2","Macbeth","2026-02-31", "2026-02-31T20:00:00+01:00")])
        self.assertEqual(0,x["unique_observation_count"])

if __name__=="__main__":
    unittest.main()

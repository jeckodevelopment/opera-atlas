import unittest
from scripts.audit_2026_editorial_triage import classify

def source(rows):
    return {"year":2026,"read_only":True,"catalog_updated":False,
            "complete_seasons_certified":0,"generated_at":"2026-11-24T10:00:00Z",
            "review_queue_count":len(rows),"review_queue":rows}

def item(url,title="Concerto",date="2026-12-01",time="21:00",venue="Teatro A"):
    return {"source_key":"source-a","source_url":url,"date":date,
            "time":time,"event_title":title,"venue":venue,
            "status":"unmatched_requires_official_review"}

class EditorialTriageTests(unittest.TestCase):
    def test_different_url_same_event_is_diagnostic_only(self):
        a=item("https://official.example/stagione")
        b=item("https://official.example/calendario")
        old={"decisions":[{"source_url":"https://official.example/concerto",
                           "event_title":"Concerto","date":"2026-12-01",
                           "time":"21:00","venue":"Teatro A","decision":"exclude_nonopera",
                           "reason":"documented concert"}]}
        result=classify(source([a,b]),old,{"records":[]})
        self.assertEqual(1,result["event_groups"])
        self.assertEqual(1,result["cross_url_observations_consolidated"])
        g=result["review_groups"][0]
        self.assertEqual("previous_nonopera_decision_cross_url_corroboration",g["bucket"])
        self.assertFalse(g["automatic_exclusion"])
        self.assertFalse(g["automatic_publication"])

    def test_different_venue_never_borrows_decision(self):
        a=item("https://official.example/stagione",venue="Teatro B")
        d={"decisions":[{"source_url":"https://official.example/concerto",
                          "event_title":"Concerto","date":"2026-12-01",
                          "time":"21:00","venue":"Teatro A","decision":"exclude_nonopera"}]}
        result=classify(source([a]),d,{"records":[]})
        self.assertEqual("unclassified_requires_source_review",
                         result["review_groups"][0]["bucket"])

    def test_different_hosts_never_borrow_decision(self):
        a=item("https://other.example/stagione")
        d={"decisions":[{"source_url":"https://official.example/concerto",
                          "event_title":"Concerto","date":"2026-12-01",
                          "time":"21:00","venue":"Teatro A","decision":"exclude_nonopera"}]}
        result=classify(source([a]),d,{"records":[]})
        self.assertEqual("unclassified_requires_source_review",
                         result["review_groups"][0]["bucket"])

    def test_distinct_times_and_dates_never_cluster(self):
        items=[item("https://official.example/a"),
               item("https://official.example/b",time="18:00"),
               item("https://official.example/c",date="2026-12-02")]
        result=classify(source(items),{"decisions":[]},{"records":[]})
        self.assertEqual(3,result["event_groups"])

    def test_official_candidate_retained(self):
        a=item("https://official.example/calendar","Macbeth")
        p={"records":[{"date":"2026-12-01","event_title":"Macbeth",
                       "classification":"official_opera_candidate_needs_publication_review",
                       "official_detail_url":"https://official.example/macbeth",
                       "source_url":"https://official.example/macbeth",
                       "venue":"Teatro A","time":"20:30"}]}
        result=classify(source([a]),{"decisions":[]},p)
        self.assertEqual("official_opera_candidate_needs_editorial_review",
                         result["review_groups"][0]["bucket"])

    def test_invalid_input_fails_closed(self):
        x=source([item("https://official.example/calendar")])
        x["catalog_updated"]=True
        with self.assertRaises(ValueError):
            classify(x,{"decisions":[]},{"records":[]})

if __name__=="__main__":
    unittest.main()

"""H1 2026 source evidence comparison must be conservative."""
import unittest
from scripts.audit_2026_jan_jun_reconciliation import reconcile_first_half

V={"venues":[{"id":"v1","name":"Teatro Esempio","city":"Milano"}]}
def fact(day="2026-03-12",title="Macbeth",
         url="https://official.example/opera/macbeth",hour="20:00"):
    return {"venue_id_candidate":"v1","official_url":url,"event_title":title,
            "date":day,"starts_at":day+"T"+hour+":00+01:00",
            "composer":"Giuseppe Verdi","venue":"Teatro Esempio"}
def build(facts, productions=()):
    return reconcile_first_half({"year":2026,"read_only":True,
        "observations":facts},{"productions":list(productions)},{"programs":[]},
        {"records":[]},V)

class H1ReviewTests(unittest.TestCase):
    def test_published_exact_source_work_day_clock(self):
        p={"title":"Macbeth","source_url":"https://official.example/opera/macbeth",
           "venue":"Teatro Esempio","municipality":"Milano",
           "dates":[["2026-03-12","20:00"]]}
        r=build([fact()],[p])
        self.assertEqual({"already_in_public_catalog":1},r["status_counts"])
        self.assertFalse(r["catalog_updated"])

    def test_unpublished_is_review_not_auto_publication(self):
        r=build([fact()])
        self.assertEqual({"source_credited_not_in_reviewed_catalog":1},r["status_counts"])
        self.assertEqual(6,len(r["monthly_venue_coverage"]))
        self.assertFalse(any(x["complete_month_verified"] for x in r["monthly_venue_coverage"]))

    def test_school_family_format_is_flagged_not_excluded(self):
        r=build([fact(title="Il piccolo principe")])
        self.assertEqual({"audience_and_format_review":1},r["status_counts"])

    def test_future_dates_fail_closed(self):
        with self.assertRaises(ValueError):
            build([fact(day="2027-03-12")])

if __name__=="__main__":
    unittest.main()

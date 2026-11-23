"""Guard against reporting published performances as missing in mass audit."""
import unittest
from scripts.audit_2026_mass_reconciliation import triage


class MassReconciliationTests(unittest.TestCase):
    def test_matches_only_identical_official_url_and_day(self):
        catalog={"productions":[{"title":"Carmen","venue":"Palazzo Ducale",
            "municipality":"Martina Franca",
            "source_url":"https://www.festivaldellavalleditria.it/spettacolo/carmen/2026-07-25",
            "dates":[["2026-07-25","21:00"]]}]}
        report={"detail_results":[
            {"source_key":"martina-valle-itria-2026",
             "source_url":"https://www.festivaldellavalleditria.it/spettacolo/carmen/2026-07-25",
             "facts":[{"event_title":"Carmen","date":"2026-07-25"}]},
            {"source_key":"martina-valle-itria-2026",
             "source_url":"https://www.festivaldellavalleditria.it/spettacolo/other/2026-07-25",
             "facts":[{"event_title":"Carmen","date":"2026-07-25"}]}
        ],"index_results":[]}
        out=triage(report,catalog)
        self.assertEqual("already_catalogued_source_and_date",out["observations"][0]["status"])
        self.assertEqual("needs_editorial_reconciliation",out["observations"][1]["status"])
        self.assertFalse(out["catalog_updated"])

    def test_existing_approved_exclusion_beats_a_published_record(self):
        url="https://www.festivaldellavalleditria.it/spettacolo/approfondimenti/2026-07-18"
        report={"detail_results":[{"source_key":"martina-valle-itria-2026",
            "source_url":url,"facts":[{"date":"2026-07-18","event_title":"Approfondimenti"}]}],
            "index_results":[]}
        out=triage(report,{"productions":[]})
        self.assertEqual("excluded_by_existing_official_source_policy",out["observations"][0]["status"])

    def test_failures_not_interpreted_as_empty_programs(self):
        report={"detail_results":[],"index_results":[
            {"source_key":"a","status":"unverified","reason":"FetchUnavailable","index_url":"https://x.example"},
            {"source_key":"b","status":"unverified","reason":"ValueError","index_url":"https://y.example"},
            {"source_key":"c","status":"scanned","candidate_urls":[]}]}
        out=triage(report,{"productions":[]})
        self.assertEqual(1,out["index_failure_counts"]["source_unavailable"])
        self.assertEqual(1,out["index_failure_counts"]["parser_or_structure"])
        self.assertEqual([],out["observations"])


if __name__=="__main__":
    unittest.main()

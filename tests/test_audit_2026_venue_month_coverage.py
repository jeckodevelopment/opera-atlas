"""National 2026 coverage is an evidence-gap matrix, never a completeness claim."""
import copy
import json
import unittest

from scripts.audit_2026_venue_month_coverage import (
    VENUES,REGISTRY,MANIFEST,PROGRAMS,HISTORICAL,H1,H2,SEEDS,SEED_SCAN,
    build_matrix,source_slot,
)

PATHS=(VENUES,REGISTRY,MANIFEST,PROGRAMS,HISTORICAL,H1,H2,SEEDS,SEED_SCAN)
def docs():
    return [json.loads(path.read_text(encoding="utf-8")) for path in PATHS]


class VenueMonthMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=docs()
        cls.report=build_matrix(*cls.inputs)

    def test_complete_72_x_12_grid_without_certifying_any_missing_month(self):
        r=self.report
        self.assertEqual(72,r["venue_count"])
        self.assertEqual(864,r["cell_count"])
        self.assertEqual(864,len(r["rows"]))
        self.assertEqual(864,len({(x["venue_id"],x["month"]) for x in r["rows"]}))
        self.assertEqual(0,r["complete_venue_months"])
        self.assertEqual(0,r["complete_annual_venues"])
        self.assertTrue(all(x["complete_month_verified"] is False for x in r["rows"]))
        self.assertTrue(r["read_only"])
        self.assertFalse(r["catalog_updated"])

    def test_zero_published_priorities_are_not_missing_recite_claims(self):
        r=self.report
        priorities=r["venue_audit_priorities"]
        self.assertEqual(72,len(priorities))
        self.assertEqual(72,len({x["venue_id"] for x in priorities}))
        zero=[x for x in priorities if x["published_2026_showtimes"]==0]
        self.assertEqual(len(zero),r["zero_published_venue_count"])
        self.assertEqual(len(zero),sum(r["zero_published_by_calendar_status"].values()))
        self.assertTrue(all(x["missing_recite_certified"] is False for x in priorities))
        self.assertTrue(all(x["audit_priority"].startswith("zero_published") for x in zero))
        # A calendar being acquired is not proof of a complete 2026 season.
        acquired=[x for x in zero if x["calendar_status"]=="acquired"]
        self.assertEqual(len(acquired),r["zero_published_by_calendar_status"].get("acquired",0))
        self.assertTrue(all(x["audit_priority"]=="zero_published_acquired_calendar" for x in acquired))
        self.assertTrue(any(x["venue"]=="Arena di Verona" for x in acquired))
        bologna=next(x for x in zero if x["venue"]=="Teatro Comunale di Bologna")
        self.assertGreater(bologna["historical_source_seed_count"],0)
        self.assertFalse(bologna["missing_recite_certified"])

    def test_existing_2026_carmen_publications_are_not_reported_missing(self):
        r=self.report
        for name,city,month in (
            ("Teatro alla Scala","Milano","2026-06"),
            ("Teatro La Fenice","Venezia","2026-05")
        ):
            x=next(x for x in r["rows"]
                   if x["venue"]==name and x["city"]==city and x["month"]==month)
            self.assertGreater(x["published_showtimes"],0)
            self.assertGreater(x["observed_already_published"],0)
            self.assertEqual(0,x["observed_not_in_publication"])

    def test_malibran_calendar_not_wrongly_attributed_to_la_fenice(self):
        r=self.report
        malibran=[x for x in r["rows"] if x["venue"]=="Teatro Malibran"
                  and x["city"]=="Venezia"]
        self.assertEqual(12,len(malibran))
        self.assertEqual(10,sum(x["source_observed_opera_showtimes"] for x in malibran))
        fenice=[x for x in r["rows"] if x["venue"]=="Teatro La Fenice"
                and x["city"]=="Venezia"]
        self.assertEqual(30,sum(x["source_observed_opera_showtimes"] for x in fenice))

    def test_regio_historical_published_dates_reconcile_after_source_verified_promotion(self):
        r=self.report
        regio=[x for x in r["rows"] if x["venue"]=="Teatro Regio di Torino"]
        self.assertEqual(25,sum(x["source_observed_opera_showtimes"] for x in regio))
        self.assertEqual(25,sum(x["observed_already_published"] for x in regio))
        self.assertEqual(0,sum(x["observed_not_in_publication"] for x in regio))

    def test_family_and_nonopera_candidates_never_inflate_opera_denominator(self):
        r=self.report
        self.assertEqual(3,len(r["h1_scope_review"]))
        self.assertGreater(r["h2_mixed_genre_observation_counts"].get(
            "screened_nonopera_exact_source",0),0)
        for x in r["rows"]:
            self.assertNotIn("percent_complete",x)
            self.assertFalse(x["source_exhaustiveness_verified"])

    def test_absence_of_performance_does_not_mean_completed_month(self):
        empty=next(x for x in self.report["rows"]
                   if x["published_showtimes"]==0
                   and x["source_observed_opera_showtimes"]==0)
        self.assertEqual("coverage_not_established",empty["status"])
        self.assertFalse(empty["complete_month_verified"])

    def test_tampered_historical_facts_never_become_2026_observations(self):
        self.assertIsNone(source_slot({"date":"2027-01-03","time":"20:00"}))
        self.assertIsNone(source_slot({"date":"2026-02-31","time":"20:00"}))
        self.assertIsNone(source_slot({"date":"2026-02-03","time":"TBD"}))

    def test_coverage_refresh_is_linked_to_completed_cached_publication(self):
        from pathlib import Path
        workflow=(Path(__file__).resolve().parents[1]/".github"/"workflows"/
                  "audit-2026-venue-month-coverage.yml").read_text(encoding="utf-8")
        self.assertIn('workflows: ["Publish cached verified Opera Atlas recite"]',workflow)
        self.assertIn("types: [completed]",workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'",workflow)

    def test_does_not_read_or_change_live_published_records(self):
        before=json.dumps(self.inputs[2],sort_keys=True)
        build_matrix(*self.inputs)
        self.assertEqual(before,json.dumps(self.inputs[2],sort_keys=True))


if __name__=="__main__":
    unittest.main()

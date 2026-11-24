"""National 2026 coverage is an evidence-gap matrix, never a completeness claim."""
import copy
import json
import unittest

from scripts.audit_2026_venue_month_coverage import (
    VENUES,REGISTRY,MANIFEST,PROGRAMS,HISTORICAL,H1,H2,SEEDS,SEED_SCAN,
    OFFICIAL_ZERO_VENUE_LEADS,build_matrix,source_slot,validated_venue_leads,
)

PATHS=(VENUES,REGISTRY,MANIFEST,PROGRAMS,HISTORICAL,H1,H2,SEEDS,SEED_SCAN)
def docs():
    return [json.loads(path.read_text(encoding="utf-8")) for path in PATHS]


class VenueMonthMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=docs()
        cls.leads=json.loads(OFFICIAL_ZERO_VENUE_LEADS.read_text(encoding="utf-8"))
        cls.report=build_matrix(*cls.inputs,cls.leads)

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
        self.assertTrue(all(x["audit_priority"] in
            {"zero_published_acquired_calendar","zero_published_with_official_opera_leads"}
            for x in acquired))
        self.assertFalse(any(x["venue"]=="Arena di Verona" for x in acquired))
        bologna=next(x for x in zero if x["venue"]=="Teatro Comunale di Bologna")
        self.assertGreater(bologna["historical_source_seed_count"],0)
        self.assertFalse(bologna["missing_recite_certified"])

    def test_primary_source_leads_are_never_auto_published(self):
        r=self.report
        self.assertEqual(93,r["official_2026_opera_lead_count"])
        self.assertEqual(13,r["official_2026_opera_lead_venue_count"])
        self.assertEqual(2,r["official_unpublished_opera_lead_count"])
        self.assertEqual(0,r["official_lead_venues_with_zero_published"])
        self.assertEqual(11,r["zero_published_venue_count"])
        sources={x["venue"]:x for x in r["venue_audit_priorities"]
                 if x["official_verified_opera_lead_count"]}
        self.assertEqual({"Teatro Sociale","Arena di Verona","Arena Sferisterio","Teatro Filarmonico","Gran Teatro Giacomo Puccini","Teatro Vittorio Emanuele","Teatro Lirico di Cagliari","Teatro Ponchielli","Teatro Coccia","Teatro del Giglio Giacomo Puccini","Teatro Sociale di Mantova","Teatro Dante Alighieri","Teatro Alfieri"},
                         set(sources))
        for entry in sources.values():
            self.assertEqual("published_not_exhaustively_verified" if entry["venue"] in {"Teatro Lirico di Cagliari","Teatro Sociale","Arena di Verona","Teatro Filarmonico","Teatro Vittorio Emanuele","Teatro Ponchielli","Teatro del Giglio Giacomo Puccini","Teatro Coccia","Teatro Sociale di Mantova","Teatro Alfieri","Arena Sferisterio","Gran Teatro Giacomo Puccini","Teatro Dante Alighieri"} else "zero_published_with_official_opera_leads",
                             entry["audit_priority"])
            self.assertFalse(entry["missing_recite_certified"])
        self.assertEqual(0,sources["Teatro Sociale"]["official_unpublished_opera_lead_count"])
        self.assertEqual(0,sources["Arena di Verona"]["official_unpublished_opera_lead_count"])
        self.assertEqual(0,sources["Arena Sferisterio"]["official_unpublished_opera_lead_count"])
        self.assertEqual(0,sources["Teatro Filarmonico"]["official_unpublished_opera_lead_count"])
        self.assertEqual(2,sources["Gran Teatro Giacomo Puccini"]["official_unpublished_opera_lead_count"])
        self.assertEqual(0,sources["Teatro Vittorio Emanuele"]["official_unpublished_opera_lead_count"])
        self.assertEqual(0,sources["Teatro Lirico di Cagliari"]["official_unpublished_opera_lead_count"])
        self.assertEqual(91,r["official_lead_reconciliation_counts"]["exact_match"])
        self.assertEqual(0,sources["Teatro Ponchielli"]["official_unpublished_opera_lead_count"])
        self.assertEqual(0,sources["Teatro Coccia"]["official_unpublished_opera_lead_count"])
        self.assertEqual(0,sources["Teatro del Giglio Giacomo Puccini"]["official_unpublished_opera_lead_count"])
        self.assertEqual(0,sources["Teatro Sociale di Mantova"]["official_unpublished_opera_lead_count"])
        self.assertEqual(0,sources["Teatro Dante Alighieri"]["official_unpublished_opera_lead_count"])
        ravenna=[p for p in self.leads["records"] if p["city"]=="Ravenna"]
        self.assertEqual(3,len(ravenna))
        self.assertTrue(all(clock is None for p in ravenna for day,clock in p["dates"]))
        self.assertEqual(0,sources["Teatro Alfieri"]["official_unpublished_opera_lead_count"])
        forbidden_school={("2026-01-30","11:00"),("2026-03-20","11:00"),
                          ("2026-04-21","11:00"),("2026-11-17","11:00"),
                          ("2026-11-18","11:00")}
        cagliari=[r for r in self.leads["records"] if r["city"]=="Cagliari"]
        self.assertTrue(all((date,clock) not in forbidden_school for p in cagliari
                            for date,clock in p["dates"]))
        self.assertTrue(all(p["dates"] and all(clock is not None for date,clock in p["dates"]) for p in cagliari))
        self.assertEqual(2,len([r for r in self.leads["records"] if r["city"]=="Novara"]))
        self.assertEqual(2,len(next(r for r in self.leads["records"]
                                   if r["title"].startswith("L’azzardo"))["dates"]))
        for row in r["rows"]:
            self.assertFalse(row["complete_month_verified"])
            for entry in row["official_unpublished_opera_leads"]:
                self.assertTrue(entry["publication_review_required"])
                self.assertFalse(entry["complete_month_verified"])
                self.assertEqual(row["month"],entry["date"][:7])
                if row["venue"]=="Arena Sferisterio":
                    self.assertIsNone(entry["time"])

    def test_official_leads_reject_mismatched_identity_and_duplicate_dates(self):
        import copy
        venues=self.inputs[0]["venues"]
        for patch in (
            {"venue_id":"oa-v-000999"},
            {"city":"Milano"},
            {"venue":"Teatro alla Scala"},
            {"official_url":"https://random.example.org/aida"},
            {"dates":[["2027-06-25","21:15"]]},
            {"dates":[["2026-06-25","25:15"]]},
        ):
            changed=copy.deepcopy(self.leads)
            changed["records"][0].update(patch)
            with self.assertRaises(ValueError):
                validated_venue_leads(changed,venues)
        changed=copy.deepcopy(self.leads)
        changed["records"].append(copy.deepcopy(changed["records"][0]))
        with self.assertRaises(ValueError):
            validated_venue_leads(changed,venues)

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

    def test_publish_restores_downloaded_artifact_before_checkout_latest_main(self):
        from pathlib import Path
        workflow=(Path(__file__).resolve().parents[1]/".github"/"workflows"/
                  "audit-2026-venue-month-coverage.yml").read_text(encoding="utf-8")
        backup="cp public/diagnostics/atlas-2026-venue-month-coverage.json /tmp/atlas-2026-venue-month-coverage.json"
        restore="git restore --worktree -- public/diagnostics/atlas-2026-venue-month-coverage.json"
        switch="git checkout -B publish-2026-venue-month FETCH_HEAD"
        replay="cp /tmp/atlas-2026-venue-month-coverage.json public/diagnostics/atlas-2026-venue-month-coverage.json"
        self.assertTrue(workflow.index(backup)<workflow.index(restore)<
                        workflow.index(switch)<workflow.index(replay))

    def test_does_not_read_or_change_live_published_records(self):
        before=json.dumps(self.inputs[2],sort_keys=True)
        build_matrix(*self.inputs)
        self.assertEqual(before,json.dumps(self.inputs[2],sort_keys=True))


if __name__=="__main__":
    unittest.main()


class IdentityAwareLeadTests(unittest.TestCase):
    def test_conservative_matching(self):
        from scripts.audit_2026_venue_month_coverage import reconcile_lead
        lead=dict(title="Carmen",composer="Georges Bizet",date="2026-04-24",time="20:00")
        candidate=dict(lead,venue_id="a")
        self.assertEqual("exact_match",reconcile_lead(lead,"a",[candidate]))
        self.assertEqual("identity_review",reconcile_lead(lead,"a",[dict(candidate,composer="Other")]))
        self.assertEqual("identity_review",reconcile_lead(lead,"a",[dict(candidate,title="Tosca")]))
        self.assertEqual("clock_review",reconcile_lead(lead,"a",[dict(candidate,time="21:00")]))
        self.assertEqual("clock_review",reconcile_lead(dict(lead,time=None),"a",[candidate]))
        self.assertEqual("venue_review",reconcile_lead(lead,"b",[candidate]))
        self.assertEqual("publication_candidate",reconcile_lead(lead,"a",[]))
        self.assertEqual("clock_review",reconcile_lead(dict(lead,time=None),"a",[]))

    def test_all_evidence_classified(self):
        report=VenueMonthMatrixTests.report if hasattr(VenueMonthMatrixTests,"report") else build_matrix(*docs(),json.loads(OFFICIAL_ZERO_VENUE_LEADS.read_text(encoding="utf-8")))
        self.assertEqual(93,sum(report["official_lead_reconciliation_counts"].values()))
        self.assertEqual(93,len(report["official_lead_reconciliation"]))


class CagliariReconciliationTests(unittest.TestCase):
    def test_frozen_archive_scope(self):
        from scripts.build_verified_catalog import build
        from scripts.publish_catalog_v2 import assemble
        manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        url="https://www.liricocagliari.it/archivio/it/spettacoli/2026_lirica.html"
        rows=[p for p in manifest["productions"] if p["source_url"]==url]
        self.assertEqual({"Norma","Turandot","Rigoletto","Lucrezia Borgia","Così fan tutte","Il cappello di paglia di Firenze"},{p["title"] for p in rows})
        self.assertEqual(35,sum(len(p["dates"]) for p in rows))
        published=[p for p in assemble(manifest,registry)["performances"] if p["source_url"]==url]
        self.assertEqual(35,len(published))
        self.assertEqual(35,len({p["id"] for p in published}))
        for field,value in (("composer","Other"),("venue","Other"),("dates",[["2026-03-20","11:00"]])):
            changed=copy.deepcopy(manifest)
            next(p for p in changed["productions"] if p["source_url"]==url)[field]=value
            with self.assertRaises(ValueError):
                build(changed)

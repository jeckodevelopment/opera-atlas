"""Daily network ingestion is opt-in, fail-closed and preserves permanent IDs."""
import copy
import json
import unittest
from datetime import date

from opera_atlas.controlled_fetch import FetchResult, FetchUnavailable
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY
from scripts.daily_ingest import scan_approved, validate_source_config, CONFIG

URL="https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata"


class DailyIngestionTests(unittest.TestCase):
    def setUp(self):
        self.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.config=json.loads(CONFIG.read_text(encoding="utf-8"))
        self.source=copy.deepcopy(self.config["sources"][0])
        self.source["access_status"]="approved"
        self.source["approval_evidence"]="Manually reviewed site robots.txt and use policy"

    def html(self, *,extra=None, omitted=None, change_time=False):
        dates=self.facts["productions"][0]["dates"]
        rows=[]
        for day,hour in dates:
            if day == omitted:
                continue
            if change_time and day=="2027-02-26":
                hour="21:00"
            rows.append(f"<p>{day} {hour}:00 Europe/Rome</p>")
        if extra:
            rows.append(f"<p>{extra} 20:00:00 Europe/Rome</p>")
        return "<h1>La traviata Giuseppe Verdi</h1>" + "".join(rows)

    def fetcher(self, html):
        return lambda conn, **kwargs: FetchResult(URL,html,"a"*64,len(html))

    def scan(self, html, *, sources=None):
        return scan_approved(
            self.facts,self.registry,sources if sources is not None else [self.source],
            network_enabled=True,fetcher=self.fetcher(html),today=date(2026,11,20),
        )

    def test_disabled_by_default_no_fetch(self):
        pending=copy.deepcopy(self.config)
        for item in pending["sources"]:
            item["access_status"]="pending"
            item["approval_evidence"]=None
        sources=validate_source_config(pending)
        def forbidden(*args, **kwargs):
            raise AssertionError("unapproved source must not fetch")
        facts,registry,status,added=scan_approved(
            self.facts,self.registry,sources,network_enabled=True,
            fetcher=forbidden,today=date(2026,11,20),
        )
        self.assertEqual(added,0)
        self.assertEqual(facts,self.facts)
        self.assertEqual(registry,self.registry)
        self.assertTrue(all(s["outcome"]=="pending" for s in status))

    def test_approval_requires_review_evidence(self):
        invalid=copy.deepcopy(self.config)
        invalid["sources"][0]["access_status"]="approved"
        invalid["sources"][0]["approval_evidence"]=None
        with self.assertRaises(ValueError):
            validate_source_config(invalid)

    def test_new_verified_date_allocates_persistent_id_and_preserves_old(self):
        facts,registry,health,added=self.scan(self.html(extra="2027-03-11"))
        self.assertEqual(added,1)
        self.assertEqual(health[0]["outcome"],"success")
        self.assertEqual(len(registry["performances"]),20)
        self.assertEqual(registry["performances"]["regio-traviata-2027|2027-02-26"],
                         self.registry["performances"]["regio-traviata-2027|2027-02-26"])
        self.assertEqual(registry["performances"]["regio-traviata-2027|2027-03-11"]["id"],
                         "oa-r-000020")
        self.assertEqual(facts["reviewed_on"],"2026-11-20")
        facts2,registry2,health2,added2=scan_approved(
            facts,registry,[self.source],network_enabled=True,
            fetcher=self.fetcher(self.html(extra="2027-03-11")),
            today=date(2026,11,20),
        )
        self.assertEqual(added2,0)
        self.assertEqual(registry2,registry)

    def test_missing_plus_new_date_is_manual_review(self):
        facts,registry,health,added=self.scan(
            self.html(extra="2027-03-11",omitted="2027-02-26")
        )
        self.assertEqual(added,0)
        self.assertEqual(facts,self.facts)
        self.assertEqual(registry,self.registry)
        self.assertEqual(health[0]["outcome"],"review_required")
        self.assertIn("possible_reschedule",
                      [a["kind"] for a in health[0]["anomalies"]])

    def test_changed_existing_hour_is_review_not_mutation(self):
        facts,registry,health,added=self.scan(self.html(change_time=True))
        self.assertEqual(added,0)
        self.assertEqual(facts,self.facts)
        self.assertEqual(registry,self.registry)
        self.assertIn("time_changed",[a["kind"] for a in health[0]["anomalies"]])

    def test_new_date_is_blocked_when_existing_hour_changed_same_page(self):
        facts,registry,health,added=self.scan(
            self.html(extra="2027-03-11", change_time=True)
        )
        self.assertEqual(added,0)
        self.assertEqual(facts,self.facts)
        self.assertEqual(registry,self.registry)
        self.assertEqual(health[0]["outcome"],"review_required")
        self.assertIn("time_changed",
                      [x["kind"] for x in health[0]["anomalies"]])

    def test_duplicate_dates_block_entire_page(self):
        html=self.html(extra="2027-03-11")
        html += "<p>2027-03-11 20:00:00 Europe/Rome</p>"
        # The Regio parser deduplicates identical source timestamps; a
        # genuinely contradictory record is the correct rejection scenario.
        html += "<p>2027-03-11 21:00:00 Europe/Rome</p>"
        facts,registry,health,added=self.scan(html)
        self.assertEqual(added,0)
        self.assertEqual(facts,self.facts)
        self.assertEqual(registry,self.registry)
        self.assertEqual(health[0]["outcome"],"review_required")

    def test_fetch_failure_preserves_last_known_good(self):
        def unavailable(*args,**kwargs):
            raise FetchUnavailable("robots.txt unavailable")
        facts,registry,health,added=scan_approved(
            self.facts,self.registry,[self.source],
            network_enabled=True,fetcher=unavailable,today=date(2026,11,20),
        )
        self.assertEqual((facts,registry,added),(self.facts,self.registry,0))
        self.assertEqual(health[0]["outcome"],"unavailable_or_invalid")

if __name__=="__main__":
    unittest.main()

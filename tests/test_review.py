"""Human-controlled review resolution and provenance retention."""
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from opera_atlas.db import add_work, add_performance, connect, migrate
from opera_atlas.reconciliation import reconcile
from opera_atlas.review import resolve_review


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        migrate(self.db)
        work = add_work(self.db, "Rigoletto", "Giuseppe Verdi")
        self.db.execute("INSERT INTO venues(name,municipality,region) VALUES ('Regio','Torino','Piemonte')")
        for key in ("first","second"):
            self.db.execute("INSERT INTO productions(work_id,production_key) VALUES (?,?)",(work,key))
        self.db.execute("INSERT INTO sources(official_url) VALUES ('https://example.org')")
        self.when = datetime(2026,12,3,20,tzinfo=ZoneInfo("Europe/Rome"))

    def tearDown(self):
        self.db.close()

    def ingest(self, when):
        return reconcile(self.db,source_id=1,external_id="original",
                         source_url="https://example.org/event/1",
                         production_id=1,venue_id=1,starts_at=when,
                         payload={"starts":when.isoformat()})

    def test_changed_date_resolved_by_creating_new_event(self):
        old=self.ingest(self.when)
        proposal=self.ingest(self.when + timedelta(days=1))
        self.assertEqual(proposal.state,"review")
        target=resolve_review(self.db,proposal.review_id,action="create")
        self.assertNotEqual(target,old.performance_id)
        self.assertEqual(self.db.execute("SELECT performance_id FROM source_events").fetchone()[0],target)
        self.assertEqual(self.db.execute("SELECT count(*) FROM reconciliation_reviews WHERE state='open'").fetchone()[0],0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM performance_sources").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM performances").fetchone()[0],2)

    def test_ambiguous_match_resolved_by_explicit_selection(self):
        self.ingest(self.when)
        second=add_performance(self.db,2,1,self.when)
        proposal=reconcile(self.db,source_id=1,external_id="another",
                           source_url="https://example.org/event/2",
                           production_id=2,venue_id=1,starts_at=self.when,payload={})
        self.assertEqual(proposal.state,"review")
        self.assertEqual(resolve_review(self.db,proposal.review_id,action="link",
                                        selected_performance_id=second),second)

    def test_refuses_wrong_date_and_duplicate_resolution(self):
        self.ingest(self.when)
        proposal=self.ingest(self.when + timedelta(days=1))
        with self.assertRaises(ValueError):
            resolve_review(self.db,proposal.review_id,action="link",selected_performance_id=1)
        resolve_review(self.db,proposal.review_id,action="create")
        with self.assertRaises(ValueError):
            resolve_review(self.db,proposal.review_id,action="create")

    def test_migrations_idempotent(self):
        self.ingest(self.when)
        migrate(self.db)
        self.assertEqual(self.db.execute("SELECT count(*) FROM schema_migrations").fetchone()[0], 6)


if __name__ == "__main__":
    unittest.main()

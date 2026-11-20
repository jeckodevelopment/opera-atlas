"""Cross-source matching, refusal to rewrite identities, and collisions."""
import sqlite3
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from opera_atlas.db import add_performance, add_work, connect, migrate
from opera_atlas.reconciliation import reconcile


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        migrate(self.db)
        work = add_work(self.db, "Rigoletto", "Giuseppe Verdi")
        second = add_work(self.db, "Rigoletto", "Different composer")
        self.db.execute("INSERT INTO venues(name,municipality,region) VALUES ('Regio','Torino','Piemonte')")
        for work_id, key in ((work,"regio"),(work,"festival"),(second,"other")):
            self.db.execute("INSERT INTO productions(work_id,production_key) VALUES (?,?)", (work_id,key))
        for url in ("https://example.org/regio", "https://example.org/festival"):
            self.db.execute("INSERT INTO sources(official_url) VALUES (?)", (url,))
        self.when = datetime(2026, 12, 2, 20, 0, tzinfo=ZoneInfo("Europe/Rome"))

    def tearDown(self):
        self.db.close()

    def ingest(self, source, external, production, when=None, payload=None):
        return reconcile(
            self.db, source_id=source, external_id=external,
            source_url=f"https://example.org/{source}/{external}",
            production_id=production, venue_id=1,
            starts_at=when or self.when, payload=payload or {"title":"Rigoletto"},
        )

    def test_duplicate_across_theatre_and_festival(self):
        a = self.ingest(1, "one", 1)
        b = self.ingest(2, "event-55", 2)
        self.assertEqual(a.performance_id,b.performance_id)
        self.assertEqual(self.db.execute("SELECT count(*) FROM performances").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM performance_sources").fetchone()[0],2)

    def test_exact_source_rerun_idempotent(self):
        a = self.ingest(1,"one",1)
        b = self.ingest(1,"one",1)
        self.assertEqual(a,b)
        self.assertEqual(self.db.execute("SELECT count(*) FROM source_events").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM performance_sources").fetchone()[0],1)

    def test_timezone_equivalence(self):
        a = self.ingest(1,"one",1)
        b = self.ingest(2,"two",2,self.when.astimezone(timezone.utc))
        self.assertEqual(a.performance_id,b.performance_id)

    def test_changed_date_requires_review_and_keeps_old_link(self):
        a = self.ingest(1,"one",1)
        later = self.when + timedelta(days=1)
        b = self.ingest(1,"one",1,later,payload={"date":"changed"})
        self.assertEqual(b.state,"review")
        self.assertEqual(b.performance_id,a.performance_id)
        self.assertIsNotNone(b.review_id)
        self.assertEqual(self.db.execute("SELECT count(*) FROM performances").fetchone()[0],1)
        again = self.ingest(1,"one",1,later,payload={"date":"changed"})
        self.assertEqual(again.review_id,b.review_id)

    def test_homonymous_opera_not_merged(self):
        a = self.ingest(1,"one",1)
        b = self.ingest(2,"two",3)
        self.assertNotEqual(a.performance_id,b.performance_id)

    def test_multiple_candidates_are_reviewed(self):
        a = self.ingest(1,"one",1)
        # Simulate legacy duplicates to force a collision.
        add_performance(self.db,2,1,self.when)
        b = self.ingest(2,"two",2)
        self.assertEqual(b.state,"review")
        self.assertIsNone(b.performance_id)
        self.assertEqual(self.db.execute("SELECT count(*) FROM performances").fetchone()[0],2)

    def test_missing_source_rejected(self):
        with self.assertRaises(ValueError):
            self.ingest(999,"one",1)

    def test_invalid_source_url_rejected(self):
        with self.assertRaises(ValueError):
            reconcile(self.db,source_id=1,external_id="x",source_url="file:///tmp/a",
                      production_id=1,venue_id=1,starts_at=self.when,payload={})

    def test_migration_repeated_without_loss(self):
        self.ingest(1,"one",1)
        migrate(self.db)
        self.assertEqual(self.db.execute("SELECT count(*) FROM schema_migrations").fetchone()[0], 6)
        self.assertEqual(self.db.execute("SELECT count(*) FROM source_events").fetchone()[0],1)


if __name__ == "__main__":
    unittest.main()

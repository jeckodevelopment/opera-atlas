"""Incremental snapshots must never confuse a reschedule with a new show."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from opera_atlas.catalog import register_work
from opera_atlas.db import connect,migrate
from opera_atlas.ingestion import import_regio_snapshot
from opera_atlas.incremental import acknowledge_delta,compare_snapshot

URL="https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata"
def page(*times):
    return "<h1>La traviata | Giuseppe Verdi</h1>"+"".join(
        f"<p>{v} Europe/Rome</p>" for v in times
    )

class IncrementalTests(unittest.TestCase):
    def setUp(self):
        self.conn=connect()
        migrate(self.conn)
        work=register_work(self.conn,"La traviata","Giuseppe Verdi")
        self.conn.execute("INSERT INTO productions(work_id) VALUES (?)",(work,))
        self.conn.execute("INSERT INTO venues(name,municipality,region) VALUES ('Teatro Regio','Torino','Piemonte')")
        self.conn.execute("INSERT INTO sources(official_url,access_status) VALUES ('https://www.teatroregio.torino.it/','approved')")

    def tearDown(self):
        self.conn.close()

    def ingest(self,html):
        return import_regio_snapshot(
            self.conn,html=html,source_url=URL,source_id=1,
            venue_id=1,production_id=1,expected_title="La traviata",
            expected_composer="Giuseppe Verdi",
        )

    def test_changed_date_does_not_create_duplicate(self):
        first=self.ingest(page("2027-02-26 20:00:00"))
        self.assertEqual(first.linked,1)
        changed=self.ingest(page("2027-03-02 20:00:00"))
        self.assertEqual(changed.linked,0)
        self.assertEqual(changed.review,1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM performances").fetchone()[0],1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM source_snapshot_deltas").fetchone()[0],1)
        self.ingest(page("2027-03-02 20:00:00"))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM source_snapshot_deltas").fetchone()[0],1)

    def test_new_added_without_missing_can_be_imported(self):
        self.ingest(page("2027-02-26 20:00:00"))
        result=self.ingest(page("2027-02-26 20:00:00","2027-02-27 20:00:00"))
        self.assertEqual(result.linked,2)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM performances").fetchone()[0],2)

    def test_removed_date_never_cancels_event(self):
        self.ingest(page("2027-02-26 20:00:00","2027-02-27 20:00:00"))
        changed=self.ingest(page("2027-02-26 20:00:00"))
        self.assertEqual(changed.review,0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM performances").fetchone()[0],2)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM performances WHERE status='cancelled'").fetchone()[0],0)

    def test_empty_snapshot_no_deletion_or_delta(self):
        self.ingest(page("2027-02-26 20:00:00"))
        with self.assertRaises(ValueError):
            self.ingest("<h1>La traviata | Giuseppe Verdi</h1>")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM performances").fetchone()[0],1)

    def test_delta_acknowledgement_requires_explanation(self):
        self.ingest(page("2027-02-26 20:00:00"))
        self.ingest(page("2027-02-27 20:00:00"))
        with self.assertRaises(ValueError):
            acknowledge_delta(self.conn,1,reason="")
        acknowledge_delta(self.conn,1,reason="Verified dates on source")
        self.assertEqual(self.conn.execute("SELECT state FROM source_snapshot_deltas").fetchone()[0],"acknowledged")
        with self.assertRaises(ValueError):
            acknowledge_delta(self.conn,1,reason="again")

    def test_official_stable_id_date_change_enters_existing_review(self):
        old = ('<h1>La traviata | Giuseppe Verdi</h1>'
               '<time data-event-id="recita-34" datetime="2027-02-26T20:00:00+01:00"></time>')
        moved = ('<h1>La traviata | Giuseppe Verdi</h1>'
                 '<time data-event-id="recita-34" datetime="2027-03-02T20:00:00+01:00"></time>')
        first=self.ingest(old)
        second=self.ingest(moved)
        self.assertEqual(first.linked,1)
        self.assertEqual(second.review,1)
        self.assertEqual(second.linked,0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM performances").fetchone()[0],1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM reconciliation_reviews").fetchone()[0],1)
        external=self.conn.execute("SELECT external_id FROM source_events").fetchone()[0]
        self.assertTrue(external.endswith(":event:recita-34"))

    def test_stable_id_conflicting_times_refused(self):
        invalid=('<h1>La traviata | Giuseppe Verdi</h1>'
                 '<time data-event-id="recita-34" datetime="2027-02-26T20:00:00+01:00"></time>'
                 '<time data-event-id="recita-34" datetime="2027-03-02T20:00:00+01:00"></time>')
        with self.assertRaises(ValueError):
            self.ingest(invalid)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM performances").fetchone()[0],0)

    def test_migration_repeated(self):
        migrate(self.conn)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM schema_migrations").fetchone()[0],7)

if __name__=="__main__":
    unittest.main()

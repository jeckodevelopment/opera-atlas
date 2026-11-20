"""Explicit lifecycle changes, evidence verification and export filtering."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from opera_atlas.changes import list_status_history,set_performance_status
from opera_atlas.db import add_performance,add_work,connect,migrate
from opera_atlas.ingestion import export_public_catalog
from opera_atlas.reconciliation import reconcile

URL="https://example.org/recita/1"


class ChangeTests(unittest.TestCase):
    def setUp(self):
        self.conn=connect()
        migrate(self.conn)
        work=add_work(self.conn,"Rigoletto","Giuseppe Verdi")
        self.conn.execute("INSERT INTO productions(work_id) VALUES (?)",(work,))
        self.conn.execute("INSERT INTO venues(name,municipality,region) VALUES ('Regio','Torino','Piemonte')")
        self.conn.execute("INSERT INTO sources(official_url,access_status) VALUES ('https://example.org','approved')")
        self.start=datetime(2027,2,1,20,tzinfo=ZoneInfo("Europe/Rome"))
        self.pid=reconcile(
            self.conn,source_id=1,external_id="recita-1",source_url=URL,
            production_id=1,venue_id=1,starts_at=self.start,payload={"event":"first"}
        ).performance_id

    def tearDown(self):
        self.conn.close()

    def update(self,status,reason="Official update",url=URL):
        return set_performance_status(
            self.conn,performance_id=self.pid,status=status,
            source_url=url,reason=reason,
        )

    def test_confirm_then_cancel_is_audited(self):
        self.assertTrue(self.update("confirmed"))
        self.assertTrue(self.update("cancelled","Cancelled by organizer"))
        history=list_status_history(self.conn,self.pid)
        self.assertEqual([(x["previous_status"],x["new_status"]) for x in history],
                         [("announced","confirmed"),("confirmed","cancelled")])
        self.assertEqual(self.conn.execute("SELECT status FROM performances").fetchone()[0],
                         "cancelled")

    def test_repeat_is_noop(self):
        self.update("confirmed")
        self.assertFalse(self.update("confirmed"))
        self.assertEqual(len(list_status_history(self.conn,self.pid)),1)

    def test_reject_invalid_transition(self):
        self.update("cancelled")
        with self.assertRaises(ValueError):
            self.update("announced")
        self.assertEqual(len(list_status_history(self.conn,self.pid)),1)

    def test_reject_unapproved_or_unlinked_source(self):
        with self.assertRaises(ValueError):
            self.update("cancelled",url="https://example.org/recita/other")
        self.conn.execute("UPDATE sources SET access_status='blocked'")
        with self.assertRaises(ValueError):
            self.update("cancelled")
        self.assertEqual(len(list_status_history(self.conn,self.pid)),0)

    def test_reject_empty_reason(self):
        with self.assertRaises(ValueError):
            self.update("postponed",reason="  ")

    def test_reimport_does_not_reset_status(self):
        self.update("postponed")
        reconcile(self.conn,source_id=1,external_id="recita-1",source_url=URL,
                  production_id=1,venue_id=1,starts_at=self.start,payload={"event":"first"})
        self.assertEqual(self.conn.execute("SELECT status FROM performances").fetchone()[0],
                         "postponed")

    def test_cancelled_excluded_from_public_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"catalog.json"
            self.assertEqual(export_public_catalog(self.conn,path),1)
            self.update("cancelled")
            self.assertEqual(export_public_catalog(self.conn,path),0)
            self.assertEqual(json.loads(path.read_text())["performances"],[])

    def test_migration_repeated(self):
        migrate(self.conn)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0],6)


if __name__=="__main__":
    unittest.main()

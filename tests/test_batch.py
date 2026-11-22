"""Batch preflight, idempotence and savepoint isolation with fake HTTP only."""
import json
import tempfile
import unittest
from pathlib import Path

from opera_atlas.batch import load_manifest, run_batch
from opera_atlas.catalog import register_work
from opera_atlas.db import connect, migrate
from test_controlled_fetch import FakeOpener

URL = "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata"
PAGE = (b"<h1>La traviata | Giuseppe Verdi</h1>"
        b"<p>2027-02-26 20:00:00 Europe/Rome</p>")


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.conn = connect()
        migrate(self.conn)
        work = register_work(self.conn, "La traviata", "Giuseppe Verdi")
        self.conn.execute("INSERT INTO productions(work_id) VALUES (?)", (work,))
        self.conn.execute(
            "INSERT INTO venues(name,municipality,region) VALUES "
            "('Teatro Regio','Torino','Piemonte')"
        )
        self.conn.execute(
            "INSERT INTO sources(official_url,access_status) "
            "VALUES ('https://www.teatroregio.torino.it/','approved')"
        )
        self.entry = {
            "url": URL, "source_id": 1, "venue_id": 1,
            "production_id": 1, "title": "La traviata",
            "composer": "Giuseppe Verdi"
        }

    def tearDown(self):
        self.conn.close()

    def test_one_page_success_and_idempotency(self):
        r = run_batch(self.conn, [self.entry], network_enabled=True,
                      opener=FakeOpener(html=PAGE))
        self.assertEqual((r.succeeded, r.linked), (1, 1))
        r = run_batch(self.conn, [self.entry], network_enabled=True,
                      opener=FakeOpener(html=PAGE))
        self.assertEqual(r.discovered, 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM performances").fetchone()[0],1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM source_checks").fetchone()[0],2)

    def test_robots_unavailable_does_not_block_approved_page(self):
        r=run_batch(self.conn,[self.entry],network_enabled=True,
                    opener=FakeOpener(robots=None,html=PAGE))
        self.assertEqual((r.succeeded,r.failed),(1,0))
        self.assertEqual(self.conn.execute("SELECT outcome FROM source_checks").fetchone()[0],
                         "success")

    def test_rejected_source_blocks_entire_batch_before_http(self):
        self.conn.execute("UPDATE sources SET access_status='pending'")
        opener=FakeOpener(html=PAGE)
        with self.assertRaises(ValueError):
            run_batch(self.conn,[self.entry],network_enabled=True,opener=opener)
        self.assertEqual(opener.calls, [])

    def test_no_implicit_network(self):
        with self.assertRaises(ValueError):
            run_batch(self.conn,[self.entry])
    
    def test_isolate_page_failure_with_savepoint(self):
        second = dict(self.entry)
        second["url"] = URL + "-variant"
        second["composer"] = "Incorrect composer"
        # Same source but invalid curation should fail after fetch, leaving no partial writes.
        r=run_batch(self.conn,[self.entry,second],network_enabled=True,opener=FakeOpener(html=PAGE))
        self.assertEqual((r.succeeded,r.failed),(1,1))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM performances").fetchone()[0],1)
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM source_checks WHERE outcome='import_error'"
        ).fetchone()[0],1)

    def test_registry_rejects_duplicated_and_noncanonical_urls(self):
        doc={"schema_version":1,"productions":[self.entry,self.entry]}
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"manifest.json"
            p.write_text(json.dumps(doc),encoding="utf-8")
            with self.assertRaises(ValueError):
                load_manifest(p)
            doc["productions"]=[{**self.entry,"url":"https://example.org/event"}]
            p.write_text(json.dumps(doc),encoding="utf-8")
            with self.assertRaises(ValueError):
                load_manifest(p)

    def test_registry_single_fixture(self):
        data=load_manifest(Path(__file__).parent/"fixtures"/"regio-manifest.json")
        self.assertEqual(len(data),1)

if __name__ == "__main__":
    unittest.main()

"""Schema, integrity and timezone checks: python -m unittest discover -s tests."""
import sqlite3
import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from opera_atlas.db import (
    add_performance,
    add_work,
    connect,
    local_start,
    migrate,
    normalize_title,
)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        migrate(self.db)
        self.db.execute(
            "INSERT INTO organizations(name,kind) VALUES ('Example','theatre')"
        )
        self.db.execute(
            "INSERT INTO venues(name,municipality,region) VALUES "
            "('Teatro Demo','Torino','Piemonte')"
        )
        self.work = add_work(self.db, "Rigoletto", "Giuseppe Verdi")
        self.db.execute(
            "INSERT INTO productions(work_id,production_key) VALUES (?,?)",
            (self.work, "demo-production"),
        )

    def tearDown(self):
        self.db.close()

    def test_migration_idempotent(self):
        migrate(self.db)
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0],
            1,
        )

    def test_normalization_without_inventing_identity(self):
        self.assertEqual(normalize_title("  LA   Bohème "), "la bohème")
        other = add_work(self.db, "Rigoletto", "Other composer")
        self.assertNotEqual(self.work, other)

    def test_invalid_coordinates_are_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO venues(name,municipality,region,latitude) "
                "VALUES ('Invalid','Roma','Lazio',41.9)"
            )

    def test_fk_enforced(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO productions(work_id) VALUES (999999)")

    def test_performance_requires_timezone(self):
        with self.assertRaises(ValueError):
            local_start(datetime(2026, 11, 25, 20, 0))

    def test_idempotent_performance(self):
        start = datetime(2026, 11, 25, 19, 30, tzinfo=ZoneInfo("Europe/Rome"))
        first = add_performance(self.db, 1, 1, start)
        second = add_performance(self.db, 1, 1, start)
        self.assertEqual(first, second)
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM performances").fetchone()[0], 1
        )

    def test_observation_fingerprint_idempotent(self):
        self.db.execute(
            "INSERT INTO sources(official_url) VALUES ('https://example.org')"
        )
        for _ in range(2):
            self.db.execute(
                "INSERT OR IGNORE INTO observations"
                "(source_id, external_id, fingerprint, payload_json)"
                " VALUES (1,'evt-1','abc','{}')"
            )
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 1
        )

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            add_performance(
                self.db, 1, 1,
                datetime(2026, 11, 25, 19, tzinfo=timezone.utc),
                status="invented"
            )


if __name__ == "__main__":
    unittest.main()

"""F1 #3 regressions: namesake venues and multi-organizer productions.

Only in-memory SQLite fixtures; never operate on a published identity registry.
"""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from opera_atlas.db import add_work, connect, migrate
from opera_atlas.reconciliation import reconcile


class CanonicalIdentityEdgeTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        migrate(self.db)
        work_id = add_work(self.db, "Rigoletto", "Giuseppe Verdi")
        self.db.execute(
            "INSERT INTO productions(work_id, production_key) VALUES (?, ?)",
            (work_id, "f1-verified-production"),
        )
        self.db.executemany(
            "INSERT INTO sources(official_url) VALUES (?)",
            [("https://example.org/theatre",), ("https://example.org/festival",)],
        )
        self.when = datetime(2027, 2, 6, 20, tzinfo=ZoneInfo("Europe/Rome"))

    def tearDown(self):
        self.db.close()

    def ingest(self, source_id, external_id, venue_id, production_id=1):
        return reconcile(
            self.db,
            source_id=source_id,
            external_id=external_id,
            source_url=f"https://example.org/{source_id}/{external_id}",
            production_id=production_id,
            venue_id=venue_id,
            starts_at=self.when,
            payload={"work": "Rigoletto", "date": self.when.isoformat()},
        )

    def test_namesake_venues_in_different_cities_never_merge(self):
        self.db.executemany(
            "INSERT INTO venues(name, municipality, region) VALUES (?, ?, ?)",
            [("Teatro Comunale", "Torino", "Piemonte"),
             ("Teatro Comunale", "Bologna", "Emilia-Romagna")],
        )
        torino = self.ingest(1, "performance-1", 1)
        bologna = self.ingest(2, "performance-1", 2)
        self.assertEqual(torino.state, "linked")
        self.assertEqual(bologna.state, "linked")
        self.assertNotEqual(torino.performance_id, bologna.performance_id)
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM performances").fetchone()[0], 2
        )
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM performance_sources").fetchone()[0], 2
        )
        self.assertEqual(
            self.ingest(1, "performance-1", 1).performance_id, torino.performance_id
        )
        self.assertEqual(
            self.ingest(2, "performance-1", 2).performance_id, bologna.performance_id
        )
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM performances").fetchone()[0], 2
        )

    def test_coproduction_two_organizers_one_performance_two_sources(self):
        self.db.execute(
            "INSERT INTO venues(name, municipality, region) VALUES ('Teatro Sociale', 'Como', 'Lombardia')"
        )
        self.db.executemany(
            "INSERT INTO organizations(name, kind) VALUES (?, ?)",
            [("Teatro capofila", "theatre"), ("Festival partner", "festival")],
        )
        self.db.executemany(
            "INSERT INTO production_organizations(production_id, organization_id, role)"
            " VALUES (1, ?, ?)",
            [(1, "producer"), (2, "coproducer")],
        )
        first = self.ingest(1, "theatre-ticket-22", 1)
        partner = self.ingest(2, "festival-ticket-22", 1)
        self.assertEqual(first.state, "linked")
        self.assertEqual(partner.state, "linked")
        self.assertEqual(first.performance_id, partner.performance_id)
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM performances").fetchone()[0], 1
        )
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM production_organizations").fetchone()[0],
            2,
        )
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM performance_sources").fetchone()[0], 2
        )
        self.assertEqual(
            self.ingest(2, "festival-ticket-22", 1).performance_id,
            first.performance_id,
        )
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM performances").fetchone()[0], 1
        )
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM production_organizations").fetchone()[0],
            2,
        )


if __name__ == "__main__":
    unittest.main()

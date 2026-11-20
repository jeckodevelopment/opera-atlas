"""Official source registry validation and idempotent seeding."""
import json
import tempfile
import unittest
from pathlib import Path

from opera_atlas.db import connect, migrate
from opera_atlas.source_registry import read_registry, seed_sources


class SourceRegistryTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        migrate(self.db)

    def tearDown(self):
        self.db.close()

    def test_official_entries_pass_validation(self):
        rows = read_registry()
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(x["access_status"] == "pending" for x in rows))

    def test_seed_is_idempotent_and_never_enables_crawling(self):
        self.assertEqual(seed_sources(self.db), 8)
        self.assertEqual(seed_sources(self.db), 0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM sources").fetchone()[0], 8)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM sources WHERE access_status='approved'"
        ).fetchone()[0], 0)

    def test_existing_access_decision_is_not_overwritten(self):
        seed_sources(self.db)
        self.db.execute(
            "UPDATE sources SET access_status='blocked' WHERE official_url=?",
            ("https://www.teatroregio.torino.it/",),
        )
        seed_sources(self.db)
        state = self.db.execute(
            "SELECT access_status FROM sources WHERE official_url=?",
            ("https://www.teatroregio.torino.it/",),
        ).fetchone()[0]
        self.assertEqual(state, "blocked")

    def test_rejects_duplicate_registry_entries(self):
        doc = {"schema_version":1, "sources":read_registry()*2}
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sources.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_registry(p)

    def test_rejects_unauthorized_crawling_status(self):
        doc = {"schema_version":1, "sources":read_registry()}
        doc["sources"][0]["access_status"] = "approved"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sources.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_registry(p)


if __name__ == "__main__":
    unittest.main()

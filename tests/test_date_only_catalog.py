"""Date-only published evidence must appear without fictitious hours.

These tests rely on synthetic HTML and local SQLite: they do not fetch live data.
"""
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from opera_atlas.db import connect, migrate
from opera_atlas.catalog import register_work
from opera_atlas.reconciliation import reconcile
from opera_atlas.ingestion import export_public_catalog
from opera_atlas.operalombardia import stage_dates

SOURCE = "https://www.operalombardia.it/"
URL = SOURCE + "l-italiana-in-algeri/"
HTML = ('<h1>L’italiana in Algeri</h1><h2>RECITE:</h2>'
        '<p>Teatro Sociale, Como – 13 e 15 novembre 2026</p>'
        '<p>Teatro Fraschini, Pavia – 20 e 22 novembre 2026</p>')


class DateOnlyPublicCatalogTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        migrate(self.db)
        self.db.execute(
            "INSERT INTO sources(official_url,access_status) "
            "VALUES (?, 'approved')", (SOURCE,),
        )

    def tearDown(self):
        self.db.close()

    def stage(self):
        return stage_dates(
            self.db, source_id=1, html=HTML, url=URL,
            title="L’italiana in Algeri",
        )

    def catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / "catalog.json"
            total = export_public_catalog(self.db, filename)
            return total, json.loads(filename.read_text(encoding="utf-8"))["performances"]

    def test_date_and_place_without_hour_is_public(self):
        self.assertEqual(self.stage(), 4)
        total, events = self.catalog()
        self.assertEqual(total, 4)
        self.assertEqual(len(events), 4)
        self.assertEqual([x["local_date"] for x in events],
                         ["2026-11-13", "2026-11-15", "2026-11-20", "2026-11-22"])
        self.assertTrue(all(x["starts_at"] is None and not x["time_known"] for x in events))
        self.assertTrue(all(x["time_label"] == "Orario da confermare" for x in events))
        self.assertTrue(all(x["sources"] == [URL] for x in events))
        self.assertTrue(all(x["venue"] and x["municipality"] and x["title"] for x in events))
        self.assertTrue(all(str(x["id"]).startswith("staged:") for x in events))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM performances").fetchone()[0], 0)

    def test_unchanged_staging_is_idempotent(self):
        self.stage()
        self.stage()
        total, _ = self.catalog()
        self.assertEqual(total, 4)

    def test_source_approval_controls_visibility(self):
        self.stage()
        self.db.execute("UPDATE sources SET access_status='blocked'")
        total, events = self.catalog()
        self.assertEqual((total, events), (0, []))

    def test_discarded_or_review_state_is_not_public(self):
        self.stage()
        self.db.execute("UPDATE staged_recite SET state='discarded' WHERE local_date='2026-11-15'")
        self.db.execute("UPDATE staged_recite SET state='ready_for_review' WHERE local_date='2026-11-22'")
        total, _ = self.catalog()
        self.assertEqual(total, 2)

    def test_verified_hour_supersedes_date_only_entry(self):
        self.stage()
        work = register_work(self.db,"L’italiana in Algeri","Gioachino Rossini")
        self.db.execute("INSERT INTO productions(work_id) VALUES (?)", (work,))
        self.db.execute(
            "INSERT INTO venues(name,municipality,region) VALUES "
            "('Teatro Sociale','Como','Lombardia')"
        )
        self.db.execute(
            "INSERT INTO sources(official_url,access_status) VALUES "
            "('https://example.org/','approved')"
        )
        exact_time = datetime(2026,11,13,20,30,tzinfo=ZoneInfo("Europe/Rome"))
        reconcile(
            self.db,source_id=2,external_id="show-1",
            source_url="https://example.org/show-1",
            production_id=1,venue_id=1,starts_at=exact_time,payload={"verified":True},
        )
        total, events=self.catalog()
        self.assertEqual(total,4)
        matching=[x for x in events if x["local_date"]=="2026-11-13"]
        self.assertEqual(len(matching),1)
        self.assertTrue(matching[0]["time_known"])
        self.assertEqual(matching[0]["time_label"],"20:30")
        self.assertEqual(matching[0]["starts_at"],"2026-11-13T20:30:00+01:00")
        # The staged evidence stays in the DB, even though the public card is merged.
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM staged_recite").fetchone()[0],4)

    def test_unknown_venue_never_merges_by_city_only(self):
        self.stage()
        work=register_work(self.db,"L’italiana in Algeri","Gioachino Rossini")
        self.db.execute("INSERT INTO productions(work_id) VALUES (?)",(work,))
        self.db.execute(
            "INSERT INTO venues(name,municipality,region) VALUES "
            "('Teatro Alternativo','Como','Lombardia')"
        )
        self.db.execute(
            "INSERT INTO sources(official_url,access_status) VALUES "
            "('https://example.org/','approved')"
        )
        reconcile(
            self.db,source_id=2,external_id="other",
            source_url="https://example.org/other",
            production_id=1,venue_id=1,
            starts_at=datetime(2026,11,13,20,tzinfo=ZoneInfo("Europe/Rome")),
            payload={},
        )
        total, events=self.catalog()
        self.assertEqual(total,5)
        self.assertEqual(len([x for x in events if x["local_date"]=="2026-11-13"]),2)

if __name__=="__main__":
    unittest.main()

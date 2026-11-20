"""Ingestion/audit orchestration: all HTTP calls fake, no live networking."""
import unittest
from opera_atlas.catalog import register_work
from opera_atlas.db import connect, migrate
from opera_atlas.scan import scan_regio_detail
from test_controlled_fetch import FakeOpener

URL = "https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata"
HTML = (b"<html><h1>La traviata | Giuseppe Verdi</h1>"
        b"<section>2027-02-26 20:00:00 Europe/Rome</section></html>")


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        migrate(self.db)
        work = register_work(self.db, "La traviata", "Giuseppe Verdi")
        self.db.execute("INSERT INTO productions(work_id,production_key) VALUES (?,?)",
                        (work,"demo"))
        self.db.execute("INSERT INTO venues(name,municipality,region) VALUES ('Teatro Regio','Torino','Piemonte')")
        self.db.execute("INSERT INTO sources(official_url,access_status) VALUES "
                        "('https://www.teatroregio.torino.it/','approved')")

    def tearDown(self):
        self.db.close()

    def scan(self, opener):
        return scan_regio_detail(
            self.db, url=URL, source_id=1, venue_id=1, production_id=1,
            title="La traviata", composer="Giuseppe Verdi",
            opener=opener, network_enabled=True,
        )

    def test_import_and_audit(self):
        self.assertEqual(self.scan(FakeOpener(html=HTML)).outcome,"success")
        self.assertEqual(self.scan(FakeOpener(html=HTML)).linked,1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM performances").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM source_checks WHERE outcome='success'").fetchone()[0],2)

    def test_no_robots_no_import(self):
        result = self.scan(FakeOpener(robots=None,html=HTML))
        self.assertEqual(result.outcome,"robots_unavailable")
        self.assertEqual(self.db.execute("SELECT count(*) FROM performances").fetchone()[0],0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM source_checks").fetchone()[0],1)

    def test_explicit_robots_denial(self):
        result = self.scan(FakeOpener(robots=b"User-agent: *\nDisallow: /",html=HTML))
        self.assertEqual(result.outcome,"robots_blocked")
        self.assertEqual(self.db.execute("SELECT count(*) FROM performances").fetchone()[0],0)


if __name__ == "__main__":
    unittest.main()

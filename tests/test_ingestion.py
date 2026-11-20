"""Offline production-page extraction and transactional catalog integration."""
import json
import tempfile
import unittest
from pathlib import Path

from opera_atlas.catalog import register_work
from opera_atlas.db import connect,migrate
from opera_atlas.ingestion import import_regio_snapshot,export_public_catalog
from opera_atlas.regio_parser import parse_regio_detail

URL="https://www.teatroregio.torino.it/opera-e-balletto-2026-2027/la-traviata"
HTML=(Path(__file__).parent/"fixtures"/"regio-traviata.html").read_text(encoding="utf-8")


class RegioIngestionTests(unittest.TestCase):
    def setUp(self):
        self.db=connect()
        migrate(self.db)
        self.work=register_work(self.db,"La traviata","Giuseppe Verdi")
        self.db.execute("INSERT INTO productions(work_id,production_key) VALUES (?,?)",(self.work,"regio-2027-traviata"))
        self.db.execute("INSERT INTO venues(name,municipality,region,verification_status) VALUES ('Teatro Regio','Torino','Piemonte','verified')")
        self.db.execute("INSERT INTO sources(official_url,access_status) VALUES ('https://www.teatroregio.torino.it/','approved')")

    def tearDown(self):
        self.db.close()

    def ingest(self):
        return import_regio_snapshot(self.db,html=HTML,source_url=URL,source_id=1,
                                     venue_id=1,production_id=1,
                                     expected_title="La traviata",expected_composer="Giuseppe Verdi")

    def test_extract_deduplicated_individual_dates(self):
        facts=parse_regio_detail(HTML,source_url=URL,expected_title="La traviata",expected_composer="Giuseppe Verdi")
        self.assertEqual(len(facts),2)
        self.assertEqual(facts[0].starts_at.isoformat(),"2027-02-26T20:00:00+01:00")

    def test_no_dates_does_not_invent_recite(self):
        html="<h1>La traviata | Giuseppe Verdi</h1><p>27 Febbraio-13 Marzo 2027</p>"
        self.assertEqual(parse_regio_detail(html,source_url=URL,expected_title="La traviata",expected_composer="Giuseppe Verdi"),[])

    def test_reject_listing_and_other_domains(self):
        for url in ("https://www.teatroregio.torino.it/calendario/opera","https://example.com/opera"):
            with self.assertRaises(ValueError):
                parse_regio_detail(HTML,source_url=url,expected_title="La traviata",expected_composer="Giuseppe Verdi")

    def test_full_import_idempotent_and_provenance(self):
        self.assertEqual(self.ingest().linked,2)
        self.assertEqual(self.ingest().linked,2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM performances").fetchone()[0],2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM performance_sources").fetchone()[0],2)

    def test_source_requires_approval(self):
        self.db.execute("UPDATE sources SET access_status='pending'")
        with self.assertRaises(ValueError):
            self.ingest()
        self.assertEqual(self.db.execute("SELECT count(*) FROM performances").fetchone()[0],0)

    def test_reject_noncanonical_production(self):
        another=register_work(self.db,"Carmen","Georges Bizet")
        self.db.execute("UPDATE productions SET work_id=? WHERE id=1",(another,))
        with self.assertRaises(ValueError):
            self.ingest()

    def test_export_only_verified_provenance(self):
        self.ingest()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"public.json"
            self.assertEqual(export_public_catalog(self.db,path),2)
            data=json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(data["performances"]),2)
            self.assertEqual(len(data["performances"][0]["sources"]),1)
            self.db.execute("UPDATE sources SET access_status='blocked'")
            self.assertEqual(export_public_catalog(self.db,path),0)

    def test_ballet_is_not_an_opera(self):
        self.assertEqual(parse_regio_detail(
            "<h1>The Tokyo Ballet | Composer</h1><p>2027-03-02 20:00:00 Europe/Rome</p>",
            source_url=URL,expected_title="The Tokyo Ballet",expected_composer="Composer"),[])


if __name__=="__main__":
    unittest.main()

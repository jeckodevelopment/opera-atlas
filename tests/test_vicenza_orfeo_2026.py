"""Prevent a Vicenza festival staging from being misassigned to Teatro Olimpico."""
import json
import unittest
from datetime import date

from opera_atlas.controlled_fetch import FetchResult
from opera_atlas.vicenza_orfeo_2026 import (
    URL, PRESS_URL, verified_calendar,
)
from opera_atlas.vicenza_olimpico_opera import KEY
from scripts.auto_catalogue import verified_venue, official_identity_candidates
from scripts.collect_candidate_details import collect
from scripts.publish_catalog_v2 import ROOT, slugify
from scripts.publish_work_posters import load_archival_art


DETAIL = """<html><h1>L’Orfeo – Monteverdi</h1>
<p>Vicenza in Lirica FUORI LE MURA</p>
<p>Domenica 20 settembre | ore 17.00</p>
<p>Villa Pisani Bonetti di Bagnolo di Lonigo</p>
<h3>L’ORFEO</h3><p>di C. MONTEVERDI</p></html>"""
PRESS = """<html><h1>L’Orfeo di Monteverdi chiude la XIV edizione</h1>
<p>Sarà L’Orfeo di Claudio Monteverdi, capolavoro nella storia dell'opera,
per il festival Vicenza in Lirica 2026.</p>
<p>L’appuntamento è per domenica 20 settembre alle ore 17.00 a Villa
Pisani Bonetti, a Bagnolo di Lonigo.</p></html>"""


class VicenzaOrfeo2026Tests(unittest.TestCase):
    def test_two_official_sources_prove_exact_location_and_date(self):
        rows=verified_calendar(DETAIL,PRESS,source_key=KEY,source_url=URL)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["event_title"],"L'Orfeo")
        self.assertEqual(rows[0]["composer"],"Claudio Monteverdi")
        self.assertEqual(rows[0]["venue"],"Villa Pisani Bonetti")
        self.assertEqual(rows[0]["date"],"2026-09-20")
        self.assertEqual(rows[0]["starts_at"],"2026-09-20T17:00:00+02:00")
        city, venue, canonical=verified_venue(KEY,rows,{"venues":{}})
        self.assertEqual((city,venue),("Lonigo","Villa Pisani Bonetti"))
        self.assertIsNone(canonical)

    def test_wrong_venue_clock_composer_or_edition_is_rejected(self):
        cases=(
            (DETAIL.replace("Villa Pisani Bonetti di Bagnolo di Lonigo",
                            "Teatro Olimpico di Vicenza"),PRESS),
            (DETAIL.replace("ore 17.00","ore 18.00"),PRESS),
            (DETAIL.replace("di C. MONTEVERDI","di G. ROSSINI"),PRESS),
            (DETAIL,PRESS.replace("2026","2027")),
        )
        for detail,press in cases:
            with self.subTest(detail=detail[:75],press=press[-65:]):
                with self.assertRaises(ValueError):
                    verified_calendar(detail,press,source_key=KEY,source_url=URL)
        with self.assertRaises(ValueError):
            verified_calendar(DETAIL,PRESS,source_key="unapproved",source_url=URL)

    def test_acquisition_records_press_hash_and_correct_city(self):
        candidate={"id":"test-vicenza-orfeo-2026","source_key":KEY,
                   "official_url":URL,"status":"needs_review"}
        queue={"schema_version":1,"candidates":[candidate]}
        def fetch(db,*,source_id,url,network_enabled):
            if url not in (URL,PRESS_URL):
                raise AssertionError("unexpected source URL: "+url)
            return FetchResult(url,DETAIL if url==URL else PRESS,"b"*64,100)
        found,health=collect(
            queue,{"schema_version":1,"evidence":[]},network_enabled=True,
            fetcher=fetch,today=date(2026,11,23))
        self.assertEqual(health[0]["outcome"],"verified_first_party_press",health)
        record=found["evidence"][0]
        self.assertEqual(record["official_schedule_evidence_url"],PRESS_URL)
        self.assertEqual(record["official_schedule_sha256"],"b"*64)
        self.assertEqual(record["event_facts"][0]["venue"],"Villa Pisani Bonetti")

    def test_source_bound_work_authority_and_public_domain_image(self):
        record={"candidate_id":"test-vicenza-orfeo-2026",
                "source_key":KEY,"source_url":URL,
                "status":"needs_editorial_review",
                "event_facts":verified_calendar(
                    DETAIL,PRESS,source_key=KEY,source_url=URL)}
        queue={"schema_version":1,"candidates":[{
            "id":record["candidate_id"],"source_key":KEY,
            "official_url":URL,"status":"needs_review"}]}
        result=official_identity_candidates(
            {"schema_version":1,"evidence":[record]},queue,
            {"schema_version":1,"works":[]})
        self.assertEqual(len(result["works"]),1)
        work=result["works"][0]
        self.assertEqual(work["history"]["premiere_year"],1607)
        self.assertEqual(work["history"]["librettist"],"Alessandro Striggio")
        self.assertTrue(45<=len(work["synopsis"])<=300)
        cover=load_archival_art({slugify(work["title"])})
        self.assertIn("orfeo",cover)
        self.assertIn("1609",cover["orfeo"]["alt"])

    def test_festival_whitelist_is_official_host_and_edition_is_not_empty(self):
        registry=json.loads((ROOT/"data/festival-registry.json").read_text(encoding="utf-8"))
        rule=next(x for x in registry["festivals"] if x["id"]=="vicenza-in-lirica")
        self.assertEqual(rule["source_hosts"],["www.vicenzainlirica.it"])
        edition=json.loads((ROOT/"public/catalog/v2/festival-index.json").read_text(
            encoding="utf-8"))
        festival=next(x for x in edition["festivals"]
                      if x["id"]=="vicenza-in-lirica-2026")
        self.assertIn("oa-s-000283",festival["staging_ids"])


if __name__=="__main__":
    unittest.main()

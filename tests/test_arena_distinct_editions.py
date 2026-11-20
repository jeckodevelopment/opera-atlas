"""Official Arena editions of one opera keep distinct staging IDs and routes."""
import json
import unittest
from datetime import date

from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.auto_catalogue import promote
from scripts.collect_candidate_details import parse_known_opera_detail

URL="https://www.arena.it/arena-opera-festival/aida-ed-stefano-poda/"
CID="test-aida-poda-official-edition"

class ArenaEditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_official_edition_slug_requires_canonical_composer_on_page(self):
        html="""<h2>Aida ed. Stefano Poda | 2027</h2><p>Opera</p>
        <p>Giuseppe Verdi</p><h2>In breve</h2><p>Aida</p>
        <h2>Prossimi spettacoli</h2>
        <h3>12 agosto 2027</h3><p>ore 21:00</p>
        <h3>22 agosto 2027</h3><p>ore 21:00</p>"""
        rows=parse_known_opera_detail("arena-festival-2027",URL,html,self.registry)
        self.assertEqual([x["date"] for x in rows],["2027-08-12","2027-08-22"])
        self.assertEqual(rows[0]["composer"],"Giuseppe Verdi")
        with self.assertRaises(ValueError):
            parse_known_opera_detail("arena-festival-2027",URL,
                html.replace("Giuseppe Verdi","Other composer"),self.registry)

    def test_distinct_arena_production_keeps_existing_aida_route_and_ids(self):
        candidates={"schema_version":1,"candidates":[{
            "id":CID,"source_key":"arena-festival-2027",
            "official_url":URL,"status":"needs_review"}]}
        evidence={"schema_version":1,"evidence":[{
            "candidate_id":CID,"source_key":"arena-festival-2027","source_url":URL,
            "status":"needs_editorial_review","event_facts":[{
                "event_title":"Aida","composer":"Giuseppe Verdi",
                "date":"2027-08-12","starts_at":"2027-08-12T21:00:00+02:00",
                "venue":"Arena di Verona"}]}]}
        data,ids,urls,report=promote(
            self.facts,self.registry,evidence,candidates,[],today=date(2026,11,20))
        self.assertEqual(report["new_stagings"],1)
        self.assertEqual(report["new_recite"],1)
        self.assertIn(URL,urls)
        staging=next(v for v in ids["stagings"].values() if v["source_url"]==URL)
        self.assertEqual(staging["route_slug"],"aida-ed-stefano-poda")
        graph=assemble(data,ids,approved_extra=set(urls))
        newer=next(x for x in graph["stagings"] if x["id"]==staging["id"])
        self.assertEqual(newer["url"],"/verona/arena-di-verona/aida-ed-stefano-poda/")
        original=next(x for x in graph["stagings"]
                      if x["source_url"].endswith("/aida-ed-gianfranco-de-bosio/"))
        self.assertEqual(original["url"],"/verona/arena-di-verona/aida/")
        second=promote(data,ids,evidence,candidates,urls,today=date(2026,11,20))
        self.assertEqual(second[3]["new_stagings"],0)
        self.assertEqual(second[3]["new_recite"],0)
        self.assertEqual(second[0],data)
        self.assertEqual(second[1],ids)
if __name__=="__main__":
    unittest.main()

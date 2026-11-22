"""Two Parma public family recite on one date, no school tickets or ID clashes."""
import copy
import json
import unittest
from datetime import date

from opera_atlas.parma_public_recite import URL,PUBLIC,official_public_recite
from opera_atlas.verified_original_work_art import verified_original_art
from scripts.build_verified_catalog import MANIFEST,build,replica_registry_key
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.auto_catalogue import official_identity_candidates,promote_new_works
from scripts.publish_catalog_v2 import REGISTRY,assemble,ROOT
from scripts.publish_work_editorial import EDITORIAL,HISTORY
from tests.test_parma_family_opera import page

CID="oa-index-e6f08bbcef00e05cc2ee"
TITLE="Piccolo Orso e la montagna di ghiaccio"

class ParmaSameDayPublicOperaTests(unittest.TestCase):
    def test_venue_ticket_labels_select_public_not_schools(self):
        rows=official_public_recite(page(),url=URL)
        self.assertEqual([(x["date"],x["starts_at"][11:16]) for x in rows],
                         list(PUBLIC))
        self.assertEqual({x["venue"] for x in rows},{"Teatro Regio di Parma"})
        with self.assertRaises(ValueError):
            official_public_recite(page().replace("Famiglie","Scuole"),url=URL)
        with self.assertRaises(ValueError):
            official_public_recite(page().replace("18:00","19:00"),url=URL)

    def test_fragmented_source_ticket_columns_are_still_audited(self):
        html=page()
        # Simulate real WordPress columns with long assistive labels between
        # a dated ticket card and its adjacent clock.
        html=html.replace("<div>09:00</div>",
                          "<span>Dettagli accessibilità e biglietteria " +
                          ("informazioni " * 18) + "</span><div>09:00</div>")
        rows=official_public_recite(html,url=URL)
        self.assertEqual([(x["date"],x["starts_at"][11:16]) for x in rows],
                         list(PUBLIC))
        with self.assertRaises(ValueError):
            official_public_recite(
                html.replace("<div>18:00</div>","<div>17:30</div>"),url=URL)

    def test_two_recite_have_distinct_ids_and_one_canonical_staging(self):
        facts=json.loads(MANIFEST.read_text())
        registry=json.loads(REGISTRY.read_text())
        candidates={"schema_version":1,"candidates":[{
            "id":CID,"source_key":"parma-opera-2027",
            "official_url":URL,"status":"needs_review"}]}
        detail={"schema_version":1,"evidence":[{
            "candidate_id":CID,"source_key":"parma-opera-2027",
            "source_url":URL,"status":"needs_editorial_review",
            "event_facts":official_public_recite(page(),url=URL)}]}
        material=official_identity_candidates(
            detail,candidates,{"schema_version":1,"works":[]})
        self.assertEqual(len(material["works"]),1)
        self.assertEqual(material["works"][0]["title"],TITLE)
        self.assertEqual(material["works"][0]["history"]["premiere_year"],2026)
        self.assertIsNotNone(verified_original_art(
            source_url=URL,title=TITLE,composer="Giovanni Sollima"))
        synopses=json.loads(EDITORIAL.read_text())
        history=json.loads(HISTORY.read_text())
        f,identities,urls,editorial,history,new=promote_new_works(
            facts,registry,detail,candidates,material,synopses,[],
            today=date(2026,11,22),history=history,require_image=True)
        self.assertEqual(new["new_works"],1,new)
        self.assertEqual(new["new_stagings"],1,new)
        self.assertEqual(new["new_recite"],2,new)
        product=next(p for p in f["productions"] if p["source_url"]==URL)
        self.assertEqual(product["dates"],[["2026-12-05","15:00"],
                                           ["2026-12-05","18:00"]])
        self.assertEqual(len({replica_registry_key(product,d,t)
                              for d,t in product["dates"]}),2)
        self.assertEqual(len([x for x in identities["performances"]
                              if x.startswith(product["key"]+"|2026-12-05|")]),2)
        published=assemble(f,identities,approved_extra=set(urls))
        recite=[x for x in published["performances"]
                if x["staging_id"]==identities["stagings"][product["key"]]["id"]]
        self.assertEqual(len(recite),2)
        self.assertEqual(len({x["id"] for x in recite}),2)
        self.assertEqual({x["starts_at"][11:16] for x in recite},{"15:00","18:00"})
        self.assertFalse(any(x["local_date"]=="2026-12-04" for x in recite))

if __name__=="__main__":
    unittest.main()

"""A checked opera identity from the official Maggio calendar publishes offline."""
import json
import unittest
from datetime import date

from scripts.publish_cached_known import promote_cached_verified_new_works
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.discover_season_indexes import OUTPUT as INDEX
from scripts.auto_catalogue import SOURCE_ALLOWLIST
from scripts.publish_work_editorial import build_editorial

OFFICIAL="https://www.maggiofiorentino.com/events/les-contes-dhoffmann"
DATES={"2026-12-20","2026-12-27","2026-12-30","2027-01-02"}

class OffenbachPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.evidence=json.loads(DETAILS.read_text(encoding="utf-8"))
        cls.candidates=json.loads(INDEX.read_text(encoding="utf-8"))
        cls.urls=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))["urls"]

    def test_verified_new_opera_works_on_first_import_and_remains_idempotent(self):
        initial=next((p for p in self.facts["productions"]
                      if p["source_url"]==OFFICIAL),None)
        output=promote_cached_verified_new_works(
            self.facts,self.registry,self.evidence,self.candidates,self.urls,
            today=date(2026,11,21))
        facts,registry,urls,editorial,history,report=output
        published=[p for p in facts["productions"] if p["source_url"]==OFFICIAL]
        self.assertEqual(len(published),1)
        self.assertEqual(published[0]["title"],"Les contes d'Hoffmann")
        self.assertEqual(published[0]["composer"],"Jacques Offenbach")
        self.assertEqual(published[0]["municipality"],"Firenze")
        self.assertEqual(published[0]["venue"],"Teatro del Maggio Musicale Fiorentino")
        self.assertEqual({d for d,_ in published[0]["dates"]},DATES)
        self.assertTrue(all(h is not None for _,h in published[0]["dates"]))
        if not initial:
            self.assertEqual(report["new_works"],1)
            self.assertEqual(report["new_recite"],4)
        else:
            self.assertEqual(report["new_works"],0)
            self.assertEqual(report["new_recite"],0)
        self.assertIn(OFFICIAL,urls)
        works=[w for w in registry["works"].values()
               if w["title"]=="Les contes d'Hoffmann"]
        self.assertEqual(len(works),1)
        self.assertEqual(works[0]["wikidata_id"],"Q335012")
        graph=assemble(facts,registry,approved_extra=set(urls))
        self.assertTrue(graph["performances"])
        cards=build_editorial(facts,registry,editorial,
                             approved_extra=set(urls),history=history)
        self.assertTrue(any(w["title"]=="Les contes d'Hoffmann" for w in cards["works"]))
        again=promote_cached_verified_new_works(
            facts,registry,self.evidence,self.candidates,urls,today=date(2026,11,21),
            editorial_snapshot=editorial,history_snapshot=history)
        self.assertEqual(again[-1]["new_works"],0)
        self.assertEqual(again[-1]["new_recite"],0)
        self.assertEqual(again[0],facts)
        self.assertEqual(again[1],registry)

    def test_missing_official_composer_or_untrusted_origin_fails_closed(self):
        import copy
        for mutation in ("composer_missing","composer_changed","url_changed","venue_changed"):
            evidence=copy.deepcopy(self.evidence)
            row=next(x for x in evidence["evidence"] if x["source_url"]==OFFICIAL)
            if mutation=="composer_missing":
                row["event_facts"][0].pop("composer")
            elif mutation=="composer_changed":
                row["event_facts"][0]["composer"]="Another composer"
            elif mutation=="url_changed":
                row["source_url"]="https://external.example/events/les-contes-dhoffmann"
            else:
                row["event_facts"][0]["venue"]="Teatro Goldoni"
            output=promote_cached_verified_new_works(
                self.facts,self.registry,evidence,self.candidates,self.urls,
                today=date(2026,11,21))
            # Once published, the immutable work remains in facts; on fresh
            # fixture, no new staging can be promoted from malformed proof.
            self.assertEqual(output[-1]["new_recite"],0,mutation)

if __name__=="__main__":
    unittest.main()

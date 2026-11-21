"""Regression tests for composition-safe reuse and actionable refresh retries."""
import unittest
from datetime import date

from scripts.auto_work_research import canonical_editorial_material, research
from scripts.publish_catalog_v2 import REGISTRY
import json


class CanonicalEditorialReuseTests(unittest.TestCase):
    def test_unique_canonical_composition_reuses_published_prose(self):
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        norm=next(row for row in registry["works"].values() if row["slug"]=="norma")
        identity={"title":norm["title"],"composer":norm["composer"],
                  "wikidata_id":norm.get("wikidata_id","Q320353"),
                  "title_candidate_count":1}
        result=canonical_editorial_material(identity)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result["synopsis"]),45)
        self.assertTrue(result["history"]["sources"])
        self.assertIsNone(canonical_editorial_material(
            {**identity,"composer":"Giuseppe Verdi"}))

    def test_explicit_canonical_qid_never_matches_wrong_composition(self):
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        works=[row for row in registry["works"].values() if row.get("wikidata_id")]
        self.assertTrue(works)
        original=works[0]
        self.assertIsNone(canonical_editorial_material({
            "title":original["title"],"composer":original["composer"],
            "wikidata_id":"Q999999999","title_candidate_count":1}))

    def test_translated_title_reuses_only_when_qid_is_exact(self):
        from scripts.auto_work_research import validated_editorial_attributions
        from scripts.publish_catalog_v2 import REGISTRY
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        attributions=validated_editorial_attributions()
        # Select a fully sourced composition with an explicit QID.
        sourced=next((w for w in registry["works"].values()
                      if w["slug"] in attributions),None)
        self.assertIsNotNone(sourced)
        qid=attributions[sourced["slug"]]["wikidata_id"]
        identity={"title":"Alternative exact title for testing",
                  "composer":sourced["composer"],"wikidata_id":qid,
                  "title_candidate_count":2}
        result=canonical_editorial_material(identity)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result["synopsis"]),45)
        self.assertIsNone(canonical_editorial_material(
            {**identity,"wikidata_id":"Q999999999"}))

    def test_retry_report_includes_verified_candidate_context(self):
        candidate={"id":"ctx-test","source_key":"scala-season-2026-27",
                   "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/unknown-ctx.html",
                   "status":"needs_review"}
        result,status=research({"candidates":[candidate]},
                               {"schema_version":1,"works":[]},set(),
                               today=date(2026,11,21),prepared={},
                               resolve=lambda _:None)
        self.assertEqual(result["works"],[])
        self.assertEqual(status[0]["source_key"],candidate["source_key"])
        self.assertEqual(status[0]["official_url"],candidate["official_url"])
        self.assertEqual(status[0]["title_hint"],"unknown ctx")

    def test_completed_exact_qid_reused_between_venues(self):
        previous={"candidate_id":"previous","source_key":"fenice-opera-2026-27",
                  "source_url":"https://www.teatrolafenice.it/event/norma/",
                  "title":"Norma","composer":"Vincenzo Bellini","wikidata_id":"Q320353",
                  "synopsis":"Norma vive il conflitto tra i propri sentimenti e i doveri "
                             "imposti dalla sua comunità e dalla sua famiglia.",
                  "history":{"librettist":"Felice Romani",
                             "premiere_year":1831,"premiere_venue":"Teatro alla Scala",
                             "premiere_city":"Milano",
                             "sources":["https://www.wikidata.org/wiki/Q320353"]}}
        candidate={"id":"norma-new","source_key":"maggio-fiorentino-calendar-2027",
                   "official_url":"https://www.maggiofiorentino.com/events/norma-2027",
                   "status":"needs_review"}
        def resolve(title):
            return {"title":"Norma","composer":"Vincenzo Bellini",
                    "wikidata_id":"Q320353","title_candidate_count":2,
                    "authority_url":"https://www.wikidata.org/wiki/Q320353",
                    "wikipedia_url":None,"wikipedia_title":None}
        result,status=research({"candidates":[candidate]},
                               {"schema_version":1,"works":[previous]},{"norma"},
                               today=date(2026,11,21),resolve=resolve,
                               prepared={},allow_authority=False)
        self.assertEqual(status[0]["status"],"enriched")
        new=next(row for row in result["works"] if row["candidate_id"]=="norma-new")
        self.assertEqual(new["history"],previous["history"])
        self.assertEqual(new["synopsis"],previous["synopsis"])

    def test_unresolvable_authority_has_actionable_reason(self):
        candidate={"id":"unknown-new","source_key":"scala-season-2026-27",
                   "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/unknown-new.html",
                   "status":"needs_review"}
        result,status=research({"candidates":[candidate]},
                               {"schema_version":1,"works":[]},set(),
                               today=date(2026,11,21),resolve=lambda _:None,
                               prepared={})
        self.assertEqual(result["works"],[])
        self.assertEqual(status[0]["reason"],"authority_not_unique")


if __name__ == "__main__":
    unittest.main()

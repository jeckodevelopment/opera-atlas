"""Regression for source-bound Piacenza cards and archival opera covers."""
import json
import unittest

from scripts.auto_catalogue import official_identity_candidates, complete_cached_verified_work_cards
from scripts.collect_candidate_details import OUTPUT as EVIDENCE
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.auto_work_research import OUT as INTELLIGENCE
from scripts.publish_work_posters import load_archival_art


class PiacenzaConsolidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        cls.candidates = json.loads(CANDIDATES.read_text(encoding="utf-8"))
        cls.intelligence = json.loads(INTELLIGENCE.read_text(encoding="utf-8"))

    def test_two_archival_images_are_source_bound(self):
        images = load_archival_art({"siberia", "simon-boccanegra"})
        self.assertEqual(set(images), {"siberia", "simon-boccanegra"})
        for row in images.values():
            self.assertEqual(row["kind"], "archival_work_image")
            self.assertIn("commons.wikimedia.org", row["source_url"])

    def test_simon_boccanegra_known_official_source_seed(self):
        cid = "oa-index-7ee44d5187617ce9e1b7"
        # A previously published candidate need not be seeded again.
        candidate = next(x for x in self.candidates["candidates"]
                         if x["id"] == cid)
        if candidate["status"] == "already_catalogued":
            return
        doc = official_identity_candidates(self.evidence, self.candidates,
                                            self.intelligence)
        works = [x for x in doc["works"] if x.get("candidate_id") == cid]
        self.assertEqual(len(works), 1)
        self.assertEqual(works[0]["composer"], "Giuseppe Verdi")
        self.assertEqual(works[0]["official_authority_url"],
                         "https://teatripiacenza.it/event/simon-boccanegra/")
        self.assertGreaterEqual(len(works[0]["synopsis"]), 45)
        self.assertEqual(works[0]["history"]["premiere_year"], 1857)

    def test_siberia_cached_identity_receives_verified_editorial(self):
        cid = "oa-index-9fdcd7eba240da4540af"
        doc = complete_cached_verified_work_cards(self.intelligence,
                                                    self.evidence)
        works = [x for x in doc["works"] if x.get("candidate_id") == cid]
        if not works:
            # Promotion may have removed the candidate from intelligence.
            self.assertTrue(any(x["id"] == cid and
                                x["status"] == "already_catalogued"
                                for x in self.candidates["candidates"]))
            return
        self.assertEqual(works[0]["wikidata_id"], "Q2292268")
        self.assertIsInstance(works[0]["synopsis"], str)
        self.assertIn("Stephana", works[0]["synopsis"])


if __name__ == "__main__":
    unittest.main()

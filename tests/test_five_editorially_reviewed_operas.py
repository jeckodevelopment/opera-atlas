"""Source-bound editorial and artwork evidence for five new compositions."""
import json
import unittest
from scripts.auto_catalogue import official_identity_candidates, verified_candidate_image
from scripts.publish_catalog_v2 import ROOT
from opera_atlas.verified_original_work_art import is_verified_original_art

CASES = (
    ("oa-index-52b35f0089c3663c7ddb", "Ghost Cafè", "Carlo Galante", True),
    ("oa-index-d57d2a1cbc3f370f3da5", "Il schiavo di sua moglie", "Francesco Provenzale", True),
    ("oa-index-3f12fd23aa46c05bfd36", "Fuori Fuoco", "Diana Buscemi", True),
    ("oa-index-d8c22fa66fa68b8a3670", "Magic Words Circus", "Orazio Sciortino", True),
    ("oa-index-ff9fb11ad20bd9d779b3", "La favola di Orfeo", "Alfredo Casella", True),
)

class FiveReviewedOperas(unittest.TestCase):
    def test_official_identity_and_poster_evidence(self):
        read = lambda path: json.loads((ROOT / path).read_text(encoding="utf-8"))
        candidates = read("data/season-index-candidates.json")
        evidence = read("data/candidate-detail-evidence.json")
        # The live registry is mutable: a previously reviewed candidate may
        # already be published when a refresh reaches its final test phase.
        # Exercise the identity gate using only the reviewed source records,
        # with a controlled pending state independent of publication timing.
        reviewed_ids = {cid for cid, *_ in CASES}
        candidates = {"schema_version": 1, "candidates": [
            {**row, "status": "needs_review"}
            for row in candidates["candidates"] if row["id"] in reviewed_ids]}
        evidence = {"schema_version": 1, "evidence": [
            {**row, "status": "needs_editorial_review"}
            for row in evidence["evidence"] if row["candidate_id"] in reviewed_ids]}
        seeded = official_identity_candidates(evidence, candidates,
                                              {"schema_version":1, "works":[]})
        by_id = {w["candidate_id"]: w for w in seeded["works"]}
        for cid, title, composer, poster_expected in CASES:
            with self.subTest(title=title):
                work = by_id[cid]
                self.assertEqual((work["title"],work["composer"]),(title,composer))
                self.assertTrue(work["history"]["sources"])
                observation = next(e for e in evidence["evidence"] if e["candidate_id"] == cid)
                image = verified_candidate_image(observation, title=title,
                                                 composer=composer,
                                                 url=observation["source_url"])
                self.assertEqual(bool(image),poster_expected)
                if poster_expected:
                    self.assertTrue(is_verified_original_art(image,title=title,composer=composer))

    def test_wrong_composer_does_not_reuse_art(self):
        observation = {"source_key":"trapani-luglio-musicale-2026"}
        self.assertIsNone(verified_candidate_image(
            observation,title="Ghost Cafè",composer="Claudio Monteverdi",
            url="https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2026/ghost-cafe/"))

if __name__ == "__main__":
    unittest.main()

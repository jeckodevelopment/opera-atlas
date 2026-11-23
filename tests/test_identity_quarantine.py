"""A contradictory candidate cannot block unrelated verified compositions."""
import copy
import json
import unittest

from scripts.auto_catalogue import official_identity_candidates
from scripts.publish_catalog_v2 import ROOT


GHOST = "oa-index-52b35f0089c3663c7ddb"
PROVENZALE = "oa-index-d57d2a1cbc3f370f3da5"


class IdentityQuarantineTests(unittest.TestCase):
    def test_unattended_batch_rejects_only_the_conflicting_identity(self):
        registry = json.loads((ROOT / "data/season-index-candidates.json").read_text(
            encoding="utf-8"))
        details = json.loads((ROOT / "data/candidate-detail-evidence.json").read_text(
            encoding="utf-8"))
        ids = {GHOST, PROVENZALE}
        candidates = {"schema_version": 1, "candidates": [
            {**row, "status": "needs_review"}
            for row in registry["candidates"] if row["id"] in ids]}
        evidence = {"schema_version": 1, "evidence": [
            {**row, "status": "needs_editorial_review"}
            for row in details["evidence"] if row["candidate_id"] in ids]}
        corrupted = copy.deepcopy(evidence)
        next(row for row in corrupted["evidence"]
             if row["candidate_id"] == GHOST)["event_facts"][0]["composer"] = (
                 "Other Composer")
        quarantined = []
        works = official_identity_candidates(
            corrupted, candidates, {"schema_version": 1, "works": []},
            quarantine=quarantined)
        by_id = {row["candidate_id"] for row in works["works"]}
        self.assertNotIn(GHOST, by_id)
        self.assertIn(PROVENZALE, by_id)
        self.assertEqual(quarantined, [{
            "candidate_id": GHOST,
            "source_key": "trapani-luglio-musicale-2026",
            "reason": "official_identity_contradicts_reviewed_seed"}])
        # Security-sensitive strict callers must continue rejecting the batch.
        with self.assertRaisesRegex(ValueError, "contradicts"):
            official_identity_candidates(
                corrupted, candidates, {"schema_version": 1, "works": []})


if __name__ == "__main__":
    unittest.main()

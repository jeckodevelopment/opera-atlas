"""Final-candidate diagnostics never hide an actionable image-only blocker."""
import unittest
from scripts.auto_catalogue import refine_new_work_skips

class NewOperaFinalGateDiagnostics(unittest.TestCase):
    def test_missing_authentic_image_supersedes_unknown_canonical_identity(self):
        old=[
            {"candidate_id":"rome-code-unknown","reason":"unknown_work_needs_authority_data"},
            {"candidate_id":"other","reason":"unknown_work_needs_authority_data"},
        ]
        new=[{"candidate_id":"rome-code-unknown",
              "reason":"verified_work_image_missing"}]
        result=refine_new_work_skips(old,new)
        self.assertEqual(result,[
            {"candidate_id":"other","reason":"unknown_work_needs_authority_data"},
            {"candidate_id":"rome-code-unknown","reason":"verified_work_image_missing"}])
    def test_unrelated_new_work_errors_and_unknown_identity_remain_visible(self):
        old=[{"candidate_id":"a","reason":"unknown_work_needs_authority_data"}]
        new=[{"candidate_id":"a","reason":"incomplete_work_editorial"}]
        self.assertEqual(refine_new_work_skips(old,new),old+new)

if __name__=="__main__":
    unittest.main()

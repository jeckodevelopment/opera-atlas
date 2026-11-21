"""New opera publication must remove earlier same-run unknown-work diagnostics."""
import unittest
from scripts.auto_catalogue import remove_retries_for_published_works

class ReconciledNewWorkDiagnostics(unittest.TestCase):
    def test_only_successful_canonical_productions_clear_unknown_work_retries(self):
        candidates={"candidates":[
            {"id":"published","official_url":"https://official.example/a"},
            {"id":"unresolved","official_url":"https://official.example/b"},
            {"id":"old","official_url":"https://official.example/c"}]}
        before={"productions":[{"key":"old","source_url":"https://official.example/c"}]}
        after={"productions":[*before["productions"],
               {"key":"new-work","source_url":"https://official.example/a"}]}
        report={"new_stagings":0,"new_recite":0,
                "auto_skipped":[
                    {"candidate_id":"published","reason":"unknown_work_needs_authority_data"},
                    {"candidate_id":"unresolved","reason":"unknown_work_needs_authority_data"},
                    {"candidate_id":"old","reason":"unknown_work_needs_authority_data"},
                    {"candidate_id":"published","reason":"missing_verified_clock"}]}
        result=remove_retries_for_published_works(report,candidates,before,after)
        self.assertEqual(result["auto_skipped"],report["auto_skipped"][1:])
        self.assertEqual(len(report["auto_skipped"]),4)

    def test_new_recita_of_old_work_is_not_misclassified_as_new_work(self):
        # The helper is used only after promote_new_works, with the previous
        # already-known-work result as prior_facts; no inserted works -> no removal.
        candidates={"candidates":[{"id":"unresolved","official_url":"https://official.example/a"}]}
        original={"productions":[{"key":"existing","source_url":"https://official.example/a"}]}
        report={"auto_skipped":[{"candidate_id":"unresolved",
                                "reason":"unknown_work_needs_authority_data"}]}
        self.assertEqual(remove_retries_for_published_works(
            report,candidates,original,original)["auto_skipped"],
            report["auto_skipped"])

if __name__=="__main__":
    unittest.main()

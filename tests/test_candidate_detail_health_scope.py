"""Regression: a scoped candidate scan must not erase national diagnostics."""
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import collect_candidate_details as details


class CandidateDetailHealthScopeTests(unittest.TestCase):
    def test_scoped_checkpoint_is_separate_from_national_checkpoint(self):
        self.assertNotEqual(details.HEALTH, details.PARTIAL_HEALTH)
        self.assertEqual(details.HEALTH.name, "candidate-detail-health.json")
        self.assertEqual(details.PARTIAL_HEALTH.name, "candidate-detail-health-partial.json")

    def test_main_uses_scoped_checkpoint_for_source_scan(self):
        candidates = {"schema_version": 1, "candidates": []}
        previous = {"schema_version": 1, "evidence": []}
        writes = []
        with patch.object(details.argparse.ArgumentParser, "parse_args",
                          return_value=details.argparse.Namespace(
                              allow_network=False, priority_only=False,
                              source_key="opera-roma-season-2026-27")), \
             patch.object(details, "validate_config", return_value=[
                 {"key":"opera-roma-season-2026-27","access_status":"approved"}]), \
             patch.object(details.CONFIG, "read_text", return_value="{}"), \
             patch.object(details.INDEX, "read_text",
                          return_value=__import__("json").dumps(candidates)), \
             patch.object(details.OUTPUT, "exists", return_value=True), \
             patch.object(details.OUTPUT, "read_text",
                          return_value=__import__("json").dumps(previous)), \
             patch.object(details, "collect",
                          return_value=(previous, [])), \
             patch.object(details, "_write_atomic",
                          side_effect=lambda path, payload: writes.append((path,payload))):
            details.main()
        self.assertNotIn(details.HEALTH, [path for path,_ in writes])
        partial = next(payload for path,payload in writes
                       if path == details.PARTIAL_HEALTH)
        self.assertEqual(partial["scope"], "source")
        self.assertEqual(partial["source_key"], "opera-roma-season-2026-27")
        self.assertEqual(partial["attempted"], 0)


if __name__ == "__main__":
    unittest.main()

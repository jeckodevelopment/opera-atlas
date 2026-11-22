"""Source health only dispatches catalog on newly actionable candidates."""
import unittest
from pathlib import Path
from scripts.source_health_dispatch import newly_actionable

def feed(*rows):
    return {"schema_version": 1, "candidates": list(rows)}

def row(key, url, status="needs_review", **extra):
    return {"source_key": key, "official_url": url, "status": status, **extra}

class SourceHealthWorkflowTests(unittest.TestCase):
    def test_deferred_checkpoint_is_reacquired_from_latest_main(self):
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/refresh-source-health.yml").read_text(encoding="utf-8")
        self.assertIn("if: steps.checkpoint.outputs.deferred == 'true'",workflow)
        self.assertIn("git reset --hard origin/main",workflow)
        self.assertIn("for attempt in 1 2; do",workflow)
        self.assertIn("python -m scripts.discover_season_indexes --allow-network",workflow)
        self.assertIn("python -m scripts.source_automation --check",workflow)
        self.assertIn("python -m scripts.safe_push_catalog",workflow)
        self.assertIn("steps.retry.outputs.published == 'true'",workflow)
        self.assertIn("steps.retry.outputs.new_candidates == 'true'",workflow)
        self.assertIn("Fresh source health could not be persisted",workflow)
        self.assertNotIn("The next independent scheduled scan will recompute it",workflow)

class DispatchTests(unittest.TestCase):
    def test_new_candidate_wakes_catalog(self):
        before=feed(row("pisa", "https://example.org/1"))
        after=feed(row("pisa", "https://example.org/1"),
                   row("lecce", "https://example.org/2"))
        self.assertEqual(newly_actionable(before, after),
                         {("lecce","https://example.org/2")})

    def test_fresh_scan_timestamp_does_not_wake_catalog(self):
        before=feed(row("lecce", "https://example.org/2", last_seen="before"))
        after=feed(row("lecce", "https://example.org/2", last_seen="after"))
        self.assertEqual(newly_actionable(before,after), set())

    def test_newly_reviewable_existing_candidate_wakes_catalog(self):
        before=feed(row("lecce", "https://example.org/2", "not_in_official_season"))
        after=feed(row("lecce", "https://example.org/2"))
        self.assertEqual(len(newly_actionable(before,after)),1)

    def test_already_catalogued_never_wakes_catalog(self):
        before=feed()
        after=feed(row("lecce", "https://example.org/2", "already_catalogued"))
        self.assertEqual(newly_actionable(before,after),set())

    def test_invalid_schema_is_rejected(self):
        with self.assertRaises(ValueError):
            newly_actionable(feed(),{"schema_version":2,"candidates":[]})

if __name__ == "__main__":
    unittest.main()

"""Pipeline timings and workflow diagnostics do not invent publication timestamps."""
import unittest
from datetime import datetime, timezone, timedelta

from scripts.pipeline_operations_health import update_observations, workflow_health
from scripts.push_pipeline_operations_health import conflicting


NOW = datetime(2026, 11, 22, 17, 0, tzinfo=timezone.utc)


def candidate(cid, stamp):
    return {"id": cid, "first_seen": stamp, "status": "already_catalogued"}


class PipelineOperationsHealthTests(unittest.TestCase):
    def test_historical_baseline_not_counted_as_publication_latency(self):
        c = {"schema_version": 1, "candidates": [
            candidate("old", "2026-11-20T10:00:00+00:00")
        ]}
        e = {"schema_version": 1, "candidates": [
            {"candidate_id": "old", "evidence_status": "linked_solo_in_repository"}
        ]}
        state, metrics = update_observations(c, e, None, NOW)
        self.assertEqual(metrics["linked_in_repository_now"], 1)
        self.assertEqual(metrics["eligible_post_baseline_samples"], 0)
        self.assertIsNone(metrics["mean_discovery_to_first_observed_catalogue_minutes"])
        state2, again = update_observations(c, e, state, NOW + timedelta(hours=1))
        self.assertEqual(again["eligible_post_baseline_samples"], 0)
        self.assertEqual(state2["observations"]["old"]["first_observed_catalogued_at"],
                         NOW.isoformat(timespec="seconds"))

    def test_new_candidates_have_observed_not_deploy_latency(self):
        initial, _ = update_observations(
            {"schema_version": 1, "candidates": []},
            {"schema_version": 1, "candidates": []}, None, NOW)
        discovered = NOW + timedelta(minutes=5)
        c = {"schema_version": 1, "candidates": [candidate("new", discovered.isoformat())]}
        pending = {"schema_version": 1, "candidates": [
            {"candidate_id": "new", "evidence_status": "no_direct_repository_link"}
        ]}
        state, m1 = update_observations(c, pending, initial, NOW + timedelta(minutes=10))
        self.assertEqual(m1["reconciled_without_direct_link"], 1)
        self.assertIsNone(m1["publication_ready_waiting"])
        linked = {"schema_version": 1, "candidates": [
            {"candidate_id": "new", "evidence_status": "linked_program_in_repository"}
        ]}
        state2, m2 = update_observations(c, linked, state, NOW + timedelta(minutes=20))
        self.assertEqual(m2["eligible_post_baseline_samples"], 1)
        self.assertEqual(m2["mean_discovery_to_first_observed_catalogue_minutes"], 15)
        self.assertEqual(m2["new_catalogue_links_first_observed_this_run"], 1)
        _, m3 = update_observations(c, linked, state2, NOW + timedelta(minutes=60))
        self.assertEqual(m3["new_catalogue_links_first_observed_this_run"], 0)
        self.assertEqual(m3["mean_discovery_to_first_observed_catalogue_minutes"], 15)

    def test_cancelled_run_followed_by_success_not_claimed_as_failure(self):
        def run(status, conclusion, when):
            return {"status": status, "conclusion": conclusion,
                    "created_at": when.isoformat(), "updated_at": when.isoformat(),
                    "html_url": "https://github.com/example/runs/123"}
        report = workflow_health("Catalog", [
            run("completed", "success", NOW-timedelta(minutes=3)),
            run("completed", "cancelled", NOW-timedelta(minutes=8)),
        ], NOW, 24)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["cancelled_24h"], 1)
        self.assertEqual(report["cancelled_followed_by_success_24h"], 1)
        report2 = workflow_health("Catalog", [
            run("completed", "cancelled", NOW-timedelta(minutes=3)),
            run("completed", "success", NOW-timedelta(minutes=8)),
        ], NOW, 24)
        self.assertEqual(report2["status"], "attention")

    def test_workflow_history_fetches_second_page_when_24h_has_over_100_runs(self):
        from unittest.mock import patch
        from scripts.pipeline_operations_health import github_runs
        import io
        import json
        from urllib.parse import parse_qs, urlsplit
        calls = []
        def fake_open(request, timeout):
            page = int(parse_qs(urlsplit(request.full_url).query)["page"][0])
            calls.append(page)
            stamp = (NOW - timedelta(minutes=10)).isoformat()
            entries = [{"created_at":stamp, "status":"completed",
                        "conclusion":"success"} for _ in range(100 if page == 1 else 5)]
            return io.BytesIO(json.dumps({"workflow_runs": entries}).encode())
        with patch("scripts.pipeline_operations_health.urlopen", side_effect=fake_open):
            rows = github_runs("refresh-catalog.yml", token="test-token",
                               repository="jeckodevelopment/opera-atlas", now=NOW)
        self.assertEqual(len(rows), 105)
        self.assertEqual(calls, [1, 2])

    def test_conflicting_snapshot_inputs_are_not_rebased(self):
        self.assertTrue(conflicting(["data/season-index-candidates.json"]))
        self.assertTrue(conflicting(["public/catalog/candidate-publication-evidence.json"]))
        self.assertFalse(conflicting(["public/catalog/work-posters.json"]))
        self.assertFalse(conflicting(["data/candidate-detail-health.json"]))

if __name__ == "__main__":
    unittest.main()

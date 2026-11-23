"""Keep identity diagnostics synchronized with canonical candidate outcomes."""
import json
import unittest

from scripts.auto_work_research import reconcile_published_outcomes
from scripts.reconcile_work_intelligence_health import reconcile
from scripts.auto_work_research import HEALTH, INDEX, REGISTRY


class IdentityHealthReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.url="https://opera.example.org/festival/opera"
        self.reg={"works":{"opera|composer":{"id":"oa-w-000099"}},
                  "stagings":{"stage":{"source_url":self.url,
                                        "work_id":"oa-w-000099"}}}

    def test_exact_published_and_excluded_supersede_only_prior_observations(self):
        status=[{"candidate_id":"published","status":"awaiting_official_identity_evidence"},
                {"candidate_id":"excluded","status":"awaiting_official_identity_evidence"},
                {"candidate_id":"archived","status":"awaiting_official_identity_evidence"},
                {"candidate_id":"pending","status":"awaiting_official_identity_evidence"}]
        candidates={"schema_version":1,"candidates":[
            {"id":"published","source_key":"one","official_url":self.url,
             "status":"already_catalogued"},
            {"id":"excluded","source_key":"one","official_url":"https://opera.example.org/concert",
             "status":"excluded_nonopera"},
            {"id":"archived","source_key":"one","official_url":"https://opera.example.org/old",
             "status":"not_in_official_season"},
            {"id":"pending","source_key":"one","official_url":"https://opera.example.org/unverified",
             "status":"needs_review"},
            {"id":"not_seen","source_key":"one","official_url":"https://opera.example.org/other",
             "status":"excluded_nonopera"}]}
        result=reconcile_published_outcomes(candidates,status,self.reg)
        by_id={x["candidate_id"]:x for x in result}
        self.assertEqual(by_id["published"]["status"],"already_catalogued")
        self.assertEqual(by_id["published"]["work_id"],"oa-w-000099")
        self.assertEqual(by_id["excluded"]["status"],"excluded_nonopera")
        self.assertEqual(by_id["archived"]["status"],"not_in_official_season")
        self.assertEqual(by_id["pending"]["status"],"awaiting_official_identity_evidence")
        self.assertNotIn("not_seen",by_id)
        self.assertEqual(len(result),4)

    def test_unverified_published_marker_cannot_mask_research_wait(self):
        candidate={"id":"unverified","source_key":"one",
                   "official_url":"https://opera.example.org/missing",
                   "status":"already_catalogued"}
        prior=[{"candidate_id":"unverified",
                "status":"awaiting_official_identity_evidence"}]
        self.assertEqual(reconcile_published_outcomes(
            {"candidates":[candidate]},prior,self.reg),prior)

    def test_catalogued_without_exact_stage_gets_separate_diagnostic(self):
        health={"schema_version":1,"outcomes":[{
            "candidate_id":"known","status":"awaiting_official_identity_evidence"}]}
        candidates={"schema_version":1,"candidates":[{
            "id":"known","source_key":"one","official_url":"https://opera.example.org/old",
            "status":"already_catalogued"}]}
        observed=reconcile(health,candidates,self.reg)["outcomes"][0]
        self.assertEqual(observed["status"],"catalogued_source_link_unverified")
        self.assertNotIn("work_id",observed)

    def test_idempotent_health_snapshot(self):
        input_data={"schema_version":1,"checked_at":"2026-11-23T13:18:25+00:00",
                    "outcomes":[{"candidate_id":"excluded",
                                 "status":"awaiting_official_identity_evidence"}]}
        candidates={"schema_version":1,"candidates":[
            {"id":"excluded","status":"excluded_nonopera","source_key":"one",
             "official_url":"https://opera.example.org/concert"}]}
        modified=reconcile(input_data,candidates,self.reg)
        self.assertEqual(modified["outcomes"][0]["status"],"excluded_nonopera")
        self.assertEqual(reconcile(modified,candidates,self.reg),modified)

    def test_current_snapshot_has_no_false_pending_after_reconciliation(self):
        health=json.loads(HEALTH.read_text(encoding="utf-8"))
        candidates=json.loads(INDEX.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        current=reconcile(health,candidates,registry)
        by_id={x["id"]:x["status"] for x in candidates["candidates"]}
        for status in current["outcomes"]:
            if by_id.get(status["candidate_id"]) in (
                    "excluded_nonopera","not_in_official_season"):
                self.assertEqual(status["status"],by_id[status["candidate_id"]])
            if status["status"]=="awaiting_official_identity_evidence":
                self.assertEqual(by_id.get(status["candidate_id"]),"needs_review")
            if status["status"]=="catalogued_source_link_unverified":
                self.assertEqual(by_id.get(status["candidate_id"]),"already_catalogued")


if __name__=="__main__":
    unittest.main()

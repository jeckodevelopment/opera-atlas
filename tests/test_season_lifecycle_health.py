"""Lifecycle reporting never confuses implementation with observed coverage."""
import copy
import json
import unittest

from scripts.season_lifecycle_health import build, CONFIG, POLICY


class SeasonLifecycleHealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.policy=json.loads(POLICY.read_text(encoding="utf-8"))

    def test_all_configured_indexes_reported_and_strategies_separated(self):
        result=build(self.config,self.policy,{"sources":[]},{"outcomes":[]})
        self.assertEqual(result["total_indexes"],len(self.config["sources"]))
        self.assertEqual(result["verified_rollover"]+
                         result["evergreen_index_unverified"]+
                         result["legacy_year_bound"],result["total_indexes"])
        self.assertEqual(result["future_seasons_verified"],0)
        self.assertTrue(all(not row["future_season_verified"]
                            for row in result["sources"]))
        self.assertTrue(all(row["next_season_status"]=="not_checked"
                            for row in result["sources"]))

    def test_next_season_observation_is_separate_from_current_scan(self):
        result=build(self.config,self.policy,
            {"checked_at":"2026-11-22T13:00:00Z","sources":[{
                "key":"scala-season-2026-27",
                "status":"success",
                "next_season_status":"verified",
                "next_season_url":"https://www.teatroallascala.org/it/stagione/2027-2028/index.html",
                "next_season_links":4,
                "last_attempt_at":"2026-11-22T13:00:00Z",
            },{
                "key":"giglio-lucca-opera-2026-27",
                "status":"success",
                "next_season_status":"unavailable_or_invalid",
            }]},
            {"outcomes":[{"key":"scala-season-2026-27",
                          "status":"kept_last_known_good"}]})
        by_key={x["source_key"]:x for x in result["sources"]}
        self.assertTrue(by_key["scala-season-2026-27"]["future_season_verified"])
        self.assertEqual(by_key["scala-season-2026-27"]["next_season_links"],4)
        self.assertEqual(by_key["scala-season-2026-27"]["last_rollover_status"],
                         "kept_last_known_good")
        self.assertFalse(by_key["giglio-lucca-opera-2026-27"]["future_season_verified"])
        self.assertEqual(result["future_seasons_verified"],1)

    def test_bootstrap_feed_exists_for_dashboard_before_first_scheduled_scan(self):
        from scripts.season_lifecycle_health import OUT
        self.assertTrue(OUT.exists(), "Dashboard lifecycle feed must be shipped on main")
        report=json.loads(OUT.read_text(encoding="utf-8"))
        self.assertEqual(report["schema_version"],1)
        self.assertEqual(report["total_indexes"],len(self.config["sources"]))
        self.assertEqual({row["source_key"] for row in report["sources"]},
                         {item["key"] for item in self.config["sources"]})
        self.assertEqual(report["verified_rollover"]+
                         report["evergreen_index_unverified"]+
                         report["legacy_year_bound"],report["total_indexes"])

    def test_policy_incompleteness_fails_closed(self):
        policy=copy.deepcopy(self.policy)
        policy["sources"].pop("scala-season-2026-27")
        with self.assertRaises(ValueError):
            build(self.config,policy,{"sources":[]},{"outcomes":[]})


if __name__=="__main__":
    unittest.main()

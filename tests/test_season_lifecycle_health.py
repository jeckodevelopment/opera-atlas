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
        self.assertEqual(report["legacy_still_uncovered"]+report["legacy_covered_by_successor"],report["legacy_year_bound"])
        self.assertEqual(report["verified_rollover"]+
                         report["evergreen_index_unverified"]+
                         report["legacy_year_bound"],report["total_indexes"])

    def test_legacy_successors_are_explicit_and_do_not_fake_live_coverage(self):
        result=build(self.config,self.policy,{"sources":[]},{"outcomes":[]})
        rows={x["source_key"]:x for x in result["sources"]}
        self.assertEqual(result["legacy_year_bound"],19)
        self.assertEqual(result["legacy_covered_by_successor"],19)
        self.assertEqual(result["legacy_still_uncovered"],0)
        for key in ("ferrara-macbeth-opera-2026-27",
                    "ferrara-boccanegra-opera-2026-27",
                    "jesi-trittico-opera-2026",
                    "ancona-elisir-opera-2026",
                    "donizetti-opera-2026",
                    "petruzzelli-opera-2026"):
            self.assertTrue(rows[key]["legacy_covered_by_successor"])
            self.assertTrue(rows[key]["successor_source_key"])
            self.assertFalse(rows[key]["future_season_verified"])
        self.assertTrue(rows["modena-opera-2026-27"]["legacy_covered_by_successor"])
        self.assertEqual(rows["modena-opera-2026-27"]["successor_source_key"],
                         "modena-municipal-opera-2027-28")

    def test_evergreen_reusability_audit_is_exhaustive_and_not_live_proof(self):
        result=build(self.config,self.policy,{"sources":[]},{"outcomes":[]})
        self.assertEqual(result["evergreen_index_unverified"],42)
        self.assertEqual(result["evergreen_dynamic_category"],29)
        self.assertEqual(result["evergreen_fixed_production_set"],11)
        self.assertEqual(result["evergreen_historical_notice"],2)
        self.assertEqual(result["evergreen_fixed_covered"],10)
        self.assertEqual(result["evergreen_fixed_uncovered"],1)
        self.assertEqual(result["evergreen_fixed_covered"]+
                         result["evergreen_fixed_uncovered"],
                         result["evergreen_fixed_production_set"])
        self.assertEqual(result["evergreen_dynamic_category"]+
                         result["evergreen_fixed_production_set"]+
                         result["evergreen_historical_notice"],
                         result["evergreen_index_unverified"])
        by_key={x["source_key"]:x for x in result["sources"]}
        for key in ("lecce-apollo-pinocchio-2026",
                    "rovigo-regione-programma-2026-27"):
            self.assertEqual(by_key[key]["evergreen_reusability"],"historical_notice")
        for key in ("goldoni-livorno-dido-2026-27",
                    "sassari-de-carolis-opera-2026",
                    "coccia-novara-opera-2027"):
            self.assertEqual(by_key[key]["evergreen_reusability"],"fixed_production_set")
        for key in ("arena-festival-2027","modena-teatro-opera-2026-27"):
            self.assertEqual(by_key[key]["evergreen_reusability"],"dynamic_category")
            self.assertFalse(by_key[key]["future_season_verified"])

    def test_missing_or_duplicate_evergreen_audit_fails_closed(self):
        from scripts.season_lifecycle_health import EVERGREEN_AUDIT
        audit=json.loads(EVERGREEN_AUDIT.read_text(encoding="utf-8"))
        for mode in ("missing","duplicate","unknown","wrong_strategy","wrong_scope"):
            changed=copy.deepcopy(audit)
            if mode=="missing":
                changed["sources"].pop()
            elif mode=="duplicate":
                changed["sources"].append(copy.deepcopy(changed["sources"][0]))
            elif mode=="unknown":
                changed["sources"][0]["source_key"]="fictional-future-opera"
            elif mode=="wrong_strategy":
                changed["sources"][0]["source_key"]="scala-season-2026-27"
            else:
                changed["sources"][0]["scope"]="definitely_live"
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                build(self.config,self.policy,{"sources":[]},{"outcomes":[]},
                      evergreen_audit=changed)

    def test_fixed_title_successors_leave_only_lecce_uncovered(self):
        from scripts.season_lifecycle_health import EVERGREEN_AUDIT
        audit=json.loads(EVERGREEN_AUDIT.read_text(encoding="utf-8"))
        result=build(self.config,self.policy,{"sources":[]},{"outcomes":[]},
                     evergreen_audit=audit)
        indexed={x["source_key"]:x for x in result["sources"]}
        missing=[x["source_key"] for x in result["sources"]
                 if x["evergreen_reusability"]=="fixed_production_set"
                 and not x["fixed_source_successor_key"]]
        self.assertEqual(missing,["lecce-politeama-opera-2026"])
        self.assertEqual(indexed["goldoni-livorno-dido-2026-27"]["fixed_source_successor_key"],
                         "goldoni-livorno-rolling-lirica")
        self.assertEqual(indexed["sassari-de-carolis-opera-2026"]["fixed_source_successor_key"],
                         "sassari-de-carolis-rolling-opera")
        self.assertFalse(indexed["sassari-de-carolis-opera-2026"]["future_season_verified"])

    def test_invalid_fixed_title_successor_requires_real_dynamic_parser(self):
        from scripts.season_lifecycle_health import EVERGREEN_AUDIT
        audit=json.loads(EVERGREEN_AUDIT.read_text(encoding="utf-8"))
        key="sassari-de-carolis-opera-2026"
        for invalid in ("missing-key","scala-season-2026-27",
                        "goldoni-livorno-dido-2026-27",key):
            changed=copy.deepcopy(audit)
            item=next(x for x in changed["sources"] if x["source_key"]==key)
            item["successor_source_key"]=invalid
            with self.subTest(target=invalid),self.assertRaises(ValueError):
                build(self.config,self.policy,{"sources":[]},{"outcomes":[]},
                      evergreen_audit=changed)
        changed=copy.deepcopy(audit)
        item=next(x for x in changed["sources"] if x["source_key"]==key)
        item.pop("successor_source_key")
        other=next(x for x in changed["sources"]
                   if x["source_key"]=="arena-festival-2027")
        other["successor_source_key"]="sassari-de-carolis-rolling-opera"
        with self.assertRaises(ValueError):
            build(self.config,self.policy,{"sources":[]},{"outcomes":[]},
                  evergreen_audit=changed)

    def test_invalid_successor_mappings_fail_closed(self):
        from scripts.season_lifecycle_health import SUCCESSORS
        good=json.loads(SUCCESSORS.read_text(encoding="utf-8"))
        for modification in ("duplicate","missing","nonrolling","nonlegacy"):
            altered=copy.deepcopy(good)
            item=altered["mappings"][0].copy()
            if modification=="duplicate":
                altered["mappings"].append(item)
            elif modification=="missing":
                altered["mappings"].append({"legacy_source_key":"missing-key",
                                             "successor_source_key":item["successor_source_key"]})
            elif modification=="nonrolling":
                altered["mappings"].append({"legacy_source_key":"modena-opera-2026-27",
                                             "successor_source_key":"modena-opera-2026-27"})
            else:
                altered["mappings"].append({"legacy_source_key":"scala-season-2026-27",
                                             "successor_source_key":item["successor_source_key"]})
            with self.subTest(modification=modification),self.assertRaises(ValueError):
                build(self.config,self.policy,{"sources":[]},{"outcomes":[]},altered)

    def test_policy_incompleteness_fails_closed(self):
        policy=copy.deepcopy(self.policy)
        policy["sources"].pop("scala-season-2026-27")
        with self.assertRaises(ValueError):
            build(self.config,policy,{"sources":[]},{"outcomes":[]})


if __name__=="__main__":
    unittest.main()

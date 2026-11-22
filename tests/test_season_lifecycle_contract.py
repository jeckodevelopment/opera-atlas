"""A new theatre source cannot ship without an explicit multi-season contract."""
import json
import unittest
from pathlib import Path
from scripts.discover_season_indexes import CONFIG
from scripts.rollover_season_indexes import ROLLOVER_KEYS

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "data" / "season-lifecycle-policy.json"
BASELINE = "legacy_baseline_2026_11_22"
STRATEGIES = {"verified_rollover", "evergreen_index", "legacy_year_bound"}

class SeasonLifecycleContractTests(unittest.TestCase):
    def test_all_sources_have_a_declared_lifecycle_and_new_sources_cannot_use_legacy_exception(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(policy["schema_version"], 1)
        sources = {item["key"]: item for item in config["sources"]}
        self.assertEqual(set(policy["sources"]), set(sources),
                         "Every new theatre source must have a season lifecycle contract")
        for key, record in policy["sources"].items():
            with self.subTest(source=key):
                self.assertEqual(set(record), {"strategy", "verification"})
                self.assertIn(record["strategy"], STRATEGIES)
                self.assertTrue(isinstance(record["verification"], str)
                                and record["verification"].strip())
                if record["verification"] != BASELINE:
                    self.assertNotEqual(record["strategy"], "legacy_year_bound",
                                        "New sources must discover future seasons")
                    self.assertIn(record["verification"], {
                        "test_verified", "live_verified"
                    }, "New source requires verified lifecycle evidence")
                if record["strategy"] == "verified_rollover":
                    self.assertIn(key, ROLLOVER_KEYS,
                                  "Verified rollover must be implemented in code")
                if record["strategy"] == "evergreen_index":
                    from urllib.parse import urlsplit
                    import re
                    path = urlsplit(sources[key]["url"]).path
                    self.assertFalse(re.search(r"202[6-9]|26-27|27-28", path),
                                     "Evergreen index cannot be season-bound")
        self.assertEqual(set(ROLLOVER_KEYS),
                         {k for k,v in policy["sources"].items()
                          if v["strategy"] == "verified_rollover"})

    def test_baseline_exceptions_cannot_be_added_silently(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        # A fixed baseline prevents silently exempting new sources by copying
        # the legacy verification marker.
        baseline_keys = {
            k for k, v in policy["sources"].items()
            if v["verification"] == BASELINE
        }
        self.assertEqual(baseline_keys, HISTORIC_SOURCES)

HISTORIC_SOURCES = frozenset(['scala-season-2026-27','arena-festival-2027','fenice-opera-2026-27','parma-opera-2027','massimo-season-2026-27','carlo-felice-season-2026-27','donizetti-opera-2026','teatro-grande-opera-2026','maggio-fiorentino-calendar-2027','opera-roma-season-2026-27','petruzzelli-opera-2026','petruzzelli-opera-2027','bologna-comunale-opera-2026','bologna-comunale-opera-2027','verdi-trieste-season-2026-27','lirico-cagliari-opera-2027','bellini-catania-opera-2026-27','chieti-marrucino-lirica-2026','modena-teatro-opera-2026-27','modena-opera-2026-27','giglio-lucca-opera-2026-27','piacenza-opera-2026-27','reggio-valli-opera-2026-27','ferrara-macbeth-opera-2026-27','ferrara-barbiere-opera-2026-27','ferrara-dido-opera-2026-27','ferrara-clemenza-opera-2026-27','ferrara-boccanegra-opera-2026-27','goldoni-livorno-dido-2026-27','goldoni-livorno-otello-2026-27','goldoni-livorno-elisir-2026-27','jesi-trittico-opera-2026','jesi-don-pasquale-opera-2026','jesi-esecuzione-opera-2026','jesi-nabucco-opera-2026','ancona-elisir-opera-2026','ancona-cavalleria-program-2026','macerata-festival-2027','salerno-verdi-opera-2026','pisa-verdi-opera-2026-27','filarmonico-verona-opera-2027','coccia-novara-opera-2027','ravenna-alighieri-cherubini-2027','treviso-del-monaco-opera-2026-27','padova-verdi-opera-2026','rovigo-regione-programma-2026-27','rovigo-sociale-opera-2026-27','lecce-politeama-opera-2026','lecce-provincia-politeama-2026','lecce-apollo-pinocchio-2026','messina-vittorio-opera-2026-27','sassari-de-carolis-opera-2026'])

if __name__ == "__main__":
    unittest.main()

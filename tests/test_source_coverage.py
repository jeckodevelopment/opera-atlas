"""Coverage must be truthful for all eight primary sources."""
import json
import unittest
from scripts.build_verified_catalog import MANIFEST
from scripts.daily_ingest import CONFIG,HEALTH
from scripts.source_coverage import SOURCES, DOMAINS, build_coverage


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.sources=json.loads(SOURCES.read_text(encoding="utf-8"))
        self.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.config=json.loads(CONFIG.read_text(encoding="utf-8"))
        self.health=json.loads(HEALTH.read_text(encoding="utf-8")) if HEALTH.exists() else None

    def test_every_agreed_source_has_a_coverage_status(self):
        report=build_coverage(self.sources,self.facts,self.config,self.health)
        rows=report["sources"]
        self.assertEqual(len(rows),8)
        self.assertEqual({s["source_key"] for s in rows},set(DOMAINS))
        self.assertTrue(all(s["season_complete"] is False for s in rows))
        self.assertEqual(sum(s["verified_recite"] for s in rows),
                         sum(len(p["dates"]) for p in self.facts["productions"]))
        self.assertTrue(all(s["calendar_url"].startswith("https://") for s in rows))

    def test_seeded_sources_not_falsely_claimed_as_automated(self):
        report=build_coverage(self.sources,self.facts,self.config,self.health)
        by={s["source_key"]:s for s in report["sources"]}
        for key in ("teatro-alla-scala","teatro-la-fenice",
                    "fondazione-arena-verona","teatro-regio-parma","teatro-massimo-palermo"):
            if key in ("teatro-alla-scala","fondazione-arena-verona"):
                self.assertIn(by[key]["monitoring"],(
                    "editorial_only","configured_not_verified","detail_pages_verified"
                ))
            else:
                self.assertIn(by[key]["monitoring"],(
                    "editorial_only","configured_not_verified"
                ))
            self.assertGreater(by[key]["verified_recite"],0)
        self.assertEqual(by["rossini-opera-festival"]["monitoring"],"not_started")
        self.assertGreaterEqual(by["opera-lombardia"]["scheduled_pages"],7)
        self.assertGreaterEqual(by["regio-torino"]["scheduled_pages"],9)

    def test_honest_monitoring_depends_on_actual_scan_result(self):
        fake={"checked_at":"2026-11-20T10:00:00+00:00",
              "sources":[{"key":"opera-lombardia-calendar-2026-27",
                          "outcome":"unavailable_or_invalid"}]}
        report=build_coverage(self.sources,self.facts,self.config,fake)
        by={s["source_key"]:s for s in report["sources"]}
        self.assertNotEqual(by["opera-lombardia"]["monitoring"],
                            "calendar_index_verified")
        self.assertNotEqual(by["regio-torino"]["monitoring"],
                            "detail_pages_verified")

    def test_unknown_ninth_source_is_not_silently_ignored(self):
        duplicate=json.loads(json.dumps(self.sources))
        duplicate["sources"].append(dict(duplicate["sources"][0]))
        with self.assertRaises(ValueError):
            build_coverage(duplicate,self.facts,self.config,self.health)

if __name__=="__main__":
    unittest.main()

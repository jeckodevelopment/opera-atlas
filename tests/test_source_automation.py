"""Automation is based on real source checks, never venue directory labels."""
import unittest
from scripts.source_automation import build


class SourceAutomationTests(unittest.TestCase):
    def test_actual_success_and_missing_sources(self):
        # Mapping integrity requires the complete reference directory.
        from scripts.source_automation import DIRECTORY, DAILY, INDEX
        import json
        directory=json.loads(DIRECTORY.read_text())
        daily=json.loads(DAILY.read_text())
        index=json.loads(INDEX.read_text())
        dh={"sources":[{"key":"regio-traviata-2027","outcome":"success"}]}
        ih={"sources":[{"key":"opera-roma-season-2026-27",
                        "status":"success","current_scan_verified":True},
                       {"key":"petruzzelli-opera-2026",
                        "status":"unavailable_or_invalid","current_scan_verified":False}]}
        report=build(directory,daily,dh,index,ih)
        rows={(x["city"],x["venue"]):x for x in report["venues"]}
        self.assertEqual(rows["Torino","Teatro Regio di Torino"]["status"],"operational")
        self.assertEqual(rows["Roma","Teatro dell'Opera di Roma"]["status"],"operational")
        self.assertEqual(rows["Napoli","Teatro di San Carlo"]["status"],"not_automated")
        self.assertEqual(rows["Napoli","Teatro di San Carlo"]["source_attention"],"not_configured")
        self.assertEqual(rows["Roma","Teatro dell\'Opera di Roma"]["source_attention"],"none")
        self.assertEqual(report["total_venues"],len(directory["venues"]))
        self.assertEqual(report["automation_remaining"],
                         report["not_automated"]+report["configured_not_operational"])

    def test_index_link_does_not_equal_success(self):
        from scripts.source_automation import DIRECTORY, DAILY, INDEX
        import json
        report=build(json.loads(DIRECTORY.read_text()),
                     json.loads(DAILY.read_text()),{"sources":[]},
                     json.loads(INDEX.read_text()),
                     {"sources":[{"key":"opera-roma-season-2026-27",
                                  "status":"success","current_scan_verified":False,
                                  "links":20}]})
        roma=next(x for x in report["venues"] if x["city"]=="Roma"
                  and x["venue"]=="Teatro dell'Opera di Roma")
        self.assertEqual(roma["status"],"configured_not_operational")
        self.assertEqual(roma["source_attention"],"scan_failed")

    def test_blocked_and_never_checked_are_distinct(self):
        from scripts.source_automation import DIRECTORY, DAILY, INDEX
        import json
        report=build(json.loads(DIRECTORY.read_text()),
                     json.loads(DAILY.read_text()), {"sources":[]},
                     json.loads(INDEX.read_text()),
                     {"sources":[{"key":"modena-opera-2026-27",
                                  "status":"unavailable_or_invalid",
                                  "reason":"FetchUnavailable",
                                  "diagnostic":"official_robots_unavailable_or_invalid",
                                  "current_scan_verified":False}]})
        rows={(x["city"],x["venue"]):x for x in report["venues"]}
        modena=rows["Modena","Teatro Comunale Pavarotti-Freni"]
        self.assertEqual(modena["source_attention"],"scan_failed")
        self.assertEqual(next(s for s in modena["sources"] if s["source_key"]=="modena-opera-2026-27")["failure_reason"],
                         "official_robots_unavailable_or_invalid")
        self.assertEqual(rows["Livorno","Teatro Goldoni"]["source_attention"],"not_checked")
        self.assertIsNone(rows["Livorno","Teatro Goldoni"]["sources"][0]["failure_reason"])


if __name__=="__main__":
    unittest.main()

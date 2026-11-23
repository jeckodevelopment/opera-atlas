"""Public URL verification must require rendered content, not HTTP 200 alone."""
import unittest
from scripts.audit_public_atlas import classify, targets


class LivePublicationAuditTests(unittest.TestCase):
    def test_live_audit_runs_after_successful_catalog_refresh(self):
        from scripts.publish_catalog_v2 import ROOT
        workflow=(ROOT/".github/workflows/audit-public-atlas.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_run:",workflow)
        self.assertIn("workflows: ['Refresh public Opera Atlas catalog']",workflow)
        self.assertIn("types: [completed]",workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'",workflow)
        self.assertIn("cancel-in-progress: false",workflow)
        self.assertIn("git add public/catalog/live-publication-health.json",workflow)
        self.assertIn("python -m scripts.push_live_publication_audit",workflow)

    def test_static_shell_is_not_verified(self):
        self.assertEqual(classify(200, None, None, "", "La traviata", "Produzione"), "unverified")
        self.assertEqual(classify(200, "Scheda non disponibile", "Scheda", "", "La traviata", "Produzione"), "unverified")
        self.assertEqual(classify(200, "La traviata", "Produzione", "",
                                  "La traviata", "Produzione"), "verified_live")
        self.assertEqual(classify(200, "La traviata", "PRODUZIONE", "",
                                  "La traviata", "Produzione"), "verified_live")
        self.assertEqual(classify(200, "Aida", "Produzione", "",
                                  "La traviata", "Produzione"), "content_mismatch")
        self.assertEqual(classify(200, "La traviata", "Produzione",
                                  "Alcuni aggiornamenti non sono momentaneamente disponibili.",
                                  "La traviata", "Produzione"), "fallback_catalog")
        self.assertEqual(classify(404, None, None, "",
                                  "La traviata", "Produzione"), "missing_route")
        self.assertEqual(classify(403, None, None, "",
                                  "La traviata", "Produzione"), "unverified")
        self.assertEqual(classify(None, None, None, "",
                                  "La traviata", "Produzione", error="TimeoutError"), "unverified")

    def test_targets_include_solo_and_program_without_duplicate_dates(self):
        man = {"schema_version": 2}
        works = {"works": [{"id": "w1", "title": "Opera"}]}
        stagings = {"stagings": [{"id": "s1", "work_id": "w1",
                                 "venue_id": "v1", "url": "/town/theatre/opera/"}]}
        performances = {"performances": [{"staging_id": "s1"}, {"staging_id": "s1"}]}
        programs = {"programs": [{"id": "oa-p-abcd", "title": "Dittico",
                                 "performances": [{"id": "r1"}]}]}
        result = targets(man, works, {"venues": [{"id":"v1","name":"Teatro Regio","display_name":"Teatro Regio di Torino","city_slug":"torino","slug":"teatro-regio"}]}, stagings, performances, programs)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["route"], "/programmi/oa-p-abcd/")
        self.assertEqual(result[1]["expected_recite"], 2)
        self.assertEqual(result[2]["title"], "Teatro Regio di Torino")

    def test_rewrite_covers_program_route(self):
        from scripts.publish_catalog_v2 import ROOT
        htaccess = (ROOT / "site/.htaccess").read_text(encoding="utf-8")
        self.assertIn("programmi/oa-p-[a-z0-9-]+", htaccess)


if __name__ == "__main__":
    unittest.main()

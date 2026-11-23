"""The slow catalog and fast publisher must not rerun for diagnostics-only edits."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def push_paths(name: str) -> list[str]:
    contents = (ROOT / name).read_text(encoding="utf-8").splitlines()
    begin = contents.index("  push:")
    end = next(i for i in range(begin + 1, len(contents))
               if contents[i] and not contents[i].startswith(" "))
    segment = contents[begin:end]
    return [row.strip()[3:-1] for row in segment if row.strip().startswith("- '") and row.endswith("'")]


def github_path_match(path: str, globs: list[str]) -> bool:
    # Minimal evaluator for the anchored patterns used in these workflows.
    import fnmatch
    matched = False
    for pattern in globs:
        exclude = pattern.startswith("!")
        pattern = pattern.removeprefix("!")
        if fnmatch.fnmatchcase(path, pattern):
            matched = not exclude
    return matched


class TriggerScopeTests(unittest.TestCase):
    def test_full_acquisition_ignores_pure_diagnostic_changes(self):
        patterns = push_paths("refresh-catalog.yml")
        for path in (
            "scripts/pipeline_operations_health.py",
            "scripts/push_pipeline_operations_health.py",
            "scripts/audit_public_atlas.py",
            "scripts/push_live_publication_audit.py",
            "tests/test_pipeline_operations_health.py",
            "tests/test_diagnostics_lifecycle.py",
        ):
            with self.subTest(path=path):
                self.assertFalse(github_path_match(path, patterns))
        for path in (
            "opera_atlas/modena_opera_parser.py",
            "scripts/collect_candidate_details.py",
            "scripts/auto_catalogue.py",
            "data/season-index-config.json",
            "data/verified-work-authority-seeds.json",
            "tests/test_auto_catalogue.py",
            "tests/test_candidate_detail_evidence.py",
        ):
            with self.subTest(path=path):
                self.assertTrue(github_path_match(path, patterns))

    def test_catalog_refresh_reconciles_pending_queue_before_strict_check(self):
        # Approved source exclusions can change while the committed candidate
        # registry is still a cached snapshot from an earlier refresh.
        # Regeneration must precede the consistency assertion, otherwise
        # refresh aborts before it can acquire and publish the new catalog.
        workflow=(ROOT / "refresh-catalog.yml").read_text(encoding="utf-8")
        header=workflow.split(
            "      - name: Validate current public catalog before acquisition",1)[1]
        validation=header.split("      - name: Collect San Carlo secondary candidates",1)[0]
        regenerate="python -m scripts.reconcile_published_candidates\n"
        verify="python -m scripts.reconcile_published_candidates --check"
        self.assertIn(regenerate,validation)
        self.assertIn(verify,validation)
        self.assertLess(validation.index(regenerate),validation.index(verify))
        self.assertLess(validation.index(verify),
                        validation.index("python -m scripts.publish_work_editorial --check"))

    def test_cached_publication_ignores_observability_but_keeps_facts(self):
        patterns = push_paths("publish-cached-catalog.yml")
        for path in ("scripts/pipeline_operations_health.py",
                     "scripts/push_pipeline_operations_health.py",
                     "scripts/audit_public_atlas.py",
                     "scripts/push_live_publication_audit.py"):
            self.assertFalse(github_path_match(path, patterns), path)
        for path in ("scripts/publish_cached_known.py",
                     "data/candidate-detail-evidence.json",
                     "data/verified-ticketing-art.json",
                     "opera_atlas/modena_opera_parser.py"):
            self.assertTrue(github_path_match(path, patterns), path)

    def test_frontend_deploy_only_runs_for_site_changes(self):
        patterns = push_paths("deploy-atlas.yml")
        for path in ("tests/test_workflow_trigger_scope.py",
                     "tests/test_diagnostics_lifecycle.py",
                     "tests/test_auto_catalogue.py"):
            with self.subTest(path=path):
                self.assertFalse(github_path_match(path, patterns))
        for path in ("site/index.html", "site/app.js", "site/styles.css",
                     "site/.htaccess", "scripts/deploy_atlas_sftp.py"):
            with self.subTest(path=path):
                self.assertTrue(github_path_match(path, patterns))


    def test_catalog_recovery_uses_committed_checkpoints_without_recrawl(self):
        workflow = (ROOT / "refresh-catalog.yml").read_text(encoding="utf-8")
        self.assertIn("recover_from_checkpoint:", workflow)
        acquisition, recovery = workflow.split("\n  recover_from_checkpoint:", 1)
        # A deferred write must not dispatch another 75-minute acquisition.
        self.assertNotIn("event_type=catalog-refresh-retry", acquisition)
        self.assertIn("needs.update.outputs.recovery_required == 'true'", recovery)
        self.assertIn("needs.update.result == 'failure'", recovery)
        self.assertIn("ref: main", recovery)
        self.assertNotIn("--allow-network", recovery)
        self.assertNotIn("scripts.daily_ingest", recovery)
        self.assertIn("python -m unittest discover -s tests -v", recovery)
        self.assertIn("python -m scripts.safe_push_catalog", recovery)
        self.assertLess(
            recovery.index("python -m unittest discover -s tests -v"),
            recovery.index("git commit -m"))

    def test_source_health_still_runs_when_scanner_changes(self):
        patterns = push_paths("refresh-source-health.yml")
        for path in ("scripts/discover_season_indexes.py",
                     "data/season-index-config.json",
                     ".github/workflows/refresh-source-health.yml"):
            self.assertTrue(github_path_match(path, patterns), path)


if __name__ == "__main__":
    unittest.main()

"""Publish operational observations without overwriting concurrent canonical facts.

A changed candidate registry/evidence requires recalculation from fresh main.
Updates in unrelated catalogs can be rebased safely without rewriting source.
"""
from pathlib import Path
from scripts.safe_push_catalog import safe_push

WATCHED = {
    "data/season-index-candidates.json",
    "public/catalog/candidate-publication-evidence.json",
    "data/pipeline-publication-observations.json",
    "public/catalog/pipeline-operations-health.json",
    "scripts/pipeline_operations_health.py",
}
def conflicting(paths: list[str]) -> bool:
    return any(p in WATCHED for p in paths)

def main() -> None:
    result = safe_push(Path.cwd(), conflict_checker=conflicting)
    print("Pipeline observation push:", result)
    if result != "published":
        raise SystemExit("Operational snapshot deferred; next hourly observation will rebuild it")

if __name__ == "__main__":
    main()

"""Persist a public browser audit across unrelated editorial data commits."""
from pathlib import Path

from scripts.safe_push_catalog import safe_push

WATCHED_PREFIXES = ("site/", "public/catalog/v2/")
WATCHED_FILES = {
    "public/catalog/programs.json",
    "public/catalog/venue-directory.json",
    "public/catalog/production-groups.json",
    "public/catalog/live-publication-health.json",
    "scripts/audit_public_atlas.py",
    ".github/workflows/audit-public-atlas.yml",
}


def conflicting(paths: list[str]) -> bool:
    return any(path in WATCHED_FILES or path.startswith(WATCHED_PREFIXES)
               for path in paths)


def main() -> None:
    result = safe_push(Path.cwd(), conflict_checker=conflicting)
    print("Live audit push result:", result)
    if result != "published":
        raise SystemExit("Live audit report not published: important catalog input changed")


if __name__ == "__main__":
    main()

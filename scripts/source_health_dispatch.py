"""Detect newly actionable official URLs so source-health can wake catalog acquisition.

A refreshed health timestamp is not a new candidate. Compare source-key and
exact URL, not random candidate order or volatile scan metadata.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def review_urls(document: dict) -> set[tuple[str, str]]:
    if document.get("schema_version") != 1 or not isinstance(document.get("candidates"), list):
        raise ValueError("invalid season candidate feed")
    urls = set()
    for row in document["candidates"]:
        if not isinstance(row, dict):
            raise ValueError("invalid season candidate")
        if row.get("status") != "needs_review":
            continue
        key, url = row.get("source_key"), row.get("official_url")
        if not isinstance(key, str) or not key or not isinstance(url, str) or not url:
            raise ValueError("missing candidate identity")
        urls.add((key, url))
    return urls


def newly_actionable(before: dict, after: dict) -> set[tuple[str, str]]:
    return review_urls(after) - review_urls(before)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()
    earlier = json.loads(args.before.read_text(encoding="utf-8"))
    current = json.loads(args.after.read_text(encoding="utf-8"))
    discovered = newly_actionable(earlier, current)
    with args.github_output.open("a", encoding="utf-8") as output:
        output.write(f"new_candidates={'true' if discovered else 'false'}\n")
    print(f"New source-bound review candidates: {len(discovered)}")


if __name__ == "__main__":
    main()

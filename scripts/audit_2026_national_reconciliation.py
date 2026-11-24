"""Aggregate all 2026 retrospective scan slices and reconcile read-only.

Outputs are diagnostics, not automatic publication or certified season coverage.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from scripts.audit_2026_retrospective_reconciliation import reconcile

ROOT = Path(__file__).resolve().parents[1]
INPUT_NAMES = (
    "atlas-2026-retrospective-batch.json",
    "atlas-2026-retrospective-batch-240.json",
    "atlas-2026-retrospective-batch-480.json",
    "atlas-2026-retrospective-batch-720.json",
)
DIAGNOSTICS = ROOT / "public/diagnostics"
FULL_OUTPUT = DIAGNOSTICS / "atlas-2026-national-reconciliation.json"
SUMMARY_OUTPUT = DIAGNOSTICS / "atlas-2026-national-reconciliation-summary.json"
INPUTS = (
    ROOT / "data/verified-launch-catalog.json",
    ROOT / "public/catalog/programs.json",
    ROOT / "data/historical-2026-official-evidence.json",
    ROOT / "data/retrospective-2026-priority-reviews.json",
    ROOT / "data/retrospective-2026-source-specific-decisions.json",
)
REVIEW_STATUSES = {
    "unmatched_requires_official_review",
    "same_source_day_identity_or_time_conflict",
    "possible_match_needs_venue_source_review",
    "partial_multiwork_catalogued_needs_review",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def aggregate(reports, catalog, programs, historical, priority, decisions):
    if len(reports) != 4:
        raise ValueError("Expected all four retrospective batches")
    if [r.get("archive_offset", 0) for r in reports] != [0, 240, 480, 720]:
        raise ValueError("Unexpected or reordered retrospective offsets")
    for r in reports:
        if (r.get("year") != 2026 or r.get("read_only") is not True
                or r.get("catalog_updated") is not False
                or r.get("complete_seasons_certified") != 0):
            raise ValueError("Untrusted retrospective scan input")
        if not isinstance(r.get("unverified_2026_facts"), list):
            raise ValueError("Missing observation list")
    # Keep raw duplicates; the existing reconciler collapses exact source/date/
    # title/start/venue identities and retains the discovery origins.
    observations = [
        {**fact, "scan_batch_offset":r.get("archive_offset", 0)}
        for r in reports for fact in r["unverified_2026_facts"]
    ]
    combined = {
        "year":2026, "read_only":True,
        "checked_at":max(r["checked_at"] for r in reports),
        "unverified_2026_facts":observations,
        "seed_results":[], "archive_results":[], "detail_results":[],
    }
    full = reconcile(combined, catalog, programs, historical, priority, decisions)
    # Aggregate fetch metrics for operational visibility only: the same URL may
    # recur across batches, especially seed pages and detail pages.
    stages = {}
    for stage, attempted, success in (
        ("seeds", "seed_pages_attempted", "seed_pages_scanned"),
        ("archives", "historical_archives_attempted", "historical_archives_scanned"),
        ("details", "detail_pages_attempted", "detail_pages_scanned"),
    ):
        a = sum(r.get(attempted, 0) for r in reports)
        s = sum(r.get(success, 0) for r in reports)
        stages[stage] = {"attempts":a, "succeeded":s, "failed":a-s,
                         "note":"Page attempts; not deduplicated distinct URLs"}
    review = [
        {"date":row["date"], "time":row["time"],
         "event_title":row["event_title"], "venue":row["venue"],
         "source_key":row["source_key"], "source_url":row["source_url"],
         "status":row["status"]}
        for row in full["observations"]
        if (row["status"] in REVIEW_STATUSES or "time_conflict" in row["status"]
            or row["status"].startswith("official_opera_candidate"))
    ]
    by_source = defaultdict(Counter)
    for row in full["observations"]:
        by_source[row["source_key"] or "unattributed"][row["status"]] += 1
    summary = {
        "schema_version":1, "year":2026,
        "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_checked_at":[r["checked_at"] for r in reports],
        "scan_offsets":[0, 240, 480, 720],
        "read_only":True,"catalog_updated":False,
        "complete_seasons_certified":0,
        "raw_observation_count":full["raw_observation_count"],
        "unique_observation_count":full["unique_observation_count"],
        "duplicate_observations_collapsed":full["duplicate_observations_collapsed"],
        "observation_counts":full["observation_counts"],
        "monthly_counts":full["monthly_counts"],
        "fetch_attempts":stages,
        "review_queue_count":len(review),
        "review_queue":review,
        "source_counts":{k:dict(sorted(v.items())) for k,v in sorted(by_source.items())},
        "warning":"Unmatched facts are not verified missing recite. Generic Event JSON-LD cannot certify genre, audience, venue or season completeness. No catalog publication.",
    }
    return full, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnostics-dir", type=Path, default=DIAGNOSTICS)
    parser.add_argument("--full-output", type=Path, default=FULL_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=SUMMARY_OUTPUT)
    args = parser.parse_args()
    reports = [load_json(args.diagnostics_dir / name) for name in INPUT_NAMES]
    args_list = [load_json(p) for p in INPUTS]
    full, summary = aggregate(reports, *args_list)
    for path, payload in ((args.full_output, full), (args.summary_output, summary)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n",
                        encoding="utf-8")
    print("NATIONAL_2026_SUMMARY " + json.dumps({
        k:summary[k] for k in (
            "raw_observation_count","unique_observation_count",
            "duplicate_observations_collapsed","observation_counts",
            "review_queue_count","fetch_attempts",
        )}, ensure_ascii=False))
    for row in summary["review_queue"][:120]:
        print("NATIONAL_2026_REVIEW " + json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()

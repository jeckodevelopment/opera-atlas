"""Evidence-based candidate reconciliation diagnostics per physical venue.

Aggregate only source keys uniquely mapped to a single venue in the approved
source automation feed. Shared theatre/circuit sources stay unattributed rather
than multiplying candidate counts across unrelated venues.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts.publish_catalog_v2 import ROOT, payload

AUTOMATION = ROOT / "public/catalog/source-automation.json"
CANDIDATES = ROOT / "data/season-index-candidates.json"
DETAILS = ROOT / "data/candidate-detail-health.json"
IDENTITY = ROOT / "public/catalog/work-identity-review.json"
OUT = ROOT / "public/catalog/catalogation-diagnostics.json"
STATES = ("already_catalogued", "needs_review", "excluded_nonopera",
          "not_in_official_season")


def build(automation: dict, candidates: dict, details: dict, identity: dict) -> dict:
    if candidates.get("schema_version") != 1:
        raise ValueError("unsupported candidate registry schema")
    venues = automation.get("venues", [])
    ownership = defaultdict(set)
    for venue in venues:
        for source in venue.get("sources", []):
            if source.get("configured"):
                ownership[source["source_key"]].add(venue["venue_id"])
    unique = {key: next(iter(targets)) for key, targets in ownership.items()
              if len(targets) == 1}
    details_by_id = {x.get("candidate_id"): x for x in details.get("outcomes", [])
                     if isinstance(x, dict)}
    unresolved_ids = set()
    for group in identity.get("groups", []):
        unresolved_ids.update(group.get("candidate_ids", []))
    counts = defaultdict(Counter)
    unassigned = Counter()
    per_venue = defaultdict(list)
    for candidate in candidates.get("candidates", []):
        state = candidate.get("status")
        if state not in STATES:
            state = "unclassified"
        source_key = candidate.get("source_key", "")
        venue_id = unique.get(source_key)
        if not venue_id:
            unassigned[state] += 1
            continue
        counts[venue_id][state] += 1
        if state == "needs_review":
            d = details_by_id.get(candidate.get("id"), {})
            per_venue[venue_id].append({
                "candidate_id": candidate.get("id"),
                "source_key": source_key,
                "official_url": candidate.get("official_url"),
                "detail_outcome": d.get("outcome", "not_checked"),
                "detail_reason": d.get("reason"),
                "identity_review": candidate.get("id") in unresolved_ids,
            })
    rows = []
    for venue in venues:
        key = venue["venue_id"]
        state_counts = counts[key]
        rows.append({
            "venue_id": key, "venue": venue["venue"], "city": venue.get("city"),
            "region": venue.get("region"),
            "states": {state: state_counts[state] for state in STATES},
            "unclassified": state_counts["unclassified"],
            "total_attributed": sum(state_counts.values()),
            "pending": sorted(per_venue[key], key=lambda item: item["candidate_id"] or ""),
            "scope": "unique_source_key_only",
            "catalogue_identity_verification": "not_measured",
            "publication_verification": "not_measured",
        })
    return {
        "schema_version": 1,
        "checked_at": details.get("checked_at"),
        "definition": "Candidate statuses by uniquely assigned source key; already_catalogued reflects registry reconciliation, not proof of every work, production, performance or live deployment.",
        "excluded_from_attribution": dict(sorted(unassigned.items())),
        "venues": rows,
    }


def publish(check: bool = False) -> dict:
    def read(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))
    report = build(read(AUTOMATION), read(CANDIDATES), read(DETAILS),
                   read(IDENTITY))
    encoded = payload(report)
    if check:
        if not OUT.exists() or OUT.read_bytes() != encoded:
            raise ValueError("catalogation diagnostics feed out of sync")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_bytes(encoded)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = publish(check=args.check)
    print(json.dumps({
        "venues": len(report["venues"]),
        "attributed": sum(x["total_attributed"] for x in report["venues"]),
        "unassigned": sum(report["excluded_from_attribution"].values()),
    }))


if __name__ == "__main__":
    main()

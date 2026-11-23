"""Explain pending official candidates without changing editorial publication decisions.

This read-only report is safe after any checkpoint or failed reconciliation.
A missing or contradictory fact remains pending; this script never promotes it.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

from scripts.publish_catalog_v2 import ROOT

CANDIDATES = ROOT / "data/season-index-candidates.json"
DETAILS = ROOT / "data/candidate-detail-health.json"
EVIDENCE = ROOT / "data/candidate-detail-evidence.json"
IDENTITY = ROOT / "public/catalog/work-identity-review.json"
PROMOTION = ROOT / "data/autonomous-catalogue-health.json"


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build(candidates: dict, details: dict, evidence: dict,
          identity: dict, promotion: dict) -> dict:
    if candidates.get("schema_version") != 1:
        raise ValueError("invalid candidate registry")
    observed = {row["candidate_id"]: row for row in details.get("outcomes", [])
                if isinstance(row, dict) and isinstance(row.get("candidate_id"), str)}
    evidence_by_id = {row["candidate_id"]: row
                      for row in evidence.get("evidence", [])
                      if isinstance(row, dict) and isinstance(row.get("candidate_id"), str)}
    blocked = {}
    for row in promotion.get("auto_skipped", []):
        if isinstance(row, dict) and isinstance(row.get("candidate_id"), str):
            blocked.setdefault(row["candidate_id"], set()).add(
                row.get("reason") or "promotion_not_completed")
    identity_ids = set()
    for group in identity.get("groups", []):
        identity_ids.update(group.get("candidate_ids", []))

    pending = []
    for candidate in candidates.get("candidates", []):
        if candidate.get("status") != "needs_review":
            continue
        cid = candidate.get("id")
        if not isinstance(cid, str):
            continue
        detail = observed.get(cid, {})
        fact = evidence_by_id.get(cid, {})
        reasons = set(blocked.get(cid, ()))
        if cid in identity_ids:
            reasons.add("identity_requires_review")
        if detail.get("reason"):
            reasons.add(str(detail["reason"]))
        if not reasons:
            status = fact.get("status")
            if status != "needs_editorial_review":
                reasons.add("awaiting_verified_detail")
            else:
                reasons.add("awaiting_canonical_promotion")
        pending.append({
            "candidate_id": cid,
            "source_key": candidate.get("source_key"),
            "official_url": candidate.get("official_url"),
            "reasons": sorted(reasons),
            "detail_outcome": detail.get("outcome", "not_checked"),
            "evidence_status": fact.get("status", "not_checked"),
        })
    pending.sort(key=lambda row: row["candidate_id"])
    counts = Counter(reason for row in pending for reason in row["reasons"])
    return {"schema_version": 1,
            "candidate_count": len(pending),
            "reason_counts": dict(sorted(counts.items())),
            "pending": pending}


def main() -> None:
    report = build(load(CANDIDATES), load(DETAILS), load(EVIDENCE),
                   load(IDENTITY), load(PROMOTION))
    # Keep details in the action log; this isn't an alternative public feed.
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write(f"### Catalog candidate review: {report['candidate_count']} pending\n\n")
            out.write("| Reason | Candidates |\n|---|---:|\n")
            for reason, count in report["reason_counts"].items():
                out.write(f"| {reason} | {count} |\n")


if __name__ == "__main__":
    main()

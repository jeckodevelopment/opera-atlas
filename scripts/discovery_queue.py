"""Persistent, review-only discovery of productions missing from the curated catalog.

Only factual rows from approved and successfully robots-gated pages enter this
queue. Candidate records NEVER enter the public performance feed automatically.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from scripts.daily_ingest import HEALTH, CONFIG, validate_source_config, _write_atomic

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "discovery-candidates.json"
PUBLIC = ROOT / "public" / "catalog" / "discovery.json"


def reconcile(existing: dict, health: dict, config: dict) -> dict:
    if existing.get("schema_version") != 1 or not isinstance(existing.get("candidates"), list):
        raise ValueError("invalid discovery queue")
    allowed = {s["key"]: s for s in validate_source_config(config)
               if s["access_status"] == "approved"}
    result = {row["id"]: row.copy() for row in existing["candidates"]}
    checked_at = health.get("checked_at")
    if not isinstance(checked_at, str) or not checked_at:
        raise ValueError("missing scan timestamp")
    for scan in health.get("sources", []):
        source = allowed.get(scan.get("key"))
        if source is None or scan.get("outcome") != "review_required":
            continue
        for fact in scan.get("candidates", []):
            title, venue, city = (fact.get(k) for k in ("title", "venue", "city"))
            day, hour = fact.get("date"), fact.get("time")
            if not all(isinstance(v, str) and v.strip() for v in (title, venue, city, day)):
                continue
            try:
                date.fromisoformat(day)
            except ValueError:
                continue
            if hour is not None and (not isinstance(hour, str)
                                      or len(hour) != 5 or hour[2] != ":"):
                continue
            composer = fact.get("composer")
            if composer is not None and not isinstance(composer, str):
                continue
            identity = json.dumps([source["key"], title, composer, venue, city],
                                  ensure_ascii=False, separators=(",", ":"))
            candidate_id = "oa-c-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
            if candidate_id not in result:
                result[candidate_id] = {
                    "id": candidate_id, "status": "needs_review",
                    "source_key": source["key"], "source_url": source["url"],
                    "title": title, "composer": composer,
                    "venue": venue, "city": city, "dates": [],
                    "first_seen": checked_at, "last_seen": checked_at,
                }
            row = result[candidate_id]
            if row["status"] != "needs_review":
                continue
            observation = {"date": day, "time": hour}
            if observation not in row["dates"]:
                row["dates"].append(observation)
                row["dates"].sort(key=lambda v: (v["date"], v["time"] or ""))
            row["last_seen"] = checked_at
    return {"schema_version": 1, "candidates": sorted(result.values(), key=lambda x: x["id"])}


def main() -> None:
    existing = (json.loads(QUEUE.read_text(encoding="utf-8"))
                if QUEUE.exists() else {"schema_version": 1, "candidates": []})
    health = json.loads(HEALTH.read_text(encoding="utf-8"))
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    next_queue = reconcile(existing, health, config)
    _write_atomic(QUEUE, next_queue)
    _write_atomic(PUBLIC, next_queue)
    print(json.dumps({"discovery_candidates": len(next_queue["candidates"])}))


if __name__ == "__main__":
    main()

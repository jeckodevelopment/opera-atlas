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



def reconcile_published_programs(candidates: list[dict], programs: dict) -> None:
    """Retire source observations only when they jointly describe one live bill.

    A mixed opera programme must not produce two independent productions.
    Require a complete matching set of component titles, identical date sets,
    the exact theatre and locality, and no contradictory composer or clock.
    An individual partial observation is never sufficient to retire a bill.
    """
    from collections import defaultdict
    from scripts.publish_catalog_v2 import normalized

    if programs.get("schema_version") != 1 or not isinstance(programs.get("programs"), list):
        raise ValueError("invalid published programs for discovery reconciliation")
    groups = defaultdict(list)
    for candidate in candidates:
        if candidate.get("status") == "needs_review":
            groups[(candidate.get("city"), candidate.get("venue"))].append(candidate)
    resolved = {}
    for program in programs["programs"]:
        components = program.get("components")
        performances = program.get("performances")
        if (not isinstance(components, list) or len(components) < 2
                or not isinstance(performances, list) or not performances):
            continue
        key = (program.get("municipality"), program.get("venue"))
        expected_days = {p.get("local_date") for p in performances}
        if None in expected_days or len(expected_days) != len(performances):
            continue
        expected_components = {
            (normalized(c.get("title", "")), normalized(c.get("composer", "")))
            for c in components if isinstance(c, dict)
        }
        if len(expected_components) != len(components):
            continue
        matches = []
        for candidate in groups[key]:
            dates = candidate.get("dates")
            if not isinstance(dates, list) or not dates:
                continue
            if {d.get("date") for d in dates if isinstance(d, dict)} != expected_days:
                continue
            if len(dates) != len(expected_days):
                continue
            possible = [
                identity for identity in expected_components
                if normalized(candidate.get("title", "")) == identity[0]
                and (candidate.get("composer") is None
                     or normalized(candidate["composer"]) == identity[1])
            ]
            if len(possible) != 1:
                continue
            # A supplied source clock cannot contradict the published ticket.
            if any(d.get("time") is not None and not any(
                   p["local_date"] == d["date"]
                   and isinstance(p.get("starts_at"), str)
                   and p["starts_at"][11:16] == d["time"]
                   for p in performances) for d in dates):
                continue
            matches.append((candidate, possible[0]))
        if len(matches) != len(expected_components) or {
                item[1] for item in matches} != expected_components:
            continue
        ids = frozenset(item[0]["id"] for item in matches)
        for candidate, _ in matches:
            resolved.setdefault(candidate["id"], set()).add(program["id"])
    # Do not close a candidate if more than one bill independently matches.
    for candidate in candidates:
        ids = resolved.get(candidate.get("id"), set())
        if candidate.get("status") == "needs_review" and len(ids) == 1:
            candidate["status"] = "already_catalogued"
            candidate["program_id"] = next(iter(ids))


def reconcile(existing: dict, health: dict, config: dict, programs: dict | None = None) -> dict:
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
    if programs is not None:
        reconcile_published_programs(list(result.values()), programs)
    return {"schema_version": 1, "candidates": sorted(result.values(), key=lambda x: x["id"])}


def main() -> None:
    existing = (json.loads(QUEUE.read_text(encoding="utf-8"))
                if QUEUE.exists() else {"schema_version": 1, "candidates": []})
    health = json.loads(HEALTH.read_text(encoding="utf-8"))
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    programs_path = ROOT / "public" / "catalog" / "programs.json"
    programs = (json.loads(programs_path.read_text(encoding="utf-8"))
                if programs_path.exists() else {"schema_version": 1, "programs": []})
    next_queue = reconcile(existing, health, config, programs)
    _write_atomic(QUEUE, next_queue)
    _write_atomic(PUBLIC, next_queue)
    print(json.dumps({"discovery_candidates": len(next_queue["candidates"])}))


if __name__ == "__main__":
    main()

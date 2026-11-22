"""Operational pipeline health without modifying candidate reconciliation.

Preserves the first *observed* repository publication of each candidate. This is
not the exact deploy timestamp and pre-existing content cannot yield historical
publication latency. Inspect workflow run conclusions separately, without
mistaking an isolated cancellation for lost catalog work.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

from scripts.publish_catalog_v2 import ROOT, payload

CANDIDATES = ROOT / "data/season-index-candidates.json"
EVIDENCE = ROOT / "public/catalog/candidate-publication-evidence.json"
STATE = ROOT / "data/pipeline-publication-observations.json"
OUT = ROOT / "public/catalog/pipeline-operations-health.json"
WORKFLOWS = (
    ("refresh-source-health.yml", "Scansione delle fonti", 3),
    ("collect-candidate-details-fast.yml", "Acquisizione dettagli", 3),
    ("refresh-catalog.yml", "Catalogazione completa", 24),
    ("publish-cached-catalog.yml", "Pubblicazione accelerata", None),
)


def parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (ValueError, TypeError):
        return None


def workflow_health(name: str, runs: list[dict], now: datetime, cadence_hours: int | None) -> dict:
    ordered = sorted(runs, key=lambda r: r.get("created_at") or "", reverse=True)
    recent = [r for r in ordered if (dt := parse(r.get("created_at"))) and now - timedelta(hours=24) <= dt <= now]
    done = [r for r in ordered if r.get("status") == "completed"]
    last_success = next((r for r in done if r.get("conclusion") == "success"), None)
    last_terminal = done[0] if done else None
    running = [r for r in ordered if r.get("status") in ("queued", "in_progress", "pending", "waiting")]
    failed = sum(r.get("conclusion") in ("failure", "timed_out") for r in recent)
    cancelled = sum(r.get("conclusion") == "cancelled" for r in recent)
    recovered_after_cancel = sum(
        r.get("conclusion") == "cancelled" and any(
            x.get("conclusion") == "success" and
            (x.get("created_at") or "") > (r.get("created_at") or "")
            for x in ordered
        ) for r in recent
    )
    last_success_at = parse(last_success.get("updated_at")) if last_success else None
    stale = cadence_hours is not None and (
        last_success_at is None or now - last_success_at > timedelta(hours=max(2 * cadence_hours, cadence_hours + 2))
    )
    latest_unresolved = (
        last_terminal is not None and last_terminal.get("conclusion") != "success"
        and (not last_success or (last_success.get("created_at") or "") < (last_terminal.get("created_at") or ""))
    )
    status = "attention" if stale or latest_unresolved else "running" if running else "ok" if last_success else "unknown"
    return {
        "workflow": name,
        "status": status,
        "cadence_hours": cadence_hours,
        "last_success_at": last_success_at.isoformat(timespec="seconds") if last_success_at else None,
        "last_conclusion": last_terminal.get("conclusion") if last_terminal else None,
        "running_count": len(running),
        "failures_24h": failed,
        "cancelled_24h": cancelled,
        "cancelled_followed_by_success_24h": recovered_after_cancel,
        "cancellation_note": "A subsequent successful run does not prove that every deferred candidate was published.",
        "last_run_url": ordered[0].get("html_url") if ordered else None,
    }


def update_observations(candidates: dict, evidence: dict, previous: dict | None,
                        now: datetime) -> tuple[dict, dict]:
    if candidates.get("schema_version") != 1 or evidence.get("schema_version") != 1:
        raise ValueError("unknown candidate schema")
    stamp = now.isoformat(timespec="seconds")
    first_run = previous is None
    state = {"schema_version": 1, "baseline_at": previous.get("baseline_at", stamp) if previous else stamp,
             "observations": dict(previous.get("observations", {})) if previous else {}}
    rows = {x["candidate_id"]: x for x in evidence.get("candidates", [])}
    current = {x["id"]: x for x in candidates.get("candidates", [])}
    linked_states = {"linked_solo_in_repository", "linked_program_in_repository"}
    linked = 0
    unknown_links = 0
    newly_observed = 0
    latencies = []
    for cid, item in current.items():
        ev = rows.get(cid, {})
        status = ev.get("evidence_status")
        record = state["observations"].get(cid)
        if record is None:
            record = {"first_seen": item.get("first_seen"), "first_observed_at": stamp,
                      "first_observed_catalogued_at": None, "baseline": first_run}
            state["observations"][cid] = record
        if status in linked_states:
            linked += 1
            if record.get("first_observed_catalogued_at") is None:
                record["first_observed_catalogued_at"] = stamp
                if not record.get("baseline"):
                    newly_observed += 1
            # Only post-baseline observations can contribute latency estimates.
            if not record.get("baseline"):
                seen = parse(record.get("first_seen"))
                published = parse(record.get("first_observed_catalogued_at"))
                if seen and published and published >= seen:
                    latencies.append(round((published - seen).total_seconds() / 60, 1))
        elif item.get("status") == "already_catalogued":
            unknown_links += 1
    durations = sorted(latencies)
    metrics = {
        "total_candidates": len(current),
        "linked_in_repository_now": linked,
        "reconciled_without_direct_link": unknown_links,
        "new_catalogue_links_first_observed_this_run": newly_observed,
        "eligible_post_baseline_samples": len(durations),
        "mean_discovery_to_first_observed_catalogue_minutes":
            round(sum(durations) / len(durations), 1) if durations else None,
        "p90_discovery_to_first_observed_catalogue_minutes":
            durations[min(len(durations)-1, int((len(durations)-1)*0.9))] if durations else None,
        "publication_ready_waiting": None,
        "publication_ready_note": "Not measurable: no independently recorded passed publication gate exists; do not equate candidate needs_review with publishable.",
        "latency_note": "Upper bound from first_seen to first observed link in repository, not exact publication time. Historical baseline excluded.",
    }
    return state, metrics


def github_runs(workflow: str, *, token: str, repository: str) -> list[dict]:
    url = f"https://api.github.com/repos/{repository}/actions/workflows/{workflow}/runs?per_page=30"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "opera-atlas-operational-diagnostics"}
    if token:
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers), timeout=18) as response:
        return json.load(response).get("workflow_runs", [])


def build(candidates: dict, evidence: dict, previous: dict | None, runs: dict[str, list[dict]],
          now: datetime) -> tuple[dict, dict]:
    state, metrics = update_observations(candidates, evidence, previous, now)
    workflow_rows = [workflow_health(label, runs.get(filename, []), now, cadence)
                     for filename, label, cadence in WORKFLOWS]
    report = {
        "schema_version": 1,
        "checked_at": now.isoformat(timespec="seconds"),
        "catalog_release_sha256": evidence.get("catalog_release_sha256"),
        "scope": "repository_first_observation_and_github_workflow_runs",
        "discovery_to_repository": metrics,
        "workflows": workflow_rows,
        "workflow_alerts": sum(x["status"] == "attention" for x in workflow_rows),
        "definition": "Source scans and cached publication are independent. Cancelled runs are visible; later success is not proof that all candidates were published.",
    }
    return state, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Do not fetch Actions history")
    args = parser.parse_args()
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    prior = read(STATE) if STATE.exists() else None
    runs = {}
    if not args.offline:
        token = os.getenv("GH_TOKEN", "")
        repo = os.getenv("GITHUB_REPOSITORY", "jeckodevelopment/opera-atlas")
        for filename, _, _ in WORKFLOWS:
            runs[filename] = github_runs(filename, token=token, repository=repo)
    state, report = build(read(CANDIDATES), read(EVIDENCE), prior, runs, now)
    STATE.write_bytes(payload(state))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(payload(report))
    print(json.dumps({"observed": report["discovery_to_repository"],
                      "workflow_alerts": report["workflow_alerts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

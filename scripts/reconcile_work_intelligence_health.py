"""Synchronize identity research diagnostics with persisted candidate decisions.

No network calls or identity inference. The canonical candidate registry and
immutable staging URLs decide whether old identity-research waits are obsolete.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path

from scripts.auto_work_research import (
    HEALTH, INDEX, REGISTRY, reconcile_published_outcomes, _write_atomic
)


def reconcile(health:dict,candidates:dict,registry:dict)->dict:
    if (health.get("schema_version")!=1
            or not isinstance(health.get("outcomes"),list)
            or candidates.get("schema_version")!=1
            or not isinstance(candidates.get("candidates"),list)):
        raise ValueError("invalid identity or candidate diagnostics")
    previous=health["outcomes"]
    next_outcomes=reconcile_published_outcomes(candidates,previous,registry)
    # Preserve a stable timestamp when the report is already synchronized.
    if next_outcomes==previous:
        return health
    return {**health,
            "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "outcomes":next_outcomes}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    health=json.loads(HEALTH.read_text(encoding="utf-8"))
    candidates=json.loads(INDEX.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    updated=reconcile(health,candidates,registry)
    if args.check:
        if updated!=health:raise ValueError("identity research diagnostics stale")
    elif updated!=health:
        _write_atomic(HEALTH,updated)
    print(json.dumps({
        "identity_report_changed":updated!=health,
        "awaiting_official_identity_evidence":sum(
            x.get("status")=="awaiting_official_identity_evidence"
            for x in updated["outcomes"])
    }))


if __name__=="__main__":
    main()

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


def reconcile(health:dict,candidates:dict,registry:dict,programs:dict|None=None)->dict:
    if (health.get("schema_version")!=1
            or not isinstance(health.get("outcomes"),list)
            or candidates.get("schema_version")!=1
            or not isinstance(candidates.get("candidates"),list)):
        raise ValueError("invalid identity or candidate diagnostics")
    previous=health["outcomes"]
    next_outcomes=reconcile_published_outcomes(candidates,previous,registry)
    # A catalogued candidate can reference a shared programme, an older
    # first-party URL, or multiple matching stagings. Do not present it as
    # an *unresearched opera*, but equally do not invent one work_id when
    # the immutable stage linkage is not uniquely proven.
    states={x["id"]:x["status"] for x in candidates["candidates"]}
    next_outcomes=[
        {**item,"status":"catalogued_source_link_unverified"}
        if (item.get("status")=="awaiting_official_identity_evidence"
            and states.get(item.get("candidate_id"))=="already_catalogued")
        else item for item in next_outcomes
    ]
    # Composite programs do not have a single canonical work_id or staging.
    # Link them only through one exact, verified public program source,
    # retaining the program identity instead of inventing a work match.
    programme_rows=(programs or {}).get("programs",[])
    if not isinstance(programme_rows,list):
        raise ValueError("invalid published program feed")
    by_candidate={x["id"]:x for x in candidates["candidates"]}
    resolved=[]
    for item in next_outcomes:
        candidate=by_candidate.get(item.get("candidate_id"),{})
        if (item.get("status")=="catalogued_source_link_unverified"
                and candidate.get("status")=="already_catalogued"):
            matches=[p for p in programme_rows
                     if p.get("source_url")==candidate.get("official_url")
                     and p.get("source_key")==candidate.get("source_key")
                     and isinstance(p.get("id"),str)
                     and len(p.get("components",[]))>=2
                     and bool(p.get("performances"))]
            if len(matches)==1:
                item={**item,"status":"already_catalogued_program",
                      "program_id":matches[0]["id"]}
        resolved.append(item)
    next_outcomes=resolved
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
    program_path=Path(__file__).resolve().parents[1]/"public"/"catalog"/"programs.json"
    programs=json.loads(program_path.read_text(encoding="utf-8"))
    updated=reconcile(health,candidates,registry,programs)
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

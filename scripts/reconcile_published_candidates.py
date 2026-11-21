"""Finalize candidate states in the same import transaction, before publication.

Only verified, generated canonical opera and program feeds can mark a candidate
as already catalogued. Preserve audit history and ensure subsequent refreshes
rebuild the same public feeds without a manual post-import reconciliation.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime,timezone
from scripts.daily_ingest import _write_atomic
from scripts.discover_season_indexes import (
    OUTPUT, PUBLIC, classify, reviewed_source_urls,
)
from scripts.publish_catalog_v2 import ROOT

HEALTH=ROOT/"data"/"candidate-reconciliation-health.json"
AUTO_STATES=frozenset({"needs_review","already_catalogued","excluded_nonopera"})

def verified_secondary_source_urls(manifest:dict, evidence:dict)->set[str]:
    """Recognize complete independently verified second-source theater dates.

    A source only matches an existing circuit production if every scheduled
    performance has independently validated time evidence from that same
    approved official venue URL. Partial or ambiguous observations stay open.
    """
    from scripts.build_verified_catalog import TIME_EVIDENCE_URLS,validate_time_evidence
    validate_time_evidence(manifest,evidence)
    matches=set()
    times=evidence["times"]
    for production in manifest["productions"]:
        days=[day for day,_ in production["dates"]]
        if not days:
            continue
        rows=[times.get(production["key"]+"|"+day) for day in days]
        if any(row is None for row in rows):
            continue
        urls={row["url"] for row in rows}
        if len(urls)!=1:
            continue
        url=next(iter(urls))
        if url in TIME_EVIDENCE_URLS.get(production["key"],set()):
            matches.add(url)
    return matches

def reconcile(candidates:dict,verified_urls:set[str])->tuple[dict,dict]:
    if candidates.get("schema_version")!=1 or not isinstance(candidates.get("candidates"),list):
        raise ValueError("invalid season index candidate registry")
    updated={"schema_version":1,"candidates":[]}
    changes=[]
    for row in candidates["candidates"]:
        entry=row.copy()
        if entry.get("status") in AUTO_STATES:
            now=classify(entry["source_key"],entry["official_url"],verified_urls)
            if now!=entry["status"]:
                changes.append({"candidate_id":entry["id"],"before":entry["status"],"after":now})
            entry["status"]=now
        # Preserve first_seen / last_seen, source and ID for accountability.
        updated["candidates"].append(entry)
    states={}
    for row in updated["candidates"]:
        states[row["status"]]=states.get(row["status"],0)+1
    return updated,{"total":len(updated["candidates"]),"states":states,
                    "changes":changes}

def run(*,check:bool=False):
    original=json.loads(OUTPUT.read_text(encoding="utf-8"))
    from scripts.build_verified_catalog import MANIFEST,TIME_EVIDENCE
    published=reviewed_source_urls()
    if TIME_EVIDENCE.exists():
        manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        times=json.loads(TIME_EVIDENCE.read_text(encoding="utf-8"))
        published.update(verified_secondary_source_urls(manifest,times))
    updated,report=reconcile(original,published)
    if check:
        if updated!=original:
            raise ValueError("discovery queue out of sync with canonical catalog")
        if not PUBLIC.exists() or json.loads(PUBLIC.read_text(encoding="utf-8"))!=updated:
            raise ValueError("public discovery queue out of sync")
    else:
        _write_atomic(OUTPUT,updated)
        _write_atomic(PUBLIC,updated)
        _write_atomic(HEALTH,{"schema_version":1,
            "checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
            **report})
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    print(json.dumps(run(check=args.check),ensure_ascii=False))
if __name__=="__main__":
    main()

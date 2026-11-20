"""Synchronize eight-source registry from real scheduled scans, not manual edits.

Access approval is derived from the approved exact schedules; monitoring
proof comes separately from actual recorded successful runs. The registry
cannot silently claim a source is fully catalogued.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from scripts.publish_catalog_v2 import ROOT
from scripts.daily_ingest import CONFIG as DAILY, HEALTH as DAILY_HEALTH, validate_source_config
from scripts.discover_season_indexes import CONFIG as SEASONS, HEALTH as SEASON_HEALTH, validate_config
from scripts.source_coverage import SOURCES,DOMAINS,hostname
from scripts.daily_ingest import _write_atomic

INDEX_MAP={
    "regio-torino":None,
    "opera-lombardia":None,
    "rossini-opera-festival":None,
    "teatro-alla-scala":"scala-season-2026-27",
    "teatro-la-fenice":"fenice-opera-2026-27",
    "fondazione-arena-verona":"arena-festival-2027",
    "teatro-regio-parma":"parma-opera-2027",
    "teatro-massimo-palermo":"massimo-season-2026-27",
}

def reconcile(registry:dict,daily:dict,season:dict,
              daily_health:dict|None,season_health:dict|None)->dict:
    if set(INDEX_MAP)!=set(DOMAINS) or registry.get("schema_version")!=1:
        raise ValueError("source registry mapping incomplete")
    entries=registry.get("sources")
    if not isinstance(entries,list) or len(entries)!=8 or {x["key"] for x in entries}!=set(DOMAINS):
        raise ValueError("eight primary sources required")
    daily_sources=validate_source_config(daily)
    index_sources=validate_config(season)
    daily_outcomes={x["key"]:x for x in (daily_health or {}).get("sources",[])}
    season_outcomes={x["key"]:x for x in (season_health or {}).get("sources",[])}
    updated=json.loads(json.dumps(registry))
    for entry in updated["sources"]:
        key=entry["key"]
        relevant=[x for x in daily_sources if hostname(x["official_url"]) in DOMAINS[key]]
        indexed=[x for x in index_sources if x["key"]==INDEX_MAP[key]]
        approved=any(x["access_status"]=="approved" for x in relevant+indexed)
        entry["access_status"]="approved" if approved else "pending"
        index_ok=any(x["access_status"]=="approved" and
                     season_outcomes.get(x["key"],{}).get("status")=="success"
                     for x in indexed)
        detail_ok=any(x["access_status"]=="approved" and
                      daily_outcomes.get(x["key"],{}).get("outcome")=="success"
                      for x in relevant)
        entry["monitoring_status"]=(
            "index_verified" if index_ok else
            "detail_verified" if detail_ok else
            "configured_unverified" if approved else "not_started")
        entry["automated_index"]=index_ok
        entry["autonomous_publication_verified"]=False
        # The URL is a user-facing official entry; exact season indexes live
        # in the configured schedule and are not inferred from calendar_url.
    return updated

def run(*,check:bool=False):
    doc=json.loads(SOURCES.read_text(encoding="utf-8"))
    daily=json.loads(DAILY.read_text(encoding="utf-8"))
    season=json.loads(SEASONS.read_text(encoding="utf-8"))
    dh=json.loads(DAILY_HEALTH.read_text(encoding="utf-8")) if DAILY_HEALTH.exists() else None
    sh=json.loads(SEASON_HEALTH.read_text(encoding="utf-8")) if SEASON_HEALTH.exists() else None
    output=reconcile(doc,daily,season,dh,sh)
    if check:
        if output!=doc:raise ValueError("source registry not synced with approved monitoring")
    else:
        _write_atomic(SOURCES,output)
    return output

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    data=run(check=args.check)
    print(json.dumps({"sources":len(data["sources"]),
                      "approved":sum(x["access_status"]=="approved" for x in data["sources"]),
                      "verified_indexes":sum(x["automated_index"] for x in data["sources"])}))

if __name__=="__main__":
    main()

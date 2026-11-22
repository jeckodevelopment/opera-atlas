"""Explicit lifecycle readiness feed for the Opera Atlas diagnostics dashboard.

An evergreen URL is not proof that future seasons are present. This feed
reports implementation capability separately from actual scanned evidence.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"data/season-index-config.json"
POLICY=ROOT/"data/season-lifecycle-policy.json"
HEALTH=ROOT/"data/season-index-health.json"
ROLLOVER_HEALTH=ROOT/"data/season-rollover-health.json"
OUT=ROOT/"public/catalog/season-lifecycle.json"
SUCCESSORS=ROOT/"data/season-successor-coverage.json"

STRATEGIES={"verified_rollover","evergreen_index","legacy_year_bound"}

def build(config:dict,policy:dict,health:dict,rollover_health:dict,
          successor_coverage:dict|None=None)->dict:
    sources=config["sources"]
    plans=policy["sources"]
    if set(plans)!={x["key"] for x in sources}:
        raise ValueError("season lifecycle policy is incomplete")
    if successor_coverage is None:
        successor_coverage=json.loads(SUCCESSORS.read_text(encoding="utf-8"))
    if successor_coverage.get("schema_version")!=1 or not isinstance(
            successor_coverage.get("mappings"),list):
        raise ValueError("invalid successor coverage contract")
    successor_for={}
    for pair in successor_coverage["mappings"]:
        if not isinstance(pair,dict) or set(pair)!={"legacy_source_key","successor_source_key"}:
            raise ValueError("invalid explicit successor mapping")
        legacy,successor=pair["legacy_source_key"],pair["successor_source_key"]
        if (not isinstance(legacy,str) or not isinstance(successor,str)
                or legacy in successor_for or legacy==successor
                or legacy not in plans or successor not in plans
                or plans[legacy]["strategy"]!="legacy_year_bound"
                or plans[successor]["strategy"]!="verified_rollover"):
            raise ValueError("invalid, duplicate or unimplemented historical successor")
        successor_for[legacy]=successor
    checks={x["key"]:x for x in health.get("sources",[])
            if isinstance(x,dict) and isinstance(x.get("key"),str)}
    rollovers={x["key"]:x for x in rollover_health.get("outcomes",[])
               if isinstance(x,dict) and isinstance(x.get("key"),str)}
    rows=[]
    for item in sources:
        key=item["key"]
        strategy=plans[key]["strategy"]
        if strategy not in STRATEGIES:
            raise ValueError("unknown lifecycle strategy")
        check=checks.get(key,{})
        rollover=rollovers.get(key,{})
        next_status=check.get("next_season_status")
        if next_status not in ("verified","unavailable_or_invalid"):
            next_status="not_checked"
        rows.append({
            "source_key":key,
            "index_url":item["url"],
            "strategy":strategy,
            "successor_source_key":successor_for.get(key),
            "legacy_covered_by_successor":key in successor_for,
            "rollover_implemented":strategy=="verified_rollover",
            "future_season_verified":next_status=="verified",
            "next_season_status":next_status,
            "next_season_url":check.get("next_season_url"),
            "next_season_links":check.get("next_season_links",0),
            "current_scan_status":check.get("status","not_checked"),
            "last_attempt_at":check.get("last_attempt_at"),
            "last_success_at":check.get("last_success_at"),
            "last_rollover_status":rollover.get("status","not_checked"),
        })
    counts=Counter(x["strategy"] for x in rows)
    return {
        "schema_version":1,
        "checked_at":health.get("checked_at"),
        "scope":"configured_season_indexes",
        "definition":"Rollover implemented is a code capability, not evidence of next-season availability or exhaustive recite coverage. Evergreen sources still require future-season verification.",
        "total_indexes":len(rows),
        "verified_rollover":counts["verified_rollover"],
        "evergreen_index_unverified":counts["evergreen_index"],
        "legacy_year_bound":counts["legacy_year_bound"],
        "legacy_covered_by_successor":len(successor_for),
        "legacy_still_uncovered":counts["legacy_year_bound"]-len(successor_for),
        "future_seasons_verified":sum(x["future_season_verified"] for x in rows),
        "sources":rows,
    }

def publish(*,check:bool=False)->dict:
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    result=build(read(CONFIG),read(POLICY),read(HEALTH),read(ROLLOVER_HEALTH),read(SUCCESSORS))
    encoded=(json.dumps(result,ensure_ascii=False,sort_keys=True,
                        separators=(",",":"))+"\n").encode("utf-8")
    if check:
        if not OUT.exists() or OUT.read_bytes()!=encoded:
            raise ValueError("season lifecycle feed is out of sync")
    else:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_bytes(encoded)
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    result=publish(check=args.check)
    print(json.dumps({k:result[k] for k in (
        "total_indexes","verified_rollover","evergreen_index_unverified",
        "legacy_year_bound","legacy_covered_by_successor","legacy_still_uncovered","future_seasons_verified")}))

if __name__=="__main__":
    main()

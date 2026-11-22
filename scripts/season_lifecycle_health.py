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
EVERGREEN_AUDIT=ROOT/"data/evergreen-reusability-audit.json"

STRATEGIES={"verified_rollover","evergreen_index","legacy_year_bound"}

def build(config:dict,policy:dict,health:dict,rollover_health:dict,
          successor_coverage:dict|None=None,
          evergreen_audit:dict|None=None)->dict:
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
    if evergreen_audit is None:
        evergreen_audit=json.loads(EVERGREEN_AUDIT.read_text(encoding="utf-8"))
    evergreen_keys={key for key,plan in plans.items()
                    if plan["strategy"]=="evergreen_index"}
    if evergreen_audit.get("schema_version")!=1 or not isinstance(
            evergreen_audit.get("sources"),list):
        raise ValueError("invalid evergreen source audit")
    scopes={"dynamic_category","fixed_production_set","historical_notice"}
    audited={}
    fixed_successors={}
    for record in evergreen_audit["sources"]:
        if (not isinstance(record,dict) or
                set(record) not in ({"source_key","scope","evidence"},
                                    {"source_key","scope","evidence","successor_source_key"}) or
                record["source_key"] in audited or
                record["source_key"] not in evergreen_keys or
                record["scope"] not in scopes or
                not isinstance(record["evidence"],str) or
                not record["evidence"].strip()):
            raise ValueError("invalid or duplicate evergreen audit record")
        audited[record["source_key"]]=record["scope"]
        if "successor_source_key" in record:
            if (record["scope"]!="fixed_production_set" or
                    not isinstance(record["successor_source_key"],str) or
                    not record["successor_source_key"].strip()):
                raise ValueError("only fixed legacy sources may have successors")
            fixed_successors[record["source_key"]]=record["successor_source_key"]
    if set(audited)!=evergreen_keys:
        raise ValueError("every evergreen source requires explicit reusability audit")
    for legacy,successor in fixed_successors.items():
        if (legacy==successor or successor not in plans or
                plans[successor]["strategy"] not in
                {"evergreen_index","verified_rollover"} or
                (successor in audited and audited[successor]!="dynamic_category")):
            raise ValueError("fixed source successor must be a dynamic or rollover source")
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
            "evergreen_reusability":audited.get(key),
            "fixed_source_successor_key":fixed_successors.get(key),
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
    reusability=Counter(x["evergreen_reusability"] for x in rows)
    return {
        "schema_version":1,
        "checked_at":health.get("checked_at"),
        "scope":"configured_season_indexes",
        "definition":"Rollover implemented is a code capability, not evidence of next-season availability or exhaustive recite coverage. Evergreen source classification separately reports fixed-title historical sources with an implemented dynamic successor versus those still requiring migration. Neither is live future-season proof.",
        "total_indexes":len(rows),
        "verified_rollover":counts["verified_rollover"],
        "evergreen_index_unverified":counts["evergreen_index"],
        "evergreen_dynamic_category":reusability["dynamic_category"],
        "evergreen_fixed_production_set":reusability["fixed_production_set"],
        "evergreen_fixed_covered":len(fixed_successors),
        "evergreen_fixed_uncovered":reusability["fixed_production_set"]-len(fixed_successors),
        "evergreen_historical_notice":reusability["historical_notice"],
        "legacy_year_bound":counts["legacy_year_bound"],
        "legacy_covered_by_successor":len(successor_for),
        "legacy_still_uncovered":counts["legacy_year_bound"]-len(successor_for),
        "future_seasons_verified":sum(x["future_season_verified"] for x in rows),
        "sources":rows,
    }

def publish(*,check:bool=False)->dict:
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    result=build(read(CONFIG),read(POLICY),read(HEALTH),read(ROLLOVER_HEALTH),read(SUCCESSORS),read(EVERGREEN_AUDIT))
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
        "evergreen_dynamic_category","evergreen_fixed_production_set","evergreen_historical_notice",
        "evergreen_fixed_covered","evergreen_fixed_uncovered",
        "legacy_year_bound","legacy_covered_by_successor","legacy_still_uncovered","future_seasons_verified")}))

if __name__=="__main__":
    main()

"""Read-only triage of 2026 mass-scan observations and failed indexes.

A matching official source URL and exact date/time is strong evidence a recita
is already catalogued. Existing explicit non-opera exclusions take precedence.
Everything else remains pending review, NOT a missing recita.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit
from scripts.discover_season_indexes import excluded_nonopera

ROOT=Path(__file__).resolve().parents[1]
MASS=ROOT/"public/diagnostics/atlas-2026-mass-scan.json"
CATALOG=ROOT/"data/verified-launch-catalog.json"
OUTPUT=ROOT/"public/diagnostics/atlas-2026-mass-reconciliation.json"


def exact_key(url):
    p=urlsplit(url or "")
    return (p.hostname or "", p.path.rstrip("/"))


def triage(report, catalog):
    published={}
    for p in catalog.get("productions",[]):
        source=exact_key(p.get("source_url"))
        for value in p.get("dates",[]):
            if isinstance(value,list) and value and isinstance(value[0],str):
                published.setdefault((source,value[0]),[]).append(p)
    findings=[]
    for detail in report.get("detail_results",[]):
        source=detail.get("source_url","")
        key=detail.get("source_key","")
        for fact in detail.get("facts",[]):
            day=fact.get("date")
            if excluded_nonopera(key,source):
                status="excluded_by_existing_official_source_policy"
                matches=[]
            else:
                matches=published.get((exact_key(source),day),[])
                status="already_catalogued_source_and_date" if matches else "needs_editorial_reconciliation"
            findings.append({
                "source_key":key,"source_url":source,
                "event_title":fact.get("event_title"),
                "date":day,"starts_at":fact.get("starts_at"),
                "reported_venue":fact.get("venue"),"status":status,
                "catalogued_matches":[{"title":m.get("title"),"venue":m.get("venue"),
                                       "city":m.get("municipality")} for m in matches],
            })
    index_groups={"access_denied":[],"source_unavailable":[],"parser_or_structure":[],"other":[]}
    for row in report.get("index_results",[]):
        if row.get("status")=="scanned":continue
        reason=row.get("reason","unknown")
        category=("access_denied" if reason in ("AccessDenied","SanCarloSecurityChallenge")
                  else "source_unavailable" if reason=="FetchUnavailable"
                  else "parser_or_structure" if reason=="ValueError"
                  else "other")
        index_groups[category].append({"source_key":row.get("source_key"),"reason":reason,
                                       "url":row.get("index_url"),"status":"unverified"})
    return {
        "schema_version":1,"year":2026,
        "source_scan_checked_at":report.get("checked_at"),
        "read_only":True,"catalog_updated":False,
        "observation_counts":dict(sorted(Counter(x["status"] for x in findings).items())),
        "index_failure_counts":{k:len(v) for k,v in index_groups.items()},
        "index_failures":index_groups,
        "observations":findings,
        "warning":"Unmatched is NOT missing: source, venue, work, public audience and showtime require further verification. Source URL exact match does not certify full season coverage."
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=OUTPUT)
    args=parser.parse_args()
    report=triage(json.loads(MASS.read_text(encoding="utf-8")),
                  json.loads(CATALOG.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"observations":report["observation_counts"],
                      "indexes":report["index_failure_counts"]}))

if __name__=="__main__":
    main()

"""Read-only 2026 residual audit: check canonical recite before proposing additions.

Never classify a same-day performance as missing without verifying its work,
venue and published calendar. Differences in clock are conflicts, not additions.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scripts.audit_2026_retrospective_reconciliation import norm

ROOT = Path(__file__).resolve().parents[1]
TRIAGE = ROOT / "public/diagnostics/atlas-2026-editorial-triage.json"
CATALOG = ROOT / "data/verified-launch-catalog.json"
OUTPUT = ROOT / "public/diagnostics/atlas-2026-residual-catalog-check.json"

# These entries are aliases / attributive composer headings *on the source*,
# not permission to merge different opera titles by similarity.
TITLE_PREFIXES = (
    ("giuseppe verdi", "macbeth"),
    ("richard wagner", "der fliegende hollander"),
    ("salvatore passantino", "l esecuzione"),
    ("daniele furlati", "i salvatori della mezzanotte"),
)
# Explicit official same-host source for three performances; no heuristic
# decisions should be applied to unrelated future titles or dates.
OFFICIAL_NONOPERA = {
    ("https://www.tcbo.it/evento/speciale/opera-guccini-2026/", "Opera Guccini"):
    {"days":["2026-10-29","2026-10-30","2026-10-31"],
     "reason":"The Teatro Comunale di Bologna describes the event as a concert-show of Guccini songs, not a staged opera.",
     "official_detail_url":"https://www.tcbo.it/evento/speciale/opera-guccini-2026/"},
}


def canonical_title(value):
    value=norm(html.unescape(value or ""))
    for composer, title in TITLE_PREFIXES:
        if value.startswith(composer+" ") and (title in value or title == "der fliegende hollander"):
            if title == "der fliegende hollander" and "fliegende" not in value:
                continue
            return title
    return value


def catalog_occurrences(catalog):
    rows=[]
    for p in catalog.get("productions", []):
        for d in p.get("dates", []):
            if isinstance(d,list) and len(d)>=1 and isinstance(d[0],str) and d[0].startswith("2026-"):
                rows.append({
                    "date":d[0], "clock":d[1] if len(d)>1 else None,
                    "title":p.get("title"),"venue":p.get("venue"),
                    "city":p.get("municipality"),"source_url":p.get("source_url"),
                })
    return rows


def check(triage, catalog):
    if (triage.get("year") != 2026 or triage.get("read_only") is not True
            or triage.get("catalog_updated") is not False
            or triage.get("complete_seasons_certified") != 0):
        raise ValueError("Invalid source triage")
    if len(triage.get("review_groups",[])) != triage.get("event_groups"):
        raise ValueError("Incomplete triage")
    rows=catalog_occurrences(catalog)
    results=[]
    for g in triage["review_groups"]:
        title=canonical_title(g["event_title"])
        venue=norm(g.get("venue"))
        same_day=[p for p in rows if p["date"]==g["date"]
                  and canonical_title(p["title"])==title
                  and venue and norm(p.get("venue"))==venue]
        # Published records can be on a separately corroborated detail URL,
        # while the audit source is a generic theatre index.
        # Same day, work, venue is strong evidence against an automatic
        # "missing" claim but is not proof of exact time matching.
        if same_day:
            matches=[{"title":p["title"],"clock":p["clock"],
                      "source_url":p["source_url"],"venue":p["venue"]}
                     for p in same_day]
            if g.get("time") is not None and any(g["time"]==p["clock"] for p in same_day):
                status="catalog_same_work_day_venue_exact_clock"
            else:
                status="catalog_same_work_day_venue_clock_discrepancy"
            evidence=None
        else:
            matches=[]
            evidence=None
            status="requires_official_genre_and_catalog_review"
            for (url, work), decision in OFFICIAL_NONOPERA.items():
                if (g["event_title"]==work and url in g.get("source_urls",[])
                        and g["date"] in decision["days"]):
                    status="official_nonopera_source_scoped"
                    evidence=decision
                    break
        results.append({
            "date":g["date"],"title":g["event_title"],"time":g.get("time"),
            "venue":g.get("venue"),"source_key":g["source_key"],
            "source_urls":g["source_urls"],"triage_bucket":g["bucket"],
            "status":status,"catalog_matches":matches,
            "official_nonopera_evidence":evidence,
            "automatic_publication":False,"automatic_exclusion":False,
        })
    counts=dict(sorted(Counter(r["status"] for r in results).items()))
    by_source={}
    for row in results:
        by_source.setdefault(row["source_key"],Counter())[row["status"]]+=1
    return {
        "schema_version":1,"year":2026,"generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "read_only":True,"catalog_updated":False,"complete_seasons_certified":0,
        "input_event_groups":len(results),"counts":counts,
        "by_source":{k:dict(sorted(v.items())) for k,v in sorted(by_source.items())},
        "observations":results,
        "warning":"Matching canonical title+day+venue is not proof that the reported clock is correct; preserve conflicts. Any non-opera decision is source-scoped. Other cases need primary-source review. No automatic publication.",
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=OUTPUT)
    args=parser.parse_args()
    result=check(json.loads(TRIAGE.read_text(encoding="utf-8")),
                 json.loads(CATALOG.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("RESIDUAL_2026_COUNTERS "+json.dumps(result["counts"],ensure_ascii=False))
    for r in result["observations"]:
        if r["status"]=="catalog_same_work_day_venue_clock_discrepancy":
            print("RESIDUAL_2026_TIME_REVIEW "+json.dumps({
                "date":r["date"],"title":r["title"],"time":r["time"],
                "catalog":r["catalog_matches"],"source":r["source_urls"]
            },ensure_ascii=False))


if __name__=="__main__":
    main()

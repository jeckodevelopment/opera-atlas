"""Offline comparison of 2026 H1 source-credited recite with Atlas catalog.

This does not attest whole-season coverage and cannot publish. Preserve work,
source URL, local performance date/time and separate venue and audience review.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts.audit_2026_retrospective_reconciliation import norm, url_key, catalog_rows

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"public/diagnostics/atlas-2026-jan-jun-official-archive.json"
CATALOG=ROOT/"data/verified-launch-catalog.json"
PROGRAMS=ROOT/"public/catalog/programs.json"
HISTORICAL=ROOT/"data/historical-2026-official-evidence.json"
VENUES=ROOT/"data/venue-directory.json"
OUTPUT=ROOT/"public/diagnostics/atlas-2026-jan-jun-reconciliation.json"

# Exact genre/audience alerts: these are *review flags*, not automatic exclusions.
SCOPE_REVIEW={
    "il piccolo principe",
    "piccolo orso e la montagna di ghiaccio",
}

def reconcile_first_half(scan, catalog, programs, historical, venues):
    if scan.get("year")!=2026 or scan.get("read_only") is not True:
        raise ValueError("first half source diagnostics must be read-only 2026")
    by_venue_id={v["id"]:v for v in venues.get("venues",[])}
    published=catalog_rows(catalog,programs,historical)
    by_source=defaultdict(list)
    by_title_date=defaultdict(list)
    for record in published:
        by_source[(url_key(record["source_url"]),record["date"])].append(record)
        by_title_date[(norm(record["title"]),record["date"])].append(record)
    output=[]
    seen=set()
    for fact in scan.get("observations",[]):
        day=fact.get("date")
        if not isinstance(day,str) or not ("2026-01-01"<=day<"2026-07-01"):
            raise ValueError("observation outside first semester 2026")
        vid=fact.get("venue_id_candidate")
        if vid not in by_venue_id or not url_key(fact.get("official_url")):
            raise ValueError("unrecognized venue or source in 2026 evidence")
        title=norm(fact.get("event_title"))
        hour=(fact.get("starts_at") or "")[11:16]
        if not title or len(hour)!=5 or hour[2]!=":":
            # Preserve unverified timestamp separately, not as a recita.
            status="missing_exact_showtime_review"
        else:
            status=None
        key=(vid,url_key(fact["official_url"]),day,hour,title)
        if key in seen:
            continue
        seen.add(key)
        direct=[x for x in by_source[(url_key(fact["official_url"]),day)]
                if norm(x["title"])==title and x["time"]==hour]
        possible=[x for x in by_title_date[(title,day)]
                  if x["time"]==hour and norm(x["city"])==norm(by_venue_id[vid]["city"])]
        if status is None:
            if direct and any(x["origin"]!="official_archive_diagnostic" for x in direct):
                status="already_in_public_catalog"
            elif direct:
                status="already_in_approved_historical_evidence"
            elif possible:
                status="possible_alias_or_source_duplicate_review"
            elif title in SCOPE_REVIEW:
                status="audience_and_format_review"
            else:
                status="source_credited_not_in_reviewed_catalog"
        output.append({
            "venue_id":vid,"city":by_venue_id[vid]["city"],
            "venue_candidate":fact.get("venue"),"title":fact.get("event_title"),
            "composer":fact.get("composer"),
            "date":day,"time":hour or None,"source_url":fact["official_url"],
            "status":status,
            "public_catalog_updated":False,
            "match_count":len(direct),"possible_same_city_match_count":len(possible),
            "editorial_note":"Not automatically publishable; verify general audience, aliases, staging and official cancellations.",
        })
    counts=dict(sorted(Counter(x["status"] for x in output).items()))
    by_venue_month=defaultdict(lambda:Counter())
    for x in output:
        by_venue_month[(x["venue_id"],x["date"][:7])][x["status"]]+=1
    coverage=[]
    for v in venues.get("venues",[]):
        for month in range(1,7):
            ym=f"2026-{month:02d}"
            observed=by_venue_month[(v["id"],ym)]
            coverage.append({
                "venue_id":v["id"],"venue":v["name"],"city":v.get("city"),
                "month":ym,"official_source_observations":sum(observed.values()),
                "counts":dict(observed),
                "complete_month_verified":False,
            })
    return {
        "schema_version":1,"year":2026,"period":"2026-01/2026-06",
        "source_checked_at":scan.get("checked_at"),
        "read_only":True,"catalog_updated":False,
        "complete_seasons_certified":0,
        "source_observations":len(scan.get("observations",[])),
        "unique_reconciled":len(output),
        "status_counts":counts,
        "monthly_venue_coverage":coverage,
        "observations":output,
        "warning":"Officially credited showtimes not in the reviewed launch manifest are NOT automatically published missing performances. Verify exclusions, venue, audience, edition and work identity.",
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=OUTPUT)
    a=parser.parse_args()
    def read(path):return json.loads(path.read_text(encoding="utf-8"))
    report=reconcile_first_half(read(INPUT),read(CATALOG),read(PROGRAMS),
                                read(HISTORICAL),read(VENUES))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"observed":report["source_observations"],
                      "reconciled":report["unique_reconciled"],
                      "statuses":report["status_counts"]},ensure_ascii=False))
if __name__=="__main__":
    main()
